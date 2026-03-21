import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI
from app.core.config import settings


class StreamService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL

    def _get_weekday_cn(self) -> str:
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[datetime.now().weekday()]

    def _build_system_prompt(self, context: str, current_user_id: int = None, db=None) -> str:
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()
        
        if db:
            from app.api.routes.prompts import get_prompt_by_category, render_prompt
            prompt = get_prompt_by_category("ai_chat", current_user_id, db)
            if prompt:
                system_prompt, _ = render_prompt(
                    prompt,
                    current_date=current_date,
                    current_weekday=current_weekday,
                    context=context,
                    question=""
                )
                return system_prompt
        
        return f"""你是一个友善、专业的智能知识助手，名为"知枢星图AI助手"。

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
当涉及医疗、法律、金融等专业知识时，请提醒用户寻求专业人士的意见。"""

    def _build_user_prompt(self, message: str, context: str) -> str:
        if context:
            return f"""知识库相关内容：
{context}

---
用户消息：{message}

请根据以上知识库内容回答问题："""
        return message

    def _check_content(self, text: str) -> dict:
        from app.api.routes.prompts import multi_layer_content_check
        return multi_layer_content_check(text)

    def _apply_disclaimer(self, content: str) -> str:
        from app.api.routes.prompts import apply_disclaimer
        return apply_disclaimer(content)

    async def stream_chat(
        self,
        message: str,
        context_docs: List[Tuple[Any, float]],
        history: List[Dict] = None,
        current_user_id: int = None,
        db = None
    ) -> AsyncGenerator[str, None]:
        check_result = self._check_content(message)
        if not check_result["passed"]:
            error_msg = f"抱歉，您的消息无法处理：{check_result['reason']}"
            data = json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
            return

        context = ""
        source_notes = []
        if context_docs:
            context = "\n\n".join([
                f"【笔记: {note.title}】\n{note.content or '(无内容)'}"
                for note, score in context_docs
            ])
            source_notes = [{"id": note.id, "title": note.title} for note, _ in context_docs]

        system_prompt = self._build_system_prompt(context, current_user_id, db)
        user_prompt = self._build_user_prompt(message, context)

        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for h in history[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )

            full_content = ""
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content = delta.content
                        full_content += content
                        data = json.dumps({'type': 'content', 'text': content}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                    if chunk.choices[0].finish_reason == "stop":
                        break

            final_content = self._apply_disclaimer(full_content)
            if final_content != full_content:
                from app.api.routes.prompts import DISCLAIMER
                data = json.dumps({'type': 'disclaimer', 'text': DISCLAIMER}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            if source_notes:
                data = json.dumps({'type': 'sources', 'notes': source_notes}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"AI 服务暂时不可用：{str(e)}"
            data = json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"

    async def stream_rag(
        self,
        question: str,
        context_docs: List[Tuple[Any, float]],
        current_user_id: int = None,
        db = None
    ) -> AsyncGenerator[str, None]:
        from app.api.routes.prompts import EMPTY_RESULT_RESPONSE, DISCLAIMER
        
        check_result = self._check_content(question)
        if not check_result["passed"]:
            error_msg = f"抱歉，您的问题无法处理：{check_result['reason']}"
            data = json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
            return

        if not context_docs:
            data = json.dumps({'type': 'content', 'text': EMPTY_RESULT_RESPONSE}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
            return

        context = "\n\n".join([
            f"【笔记标题: {note.title}】\n{note.content or '(无内容)'}"
            for note, score in context_docs
        ])
        source_notes = [{"id": note.id, "title": note.title} for note, _ in context_docs]

        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()

        system_prompt = None
        user_prompt = None
        
        if db:
            from app.api.routes.prompts import get_prompt_by_category, render_prompt
            prompt = get_prompt_by_category("ai_search", current_user_id, db)
            if prompt:
                system_prompt, user_prompt = render_prompt(
                    prompt,
                    current_date=current_date,
                    current_weekday=current_weekday,
                    context=context,
                    question=question
                )
        
        if not system_prompt:
            system_prompt = f"""你是一个智能知识检索助手，帮助用户从个人知识库中找到相关信息并回答问题。

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
本回答仅供参考，如有重要决策请咨询专业人士。"""
            user_prompt = f"""以下是知识库中的相关笔记：

{context}

---

用户问题：{question}

请基于以上笔记内容回答问题："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )

            full_content = ""
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content = delta.content
                        full_content += content
                        data = json.dumps({'type': 'content', 'text': content}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                    if chunk.choices[0].finish_reason == "stop":
                        break

            final_content = self._apply_disclaimer(full_content)
            if final_content != full_content:
                data = json.dumps({'type': 'disclaimer', 'text': DISCLAIMER}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            if source_notes:
                data = json.dumps({'type': 'sources', 'notes': source_notes}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"AI 服务暂时不可用：{str(e)}"
            data = json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"


_stream_service_instance = None

def get_stream_service() -> StreamService:
    global _stream_service_instance
    if _stream_service_instance is None:
        _stream_service_instance = StreamService()
    return _stream_service_instance
