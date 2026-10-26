"""Phase 4 一次性迁移:agent_sessions 增加会话用量两列(SQLite 不支持优雅加列,幂等处理)。

运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_session_usage.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

COLUMNS = (
    ("total_tokens", "INTEGER DEFAULT 0"),
    ("total_cost_cny", "FLOAT DEFAULT 0"),
)

db = SessionLocal()
try:
    cols = [row[1] for row in db.execute(text("PRAGMA table_info(agent_sessions)")).fetchall()]
    for name, ddl in COLUMNS:
        if name in cols:
            print(f"列已存在,跳过:{name}")
            continue
        db.execute(text(f"ALTER TABLE agent_sessions ADD COLUMN {name} {ddl}"))
        db.commit()
        print(f"已添加 agent_sessions.{name}")
finally:
    db.close()
