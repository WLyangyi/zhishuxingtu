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
from app.db.base import Base
from app.db.session import get_db
from app.models import ImportVisualAsset, Note, User


@pytest.fixture()
def api():
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
    app = FastAPI()
    app.include_router(smart_import.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, db=db, app=app)
    finally:
        db.close()
        engine.dispose()


def test_owner_can_read_visual_asset_image(api, tmp_path):
    png = b"\x89PNG\r\n\x1a\nvisual"
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(png)
    api.db.add(ImportVisualAsset(
        id="asset1",
        user_id="u1",
        note_id="n1",
        page_number=1,
        image_path=str(image_path),
        mime_type="image/png",
        sha256="a" * 64,
    ))
    api.db.commit()

    response = api.client.get("/api/import/notes/n1/assets/asset1/image")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == png


def test_missing_visual_image_returns_not_found(api, tmp_path):
    api.db.add(ImportVisualAsset(
        id="asset-missing",
        user_id="u1",
        note_id="n1",
        page_number=1,
        image_path=str(tmp_path / "missing.png"),
        mime_type="image/png",
        sha256="a" * 64,
    ))
    api.db.commit()

    response = api.client.get("/api/import/notes/n1/assets/asset-missing/image")

    assert response.status_code == 404


def test_other_user_cannot_read_visual_image(api, tmp_path):
    image_path = tmp_path / "page-1.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nvisual")
    api.db.add(ImportVisualAsset(
        id="asset-1",
        user_id="u1",
        note_id="n1",
        page_number=1,
        image_path=str(image_path),
        mime_type="image/png",
        sha256="a" * 64,
    ))
    api.db.commit()
    other = User(id="u2", username="other", password_hash="x")
    api.app.dependency_overrides[get_current_user] = lambda: other

    response = api.client.get("/api/import/notes/n1/assets/asset-1/image")

    assert response.status_code == 404
