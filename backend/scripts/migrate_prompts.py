import sys
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import os

def migrate():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    print(f"Database path: {db_path}")

    engine = create_engine(settings.DATABASE_URL)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")

    with engine.connect() as conn:
        if "prompts" not in existing_tables:
            print("Creating prompts table...")
            conn.execute(text("""
                CREATE TABLE prompts (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) NOT NULL,
                    system_prompt TEXT NOT NULL,
                    user_prompt_template TEXT DEFAULT '',
                    output_format TEXT DEFAULT '',
                    variables TEXT DEFAULT '[]',
                    is_system BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_default BOOLEAN DEFAULT FALSE,
                    priority VARCHAR(20) DEFAULT 'normal',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("prompts table created.")

            print("Initializing default prompts...")
            default_prompts = [
                {
                    "id": "prompt-knowledge-chat",
                    "name": "知识问答",
                    "description": "基于知识库的智能问答助手",
                    "category": "ai_chat",
                    "system_prompt": """你是一个友善、专业的智能知识助手，名为"知枢星图AI助手"。

当前日期：{current_date}，{current_weekday}

## 你的主要职责
1. 回答用户关于知识库内容的问题
2. 帮助用户整理和总结笔记
3. 提供学习和知识管理的建议
4. 进行一般性的对话交流

## 回答原则
1. **简洁明了**：直接回答问题，不啰嗦
2. **有据可依**：如果引用了知识库内容，请注明来源
3. **诚实可靠**：如果知识库没有相关信息，诚实地告知用户
4. **友好亲切**：用友好、专业的方式与用户交流

## 限制
- 不知道的问题要诚实说"我不知道"或"知识库中没有相关信息"
- 不要编造知识库中没有的内容
- 回答问题的语言要与问题一致（用户用中文问就用中文答）

## 免责声明
当涉及医疗、法律、金融等专业知识时，请提醒用户寻求专业人士的意见。""",
                    "user_prompt_template": """知识库相关内容：
{context}

---
用户问题：{question}

请根据以上知识库内容回答问题：""",
                    "output_format": "自由文本，使用中文回答",
                    "variables": '["current_date", "current_weekday", "context", "question"]',
                    "is_system": True,
                    "is_active": True,
                    "is_default": True,
                    "priority": "high"
                },
                {
                    "id": "prompt-ai-search",
                    "name": "AI搜索问答",
                    "description": "用于全局搜索的AI问答提示词",
                    "category": "ai_search",
                    "system_prompt": """你是一个智能知识检索助手，帮助用户从个人知识库中找到相关信息并回答问题。

当前日期：{current_date}，{current_weekday}

## 工作流程
1. 分析用户问题，理解其真正需求
2. 从提供的笔记内容中查找相关信息
3. 综合整理后给出准确答案
4. 如果知识库中没有相关内容，诚实地说明

## 回答要求
1. 简洁明了，直接回答问题
2. 引用知识库内容时标注来源（笔记标题）
3. 如果问题与知识库内容不太相关，给出一致性建议
4. 不知道的问题要诚实说明

## 免责声明
本回答仅供参考，如有重要决策请咨询专业人士。""",
                    "user_prompt_template": """以下是知识库中的相关笔记：

{context}

---

用户问题：{question}

请基于以上笔记内容回答问题：""",
                    "output_format": "自由文本，使用中文回答",
                    "variables": '["current_date", "current_weekday", "context", "question"]',
                    "is_system": True,
                    "is_active": True,
                    "is_default": True,
                    "priority": "normal"
                }
            ]

            for prompt in default_prompts:
                conn.execute(text("""
                    INSERT INTO prompts (id, name, description, category, system_prompt, user_prompt_template, output_format, variables, is_system, is_active, is_default, priority)
                    VALUES (:id, :name, :description, :category, :system_prompt, :user_prompt_template, :output_format, :variables, :is_system, :is_active, :is_default, :priority)
                """), prompt)
            conn.commit()
            print(f"Initialized {len(default_prompts)} default prompts.")
        else:
            print("prompts table already exists, skipping creation.")

        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
