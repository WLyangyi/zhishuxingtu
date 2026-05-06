import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from app.db.session import SessionLocal, engine
from app.models.user import User
from app.models.folder import Folder

def migrate():
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('folders')]
        
        if 'user_id' not in columns:
            print("添加 user_id 列到 folders 表...")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE folders ADD COLUMN user_id VARCHAR(36)'))
                conn.execute(text('CREATE INDEX IF NOT EXISTS ix_folders_user_id ON folders (user_id)'))
                conn.commit()
            print("user_id 列添加成功")
        else:
            print("user_id 列已存在，跳过")

        user = db.query(User).first()
        if user:
            result = db.query(Folder).filter(Folder.user_id == None).all()
            for folder in result:
                folder.user_id = user.id
            db.commit()
            print(f"已将 {len(result)} 个文件夹的 user_id 设置为用户 {user.username}")
        else:
            print("警告：没有找到用户，请手动设置 folder.user_id")

    except Exception as e:
        print(f"迁移错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
