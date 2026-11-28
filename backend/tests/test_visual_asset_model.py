import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import ImportVisualAsset, Note, User


def test_visual_asset_is_unique_per_note_and_page():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id="u1", username="tester", password_hash="x")
    note = Note(id="n1", title="文档", user_id="u1")
    db.add_all([user, note])
    db.commit()
    db.add(ImportVisualAsset(
        user_id="u1",
        note_id="n1",
        page_number=1,
        image_path="assets/u1/n1/page-1.png",
        mime_type="image/png",
        sha256="a" * 64,
    ))
    db.commit()
    db.add(ImportVisualAsset(
        user_id="u1",
        note_id="n1",
        page_number=1,
        image_path="assets/u1/n1/page-1.png",
        mime_type="image/png",
        sha256="b" * 64,
    ))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(ImportVisualAsset).count() == 1
    db.close()
    engine.dispose()
