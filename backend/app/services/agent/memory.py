"""M4 长期记忆：LangGraph Store + SQLite user_preferences。

InMemoryStore 为运行时跨线程共享层，user_preferences 表负责重启后的持久化；
每次读取会把数据库记录同步回 Store，因此云服务或进程重启都不会丢偏好。
"""
from typing import Dict, Optional

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from sqlalchemy.orm import Session

from app.models.agent_session import UserPreference

_memory_store = InMemoryStore()


def get_memory_store() -> InMemoryStore:
    return _memory_store


def preference_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "preferences")


def list_preferences(db: Session, user_id: str) -> Dict[str, str]:
    rows = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id)
        .order_by(UserPreference.preference_key.asc())
        .all()
    )
    return {row.preference_key: row.preference_value for row in rows}


def sync_preferences_to_store(
    db: Session,
    user_id: str,
    store: Optional[BaseStore] = None,
) -> Dict[str, str]:
    target = store or get_memory_store()
    preferences = list_preferences(db, user_id)
    namespace = preference_namespace(user_id)
    for key, value in preferences.items():
        target.put(namespace, key, {"value": value})
    return preferences


def upsert_preference(
    db: Session,
    user_id: str,
    key: str,
    value: str,
    store: Optional[BaseStore] = None,
) -> UserPreference:
    normalized_key = key.strip()
    row = (
        db.query(UserPreference)
        .filter(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == normalized_key,
        )
        .first()
    )
    if row:
        row.preference_value = value.strip()
    else:
        row = UserPreference(
            user_id=user_id,
            preference_key=normalized_key,
            preference_value=value.strip(),
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    (store or get_memory_store()).put(
        preference_namespace(user_id), normalized_key, {"value": row.preference_value}
    )
    return row


def delete_preference(
    db: Session,
    user_id: str,
    key: str,
    store: Optional[BaseStore] = None,
) -> bool:
    row = (
        db.query(UserPreference)
        .filter(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == key,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    (store or get_memory_store()).delete(preference_namespace(user_id), key)
    return True


def get_preference_context(user_id: str, store: Optional[BaseStore] = None) -> str:
    """返回可注入 system prompt 的长期偏好文本，失败时静默为空。"""
    if not user_id:
        return ""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        preferences = sync_preferences_to_store(db, user_id, store)
        if not preferences:
            return ""
        return "\n".join(f"- {key}: {value}" for key, value in preferences.items())
    except Exception:
        return ""
    finally:
        db.close()
