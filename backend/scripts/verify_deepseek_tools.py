# -*- coding: utf-8 -*-
"""
M1-1: 验证 DeepSeek 官方通道的工具调用契约。

用法:
    .venv\\Scripts\\python.exe scripts/verify_deepseek_tools.py

4 项检查(全过才继续,任一失败 → 停下反馈):
  1. 模型可用: 简单 chat 完成(thinking 显式关闭)
  2. 工具 schema 被接受: bind_tools 后调用,不报 schema 校验错
  3. 返回的 function.arguments 可 json.loads
  4. with_structured_output(PydanticModel) 可用(三查节点前置条件)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

from langchain_openai import ChatOpenAI  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

MODEL = settings.DEEPSEEK_MODEL or "deepseek-v4-flash"
BASE_URL = settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com"
THINKING_DISABLED = {"thinking": {"type": "disabled"}}


def make_llm():
    if not settings.DEEPSEEK_API_KEY:
        print("[失败] DEEPSEEK_API_KEY 未配置。")
        sys.exit(1)
    return ChatOpenAI(
        model=MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=BASE_URL,
        temperature=0,
        max_tokens=600,
        extra_body=THINKING_DISABLED,
    )


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}: 晴,26°C"


class GradeModel(BaseModel):
    score: int = Field(description="相关性打分 0-10")
    reason: str = Field(description="判断理由")


def check_model(llm) -> bool:
    print("\n[1/4] 模型可用(简单 chat 完成) ...")
    try:
        resp = llm.invoke("只回复两个字:正常")
        text = getattr(resp, "content", "")
        print(f"  回复: {text[:80]!r}")
        return bool(text)
    except Exception as e:
        print(f"  [失败] {type(e).__name__}: {e}")
        return False


def check_tool_schema(llm) -> bool:
    print("\n[2/4] 工具 schema 被接受(bind_tools 调用) ...")
    try:
        bound = llm.bind_tools([get_weather])
        resp = bound.invoke("北京天气怎么样?请调用工具查询。")
        tools = getattr(resp, "tool_calls", None) or []
        print(f"  tool_calls: {len(tools)} 个")
        for tc in tools:
            print(f"     name={tc.get('name')} args={json.dumps(tc.get('args', {}), ensure_ascii=False)}")
        return len(tools) > 0
    except Exception as e:
        print(f"  [失败] {type(e).__name__}: {e}")
        return False


def check_args_parseable(llm) -> bool:
    print("\n[3/4] function.arguments 可 json.loads ...")
    try:
        bound = llm.bind_tools([get_weather])
        resp = bound.invoke("请调用 get_weather 查询上海的天气。")
        tools = getattr(resp, "tool_calls", None) or []
        if not tools:
            print("  [失败] 模型没返回工具调用")
            return False
        tc = tools[0]
        args = tc.get("args")
        json.dumps(args)  # args 已是 dict,验证可序列化
        print(f"  args 可解析: {json.dumps(args, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"  [失败] {type(e).__name__}: {e}")
        return False


def check_structured_output(llm) -> bool:
    print("\n[4/4] with_structured_output(Pydantic) 可用 ...")
    # DeepSeek V4 官方通道不支持 response_format(JSON mode)。
    # 必须用 function_calling 方法:底层是强制 tool_choice 指定 schema 函数,不走 response_format。
    for method in ("function_calling",):
        try:
            structured = llm.with_structured_output(GradeModel, method=method)
            result = structured.invoke(
                "这段文本和问题相关吗: 问题='Python 是什么', 文本='Python 是一种编程语言'"
            )
            print(f"  method={method}: score={result.score}, reason={result.reason!r}")
            return result is not None
        except Exception as e:
            print(f"  [失败] method={method}: {type(e).__name__}: {e}")
    return False


def main() -> int:
    print(f"DeepSeek model: {MODEL}")
    print(f"Base URL: {BASE_URL}")
    print(f"thinking: disabled")
    print("=" * 50)

    llm = make_llm()

    results = [
        check_model(llm),
        check_tool_schema(llm),
        check_args_parseable(llm),
        check_structured_output(llm),
    ]

    print("\n" + "=" * 50)
    if all(results):
        print("[M1-1] 4 项全部通过。可以继续开发 agent。")
        return 0
    else:
        print(f"[M1-1] {results.count(True)}/4 通过,未全部通过。按计划停下,处理后再继续。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
