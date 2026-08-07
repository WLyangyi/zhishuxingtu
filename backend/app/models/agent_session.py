from sqlalchemy import Column, Index, Integer, String, Text

from app.db.base import Base, TimestampMixin, generate_uuid


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_sessions"
    __table_args__ = (Index("idx_agent_sessions_user_updated", "user_id", "updated_at"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)  # = LangGraph thread_id
    user_id = Column(String(36), index=True)
    title = Column(String(500), default="新会话")


class AgentToolCall(Base, TimestampMixin):
    __tablename__ = "agent_tool_calls"
    __table_args__ = (Index("idx_agent_tool_calls_session_created", "session_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), index=True)
    tool_name = Column(String(100))
    args_json = Column(Text)
    result_json = Column(Text)
    latency_ms = Column(Integer, default=0)
    status = Column(String(50), default="success")
