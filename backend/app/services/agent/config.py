import os

from app.core.config import settings

MAX_ITERATIONS = int(getattr(settings, "AGENT_MAX_ITERATIONS", 8))
TOKEN_BUDGET = int(getattr(settings, "AGENT_TOKEN_BUDGET", 10000))
MAX_HISTORY_MESSAGES = int(getattr(settings, "AGENT_MAX_HISTORY_MESSAGES", 24))
CHECKPOINT_DB = getattr(
    settings, "AGENT_CHECKPOINT_DB", os.path.join("data", "langgraph_checkpoints.db")
)
# M7 A′ 多 Agent 图开关(false=单 Agent 图回退位)
MULTI_AGENT = bool(getattr(settings, "AGENT_MULTI_AGENT", False))
