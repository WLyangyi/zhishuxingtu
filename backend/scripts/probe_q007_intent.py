"""M7.0 临时探针:q007 分类随机性验证(假设:run1 的 direct_answer 误路由是 M6 既有噪声)。"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402  P11: 先缓存健康 pydantic

QUESTION = "安装克劳德code之前需要先安装什么？"  # q007,run1 recall 0.0 疑似被误路由 direct_answer
N = 5

state = {"question": QUESTION, "thoughts": []}

# intent_classify 内部依赖 get_deepseek_provider,直接调用即可(进程内)
from app.services.agent.nodes import intent_classify  # noqa: E402

results = []
for i in range(N):
    out = intent_classify(dict(state))
    results.append(out["intent"])
    print(f"  run{i + 1}: {out['intent']} | {out['thoughts'][-1]['content'][:80]}")

print(f"\n分布: {dict(Counter(results))}")
