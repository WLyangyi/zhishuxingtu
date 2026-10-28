"""Phase 4 一次性迁移:notes 增加 idempotency_key 列与 (user_id, idempotency_key) 唯一索引。

SQLite 不支持优雅加列,脚本按幂等方式执行:列/索引已存在就跳过。

运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_note_idempotency.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

db = SessionLocal()
try:
    cols = [row[1] for row in db.execute(text("PRAGMA table_info(notes)")).fetchall()]
    if "idempotency_key" in cols:
        print("列已存在,跳过:notes.idempotency_key")
    else:
        db.execute(text("ALTER TABLE notes ADD COLUMN idempotency_key VARCHAR(200)"))
        db.commit()
        print("已添加 notes.idempotency_key")

    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_notes_user_idempotency "
            "ON notes(user_id, idempotency_key)"
        )
    )
    db.commit()
    print("唯一索引 uq_notes_user_idempotency 就绪")
finally:
    db.close()
