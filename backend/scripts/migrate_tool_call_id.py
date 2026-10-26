"""Phase 4 一次性迁移:agent_tool_calls 增加 tool_call_id 列 + 会话内唯一索引(幂等)。

为什么要它：工具审计原先只靠主键 uuid5(session_id, tool_call_id) 保证幂等，
主键生成方式一旦变化（或并发重放）就可能写出两行同一调用。库里再落一道
(session_id, tool_call_id) 唯一索引，才叫"约束"，而不是"约定"。

SQLite 不能给已有表优雅补列/补约束，故沿用 scripts/migrate_agent_route.py 的做法。

运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\migrate_tool_call_id.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic
from app.db.session import SessionLocal  # noqa: E402

from sqlalchemy import text  # noqa: E402

db = SessionLocal()
try:
    cols = [row[1] for row in db.execute(text("PRAGMA table_info(agent_tool_calls)")).fetchall()]
    if "tool_call_id" in cols:
        print("列已存在,跳过加列")
    else:
        db.execute(text("ALTER TABLE agent_tool_calls ADD COLUMN tool_call_id VARCHAR(64)"))
        db.commit()
        print("已添加 agent_tool_calls.tool_call_id")

    indexes = [row[1] for row in db.execute(text("PRAGMA index_list(agent_tool_calls)")).fetchall()]
    if "uq_agent_tool_calls_session_tool_call" in indexes:
        print("唯一索引已存在,跳过")
    else:
        dup = db.execute(
            text(
                "SELECT COUNT(*) FROM ("
                " SELECT session_id, tool_call_id FROM agent_tool_calls"
                " WHERE tool_call_id IS NOT NULL"
                " GROUP BY session_id, tool_call_id HAVING COUNT(*) > 1)"
            )
        ).scalar()
        if dup:
            # 有重复时不静默建索引失败：先人工确认，避免迁移把审计数据改坏
            print(f"[中止] 发现 {dup} 组重复 (session_id, tool_call_id)，请先人工核对再迁移")
            sys.exit(1)
        db.execute(
            text(
                "CREATE UNIQUE INDEX uq_agent_tool_calls_session_tool_call"
                " ON agent_tool_calls (session_id, tool_call_id)"
            )
        )
        db.commit()
        print("已创建唯一索引 uq_agent_tool_calls_session_tool_call")
finally:
    db.close()
