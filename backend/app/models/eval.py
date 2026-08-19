from sqlalchemy import Column, Index, Integer, String, Text

from app.db.base import Base, TimestampMixin, generate_uuid


class EvalSet(Base, TimestampMixin):
    __tablename__ = "eval_sets"
    __table_args__ = (Index("idx_eval_sets_category", "category"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    eval_id = Column(String(20), index=True)  # 外部编号 q001...
    question = Column(Text)
    expected_answer = Column(Text)
    relevant_doc_ids = Column(Text)  # JSON 数组字符串
    category = Column(String(50))


class EvalRun(Base, TimestampMixin):
    __tablename__ = "eval_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    eval_set_id = Column(String(36), index=True)  # 关联 eval_sets.id
    agent_version = Column(String(50), default="agent-v1")  # baseline / agent-v1
    metrics_json = Column(Text)  # JSON: {recall@k, faithfulness, answer_relevancy, ...}
