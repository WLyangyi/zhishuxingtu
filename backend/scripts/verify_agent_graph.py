# -*- coding: utf-8 -*-
"""
M1-6 验证:编译 LangGraph 并跑一条完整 ReAct + 三查链路。

用法:
    .venv\\Scripts\\python.exe scripts/verify_agent_graph.py [--question "你的问题"]

默认演示:多跳检索"5月10日有哪些科技产品发布?"。
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="5月10日有哪些科技产品发布?")
    args = parser.parse_args()

    from app.services import init_hybrid_search, init_vector_store

    init_vector_store(settings.FAISS_INDEX_PATH)
    init_hybrid_search()

    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
    finally:
        db.close()
    if not user:
        print("[失败] 数据库没有用户,无法设置工具上下文。")
        return 1

    from app.services.tools.context import ToolContext, set_tool_context

    set_tool_context(ToolContext(user_id=user.id, session_id="verify-sess"))

    from app.services.agent.graph import build_input, get_graph

    graph = get_graph()
    print("graph compiled OK\n")
    print(f"问题: {args.question}\n")

    thread_id = f"m1verify-{int(time.time())}"
    input_data = build_input(args.question, session_id="verify-sess", user_id=user.id)
    final_answer = ""
    for step in graph.stream(input_data, config={"configurable": {"thread_id": thread_id}}):
        for node, v in step.items():
            thoughts = v.get("thoughts") or []
            for th in thoughts:
                print(f"[{node}] {th.get('type')}: {str(th.get('content'))[:120]}")
            if v.get("answer"):
                final_answer = v["answer"]

    final_values = graph.get_state({"configurable": {"thread_id": thread_id}}).values or {}
    print(f"[意图] {final_values.get('intent', 'knowledge')}\n")

    print("\n" + "=" * 50)
    print(f"[最终答案]\n{final_answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
