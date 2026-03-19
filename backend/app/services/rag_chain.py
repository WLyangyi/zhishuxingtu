from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.services.llm_service import get_llm_service
from app.services.langchain_embeddings import get_langchain_embeddings
from app.services.langchain_vectorstore import get_langchain_vectorstore
from app.core.config import settings
from datetime import datetime


DEFAULT_SYSTEM_PROMPT = """你是一个智能知识检索助手，帮助用户从个人知识库中找到相关信息并回答问题。

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

DEFAULT_USER_PROMPT = """以下是知识库中的相关笔记：

{context}

---

用户问题：{question}

请基于以上笔记内容回答问题："""


class RAGChain:
    def __init__(self, system_prompt: str = None, user_prompt: str = None):
        self.llm = get_llm_service().client
        self.embeddings = get_langchain_embeddings()
        self.vectorstore = get_langchain_vectorstore()
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.user_prompt = user_prompt or DEFAULT_USER_PROMPT
        self._chain = None

    def _get_weekday_cn(self) -> str:
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[datetime.now().weekday()]

    def _format_docs(self, docs: List[Document]) -> str:
        if not docs:
            return "(没有找到相关笔记)"
        return "\n\n".join([
            f"【笔记标题: {doc.metadata.get('title', '未知')}】\n{doc.page_content}"
            for doc in docs
        ])

    def _build_chain(self):
        if self._chain is not None:
            return self._chain

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", self.user_prompt)
        ])

        def retrieve_and_format(query: str) -> Dict[str, Any]:
            current_date = datetime.now().strftime("%Y年%m月%d日")
            current_weekday = self._get_weekday_cn()
            
            if self.vectorstore.is_ready:
                docs = self.vectorstore.similarity_search(query, k=5)
            else:
                docs = []
            
            context = self._format_docs(docs)
            
            return {
                "context": context,
                "question": query,
                "current_date": current_date,
                "current_weekday": current_weekday,
                "source_documents": docs
            }

        self._chain = (
            RunnablePassthrough.assign(
                context_info=lambda x: retrieve_and_format(x["question"])
            )
            | {
                "answer": (
                    prompt 
                    | self.llm 
                    | StrOutputParser()
                ),
                "context": lambda x: x["context_info"]["context"],
                "source_documents": lambda x: x["context_info"]["source_documents"]
            }
        )

        return self._chain

    def invoke(self, question: str) -> Dict[str, Any]:
        chain = self._build_chain()
        
        try:
            result = chain.invoke({"question": question})
            
            source_notes = []
            for doc in result.get("source_documents", []):
                note_id = doc.metadata.get("note_id", "")
                title = doc.metadata.get("title", "未知")
                source_notes.append({"id": note_id, "title": title})
            
            return {
                "answer": result["answer"],
                "context": result["context"],
                "source_documents": source_notes
            }
        except Exception as e:
            return {
                "answer": f"AI 服务暂时不可用，请稍后再试。错误信息：{str(e)}",
                "context": "",
                "source_documents": []
            }

    def invoke_with_custom_context(
        self, 
        question: str, 
        context_docs: List[Tuple[Any, float]]
    ) -> Dict[str, Any]:
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_weekday = self._get_weekday_cn()
        
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", self.user_prompt)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            answer = chain.invoke({
                "context": context,
                "question": question,
                "current_date": current_date,
                "current_weekday": current_weekday
            })
            
            source_notes = [{"id": n.id, "title": n.title} for n, _ in context_docs]
            
            return {
                "answer": answer,
                "context": context,
                "source_documents": source_notes
            }
        except Exception as e:
            return {
                "answer": f"AI 服务暂时不可用，请稍后再试。错误信息：{str(e)}",
                "context": context,
                "source_documents": [{"id": n.id, "title": n.title} for n, _ in context_docs]
            }


_rag_chain_instance = None

def get_rag_chain() -> RAGChain:
    global _rag_chain_instance
    if _rag_chain_instance is None:
        _rag_chain_instance = RAGChain()
    return _rag_chain_instance
