# -*- coding: utf-8 -*-
"""Phase 5: Contextual Retrieval 重索引(独立索引,绝不动生产索引)。

为什么用独立索引:
- 生产索引 + 冻结基线是一套口径,为了一个实验重新编码全部向量会让基线不可追溯;
- 独立索引可以随时用 FAISS_INDEX_PATH 切过去做 on/off 对照,也方便"没提升就不切"。

做法(在 18 篇笔记的规模上做最小可用版):
1. 每篇笔记让 LLM 生成一句"它在知识库中的定位"(主题 + 回答什么问题,≤80 字);
2. 把 [标题 + 定位] 前缀拼到每个 chunk 再嵌入 —— 这解决"孤儿块"问题:
   同一段话在《安装指南》和《使用技巧》里含义不同,只按块向量会被拉平;
3. chunk 向量均值池化成笔记向量(与 scripts/reindex_all.py 口径一致,
   hybrid_search / vector_search 解析到的仍是 note.id)。

用法:
    .venv\\Scripts\\python.exe scripts/reindex_contextual.py
    .venv\\Scripts\\python.exe scripts/reindex_contextual.py --out data/contextual-faiss
"""
import argparse
import json
import os
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

# 与 eval/run_eval.py 同一套本机 workaround(WMI 卡死 / transformers→torch 连带阻塞)
sys.modules.setdefault("transformers", None)
import platform as _platform  # noqa: E402

_platform.win32_ver = lambda *a, **k: ("", "", "", "")
_platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"

CONTEXT_PROMPT = (
    "你是个人知识库的索引助手。请用一句不超过 80 字的中文，说明下面这篇笔记"
    "在知识库中的定位：它讲什么主题、回答什么问题、和哪些常见主题容易混淆。"
    "只输出这一句话，不要引号、不要解释。"
)
MAX_CONTEXT_INPUT = 2000


def build_context(llm, title: str, content: str) -> str:
    """生成笔记定位;失败时退回标题,保证重索引不因单条 LLM 抖动而中断。"""
    from app.services.llm.deepseek_provider import invoke_with_retry

    messages = [
        ("system", CONTEXT_PROMPT),
        ("user", f"标题：{title}\n\n正文（可能截断）：{content[:MAX_CONTEXT_INPUT]}"),
    ]
    try:
        reply = invoke_with_retry(llm, messages, label=f"context:{title[:20]}")
        text = (getattr(reply, "content", "") or "").strip().replace("\n", " ")
        return text[:120]
    except Exception as exc:  # noqa: BLE001 单条失败只降级,不阻断整库重建
        print(f"  [warn] 定位生成失败({title[:24]}): {exc}")
        return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/contextual-faiss", help="独立索引目录")
    parser.add_argument("--contexts", default="data/contextual-contexts.json", help="定位文本存档")
    args = parser.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(BACKEND_ROOT, args.out)
    contexts_path = (
        args.contexts if os.path.isabs(args.contexts) else os.path.join(BACKEND_ROOT, args.contexts)
    )

    import shutil

    import numpy as np

    from app.db.session import SessionLocal
    from app.models.note import Note
    from app.services.embedding_service import embedding_service
    from app.services.llm.deepseek_provider import get_deepseek_provider
    from app.services.vector_store import VectorStore

    if not embedding_service.available:
        print("[失败] embedding service 不可用,请检查 DASHSCOPE_API_KEY")
        return 1
    if not get_deepseek_provider().available:
        print("[失败] DEEPSEEK_API_KEY 未配置,无法生成定位文本")
        return 1

    print(f"[contextual] 输出索引: {out}")
    if os.path.exists(out):
        shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    llm = get_deepseek_provider().get_chat_model()
    store = VectorStore(out, dimension=embedding_service.dimension)
    db = SessionLocal()
    contexts = {}
    success = skipped = 0
    try:
        for note in db.query(Note).all():
            if not note.content or not note.content.strip():
                skipped += 1
                continue
            context = build_context(llm, note.title or "", note.content)
            contexts[note.id] = {"title": note.title, "context": context, "llm": bool(context)}
            prefix = f"{note.title}\n{context}\n" if context else f"{note.title}\n"
            try:
                chunks = embedding_service.chunker.chunk(note.id, note.title, note.content)
                if not chunks:
                    skipped += 1
                    continue
                vectors = embedding_service.embed_texts(
                    [prefix + chunk.content for chunk in chunks]
                )
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
                print(f"  [ok] {note.title[:30]} context={context[:40]}")
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                print(f"  [error] {note.title}: {exc}")
    finally:
        db.close()

    store.save()
    with open(contexts_path, "w", encoding="utf-8") as f:
        json.dump(contexts, f, ensure_ascii=False, indent=2)
    print(f"[contextual] 完成: success={success}, skipped={skipped}, 定位存档={contexts_path}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
