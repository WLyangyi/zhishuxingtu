from typing import Dict, Optional

COT_TEMPLATES = {
    "step_by_step": """
请按照以下步骤思考并回答：

步骤1：理解问题
- 分析问题的核心需求
- 识别关键信息点

步骤2：信息检索
- 从知识库中提取相关信息
- 评估信息的可靠性

步骤3：推理分析
- 基于信息进行逻辑推理
- 考虑多种可能性

步骤4：得出结论
- 总结推理结果
- 给出明确答案

现在请回答：{question}
    """,
    
    "compare_analyze": """
请使用对比分析法回答：

## 分析框架
1. **维度识别**：列出需要对比的关键维度
2. **信息提取**：从知识库提取每个维度的信息
3. **对比分析**：逐维度对比差异
4. **综合评估**：给出整体建议

问题：{question}
知识库内容：{context}

请开始分析：
    """,
    
    "deep_reasoning": """
请进行深度推理：

## 推理链
1. **问题分解**：将复杂问题拆解为子问题
2. **假设生成**：提出可能的假设
3. **假设验证**：用知识库内容验证假设
4. **结论推导**：基于验证结果得出结论

问题：{question}
相关内容：{context}

推理过程：
    """
}

class CoTEngine:
    @staticmethod
    def apply_cot(prompt: str, cot_type: str, **kwargs) -> str:
        """
        应用思维链模板
        
        Args:
            prompt: 原始提示词
            cot_type: CoT类型（step_by_step/compare_analyze/deep_reasoning）
            **kwargs: 模板变量（question, context等）
        
        Returns:
            应用CoT后的提示词
        """
        if cot_type not in COT_TEMPLATES:
            return prompt
        
        cot_template = COT_TEMPLATES[cot_type]
        try:
            cot_prompt = cot_template.format(**kwargs)
            return f"{prompt}\n\n{cot_prompt}"
        except KeyError as e:
            return prompt
    
    @staticmethod
    def get_available_templates() -> Dict[str, str]:
        """获取所有可用的CoT模板"""
        return {
            "step_by_step": "分步推理：适用于复杂问题分析",
            "compare_analyze": "对比分析：适用于对比类问题",
            "deep_reasoning": "深度推理：适用于需要深度思考的问题"
        }
    
    @staticmethod
    def recommend_cot_type(question: str) -> str:
        """
        根据问题类型推荐CoT模板
        
        Args:
            question: 用户问题
        
        Returns:
            推荐的CoT类型
        """
        question_lower = question.lower()
        
        compare_keywords = ["区别", "对比", "比较", "差异", "优缺点", "vs", "versus"]
        if any(keyword in question_lower for keyword in compare_keywords):
            return "compare_analyze"
        
        reasoning_keywords = ["为什么", "原因", "原理", "如何实现", "怎么做到"]
        if any(keyword in question_lower for keyword in reasoning_keywords):
            return "deep_reasoning"
        
        return "step_by_step"
