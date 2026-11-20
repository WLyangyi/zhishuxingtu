from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text

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
    # core_intent 意图锚点:{goal, constraints: dict[key,value], acceptance_criteria[]} 的 JSON。
    # checkpoint 是唯一真相源,本列是查询镜像(路由层回写,版本比较防旧值覆盖新值)。
    core_intent = Column(Text)
    # 每次意图变更 +1,默认 0/null(老会话无锚点)
    intent_version = Column(Integer, default=0)
    # 意图变更历史快照,JSON 数组,每条含 version/goal/constraints/change_type/source/confidence/unmapped_keys/ts
    intent_versions = Column(Text)


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


class AgentTask(Base, TimestampMixin):
    """二期 task 分层：一个会话可挂多个任务，同一时刻仅一个 active。

    phase（执行阶段）与 status（生命周期）职责分离：
    - phase: 任务内部轻量阶段 clarify/executing/review/done，完整状态机远期再设计；
    - status: 生命周期 active/completed/cancelled/archived，部分唯一索引只约束 active。

    core_intent 从 session 级下沉到 task 级（goal/constraints/acceptance_criteria，
    2.2 落地切换逻辑）；intent_versions 按 task 分区（2.3 落历史）；depends_on 支持
    new_task 闭环（2.5 落依赖失效）。一期 session 级 intent_versions 作为 legacy 不动。
    """

    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("idx_agent_tasks_session_created", "session_id", "created_at"),
        # 部分唯一索引：同一会话同一时刻仅一个 active 任务；
        # completed/cancelled/archived 不受限，active 转非 active 后释放名额。
        Index(
            "uq_agent_tasks_active_per_session",
            "session_id",
            unique=True,
            sqlite_where=text("status='active'"),
        ),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), index=True)
    user_id = Column(String(36))
    title = Column(String(500), default="")
    # core_intent 下沉 task（2.2 切换逻辑用）：goal + 约束 dict + 验收标准
    goal = Column(Text)
    constraints = Column(Text)          # JSON dict[key, value]，不带 op
    acceptance_criteria = Column(Text)  # JSON array
    intent_version = Column(Integer, default=0)
    intent_versions = Column(Text)      # JSON 数组，按 task 分区（2.3 用）
    # phase / status 职责分离
    phase = Column(String(32), default="clarify")   # clarify/executing/review/done
    status = Column(String(32), default="active")    # active/completed/cancelled/archived
    # new_task 闭环：子任务依赖父任务 id（2.5 用）
    depends_on = Column(String(36))
