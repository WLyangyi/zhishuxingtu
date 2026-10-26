import os

from app.core.config import settings

MAX_ITERATIONS = int(getattr(settings, "AGENT_MAX_ITERATIONS", 8))
TOKEN_BUDGET = int(getattr(settings, "AGENT_TOKEN_BUDGET", 10000))
MAX_SEARCHES_PER_TURN = int(getattr(settings, "AGENT_MAX_SEARCHES_PER_TURN", 4))
# Phase 4:单次工具调用硬超时 + 同工具失败熔断阈值
TOOL_TIMEOUT_SECONDS = float(getattr(settings, "AGENT_TOOL_TIMEOUT_SECONDS", 30.0))
MAX_TOOL_FAILURES = int(getattr(settings, "AGENT_MAX_TOOL_FAILURES", 2))
# Phase 4:工具结果 offload 阈值(字符数),超过则全文落库、消息只留压缩预览
ARTIFACT_THRESHOLD_CHARS = int(getattr(settings, "AGENT_ARTIFACT_THRESHOLD_CHARS", 4000))
MAX_HISTORY_MESSAGES = int(getattr(settings, "AGENT_MAX_HISTORY_MESSAGES", 24))
CHECKPOINT_DB = getattr(
    settings, "AGENT_CHECKPOINT_DB", os.path.join("data", "langgraph_checkpoints.db")
)
# M7 A′ 多 Agent 图开关(false=单 Agent 图回退位)
MULTI_AGENT = bool(getattr(settings, "AGENT_MULTI_AGENT", False))
