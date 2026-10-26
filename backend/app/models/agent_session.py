from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.db.base import Base, TimestampMixin, generate_uuid


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_sessions"
    __table_args__ = (Index("idx_agent_sessions_user_updated", "user_id", "updated_at"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)  # = LangGraph thread_id
    user_id = Column(String(36), index=True)
    title = Column(String(500), default="新会话")
    # M7.4:本会话最近一轮命中的子 Agent 路由(knowledge/web_search/note_write/direct_answer,
    # 由 _stream_graph 从图终态回写;本地审计的 agent 维度,供路由准确率分析)
    agent_route = Column(String(32), default="")
    # Phase 4:跨轮累计用量(turn 结束由 _stream_graph 累加)。用于每会话预算硬停与成本展示。
    total_tokens = Column(Integer, default=0)
    total_cost_cny = Column(Float, default=0.0)


class AgentToolCall(Base, TimestampMixin):
    __tablename__ = "agent_tool_calls"
    __table_args__ = (
        Index("idx_agent_tool_calls_session_created", "session_id", "created_at"),
        # Phase 4 幂等键：同一会话内同一个模型 tool_call_id 只允许落一行。
        # 主键 id 已按 uuid5(session_id, tool_call_id) 确定性生成，这里再加一道库级约束，
        # 防止将来改主键生成方式或并发重放把同一调用写成两行审计。
        Index("uq_agent_tool_calls_session_tool_call", "session_id", "tool_call_id", unique=True),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), index=True)
    # 模型侧 tool_call.id（幂等键的一半）；旧数据为 NULL，SQLite 唯一索引允许多行 NULL
    tool_call_id = Column(String(64))
    tool_name = Column(String(100))
    args_json = Column(Text)
    result_json = Column(Text)
    latency_ms = Column(Integer, default=0)
    status = Column(String(50), default="success")


class AgentToolArtifact(Base, TimestampMixin):
    """Phase 4:大工具结果原文存档。消息里只留压缩预览,模型可凭 id 取回全文。

    id 用 uuid5(session_id, tool_call_id) 确定性生成,重放同一请求只落一行。
    """

    __tablename__ = "agent_tool_artifacts"
    __table_args__ = (
        Index("idx_agent_tool_artifacts_session", "session_id", "created_at"),
    )

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), index=True)
    tool_call_id = Column(String(64))
    tool_name = Column(String(100))
    content = Column(Text)
    length = Column(Integer, default=0)


class UserPreference(Base, TimestampMixin):
    """跨会话长期偏好；LangGraph Store 的持久化事实来源。"""

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_preference_key"),
        Index("idx_user_preferences_user_updated", "user_id", "updated_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(Text, nullable=False)
