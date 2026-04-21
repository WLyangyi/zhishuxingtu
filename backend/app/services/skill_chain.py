from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.llm_service import get_llm_service
from app.core.config import settings


SKILL_PROMPTS = {
    "conversation_summary": {
        "system_prompt": """你是一个专业的对话总结助手，负责将对话内容整理成结构化的总结。

## 总结要求
1. 提取对话的核心主题
2. 列出关键讨论点和结论
3. 记录待办事项（如果有）
4. 总结不超过500字

## 输出格式
请按以下格式输出：
- 主题：[对话主题]
- 关键要点：[3-5个要点]
- 待办事项：[如有]
- 总结：[总体总结]""",
        "user_template": "请总结以下对话内容，提取关键要点：\n\n{conversation}"
    },
    "news_aggregate": {
        "system_prompt": """你是一个专业的资讯聚合助手，负责从多个来源收集和整理每日资讯。

## 工作要求
1. 按类别整理资讯（技术、行业、热点等）
2. 每个咨询提供简短摘要（50字以内）
3. 标注信息来源
4. 整理成易读的列表格式

## 输出格式
请按以下格式输出：
## 技术资讯
- [标题] - [来源] - [摘要]

## 行业动态
- [标题] - [来源] - [摘要]

## 今日热点
- [标题] - [来源] - [摘要]""",
        "user_template": "请汇总以下资讯来源：\n\n来源：{sources}\n关键词：{keywords}\n\n请整理成每日报表格式："
    },
    "resume_parse": {
        "system_prompt": """你是一个专业的简历解析助手，负责从简历文本中提取关键信息。

## 解析要求
1. 提取基本信息（姓名、联系方式等）
2. 识别工作经历和技术技能
3. 提取教育背景
4. 识别关键优势和亮点

## 输出格式
请按以下JSON格式输出：
{
  "name": "姓名",
  "contact": "联系方式",
  "skills": ["技能1", "技能2"],
  "experience": [
    {"company": "公司名", "position": "职位", "duration": "时长", "highlights": ["亮点1", "亮点2"]}
  ],
  "education": {"school": "学校", "degree": "学位", "major": "专业"},
  "highlights": ["亮点1", "亮点2"]
}""",
        "user_template": "请解析以下简历内容：\n\n{resume_text}"
    },
    "knowledge_card": {
        "system_prompt": """你是一个专业的知识整理助手，负责将内容整理成知识卡片格式。

## 卡片要求
1. 提取核心知识点
2. 提供简明解释
3. 列出相关关键词
4. 提供使用场景或例子

## 输出格式
请按以下格式输出：
## 知识卡片

**标题**：[知识点名称]

**定义**：[简明定义]

**关键要点**
- [要点1]
- [要点2]
- [要点3]

**相关关键词**
[关键词1] [关键词2] [关键词3]

**使用场景**
[在什么场景下可以使用这个知识点]

**举例**
[简单例子说明]""",
        "user_template": "请将以下内容整理成知识卡片：\n\n{content}"
    }
}


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
