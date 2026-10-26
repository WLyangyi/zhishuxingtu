"""Phase 4 一次性迁移:新建 agent_tool_artifacts(工具结果 offload 原文存档)。

幂等:CREATE TABLE IF NOT EXISTS,重复执行只打印跳过。
运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_tool_artifacts.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS agent_tool_artifacts (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    session_id VARCHAR(36),
    tool_call_id VARCHAR(64),
    tool_name VARCHAR(100),
    content TEXT,
    length INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
)
"""

db = SessionLocal()
try:
    existing = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_tool_artifacts'")
    ).fetchall()
    if existing:
        print("表已存在,跳过:agent_tool_artifacts")
    else:
        db.execute(text(DDL))
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_agent_tool_artifacts_session "
                "ON agent_tool_artifacts (session_id, created_at)"
            )
        )
        db.commit()
        print("已创建 agent_tool_artifacts(+ 索引)")
finally:
    db.close()
