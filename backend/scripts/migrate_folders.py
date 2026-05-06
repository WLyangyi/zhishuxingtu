"""
数据迁移脚本：重构文件夹结构
- 确保三个分类（个人、工作、素材）存在
- 在"个人"分类下创建"学习"和"游戏"文件夹
- 将现有笔记迁移到对应文件夹
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

def migrate_data():
    db: Session = SessionLocal()
    
    try:
        user = db.query(User).first()
        if not user:
            print("错误：没有找到用户，请先创建用户")
            return
        
        categories = db.query(Category).all()
        if not categories:
            print("错误：没有找到分类，请先初始化系统分类")
            return
        
        personal_cat = None
        for cat in categories:
            if "个人" in cat.name:
                personal_cat = cat
                break
        
        if not personal_cat:
            print("错误：没有找到「个人」分类")
            return
        
        print(f"找到「个人」分类: {personal_cat.name} (ID: {personal_cat.id})")
        
        existing_folders = db.query(Folder).filter(Folder.category_id == personal_cat.id).all()
        existing_names = [f.name for f in existing_folders]
        
        study_folder = None
        game_folder = None
        
        for folder in existing_folders:
            if folder.name == "学习":
                study_folder = folder
                print(f"「学习」文件夹已存在: {folder.id}")
            elif folder.name == "游戏":
                game_folder = folder
                print(f"「游戏」文件夹已存在: {folder.id}")
        
        if not study_folder:
            study_folder = Folder(
                name="学习",
                level=0,
                category_id=personal_cat.id
            )
            db.add(study_folder)
            db.commit()
            db.refresh(study_folder)
            print(f"创建「学习」文件夹: {study_folder.id}")
        
        if not game_folder:
            game_folder = Folder(
                name="游戏",
                level=0,
                category_id=personal_cat.id
            )
            db.add(game_folder)
            db.commit()
            db.refresh(game_folder)
            print(f"创建「游戏」文件夹: {game_folder.id}")
        
        notes = db.query(Note).filter(Note.user_id == user.id).all()
        print(f"\n找到 {len(notes)} 条笔记")
        
        study_keywords = ['Vue', 'React', '前端', 'TypeScript', '框架', '学习', '笔记']
        game_keywords = ['游戏']
        
        migrated_count = 0
        for note in notes:
            if note.folder_id:
                print(f"  笔记「{note.title}」已在文件夹中，跳过")
                continue
            
            content_lower = (note.title + " " + (note.content or "")).lower()
            
            target_folder = None
            for keyword in study_keywords:
                if keyword.lower() in content_lower:
                    target_folder = study_folder
                    break
            
            if not target_folder:
                for keyword in game_keywords:
                    if keyword.lower() in content_lower:
                        target_folder = game_folder
                        break
            
            if target_folder:
                note.folder_id = target_folder.id
                migrated_count += 1
                print(f"  迁移笔记「{note.title}」到「{target_folder.name}」")
        
        db.commit()
        print(f"\n迁移完成！共迁移 {migrated_count} 条笔记")
        
        study_count = db.query(Note).filter(Note.folder_id == study_folder.id).count()
        game_count = db.query(Note).filter(Note.folder_id == game_folder.id).count()
        print(f"「学习」文件夹: {study_count} 条笔记")
        print(f"「游戏」文件夹: {game_count} 条笔记")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
