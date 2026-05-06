"""
检查现有数据结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.note import Note
from app.models.folder import Folder
from app.models.category import Category

def check_data():
    db: Session = SessionLocal()
    
    try:
        print("=== 分类列表 ===")
        categories = db.query(Category).all()
        for cat in categories:
            print(f"  {cat.name} (ID: {cat.id})")
        
        print("\n=== 文件夹列表 ===")
        folders = db.query(Folder).all()
        for folder in folders:
            note_count = db.query(Note).filter(Note.folder_id == folder.id).count()
            cat_name = ""
            if folder.category_id:
                cat = db.query(Category).filter(Category.id == folder.category_id).first()
                cat_name = f" [{cat.name}]" if cat else ""
            print(f"  {folder.name}{cat_name} (ID: {folder.id}) - {note_count} 条笔记")
        
        print("\n=== 笔记列表 ===")
        notes = db.query(Note).all()
        for note in notes:
            folder_name = "无文件夹"
            if note.folder_id:
                folder = db.query(Folder).filter(Folder.id == note.folder_id).first()
                folder_name = folder.name if folder else "未知文件夹"
            print(f"  {note.title} -> {folder_name}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
