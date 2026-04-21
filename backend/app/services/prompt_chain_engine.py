import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.few_shot import PromptChain, ChainStep, ChainExecution
from app.services.llm_service import get_llm_service

PRESET_CHAINS = {
    "knowledge_analysis": {
        "name": "知识分析链",
        "description": "分析外部资料并生成结构化知识卡片",
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
    "conversation_summary": {
        "name": "对话总结链",
        "description": "总结对话内容并提取关键信息",
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
    "qa_enhance": {
        "name": "问答增强链",
        "description": "增强AI问答质量，提供更全面的答案",
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
    }
}

class PromptChainEngine:
    def __init__(self):
        self.llm_service = get_llm_service()
    
    def execute_chain(
        self, 
        chain: PromptChain, 
        input_data: Dict[str, Any],
        db: Session,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        execution = ChainExecution(
            chain_id=chain.id,
            session_id=session_id,
            input_data=json.dumps(input_data, ensure_ascii=False),
            status="running"
        )
        db.add(execution)
        db.commit()
        
        try:
            steps = sorted(chain.steps, key=lambda s: s.step_order)
            context = {"input": input_data, "steps": {}}
            
            for step in steps:
                step_input = self._prepare_step_input(step, context)
                step_output = self._execute_step(step, step_input)
                context["steps"][str(step.step_order)] = step_output
            
            final_output = context["steps"].get(str(steps[-1].step_order), "") if steps else ""
            
            execution.output_data = json.dumps({"result": final_output}, ensure_ascii=False)
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "output": final_output,
                "execution_id": execution.id
            }
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution.id
            }
    
    def _prepare_step_input(self, step: ChainStep, context: Dict) -> Dict[str, Any]:
        if not step.input_mapping:
            return context.get("input", {})
        
        try:
            mapping = json.loads(step.input_mapping)
            result = {}
            for key, path in mapping.items():
                value = self._resolve_path(path, context)
                result[key] = value
            return result
        except:
            return context.get("input", {})
    
    def _resolve_path(self, path: str, context: Dict) -> Any:
        try:
            parts = path.strip("{}").split(".")
            value = context
            for part in parts:
                if part.isdigit():
                    value = value[int(part)]
                else:
                    value = value.get(part, "")
            return value
        except:
            return ""
    
    def _execute_step(self, step: ChainStep, step_input: Dict) -> str:
        prompt = step.prompt_template
        for key, value in step_input.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        try:
            result = self.llm_service.invoke(prompt)
            return result.content
        except Exception as e:
            return f"步骤执行失败: {str(e)}"
    
    @staticmethod
    def create_preset_chain(chain_type: str, db: Session) -> Optional[PromptChain]:
        if chain_type not in PRESET_CHAINS:
            return None
        
        preset = PRESET_CHAINS[chain_type]
        chain = PromptChain(
            name=preset["name"],
            description=preset["description"]
        )
        db.add(chain)
        db.flush()
        
        for step_data in preset["steps"]:
            step = ChainStep(
                chain_id=chain.id,
                **step_data
            )
            db.add(step)
        
        db.commit()
        return chain

def get_chain_engine():
    return PromptChainEngine()
