"""M7.0 临时探针:探测 DashScope 各模型免费额度状态(仅打印 OK/FAIL,不打印任何密钥)。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

from openai import OpenAI  # noqa: E402

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

MODELS = [
    ("baseline LLM", settings.OPENAI_MODEL),
    ("judge", settings.QWEN_JUDGE_MODEL),
    ("embedding", getattr(settings, "QWEN_EMBEDDING_MODEL", "qwen3.7-text-embedding")),
]

for label, model in MODELS:
    try:
        if "embedding" in label.lower():
            client.embeddings.create(model=model, input="探针")
        else:
            client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=1
            )
        print(f"[OK]   {label}: {model}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {label}: {model} -> {str(exc)[:140]}")
