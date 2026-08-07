import os

from app.core.config import settings

MAX_ITERATIONS = int(getattr(settings, "AGENT_MAX_ITERATIONS", 8))
TOKEN_BUDGET = int(getattr(settings, "AGENT_TOKEN_BUDGET", 10000))
CHECKPOINT_DB = getattr(
    settings, "AGENT_CHECKPOINT_DB", os.path.join("data", "langgraph_checkpoints.db")
)
