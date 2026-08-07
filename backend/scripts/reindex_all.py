# -*- coding: utf-8 -*-
"""
M0-4: 全库重索引(qwen3.7-text-embedding)。

用法:
    F:\\ANACONDA\\python.exe scripts/reindex_all.py

流程:
    1. 遍历 notes 表全部笔记
    2. 每篇用 RecursiveChunker(embedding_service.embed_chunks)分块 + 向量化
    3. 块向量均值池化为"每笔记一个向量",写入临时原生 VectorStore(<FAISS_INDEX_PATH>_v2),key=真实 note.id
    4. 保存 + 自检抽查(用 3 个笔记标题当 query,确认能召回对应笔记)
    5. 通过后交换:旧目录 -> <path>.bak,临时目录 -> 正式 FAISS_INDEX_PATH

说明:
    - 写入 search 真正读的原生 store(hybrid_search/vector_search 都是 get_vector_store())。
    - 每笔记一个向量、key 用真实 note.id,是为了让
      db.query(Note).filter(Note.id == note_id) 能解析到笔记(现有 rebuild_index.py
      用 chunk_id 写原生 store,导致向量侧查不到笔记,是既有缺口)。
    - 交换后需重启后端,让 init_vector_store 加载新索引。
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 先 import config,把 Anaconda 健康 pydantic 缓存进 sys.modules,
# 避免 embedding_service.py 的 user-site sys.path hack 把 pydantic 拽到坏的用户 site。
from app.core.config import settings  # noqa: E402

import numpy as np  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.note import Note  # noqa: E402
from app.services.embedding_service import embedding_service  # noqa: E402
from app.services.vector_store import VectorStore  # noqa: E402

LIVE_PATH = settings.FAISS_INDEX_PATH
TEMP_PATH = LIVE_PATH + "_v2"
BAK_PATH = LIVE_PATH + ".bak"
SPOT_CHECK_COUNT = 3


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def spot_check(store: VectorStore, db: Session) -> None:
    print("\n[自检] 用几个笔记标题当 query,验证能召回对应笔记 ...")
    sample_notes = db.query(Note).filter(Note.content.isnot(None)).limit(SPOT_CHECK_COUNT).all()
    if not sample_notes:
        print("  (无笔记可抽查)")
        return
    for note in sample_notes:
        if not note.title:
            continue
        qv = embedding_service.embed_text(note.title)
        results = store.search(qv, k=5, threshold=0.0)
        hit = any(nid == note.id for nid, _ in results)
        print(f"  [{note.title[:20]}] 召回{'✓' if hit else '✗'} -> {results[:3]}")


def swap() -> None:
    if os.path.exists(BAK_PATH):
        shutil.rmtree(BAK_PATH, ignore_errors=True)
    if os.path.exists(LIVE_PATH):
        os.rename(LIVE_PATH, BAK_PATH)
        print(f"  旧索引 -> {BAK_PATH}")
    os.rename(TEMP_PATH, LIVE_PATH)
    print(f"  新索引 -> {LIVE_PATH}")


def main() -> int:
    if not embedding_service.available:
        print("[失败] embedding service 不可用,请检查 DASHSCOPE_API_KEY。")
        return 1

    print(f"embedding model: {embedding_service._model_name}, dimension: {embedding_service.dimension}")
    print(f"live index path: {LIVE_PATH}")
    print(f"temp index path: {TEMP_PATH}")
    print()

    db: Session = SessionLocal()
    try:
        notes = db.query(Note).all()
        total = len(notes)
        print(f"共 {total} 条笔记。")

        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH, ignore_errors=True)
        os.makedirs(TEMP_PATH, exist_ok=True)
        temp_store = VectorStore(TEMP_PATH, dimension=embedding_service.dimension)

        success = 0
        skipped_empty = 0
        skipped_error = 0

        for i, note in enumerate(notes):
            try:
                if not note.content or not note.content.strip():
                    skipped_empty += 1
                    continue
                chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
                if chunks is None or len(chunks) == 0 or vectors.size == 0:
                    skipped_error += 1
                    continue
                # 均值池化:每笔记一个向量,key 用真实 note.id
                note_vec = l2_normalize(vectors.mean(axis=0)).astype(np.float32)
                if np.allclose(note_vec, 0):
                    skipped_error += 1
                    continue
                temp_store.add_vector(note.id, note_vec)
                success += 1
            except Exception as e:
                skipped_error += 1
                print(f"  [error] note '{note.title}': {e}")

            if (i + 1) % 10 == 0 or (i + 1) == total:
                print(f"  progress {i + 1}/{total} (success={success})")

        print(f"\n重索引完成: notes={total}, success={success}, empty={skipped_empty}, error={skipped_error}")
        temp_store.save()
        print(f"临时索引向量数: {temp_store.total_vectors}, 维度: {temp_store.dimension}")

        if temp_store.total_vectors == 0:
            print("[失败] 没有写入任何向量,放弃交换。")
            return 1

        spot_check(temp_store, db)

        swap()
        print("\n[M0-4] 完成:旧索引已备份为 .bak,新索引就位。重启后端使其生效。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
