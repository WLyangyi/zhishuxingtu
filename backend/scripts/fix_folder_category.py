"""
修复文件夹分类关联
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.folder import Folder
from app.models.category import Category

def fix_folder_category():
    db: Session = SessionLocal()
    
    try:
        personal_cat = db.query(Category).filter(Category.name == "个人").first()
        if not personal_cat:
            print("错误：没有找到「个人」分类")
            return
        
        print(f"找到「个人」分类: {personal_cat.id}")
        
        empty_folders = db.query(Folder).filter(Folder.category_id == personal_cat.id).all()
        for folder in empty_folders:
            db.delete(folder)
            print(f"删除空文件夹: {folder.name}")
        
        db.commit()
        
        folders = db.query(Folder).filter(Folder.category_id == None).all()
        for folder in folders:
            folder.category_id = personal_cat.id
            print(f"关联文件夹「{folder.name}」到「个人」分类")
        
        db.commit()
        print("\n修复完成！")
        
        print("\n=== 修复后的文件夹列表 ===")
        folders = db.query(Folder).all()
        for folder in folders:
            cat_name = ""
            if folder.category_id:
                cat = db.query(Category).filter(Category.id == folder.category_id).first()
                cat_name = f" [{cat.name}]" if cat else ""
            print(f"  {folder.name}{cat_name} (ID: {folder.id})")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_folder_category()
