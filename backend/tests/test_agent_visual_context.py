from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import ImportVisualAsset, Note, User
from app.services.visual_evidence import build_visual_evidence_messages


def test_visual_context_includes_at_most_three_original_images(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    note = Note(id="n1", title="视觉文档", user_id="u1")
    db.add_all([user, note])
    db.commit()
    for page in range(1, 5):
        image_path = tmp_path / f"page-{page}.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([page]))
        db.add(ImportVisualAsset(
            id=f"asset-{page}",
            user_id="u1",
            note_id="n1",
            page_number=page,
            image_path=str(image_path),
            mime_type="image/png",
            sha256=f"{page:064x}",
            description=f"第 {page} 页描述",
        ))
    db.commit()

    messages = build_visual_evidence_messages(
        db,
        user_id="u1",
        documents=[{"id": "n1", "title": "视觉文档"}],
        max_images=3,
    )

    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    content = messages[0].content
    image_blocks = [block for block in content if block.get("type") == "image_url"]
    assert len(image_blocks) == 3
    assert all(block["image_url"]["url"].startswith("data:image/png;base64,") for block in image_blocks)
    db.close()
    engine.dispose()


def test_missing_original_image_keeps_description_only_notice(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    note = Note(id="n1", title="视觉文档", user_id="u1")
    db.add_all([user, note])
    db.commit()
    image_path = tmp_path / "page-2.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nvisual")
    db.add_all([
        ImportVisualAsset(
            id="asset-1", user_id="u1", note_id="n1", page_number=1,
            image_path=str(tmp_path / "missing.png"), mime_type="image/png",
            sha256="1" * 64, description="缺失原图描述",
        ),
        ImportVisualAsset(
            id="asset-2", user_id="u1", note_id="n1", page_number=2,
            image_path=str(image_path), mime_type="image/png",
            sha256="2" * 64, description="可用原图描述",
        ),
    ])
    db.commit()

    messages = build_visual_evidence_messages(db, "u1", [{"id": "n1"}], max_images=3)

    text = messages[0].content[0]["text"]
    image_blocks = [block for block in messages[0].content if block.get("type") == "image_url"]
    assert "未提供原图" in text
    assert len(image_blocks) == 1
    db.close()
    engine.dispose()


def test_agent_step_attaches_original_image_context(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services.agent import nodes
    import app.db.session as db_session

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    user = User(id="u1", username="tester", password_hash="x")
    note = Note(id="n1", title="视觉文档", user_id="u1")
    db.add_all([user, note])
    db.commit()
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nvisual")
    db.add(ImportVisualAsset(
        id="asset-1", user_id="u1", note_id="n1", page_number=1,
        image_path=str(image_path), mime_type="image/png",
        sha256="1" * 64, description="图表描述",
    ))
    db.commit()
    captured = []

    class FakeLLM:
        def invoke(self, messages):
            captured.extend(messages)
            return AIMessage(content="已对照原图回答")

    class FakeProvider:
        def bind_tools(self, tools, tool_choice=None):
            return FakeLLM()

    monkeypatch.setattr(settings, "VISUAL_EVIDENCE_ENABLED", True)
    monkeypatch.setattr(db_session, "SessionLocal", factory)
    monkeypatch.setattr(nodes, "get_deepseek_provider", lambda: FakeProvider())
    monkeypatch.setattr(nodes, "get_preference_context", lambda *args, **kwargs: "")

    nodes.agent_step({
        "messages": [HumanMessage(content="这张图说明了什么？")],
        "question": "这张图说明了什么？",
        "user_id": "u1",
        "session_id": "s1",
        "current_agent": "knowledge",
        "iteration": 0,
        "documents": [{"id": "n1", "title": "视觉文档", "snippet": "正文"}],
        "thoughts": [],
        "tool_calls_log": [],
    })

    assert any(
        isinstance(message.content, list)
        and any(block.get("type") == "image_url" for block in message.content)
        for message in captured
    )
    db.close()
    engine.dispose()


def test_output_attaches_visual_evidence_metadata(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services.agent import nodes
    import app.db.session as db_session

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    user = User(id="u1", username="tester", password_hash="x")
    note = Note(id="n1", title="视觉文档", user_id="u1")
    db.add_all([user, note])
    db.commit()
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nvisual")
    db.add(ImportVisualAsset(
        id="asset-1", user_id="u1", note_id="n1", page_number=1,
        image_path=str(image_path), mime_type="image/png",
        sha256="1" * 64, description="图表描述", source_filename="visual.pdf",
    ))
    db.commit()
    monkeypatch.setattr(settings, "VISUAL_EVIDENCE_ENABLED", True)
    monkeypatch.setattr(db_session, "SessionLocal", factory)

    result = nodes.output({
        "messages": [AIMessage(content="答案", id="a1")],
        "turn_start_id": "",
        "current_agent": "knowledge",
        "user_id": "u1",
        "documents": [{"id": "n1", "title": "视觉文档"}],
    })

    evidence = result["messages"][0].additional_kwargs["visual_evidence"]
    assert evidence[0]["asset_id"] == "asset-1"
    assert evidence[0]["page_number"] == 1
    assert evidence[0]["description"] == "图表描述"
    db.close()
    engine.dispose()
