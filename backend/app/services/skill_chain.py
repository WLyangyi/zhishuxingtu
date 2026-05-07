from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.llm_service import get_llm_service
from app.core.config import settings
from app.services.skill_prompts_config import SKILL_PROMPTS


class SkillChain:
    def __init__(self):
        self.llm = get_llm_service().client
        self._chains: Dict[str, Any] = {}

    def _get_or_create_chain(self, skill_type: str) -> Optional[Any]:
        if skill_type in self._chains:
            return self._chains[skill_type]
        
        prompt_config = SKILL_PROMPTS.get(skill_type)
        if not prompt_config:
            return None
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_config["system_prompt"]),
            ("human", prompt_config["user_template"])
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        self._chains[skill_type] = chain
        return chain

    def execute(
        self,
        skill_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        chain = self._get_or_create_chain(skill_type)
        
        if chain is None:
            return {
                "type": skill_type,
                "status": "error",
                "message": f"未找到 Skill 类型 '{skill_type}' 的提示词配置"
            }
        
        try:
            formatted_input = {}
            for key, value in input_data.items():
                if isinstance(value, list):
                    formatted_input[key] = ", ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    formatted_input[key] = str(value)
                else:
                    formatted_input[key] = str(value)
            
            result = chain.invoke(formatted_input)
            
            return {
                "type": skill_type,
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "type": skill_type,
                "status": "error",
                "message": f"AI 服务调用失败: {str(e)}"
            }

    def get_supported_types(self) -> list:
        return list(SKILL_PROMPTS.keys())

    def has_skill_type(self, skill_type: str) -> bool:
        return skill_type in SKILL_PROMPTS


_skill_chain_instance = None

def get_skill_chain() -> SkillChain:
    global _skill_chain_instance
    if _skill_chain_instance is None:
        _skill_chain_instance = SkillChain()
    return _skill_chain_instance
