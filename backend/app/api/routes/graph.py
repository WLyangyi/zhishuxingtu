import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.note import Note
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, GraphResponse, GraphNode, GraphEdge
from app.api.deps import get_current_user

router = APIRouter(prefix="/graph", tags=["知识图谱"])

@router.get("/global", response_model=Response[GraphResponse])
async def get_global_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    nodes = []
    edges = []
    
    folders = db.query(Folder).all()
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
    
    notes = db.query(Note).all()
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
        
        if note.linked_note_ids:
            linked_ids = json.loads(note.linked_note_ids)
            for linked_id in linked_ids:
                if linked_id in note_id_set:
                    edges.append(GraphEdge(
                        source=note.id,
                        target=linked_id,
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
    
    current_note = db.query(Note).filter(Note.id == note_id).first()
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
    
    if current_note.linked_note_ids:
        linked_ids = json.loads(current_note.linked_note_ids)
        for linked_id in linked_ids:
            linked_note = db.query(Note).filter(Note.id == linked_id).first()
            if linked_note and linked_id not in visited:
                nodes.append(GraphNode(
                    id=linked_note.id,
                    label=linked_note.title,
                    type="note",
                    color="#00d4ff",
                    size=18
                ))
                edges.append(GraphEdge(
                    source=current_note.id,
                    target=linked_id,
                    type="links_to"
                ))
                visited.add(linked_id)
    
    all_notes = db.query(Note).all()
    for note in all_notes:
        if note.id == note_id:
            continue
        if note.linked_note_ids:
            linked_ids = json.loads(note.linked_note_ids)
            if note_id in linked_ids and note.id not in visited:
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
