import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.routes import smart_import
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.models import ImportVisualAsset, Note, User
from app.services.import_task_store import ImportResult, SourceInfo, get_import_task_store


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    user = User(id="u1", username="tester", password_hash="x")
    db.add(user)
    db.commit()

    import app.services.vector_store_adapter as vector_mod

    monkeypatch.setattr(vector_mod, "get_vector_store_adapter", lambda: None)
    app = FastAPI()
    app.include_router(smart_import.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, db=db, monkeypatch=monkeypatch)
    finally:
        db.close()
        engine.dispose()


def test_save_imported_pdf_includes_extracted_original(api):
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="[第 1 页]\nOCR 原文内容",
        result=ImportResult(
            title="扫描件",
            summary="摘要",
            key_points=["要点"],
            tags=[],
            source_info=SourceInfo(type="pdf", filename="scan.pdf"),
        ),
    )

    response = api.client.post("/api/import/save", json={"task_id": task.task_id})

    assert response.status_code == 200
    note = api.db.query(Note).one()
    assert "## 原文" in note.content
    assert "OCR 原文内容" in note.content
    task_store.delete_task(task.task_id)


def test_non_pdf_import_keeps_summary_only_content(api):
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="web")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="网页全文",
        result=ImportResult(
            title="网页",
            summary="摘要",
            key_points=[],
            tags=[],
            source_info=SourceInfo(type="web", url="https://example.com"),
        ),
    )

    api.client.post("/api/import/save", json={"task_id": task.task_id})

    note = api.db.query(Note).one()
    assert "## 原文" not in note.content
    task_store.delete_task(task.task_id)


def test_pdf_original_is_passed_to_embedding_chunks(api, monkeypatch):
    import app.services.vector_store_adapter as vector_mod
    from app.services import embedding_service

    captured = []

    class DummyVectorStore:
        def add_note_chunks(self, note_id, chunks, vectors):
            return {"success": len(chunks), "chunk_ids": []}

    def fake_embed_chunks(note_id, title, content):
        captured.append(content)
        return [], []

    monkeypatch.setattr(vector_mod, "get_vector_store_adapter", lambda: DummyVectorStore())
    monkeypatch.setattr(type(embedding_service), "available", property(lambda self: True))
    monkeypatch.setattr(embedding_service, "embed_chunks", fake_embed_chunks)
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="OCR 可检索原文",
        result=ImportResult(
            title="扫描件",
            summary="摘要",
            key_points=[],
            tags=[],
            source_info=SourceInfo(type="pdf", filename="scan.pdf"),
        ),
    )

    api.client.post("/api/import/save", json={"task_id": task.task_id})

    assert captured
    assert "OCR 可检索原文" in captured[0]
    task_store.delete_task(task.task_id)


def test_repeated_save_does_not_create_duplicate_note(api):
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="OCR 原文",
        result=ImportResult(
            title="扫描件",
            summary="摘要",
            key_points=[],
            tags=[],
            source_info=SourceInfo(type="pdf", filename="scan.pdf"),
        ),
    )

    first = api.client.post("/api/import/save", json={"task_id": task.task_id})
    second = api.client.post("/api/import/save", json={"task_id": task.task_id})

    assert first.status_code == 200
    assert second.status_code == 404
    assert api.db.query(Note).count() == 1


def test_save_persists_visual_asset_with_note(api, monkeypatch, tmp_path):
    png = b"\x89PNG\r\n\x1a\nvisual"
    temp_png = tmp_path / "page-1.png"
    temp_png.write_bytes(png)
    asset_dir = tmp_path / "assets"
    monkeypatch.setattr(settings, "VISUAL_ASSET_DIR", str(asset_dir))
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="OCR 原文",
        result=ImportResult(
            title="视觉文档",
            summary="摘要",
            key_points=[],
            tags=[],
            source_info=SourceInfo(type="pdf", filename="visual.pdf"),
        ),
    )
    task.visual_assets = [{
        "page_number": 1,
        "temp_path": str(temp_png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "mime_type": "image/png",
        "description": "视觉描述",
        "description_status": "completed",
        "source_filename": "visual.pdf",
    }]

    response = api.client.post("/api/import/save", json={"task_id": task.task_id})

    assert response.status_code == 200
    note = api.db.query(Note).one()
    asset = api.db.query(ImportVisualAsset).one()
    assert asset.note_id == note.id
    assert asset.page_number == 1
    assert asset.description == "视觉描述"
    assert Path(asset.image_path).read_bytes() == png
    task_store.delete_task(task.task_id)


def test_save_persists_in_memory_visual_asset(api, monkeypatch, tmp_path):
    png = b"\x89PNG\r\n\x1a\nvisual"
    monkeypatch.setattr(settings, "VISUAL_ASSET_DIR", str(tmp_path / "assets"))
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf")
    task_store.update_task(
        task.task_id,
        status="completed",
        extracted_content="OCR 原文",
        result=ImportResult(
            title="视觉文档",
            summary="摘要",
            key_points=[],
            tags=[],
            source_info=SourceInfo(type="pdf", filename="visual.pdf"),
        ),
    )
    task.visual_assets = [{
        "page_number": 1,
        "png": png,
        "sha256": hashlib.sha256(png).hexdigest(),
        "description": "视觉描述",
        "description_status": "completed",
    }]

    response = api.client.post("/api/import/save", json={"task_id": task.task_id})

    assert response.status_code == 200
    asset = api.db.query(ImportVisualAsset).one()
    assert Path(asset.image_path).read_bytes() == png
    task_store.delete_task(task.task_id)
