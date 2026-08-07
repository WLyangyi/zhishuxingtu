import json

from langchain_core.tools import tool


@tool
def list_tags() -> str:
    """列出所有标签。返回 JSON 数组(id/name)。注:Tag 表无 user_id 字段,标签全局共享。"""
    from app.db.session import SessionLocal
    from app.models.tag import Tag

    db = SessionLocal()
    try:
        tags = [{"id": t.id, "name": t.name} for t in db.query(Tag).all()]
        return json.dumps(tags, ensure_ascii=False)
    finally:
        db.close()


@tool
def list_folders() -> str:
    """列出所有文件夹(目录)结构。返回 JSON 数组(id/name/parent_id)。注:现有 folders 表无 user_id 列,目录全局共享。"""
    from app.db.session import SessionLocal
    from app.models.folder import Folder

    db = SessionLocal()
    try:
        folders = [
            {"id": f.id, "name": f.name, "parent_id": f.parent_id}
            for f in db.query(Folder).all()
        ]
        return json.dumps(folders, ensure_ascii=False)
    finally:
        db.close()
