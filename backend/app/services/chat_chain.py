from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from app.services.llm_service import get_llm_service
from app.services.langchain_embeddings import get_langchain_embeddings
from app.services.langchain_vectorstore import get_langchain_vectorstore
from app.core.config import settings
from datetime import datetime


DEFAULT_CHAT_SYSTEM_PROMPT = """你是一个友善、专业的智能知识助手，名为"知枢星图AI助手"。

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

DEFAULT_CHAT_USER_PROMPT_WITH_CONTEXT = """知识库相关内容：
{context}

---
用户消息：{question}

请根据以上知识库内容回答问题："""

DEFAULT_CHAT_USER_PROMPT_NO_CONTEXT = "{question}"


class ChatChain:
    def __init__(self, system_prompt: str = None):
        self.llm = get_llm_service().client
        self.embeddings = get_langchain_embeddings()
        self.vectorstore = get_langchain_vectorstore()
        self.system_prompt = system_prompt or DEFAULT_CHAT_SYSTEM_PROMPT
        self._histories: Dict[str, InMemoryChatMessageHistory] = {}

    def _get_weekday_cn(self) -> str:
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[datetime.now().weekday()]

    def _format_docs(self, docs: List[Document]) -> str:
        if not docs:
            return ""
        return "\n\n".join([
            f"【笔记: {doc.metadata.get('title', '未知')}】\n{doc.page_content}"
            for doc in docs
        ])

    def _get_or_create_history(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self._histories:
            self._histories[session_id] = InMemoryChatMessageHistory()
        return self._histories[session_id]

    def _parse_history_from_json(self, history_json: List[Dict]) -> List[BaseMessage]:
        messages = []
        for h in history_json:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def invoke(
        self,
        question: str,
        history: Optional[List[Dict]] = None,
        context_docs: Optional[List[Tuple[Any, float]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()
        
        context = ""
        source_notes = []
        
        if context_docs:
            docs = []
            for note, score in context_docs:
                doc = Document(
                    page_content=note.content or "(无内容)",
                    metadata={
                        "note_id": note.id,
                        "title": note.title,
                        "score": score
                    }
                )
                docs.append(doc)
            context = self._format_docs(docs)
            source_notes = [{"id": n.id, "title": n.title} for n, _ in context_docs]
        
        messages = []
        
        system_content = self.system_prompt.format(
            current_date=current_date,
            current_weekday=current_weekday
        )
        messages.append(SystemMessage(content=system_content))
        
        if history:
            history_messages = self._parse_history_from_json(history)
            messages.extend(history_messages[-6:])
        
        if context:
            user_content = DEFAULT_CHAT_USER_PROMPT_WITH_CONTEXT.format(
                context=context,
                question=question
            )
        else:
            user_content = DEFAULT_CHAT_USER_PROMPT_NO_CONTEXT.format(question=question)
        
        messages.append(HumanMessage(content=user_content))
        
        try:
            response = self.llm.invoke(messages)
            answer = response.content
            
            return {
                "answer": answer,
                "context": context,
                "source_documents": source_notes
            }
        except Exception as e:
            return {
                "answer": f"抱歉，AI 服务暂时不可用。错误信息：{str(e)}",
                "context": context,
                "source_documents": source_notes
            }

    def invoke_with_chain(
        self,
        question: str,
        history: Optional[List[Dict]] = None,
        context_docs: Optional[List[Tuple[Any, float]]] = None
    ) -> Dict[str, Any]:
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()
        
        context = ""
        source_notes = []
        
        if context_docs:
            docs = []
            for note, score in context_docs:
                doc = Document(
                    page_content=note.content or "(无内容)",
                    metadata={
                        "note_id": note.id,
                        "title": note.title,
                        "score": score
                    }
                )
                docs.append(doc)
            context = self._format_docs(docs)
            source_notes = [{"id": n.id, "title": n.title} for n, _ in context_docs]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        chat_history = []
        if history:
            chat_history = self._parse_history_from_json(history)
        
        user_input = DEFAULT_CHAT_USER_PROMPT_WITH_CONTEXT.format(
            context=context,
            question=question
        ) if context else question
        
        try:
            answer = chain.invoke({
                "current_date": current_date,
                "current_weekday": current_weekday,
                "chat_history": chat_history[-6:],
                "input": user_input
            })
            
            return {
                "answer": answer,
                "context": context,
                "source_documents": source_notes
            }
        except Exception as e:
            return {
                "answer": f"抱歉，AI 服务暂时不可用。错误信息：{str(e)}",
                "context": context,
                "source_documents": source_notes
            }

    def clear_history(self, session_id: str = None):
        if session_id:
            if session_id in self._histories:
                del self._histories[session_id]
        else:
            self._histories.clear()


_chat_chain_instance = None

def get_chat_chain() -> ChatChain:
    global _chat_chain_instance
    if _chat_chain_instance is None:
        _chat_chain_instance = ChatChain()
    return _chat_chain_instance
