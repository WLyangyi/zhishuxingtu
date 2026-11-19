import hashlib

from fastapi import APIRouter, Depends, Request, Response as FastAPIResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, GraphResponse, GraphNode, GraphEdge
from app.api.deps import get_current_user

router = APIRouter(prefix="/graph", tags=["知识图谱"])

MAX_GRAPH_NODES = 500


def _graph_etag(db: Session, user_id: str) -> str:
    """用户维度图谱快照指纹：notes/folders 按用户，tags 是全局表。"""
    latest = []
    for model, scoped in ((Note, True), (Folder, True), (Tag, False)):
        query = db.query(func.max(model.updated_at))
        if scoped:
            query = query.filter(model.user_id == user_id)
        latest.append(str(query.scalar() or ""))
    raw = "|".join([user_id, *latest])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.get("/global", response_model=Response[GraphResponse])
async def get_global_graph(
    request: Request,
    response: FastAPIResponse,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    etag = _graph_etag(db, current_user.id)
    response.headers["ETag"] = etag
    if request.headers.get("if-none-match") == etag:
        return FastAPIResponse(status_code=304, headers={"ETag": etag})

    nodes = []
    edges = []
    
    folders = db.query(Folder).filter(Folder.user_id == current_user.id).all()
    for folder in folders:
        nodes.append(GraphNode(
            id=folder.id,
            label=folder.name,
            type="folder",
            color="#6b7280",
            size=20
        ))
    
    tags = db.query(Tag).all()
    for tag in tags:
        nodes.append(GraphNode(
            id=tag.id,
            label=tag.name,
            type="tag",
            color=tag.color,
            size=15
        ))
    
    notes = db.query(Note).filter(Note.user_id == current_user.id).options(joinedload(Note.tags)).limit(MAX_GRAPH_NODES).all()
    note_id_set = {note.id for note in notes}
    
    for note in notes:
        nodes.append(GraphNode(
            id=note.id,
            label=note.title,
            type="note",
            color="#00d4ff",
            size=18
        ))
        
        if note.folder_id:
            edges.append(GraphEdge(
                source=note.folder_id,
                target=note.id,
                type="contains"
            ))
        
        for tag in note.tags:
            edges.append(GraphEdge(
                source=note.id,
                target=tag.id,
                type="has_tag"
            ))
        
    # P1-1:出链走关联表一次批量查询，不再对每篇笔记 json.loads。
    if note_id_set:
        link_rows = db.query(NoteLink.source_id, NoteLink.target_id).filter(
            NoteLink.source_id.in_(note_id_set)
        ).all()
        for source_id, target_id in link_rows:
            if target_id in note_id_set:
                edges.append(GraphEdge(
                    source=source_id,
                    target=target_id,
                    type="links_to"
                ))

    return Response(data=GraphResponse(nodes=nodes, edges=edges))

@router.get("/local/{note_id}", response_model=Response[GraphResponse])
async def get_local_graph(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    nodes = []
    edges = []
    visited = set()
    
    current_note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not current_note:
        return Response(data=GraphResponse(nodes=[], edges=[]))
    
    nodes.append(GraphNode(
        id=current_note.id,
        label=current_note.title,
        type="note",
        color="#00d4ff",
        size=20
    ))
    visited.add(current_note.id)
    
    linked_note_ids_set = {
        row[0] for row in db.query(NoteLink.target_id).filter(NoteLink.source_id == note_id).all()
    }

    if linked_note_ids_set:
        linked_notes = db.query(Note).filter(
            Note.id.in_(linked_note_ids_set),
            Note.user_id == current_user.id
        ).all()
        for linked_note in linked_notes:
            if linked_note.id not in visited:
                nodes.append(GraphNode(
                    id=linked_note.id,
                    label=linked_note.title,
                    type="note",
                    color="#00d4ff",
                    size=18
                ))
                edges.append(GraphEdge(
                    source=current_note.id,
                    target=linked_note.id,
                    type="links_to"
                ))
                visited.add(linked_note.id)
    
    backlink_notes = (
        db.query(Note)
        .join(NoteLink, NoteLink.source_id == Note.id)
        .filter(NoteLink.target_id == note_id, Note.user_id == current_user.id)
        .all()
    )
    
    for note in backlink_notes:
        if note.id not in visited:
            nodes.append(GraphNode(
                id=note.id,
                label=note.title,
                type="note",
                color="#00d4ff",
                size=18
            ))
            edges.append(GraphEdge(
                source=note.id,
                target=note_id,
                type="links_to"
            ))
            visited.add(note.id)
    
    return Response(data=GraphResponse(nodes=nodes, edges=edges))
