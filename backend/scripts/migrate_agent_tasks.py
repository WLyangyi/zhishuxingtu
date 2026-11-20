"""二期 2.1 一次性迁移:新建 agent_tasks 表(task 分层地基)。

核心约束:
- 部分唯一索引 `uq_agent_tasks_active_per_session`:同一会话同一时刻仅一个 active
  任务(WHERE status='active');completed/cancelled/archived 不受限。
- phase(执行阶段)与 status(生命周期)职责分离,两列独立。
- core_intent 下沉字段(goal/constraints/acceptance_criteria/intent_version/
  intent_versions)与 depends_on 一并建好,为 2.2/2.3/2.5 铺路,避免二次 ALTER。

幂等:CREATE TABLE/INDEX IF NOT EXISTS,重复执行只打印跳过。
运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_agent_tasks.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS agent_tasks (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    session_id VARCHAR(36),
    user_id VARCHAR(36),
    title VARCHAR(500) DEFAULT '',
    goal TEXT,
    constraints TEXT,
    acceptance_criteria TEXT,
    intent_version INTEGER DEFAULT 0,
    intent_versions TEXT,
    phase VARCHAR(32) DEFAULT 'clarify',
    status VARCHAR(32) DEFAULT 'active',
    depends_on VARCHAR(36),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
)
"""

INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_tasks_session_created "
    "ON agent_tasks (session_id, created_at)"
)

PARTIAL_UNIQUE_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_tasks_active_per_session "
    "ON agent_tasks (session_id) WHERE status='active'"
)


def ensure_agent_tasks_table(db):
    """建表 + 索引;已存在则跳过。返回是否本次新建。"""
    existing = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_tasks'")
    ).fetchall()
    if existing:
        print("表已存在,跳过:agent_tasks")
        return False
    db.execute(text(DDL))
    db.execute(text(INDEX_SQL))
    db.execute(text(PARTIAL_UNIQUE_SQL))
    db.commit()
    print("已创建 agent_tasks(+ 索引 + 部分唯一索引)")
    return True


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ensure_agent_tasks_table(db)
    finally:
        db.close()
