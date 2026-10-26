# -*- coding: utf-8 -*-
"""Phase 5:GraphRAG-lite——双向链接 1 跳邻居扩展 + RRF。

要守住的三件事:
1. 邻居只追加、不挤掉精确命中(否则召回精度会被"顺手关联"拖下水);
2. 出边与入边都算邻居(存储是单向的,双向语义靠反查补齐);
3. 关闭开关 / 没有链接 / 坏 JSON 时,行为与扩展前一致。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.note import Note
from app.services import graph_rag


@pytest.fixture()
def db_factory():
    engine = create_engine("sqlite://")
    Note.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _note(note_id, title, content="", linked=None, user_id="u1"):
    return Note(
        id=note_id,
        title=title,
        content=content,
        user_id=user_id,
        linked_note_ids=json.dumps(linked, ensure_ascii=False) if linked is not None else None,
    )


def test_fuse_keeps_seeds_ahead_of_neighbors():
    fused = graph_rag.fuse_with_neighbors(
        ["s1", "s2"], ["n1", "n2"], rrf_k=60, neighbor_weight=0.5
    )
    ids = [note_id for note_id, _ in fused]
    assert ids[:2] == ["s1", "s2"]
    assert set(ids[2:]) == {"n1", "n2"}


def test_fuse_skips_neighbor_already_hit():
    fused = graph_rag.fuse_with_neighbors(["s1"], ["s1", "n1"], rrf_k=60)
    ids = [note_id for note_id, _ in fused]
    assert ids == ["s1", "n1"]


def test_expand_disabled_returns_seeds_unchanged(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", False)
    db = db_factory()
    seed, neighbor = _note("s1", "种子", linked=["n1"]), _note("n1", "邻居")
    db.add_all([seed, neighbor])
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(seed, 0.9)])
    assert [(n.id, via) for n, _, via in hits] == [("s1", graph_rag.SEED_MARK)]


def test_expand_appends_outgoing_neighbor_with_origin(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", True)
    db = db_factory()
    seed, neighbor = _note("s1", "索引笔记", linked=["n1"]), _note("n1", "被链接笔记")
    db.add_all([seed, neighbor])
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(seed, 0.9)])
    assert [n.id for n, _, _ in hits] == ["s1", "n1"]
    assert hits[1][2] == "索引笔记"


def test_expand_appends_inbound_backlink(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", True)
    db = db_factory()
    seed = _note("s1", "被引用笔记")
    referrer = _note("n1", "引用它的笔记", linked=["s1"])
    db.add_all([seed, referrer])
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(seed, 0.9)])
    assert [n.id for n, _, _ in hits] == ["s1", "n1"]
    assert hits[1][2] == graph_rag.INBOUND_MARK


def test_expand_respects_neighbor_limit(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "GRAPH_RAG_NEIGHBOR_LIMIT", 2)
    db = db_factory()
    seed = _note("s1", "中心", linked=["n1", "n2", "n3"])
    db.add_all([seed, _note("n1", "一"), _note("n2", "二"), _note("n3", "三")])
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(seed, 0.9)])
    assert len(hits) == 3  # 1 个种子 + 2 个邻居


def test_expand_tolerates_broken_link_json(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", True)
    db = db_factory()
    seed = _note("s1", "脏数据")
    seed.linked_note_ids = '{"not": "a list"}'
    db.add(seed)
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(seed, 0.9)])
    assert [n.id for n, _, _ in hits] == ["s1"]


def test_expand_skips_neighbor_that_is_a_seed(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_RAG_ENABLED", True)
    db = db_factory()
    a = _note("a", "甲", linked=["b"])
    b = _note("b", "乙")
    db.add_all([a, b])
    db.commit()

    hits = graph_rag.expand_with_linked_notes(db, [(a, 0.9), (b, 0.8)])
    assert [n.id for n, _, _ in hits] == ["a", "b"]
    assert [via for _, _, via in hits] == ["", ""]


def test_expand_empty_seeds(db_factory):
    db = db_factory()
    assert graph_rag.expand_with_linked_notes(db, []) == []
