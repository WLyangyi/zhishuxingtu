import asyncio
from app.db.session import get_db
from app.models.few_shot import PromptChain, ChainStep
from sqlalchemy.orm import Session

DEFAULT_CHAINS = [
    {
        "name": "知识分析链",
        "description": "分析外部资料并生成结构化知识卡片，适用于文章、论文、教程等长文本处理",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "step_name": "提取核心概念",
                "prompt_template": "请从以下内容中提取核心概念和关键知识点：\n\n{content}\n\n请以列表形式输出核心概念：",
                "input_mapping": "{\"content\": \"input.content\"}",
                "output_mapping": "{\"concepts\": \"output\"}"
            },
            {
                "step_order": 2,
                "step_name": "生成知识卡片",
                "prompt_template": "基于以下核心概念，生成结构化的知识卡片：\n\n{concepts}\n\n请按以下格式输出：\n## 核心知识点\n...\n## 关键技术\n...\n## 应用场景\n...",
                "input_mapping": "{\"concepts\": \"steps.0.output\"}",
                "output_mapping": "{\"knowledge_card\": \"output\"}"
            }
        ]
    },
    {
        "name": "对话总结链",
        "description": "总结对话内容并提取关键信息，生成结构化摘要报告",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "step_name": "提取对话要点",
                "prompt_template": "请从以下对话中提取关键要点：\n\n{conversation}\n\n请列出主要讨论的话题和结论：",
                "input_mapping": "{\"conversation\": \"input.conversation\"}",
                "output_mapping": "{\"key_points\": \"output\"}"
            },
            {
                "step_order": 2,
                "step_name": "生成总结报告",
                "prompt_template": "基于以下要点，生成对话总结报告：\n\n{key_points}\n\n请按以下格式输出：\n## 主题\n...\n## 关键要点\n...\n## 待办事项\n...",
                "input_mapping": "{\"key_points\": \"steps.0.output\"}",
                "output_mapping": "{\"summary\": \"output\"}"
            }
        ]
    },
    {
        "name": "问答增强链",
        "description": "增强AI问答质量，先分析问题再生成全面答案",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "step_name": "问题分析",
                "prompt_template": "分析以下问题，识别核心需求和隐含问题：\n\n{question}\n\n请输出：\n1. 核心需求\n2. 隐含问题\n3. 需要的背景知识",
                "input_mapping": "{\"question\": \"input.question\"}",
                "output_mapping": "{\"analysis\": \"output\"}"
            },
            {
                "step_order": 2,
                "step_name": "生成答案",
                "prompt_template": "基于问题分析，生成全面准确的答案：\n\n问题：{question}\n分析：{analysis}\n\n请提供详细答案：",
                "input_mapping": "{\"question\": \"input.question\", \"analysis\": \"steps.0.output\"}",
                "output_mapping": "{\"answer\": \"output\"}"
            }
        ]
    },
    {
        "name": "深度研究链",
        "description": "对复杂主题进行多角度深度分析，生成研究报告",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "step_name": "主题分解",
                "prompt_template": "请将以下主题分解为多个研究维度：\n\n{topic}\n\n请列出：\n1. 核心概念定义\n2. 相关技术/方法\n3. 应用领域\n4. 发展趋势",
                "input_mapping": "{\"topic\": \"input.topic\"}",
                "output_mapping": "{\"dimensions\": \"output\"}"
            },
            {
                "step_order": 2,
                "step_name": "深入分析",
                "prompt_template": "基于以下研究维度，进行深入分析：\n\n{dimensions}\n\n请对每个维度展开详细说明，包括：\n- 核心内容\n- 关键要点\n- 实际案例",
                "input_mapping": "{\"dimensions\": \"steps.0.output\"}",
                "output_mapping": "{\"analysis\": \"output\"}"
            },
            {
                "step_order": 3,
                "step_name": "生成报告",
                "prompt_template": "基于以下分析内容，生成结构化研究报告：\n\n{analysis}\n\n请按以下格式输出：\n# 研究报告\n## 概述\n...\n## 核心内容\n...\n## 关键发现\n...\n## 建议与展望\n...",
                "input_mapping": "{\"analysis\": \"steps.1.output\"}",
                "output_mapping": "{\"report\": \"output\"}"
            }
        ]
    },
    {
        "name": "内容优化链",
        "description": "对文章内容进行多轮优化，提升可读性和专业性",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "step_name": "内容审查",
                "prompt_template": "请审查以下内容，指出需要改进的地方：\n\n{content}\n\n请从以下维度评估：\n1. 逻辑结构\n2. 语言表达\n3. 专业性\n4. 可读性",
                "input_mapping": "{\"content\": \"input.content\"}",
                "output_mapping": "{\"review\": \"output\"}"
            },
            {
                "step_order": 2,
                "step_name": "优化建议",
                "prompt_template": "基于以下审查结果，提供具体优化建议：\n\n{review}\n\n请针对每个问题给出具体的修改建议：",
                "input_mapping": "{\"review\": \"steps.0.output\"}",
                "output_mapping": "{\"suggestions\": \"output\"}"
            },
            {
                "step_order": 3,
                "step_name": "生成优化版本",
                "prompt_template": "请根据以下优化建议，重写原文：\n\n原文：{content}\n\n优化建议：{suggestions}\n\n请输出优化后的内容：",
                "input_mapping": "{\"content\": \"input.content\", \"suggestions\": \"steps.1.output\"}",
                "output_mapping": "{\"optimized\": \"output\"}"
            }
        ]
    }
]

async def init_prompt_chains():
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        for chain_data in DEFAULT_CHAINS:
            existing = db.query(PromptChain).filter(
                PromptChain.name == chain_data["name"]
            ).first()
            
            if not existing:
                steps_data = chain_data.pop("steps")
                chain = PromptChain(**chain_data)
                db.add(chain)
                db.flush()
                
                for step_data in steps_data:
                    step = ChainStep(chain_id=chain.id, **step_data)
                    db.add(step)
                
                print(f"创建链: {chain_data['name']}")
            else:
                print(f"已存在: {chain_data['name']}")
        
        db.commit()
        
        total = db.query(PromptChain).count()
        active = db.query(PromptChain).filter(PromptChain.is_active == True).count()
        print(f"\n提示词链初始化完成")
        print(f"总计 {total} 个链，{active} 个已激活")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(init_prompt_chains())
