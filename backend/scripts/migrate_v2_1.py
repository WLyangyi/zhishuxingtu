import sys
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import os

def migrate():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    print(f"Database path: {db_path}")

    engine = create_engine(settings.DATABASE_URL)

    inspector = inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")

    with engine.connect() as conn:
        if "folders" in existing_tables:
            columns = [col["name"] for col in inspector.get_columns("folders")]
            print(f"folders table columns: {columns}")

            if "category_id" not in columns:
                print("Adding category_id column to folders table...")
                conn.execute(text("ALTER TABLE folders ADD COLUMN category_id VARCHAR(36)"))
                conn.commit()
                print("category_id column added.")

            try:
                conn.execute(text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS check_folder_level"))
                conn.commit()
            except:
                pass

            try:
                conn.execute(text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS check_folder_level_2"))
                conn.commit()
            except:
                pass

            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS _temp_folders AS SELECT * FROM folders
                """))
                conn.execute(text("DROP TABLE folders"))
                conn.execute(text("""
                    CREATE TABLE folders (
                        id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        parent_id VARCHAR(36),
                        level INTEGER NOT NULL DEFAULT 0,
                        category_id VARCHAR(36),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (parent_id) REFERENCES folders(id),
                        FOREIGN KEY (category_id) REFERENCES categories(id),
                        CHECK (level IN (0, 1, 2, 3))
                    )
                """))
                conn.execute(text("""
                    INSERT INTO folders (id, name, parent_id, level, category_id, created_at, updated_at)
                    SELECT id, name, parent_id, level, category_id, created_at, updated_at FROM _temp_folders
                """))
                conn.execute(text("DROP TABLE _temp_folders"))
                conn.commit()
                print("folders table recreated with 4-level support.")
            except Exception as e:
                print(f"Note: Could not modify constraints: {e}")

        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
