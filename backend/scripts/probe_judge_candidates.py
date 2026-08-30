"""M7.2 临时探针:候选裁判模型免费额度状态(为 run2 找可用裁判)。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

from openai import OpenAI  # noqa: E402

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

CANDIDATES = [
    "qwen3.7-plus",
    "qwen3.7-flash",
    "qwen-turbo",
    "qwen-plus",
]

for model in CANDIDATES:
    try:
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=1
        )
        print(f"[OK]   {model}")
    except Exception as exc:  # noqa: BLE001
        reason = "Free quota exhausted" if "Free quota" in str(exc) else str(exc)[:80]
        print(f"[FAIL] {model} -> {reason}")
