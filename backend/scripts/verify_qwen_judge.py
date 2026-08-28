# -*- coding: utf-8 -*-
"""
M2-3 验证:确认 qwen3.7-max 独立裁判可用(普通对话 + 结构化输出 function_calling)。

用法:
    .venv\\Scripts\\python.exe scripts/verify_qwen_judge.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim: str = Field(description="答案中的一句事实声明")
    grounded: bool = Field(description="该声明是否能从检索证据中找到出处")


class FaithfulnessGrade(BaseModel):
    score: float = Field(ge=0, le=1, description="faithfulness 分数 0-1")
    claims: list[Claim] = Field(default_factory=list)


def get_judge_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.QWEN_JUDGE_MODEL or "qwen3.7-max-2026-06-08",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0,
        # P16: qwen 裁判默认 thinking mode 拒绝强制 tool_choice(400),必须显式关思考
        extra_body={"enable_thinking": False},
    )


def main() -> int:
    if not settings.DASHSCOPE_API_KEY:
        print("[失败] 缺 DASHSCOPE_API_KEY")
        return 1

    llm = get_judge_llm()
    checks = []

    # 1. 普通对话可用
    try:
        r = llm.invoke("回复 OK 两个英文字母即可")
        text = (r.content or "").strip()
        checks.append(("普通对话可用", "OK" in text.upper(), text[:50]))
    except Exception as e:
        checks.append(("普通对话可用", False, str(e)[:120]))

    # 2. 结构化输出（faithfulness 裁判需要逐句判 grounded）
    try:
        structured = llm.with_structured_output(FaithfulnessGrade, method="function_calling")
        out = structured.invoke(
            "答案：北京是中国的首都。证据：<docs>北京是中国的首都</docs>。"
            "请把答案拆成事实声明并判断每条是否 grounded 于证据。"
        )
        ok = isinstance(out, FaithfulnessGrade) and 0 <= out.score <= 1 and out.claims
        checks.append(("结构化输出(function_calling)", ok, f"score={getattr(out, 'score', None)}"))
    except Exception as e:
        checks.append(("结构化输出(function_calling)", False, str(e)[:200]))

    all_ok = True
    for name, ok, detail in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
        all_ok = all_ok and ok

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\n{'全部通过' if all_ok else '存在失败'} ({passed}/{len(checks)})")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
