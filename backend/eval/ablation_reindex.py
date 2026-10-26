# -*- coding: utf-8 -*-
"""消融用:按指定分块重叠比例重建一份独立向量索引(绝不动生产索引)。

背景:分块器在 EmbeddingService 构造时读 settings.OVERLAP_RATIO,没有运行时注入口,
所以必须在 import 之前用环境变量覆盖,并把 FAISS_INDEX_PATH 指到独立路径。

用法:
    .venv\\Scripts\\python.exe eval/ablation_reindex.py --out data/ablation-overlap0-faiss --overlap 0

口径与 scripts/reindex_all.py 一致:块向量均值池化为「每笔记一个向量」,key = 真实 note.id,
这样 hybrid_search / vector_search 解析到的仍是笔记本身。
"""
import argparse
import os
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="独立索引目录(相对 backend/ 或绝对路径)")
    parser.add_argument("--overlap", type=float, default=0.0, help="分块重叠比例,0 表示无重叠")
    args = parser.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(BACKEND_ROOT, args.out)
    # 必须在 import app.* 之前设置:settings 只在 import 时读一次环境变量
    os.environ["FAISS_INDEX_PATH"] = out
    os.environ["OVERLAP_RATIO"] = str(args.overlap)

    import shutil

    import numpy as np

    from app.core.config import settings
    from app.db.session import SessionLocal
    from app.models.note import Note
    from app.services.embedding_service import embedding_service
    from app.services.vector_store import VectorStore

    if not embedding_service.available:
        print("[失败] embedding service 不可用,请检查 DASHSCOPE_API_KEY")
        return 1

    print(f"[reindex] overlap_ratio={settings.OVERLAP_RATIO} 输出索引: {out}")
    if os.path.exists(out):
        shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    store = VectorStore(out, dimension=embedding_service.dimension)
    db = SessionLocal()
    success = skipped = 0
    try:
        notes = db.query(Note).all()
        for note in notes:
            if not note.content or not note.content.strip():
                skipped += 1
                continue
            try:
                chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
                if vectors is None or len(vectors) == 0:
                    skipped += 1
                    continue
                vec = vectors.mean(axis=0)
                norm = np.linalg.norm(vec)
                if norm == 0:
                    skipped += 1
                    continue
                store.add_vector(note.id, (vec / norm).astype(np.float32))
                success += 1
            except Exception as exc:  # noqa: BLE001 单条笔记失败不阻断整体重建
                skipped += 1
                print(f"  [error] {note.title}: {exc}")
    finally:
        db.close()

    store.save()
    print(f"[reindex] 完成: notes={success + skipped}, success={success}, skipped={skipped}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
