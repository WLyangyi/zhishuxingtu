# -*- coding: utf-8 -*-
"""三期 3.1 一次性迁移:agent_tool_calls 表加 operation_id 列 + 索引。

operation_id 是业务级幂等键(session+tool_name+args 哈希),驱动
planned→succeeded/failed 生命周期,断流恢复时按它查 query_result 核对副作用。

幂等:ALTER TABLE ADD COLUMN 用 PRAGMA 探测列是否已存在,重复执行只打印跳过。
运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_operation_id.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402


def _has_column(db, table: str, column: str) -> bool:
    cols = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(c[1] == column for c in cols)


def _has_index(db, name: str) -> bool:
    idx = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": name},
    ).fetchall()
    return bool(idx)


def ensure_operation_id(db):
    """加列 + 索引;已存在则跳过。返回是否本次新建列。"""
    if not _has_column(db, "agent_tool_calls", "operation_id"):
        db.execute(text("ALTER TABLE agent_tool_calls ADD COLUMN operation_id VARCHAR(128)"))
        print("已添加列:agent_tool_calls.operation_id")
        created = True
    else:
        print("列已存在,跳过:operation_id")
        created = False
    if not _has_index(db, "idx_agent_tool_calls_operation"):
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_operation "
                "ON agent_tool_calls (session_id, operation_id)"
            )
        )
        print("已创建索引:idx_agent_tool_calls_operation")
    else:
        print("索引已存在,跳过:idx_agent_tool_calls_operation")
    db.commit()
    return created


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ensure_operation_id(db)
    finally:
        db.close()
