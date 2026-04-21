import sqlite3
import os

def run_migration():
    db_path = os.environ.get('DATABASE_URL', './data/knowledge.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path.replace('sqlite:///', '')
    
    migration_file = 'migrations/add_few_shot_tables.sql'
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    if not os.path.exists(migration_file):
        print(f"迁移文件不存在: {migration_file}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("数据库迁移成功！")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('few_shot_examples', 'prompt_versions', 'ab_experiments', 'ab_test_results', 'prompt_evaluations', 'prompt_chains', 'chain_steps', 'chain_executions')")
        tables = cursor.fetchall()
        print(f"创建的表: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
