"""
检查数据库中文件夹和笔记的实际归属情况
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.folder import Folder
from app.models.category import Category

def check_data():
    db: Session = SessionLocal()

    try:
        categories = db.query(Category).all()
        print("=== 分类列表 ===")
        for cat in categories:
            print(f"  [{cat.id}] {cat.name}")

        print("\n=== 文件夹列表 ===")
        folders = db.query(Folder).all()
        for folder in folders:
            cat_name = "无分类"
            for cat in categories:
                if cat.id == folder.category_id:
                    cat_name = cat.name
                    break
            print(f"  [{folder.id}] {folder.name} -> 分类: {cat_name} (category_id={folder.category_id})")

        print("\n=== 笔记列表 ===")
        notes = db.query(Note).all()
        for note in notes:
            folder_name = "根目录"
            cat_name = "无分类"
            for folder in folders:
                if folder.id == note.folder_id:
                    folder_name = folder.name
                    for cat in categories:
                        if cat.id == folder.category_id:
                            cat_name = cat.name
                            break
                    break
            print(f"  [{note.id}] {note.title}")
            print(f"      folder_id={note.folder_id}, folder_name={folder_name}, 分类={cat_name}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_data()