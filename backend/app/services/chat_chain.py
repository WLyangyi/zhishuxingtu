from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from app.services.llm_service import get_llm_service
from app.services.langchain_embeddings import get_langchain_embeddings
from app.services.langchain_vectorstore import get_langchain_vectorstore
from app.services.chat_memory_store import get_chat_memory_store
from app.core.config import settings
from datetime import datetime
import tiktoken

MAX_CONTEXT_MESSAGES = 10
MAX_CONTEXT_TOKENS = 3000

ROLE_PRESETS = {
    "知识问答助手": {
        "personality": "友善、专业、乐于助人",
        "speaking_style": "亲切、专业、简洁",
        "expertise": ["知识库问答", "笔记整理", "学习建议"],
        "temperature": 0.7
    },
    "技术专家": {
        "personality": "严谨、精确、逻辑性强",
        "speaking_style": "技术性强、使用专业术语、注重原理",
        "expertise": ["编程", "系统设计", "技术方案"],
        "temperature": 0.3
    },
    "创意写作助手": {
        "personality": "富有创意、想象力丰富",
        "speaking_style": "生动、富有感染力、多样化",
        "expertise": ["写作", "文案", "创意"],
        "temperature": 0.9
    },
    "学习教练": {
        "personality": "激励、耐心、循循善诱",
        "speaking_style": "鼓励性、启发式、耐心",
        "expertise": ["学习方法", "知识理解", "记忆技巧"],
        "temperature": 0.8
    }
}


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
    def __init__(self, system_prompt: str = None, role_name: str = None):
        self.llm = get_llm_service().client
        self.embeddings = get_langchain_embeddings()
        self.vectorstore = get_langchain_vectorstore()
        self.memory_store = get_chat_memory_store() if settings.USE_VECTOR_MEMORY else None
        self.system_prompt = system_prompt or DEFAULT_CHAT_SYSTEM_PROMPT
        self.role_name = role_name or "知识问答助手"
        self._histories: Dict[str, InMemoryChatMessageHistory] = {}
        self._token_counts: Dict[str, Dict[str, int]] = {}

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

    def _estimate_tokens(self, text: str) -> int:
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            return len(encoding.encode(text))
        except:
            return len(text) // 4

    def _truncate_history_by_tokens(self, messages: List[BaseMessage], max_tokens: int = MAX_CONTEXT_TOKENS) -> List[BaseMessage]:
        total_tokens = 0
        truncated = []
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens(msg.content)
            if total_tokens + msg_tokens <= max_tokens:
                truncated.insert(0, msg)
                total_tokens += msg_tokens
            else:
                break
        return truncated

    def _apply_role_config(self, base_prompt: str, role_name: str) -> str:
        if role_name not in ROLE_PRESETS:
            return base_prompt

        role = ROLE_PRESETS[role_name]
        role_section = f"""

## 角色配置
- 角色名称：{role_name}
- 性格特点：{role['personality']}
- 说话风格：{role['speaking_style']}
- 专业领域：{', '.join(role['expertise'])}

请根据以上角色配置调整你的回答方式和专业程度。"""

        if "## 角色配置" not in base_prompt:
            return base_prompt + role_section
        return base_prompt

    def invoke(
        self,
        question: str,
        history: Optional[List[Dict]] = None,
        context_docs: Optional[List[Tuple[Any, float]]] = None,
        session_id: Optional[str] = None,
        role_name: Optional[str] = None
    ) -> Dict[str, Any]:
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()
        effective_role = role_name or self.role_name

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
        system_content = self._apply_role_config(system_content, effective_role)
        messages.append(SystemMessage(content=system_content))

        vector_memory_context = ""
        if self.memory_store and session_id:
            vector_memory_context = self.memory_store.get_context_for_query(
                question,
                session_id=session_id
            )
        
        if history:
            history_messages = self._parse_history_from_json(history)
            history_messages = self._truncate_history_by_tokens(history_messages, MAX_CONTEXT_TOKENS)
            messages.extend(history_messages[-MAX_CONTEXT_MESSAGES:])
        
        if vector_memory_context:
            memory_message = HumanMessage(
                content=f"【相关的历史对话记忆】\n{vector_memory_context}\n\n请参考以上历史记忆回答当前问题。"
            )
            messages.insert(1, memory_message)
        
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
            
            if self.memory_store:
                self.memory_store.add_conversation(
                    user_message=question,
                    assistant_message=answer,
                    session_id=session_id
                )
            
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
