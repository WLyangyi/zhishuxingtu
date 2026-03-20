from typing import Dict, Optional
from app.services.llm_service import get_llm_service

class PromptEvaluator:
    """提示词效果评估引擎"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    def evaluate_response(
        self,
        question: str,
        response: str,
        context: Optional[str] = None
    ) -> Dict[str, float]:
        """
        自动评估AI回答质量
        
        Args:
            question: 用户问题
            response: AI回答
            context: 知识库上下文（可选）
        
        Returns:
            评估指标字典
        """
        relevance = self._evaluate_relevance(question, response)
        accuracy = self._evaluate_accuracy(response, context) if context else 7.0
        completeness = self._evaluate_completeness(question, response)
        clarity = self._evaluate_clarity(response)
        
        overall_score = (relevance + accuracy + completeness + clarity) / 4
        
        return {
            "relevance_score": relevance,
            "accuracy_score": accuracy,
            "completeness_score": completeness,
            "clarity_score": clarity,
            "overall_score": overall_score
        }
    
    def _evaluate_relevance(self, question: str, response: str) -> float:
        """评估相关性"""
        eval_prompt = f"""请评估以下AI回答与问题的相关性（1-10分）：

问题：{question}
回答：{response}

评分标准：
- 10分：完全相关，直接回答了问题
- 7-9分：比较相关，基本回答了问题
- 4-6分：部分相关，回答了一些相关内容
- 1-3分：不相关，没有回答问题

只输出分数（1-10的数字）："""
        
        try:
            result = self.llm_service.invoke(eval_prompt)
            score_str = result.content.strip()
            score = float(score_str)
            return max(1.0, min(10.0, score))
        except Exception as e:
            print(f"相关性评估失败: {e}")
            return 5.0
    
    def _evaluate_accuracy(self, response: str, context: str) -> float:
        """评估准确性（基于知识库）"""
        eval_prompt = f"""请评估以下AI回答的准确性（1-10分）：

知识库内容：
{context}

AI回答：
{response}

评分标准：
- 10分：完全准确，与知识库内容一致
- 7-9分：比较准确，大部分内容正确
- 4-6分：部分准确，有一些错误
- 1-3分：不准确，与知识库内容矛盾

只输出分数（1-10的数字）："""
        
        try:
            result = self.llm_service.invoke(eval_prompt)
            score_str = result.content.strip()
            score = float(score_str)
            return max(1.0, min(10.0, score))
        except Exception as e:
            print(f"准确性评估失败: {e}")
            return 5.0
    
    def _evaluate_completeness(self, question: str, response: str) -> float:
        """评估完整性"""
        eval_prompt = f"""请评估以下AI回答的完整性（1-10分）：

问题：{question}
回答：{response}

评分标准：
- 10分：完整回答，涵盖了问题的所有方面
- 7-9分：比较完整，回答了主要方面
- 4-6分：部分完整，遗漏了一些重要内容
- 1-3分：不完整，只回答了一小部分

只输出分数（1-10的数字）："""
        
        try:
            result = self.llm_service.invoke(eval_prompt)
            score_str = result.content.strip()
            score = float(score_str)
            return max(1.0, min(10.0, score))
        except Exception as e:
            print(f"完整性评估失败: {e}")
            return 5.0
    
    def _evaluate_clarity(self, response: str) -> float:
        """评估清晰度"""
        eval_prompt = f"""请评估以下AI回答的清晰度（1-10分）：

回答：
{response}

评分标准：
- 10分：非常清晰，结构良好，易于理解
- 7-9分：比较清晰，表达清楚
- 4-6分：部分清晰，有些地方不够清楚
- 1-3分：不清晰，难以理解

只输出分数（1-10的数字）："""
        
        try:
            result = self.llm_service.invoke(eval_prompt)
            score_str = result.content.strip()
            score = float(score_str)
            return max(1.0, min(10.0, score))
        except Exception as e:
            print(f"清晰度评估失败: {e}")
            return 5.0

_prompt_evaluator = None

def get_prompt_evaluator():
    global _prompt_evaluator
    if _prompt_evaluator is None:
        _prompt_evaluator = PromptEvaluator()
    return _prompt_evaluator
