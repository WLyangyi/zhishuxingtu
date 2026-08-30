"""M7.4 一次性迁移:agent_sessions 增加 agent_route 列(SQLite 不支持优雅加列重跑,幂等处理)。

运行方式(backend 目录下):
  $env:DEBUG='true'; .venv\\Scripts\\python.exe scripts\\migrate_agent_route.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

db = SessionLocal()
try:
    cols = [row[1] for row in db.execute(text("PRAGMA table_info(agent_sessions)")).fetchall()]
    if "agent_route" in cols:
        print("列已存在,跳过")
    else:
        db.execute(text("ALTER TABLE agent_sessions ADD COLUMN agent_route VARCHAR(32) DEFAULT ''"))
        db.commit()
        print("已添加 agent_sessions.agent_route")
finally:
    db.close()
