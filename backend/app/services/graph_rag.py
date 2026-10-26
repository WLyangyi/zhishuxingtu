"""Phase 5: GraphRAG-lite —— 双向链接 1 跳邻居扩展 + RRF 融合。

为什么不直接改 hybrid_search_notes:
- 该函数同时服务 /api/search/ai 与 chat_chain,改它的返回长度会连带改变 RAG/闲聊口径;
- 本阶段验收口径是"multi_hop / comparison 有可解释提升",而这几类问题全部走 agent 的
  search_notes 工具,所以在工具层扩展最直接、可回退(GRAPH_RAG_ENABLED=false 即恢复原样)。

双向链接的存储是单向的(Note.linked_note_ids 只存出边),语义上的"双向"由反查补齐,
与 api/routes/graph.py#get_local_graph 的口径一致:邻居 = 出边 ∪ 入边。
"""

import json
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.note import Note

SEED_MARK = ""
INBOUND_MARK = "inbound"


def _parse_linked_ids(raw: Any) -> List[str]:
    """linked_note_ids 是 JSON 字符串;坏数据一律当空列表,不能让脏数据打断检索。"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [str(x) for x in parsed] if isinstance(parsed, list) else []


def fuse_with_neighbors(
    seed_ids: Sequence[str],
    neighbor_ids: Sequence[str],
    rrf_k: int = 60,
    neighbor_weight: float = 0.5,
) -> List[Tuple[str, float]]:
    """RRF 融合:种子按名次计 1.0 权重,邻居按名次计 neighbor_weight。

    已经由检索直接命中的笔记不再叠加邻居分数 —— 它已经是种子,再洗一次只会
    把同一条结果的名次搅乱,而不会带来新信息。
    """
    scores: Dict[str, float] = {}
    for rank, note_id in enumerate(seed_ids):
        contribution = 1.0 / (rrf_k + rank + 1)
        scores[note_id] = max(scores.get(note_id, 0.0), contribution)

    for rank, note_id in enumerate(neighbor_ids):
        if note_id in scores:
            continue
        scores[note_id] = neighbor_weight / (rrf_k + rank + 1)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def collect_neighbor_ids(
    seeds: Sequence[Note],
    db: Session,
    limit: int,
    allowed_user_ids: Iterable[str],
) -> List[str]:
    """按种子名次收集 1 跳邻居(出边 → 入边),去重并跳过种子自身。

    先走出边再走入边:出边是作者明确写下的关联,比"被谁引用"更接近提问意图。
    """
    seed_ids = [note.id for note in seeds]
    seed_id_set = set(seed_ids)
    neighbors: List[str] = []
    seen = set(seed_id_set)

    def _push(note_id: str) -> None:
        if note_id not in seen and len(neighbors) < limit:
            seen.add(note_id)
            neighbors.append(note_id)

    for note in seeds:
        for linked_id in _parse_linked_ids(note.linked_note_ids):
            _push(linked_id)

    user_ids = {uid for uid in allowed_user_ids if uid}
    for seed_id in seed_ids:
        if len(neighbors) >= limit:
            break
        query = db.query(Note.id).filter(Note.linked_note_ids.contains(f'"{seed_id}"'))
        if user_ids:
            query = query.filter(Note.user_id.in_(user_ids))
        for (backlink_id,) in query.order_by(Note.updated_at.desc()).all():
            if len(neighbors) >= limit:
                break
            _push(backlink_id)

    return neighbors


def expand_with_linked_notes(
    db: Session,
    seeds: List[Tuple[Note, float]],
) -> List[Tuple[Note, float, str]]:
    """把混合检索结果扩成"种子 + 1 跳邻居",返回 (Note, score, 邻居来源标题)。

    - 开关关闭 / 没有种子 / 没有邻居时,行为与扩展前完全一致(via 全为空串)
    - 邻居分数低于所有种子(weight<1 时),因此只会追加在种子后面,不会挤掉精确命中
    - 邻居来源标题用于工具输出里标注"这条是顺着哪篇笔记的链接找来的",便于模型判断可信度
    """
    if not seeds:
        return []
    if not settings.GRAPH_RAG_ENABLED:
        return [(note, score, SEED_MARK) for note, score in seeds]

    seed_notes = [note for note, _ in seeds]
    seed_ids = [note.id for note in seed_notes]
    neighbor_ids = collect_neighbor_ids(
        seed_notes,
        db,
        limit=settings.GRAPH_RAG_NEIGHBOR_LIMIT,
        allowed_user_ids=(note.user_id for note in seed_notes),
    )
    if not neighbor_ids:
        return [(note, score, SEED_MARK) for note, score in seeds]

    neighbor_notes = db.query(Note).filter(Note.id.in_(neighbor_ids)).all()
    note_by_id = {note.id: note for note in neighbor_notes}

    fused = fuse_with_neighbors(
        seed_ids,
        [nid for nid in neighbor_ids if nid in note_by_id],
        rrf_k=settings.RRF_K,
        neighbor_weight=settings.GRAPH_RAG_NEIGHBOR_WEIGHT,
    )

    seed_note_by_id = {note.id: note for note in seed_notes}
    origin = _neighbor_origin(seed_notes, note_by_id)

    hits: List[Tuple[Note, float, str]] = []
    for note_id, score in fused:
        note = seed_note_by_id.get(note_id) or note_by_id.get(note_id)
        if note is None:
            continue
        if note_id in seed_note_by_id:
            hits.append((note, score, SEED_MARK))
        else:
            # 出边邻居标注来源标题,入边邻居只知道"被引用",统一标 inbound
            hits.append((note, score, origin.get(note_id) or INBOUND_MARK))
    return hits


def _neighbor_origin(
    seeds: Sequence[Note], neighbor_notes: Dict[str, Note]
) -> Dict[str, str]:
    """记录出边邻居是从哪篇种子笔记链接来的(用于工具输出的溯源标注)。

    入边邻居(谁引用了种子)没有"种子指向它的出边"可标注,留空由工具侧统一标 link。
    """
    seed_ids = {note.id for note in seeds}
    origin: Dict[str, str] = {}
    for seed in seeds:
        for linked_id in _parse_linked_ids(seed.linked_note_ids):
            if linked_id in neighbor_notes and linked_id not in seed_ids:
                origin.setdefault(linked_id, seed.title or seed.id)
    return origin
