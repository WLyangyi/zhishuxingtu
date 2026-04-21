import json
import re
import threading
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from openai import OpenAI
from app.db.session import get_db
from app.models.note import Note
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User
from app.schemas import Response, NoteResponse, NoteListResponse, GraphResponse, GraphNode, GraphEdge
from app.api.deps import get_current_user
from app.core.config import settings
from app.services import get_vector_store
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStoreError
from app.services.vector_store_adapter import get_vector_store_adapter
from app.api.routes.prompts import get_prompt_by_category, render_prompt, check_sensitive_words, filter_sensitive_content, apply_disclaimer, DISCLAIMER, EMPTY_RESULT_RESPONSE, multi_layer_content_check
from app.services.rag_chain import get_rag_chain
from app.services.chat_chain import get_chat_chain
from app.services.reranker_service import get_reranker
from app.services.stream_service import get_stream_service
from app.services.hybrid_search import get_hybrid_search_service, init_hybrid_search
from app.services.bm25_service import get_bm25_service


def vector_search_notes(
    query: str, 
    db: Session, 
    k: int = 5, 
    threshold: float = 0.3,
    use_reranker: bool = True
) -> List[tuple]:
    """
    向量搜索笔记，可选使用 Reranker 重排序
    
    Args:
        query: 搜索查询
        db: 数据库会话
        k: 返回结果数量
        threshold: 相似度阈值
        use_reranker: 是否使用 Reranker 重排序
    
    Returns:
        笔记列表，格式为 [(Note对象, score), ...]
    """
    if not embedding_service.available:
        return []

    vector_store = get_vector_store()
    if not vector_store or vector_store.total_vectors == 0:
        return []

    try:
        query_vector = embedding_service.embed_text(query)
        
        if use_reranker and settings.USE_RERANKER:
            candidates_k = settings.RERANKER_CANDIDATES
            results = vector_store.search(query_vector, k=candidates_k, threshold=threshold)
            
            notes = []
            for note_id, score in results:
                note = db.query(Note).filter(Note.id == note_id).first()
                if note:
                    notes.append((note, score))
            
            if notes:
                reranker = get_reranker()
                if reranker.available:
                    reranked_notes = reranker.rerank_with_notes(
                        query, 
                        notes, 
                        top_k=k
                    )
                    return reranked_notes
            
            return notes[:k]
        else:
            results = vector_store.search(query_vector, k=k, threshold=threshold)

            notes = []
            for note_id, score in results:
                note = db.query(Note).filter(Note.id == note_id).first()
                if note:
                    notes.append((note, score))

            return notes
    except VectorStoreError as e:
        print(f"Vector search error: {e}")
        return []
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []


def keyword_search_notes(query: str, db: Session, max_results: int = 5) -> List[Note]:
    keywords = extract_keywords(query, max_keywords=5)
    notes = []
    for kw in keywords:
        found = db.query(Note).filter(
            (Note.title.contains(kw)) | (Note.content.contains(kw))
        ).limit(3).all()
        notes.extend(found)

    seen_ids = set()
    unique_notes = []
    for n in notes:
        if n.id not in seen_ids:
            seen_ids.add(n.id)
            unique_notes.append(n)
    return unique_notes[:max_results]


router = APIRouter(prefix="/search", tags=["搜索"])

def get_llm_client():
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL
    )

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    keywords = []
    english_words = re.findall(r'[a-zA-Z]+', text)
    keywords.extend([w for w in english_words if len(w) > 2][:max_keywords])
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for phrase in chinese_chars:
        if len(phrase) >= 2:
            for i in range(0, len(phrase) - 1, 2):
                keywords.append(phrase[i:i+2])
                if len(keywords) >= max_keywords:
                    break
        if len(keywords) >= max_keywords:
            break
    if not keywords:
        keywords = [text[:10]]
    return keywords[:max_keywords]

@router.get("", response_model=Response[NoteListResponse])
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = db.query(Note).filter(
        (Note.title.contains(q)) | (Note.content.contains(q))
    ).order_by(Note.updated_at.desc()).all()

    total = len(notes)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = notes[start:end]

    items = []
    for note in paginated:
        note_dict = {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "folder_id": note.folder_id,
            "linked_note_ids": json.loads(note.linked_note_ids) if note.linked_note_ids else [],
            "tags": [],
            "created_at": note.created_at,
            "updated_at": note.updated_at
        }
        items.append(note_dict)

    return Response(data=NoteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    ))

@router.post("/ai")
async def ai_search(
    question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if settings.USE_LANGCHAIN_RAG:
        return await ai_search_langchain(question, current_user, db)
    return await ai_search_original(question, current_user, db)


async def ai_search_langchain(
    question: str,
    current_user: User,
    db: Session
):
    check_result = multi_layer_content_check(question)
    if not check_result["passed"]:
        return Response(data={
            "answer": f"抱歉，您的问题无法处理：{check_result['reason']}",
            "context": "",
            "notes": []
        })

    vector_results = hybrid_search_notes(question, db, k=5, use_reranker=True)

    if not vector_results:
        return Response(data={
            "answer": EMPTY_RESULT_RESPONSE,
            "context": "",
            "notes": []
        })

    rag_chain = get_rag_chain()
    result = rag_chain.invoke_with_custom_context(question, vector_results)
    
    answer = apply_disclaimer(result["answer"])

    return Response(data={
        "answer": answer,
        "context": result["context"],
        "notes": result["source_documents"]
    })


async def ai_search_original(
    question: str,
    current_user: User,
    db: Session
):
    check_result = multi_layer_content_check(question)
    if not check_result["passed"]:
        return Response(data={
            "answer": f"抱歉，您的问题无法处理：{check_result['reason']}",
            "context": "",
            "notes": []
        })

    vector_results = hybrid_search_notes(question, db, k=5, use_reranker=True)

    if vector_results:
        unique_notes = [note for note, score in vector_results]
    else:
        unique_notes = keyword_search_notes(question, db, max_results=5)

    if not unique_notes:
        return Response(data={
            "answer": EMPTY_RESULT_RESPONSE,
            "context": "",
            "notes": []
        })

    context = "\n\n".join([
        f"【笔记标题: {n.title}】\n{n.content or '(无内容)'}"
        for n in unique_notes
    ])

    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    current_date = datetime.now().strftime("%Y年%m月%d日")
    current_weekday = weekdays[datetime.now().weekday()]

    prompt = get_prompt_by_category("ai_search", current_user.id, db)
    if prompt:
        system_prompt, user_prompt = render_prompt(
            prompt,
            current_date=current_date,
            current_weekday=current_weekday,
            context=context,
            question=question
        )
    else:
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

    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        answer = apply_disclaimer(answer)
    except Exception as e:
        answer = f"AI 服务暂时不可用，请稍后再试。错误信息：{str(e)}"

    return Response(data={
        "answer": answer,
        "context": context,
        "notes": [{"id": n.id, "title": n.title} for n in unique_notes]
    })

@router.post("/chat")
async def ai_chat(
    message: str,
    history: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if settings.USE_LANGCHAIN_CHAT:
        return await ai_chat_langchain(message, history, session_id, current_user, db)
    return await ai_chat_original(message, history, current_user, db)


async def ai_chat_langchain(
    message: str,
    history: Optional[str],
    session_id: Optional[str],
    current_user: User,
    db: Session
):
    check_result = multi_layer_content_check(message)
    if not check_result["passed"]:
        return Response(data={
            "answer": f"抱歉，您的消息无法处理：{check_result['reason']}",
            "notes": []
        })

    vector_results = hybrid_search_notes(message, db, k=3, use_reranker=True)

    history_list = None
    if history:
        try:
            history_list = json.loads(history)
        except:
            pass

    chat_chain = get_chat_chain()
    result = chat_chain.invoke(
        question=message,
        history=history_list,
        context_docs=vector_results,
        session_id=session_id or current_user.id
    )
    
    answer = apply_disclaimer(result["answer"])

    return Response(data={
        "answer": answer,
        "notes": result["source_documents"]
    })


async def ai_chat_original(
    message: str,
    history: Optional[str],
    current_user: User,
    db: Session
):
    check_result = multi_layer_content_check(message)
    if not check_result["passed"]:
        return Response(data={
            "answer": f"抱歉，您的消息无法处理：{check_result['reason']}",
            "notes": []
        })

    vector_results = hybrid_search_notes(message, db, k=3, use_reranker=True)

    if vector_results:
        unique_notes = [note for note, score in vector_results]
    else:
        unique_notes = keyword_search_notes(message, db, max_results=3)

    context = ""
    if unique_notes:
        context = "\n\n".join([
            f"【笔记: {n.title}】\n{n.content or '(无内容)'}"
            for n in unique_notes
        ])

    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    current_date = datetime.now().strftime("%Y年%m月%d日")
    current_weekday = weekdays[datetime.now().weekday()]

    prompt = get_prompt_by_category("ai_chat", current_user.id, db)
    if prompt:
        system_prompt, user_prompt = render_prompt(
            prompt,
            current_date=current_date,
            current_weekday=current_weekday,
            context=context,
            question=message
        )
    else:
        system_prompt = f"""你是一个友善、专业的智能知识助手，名为"知枢星图AI助手"。

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

        if context:
            user_prompt = f"""知识库相关内容：
{context}

---
用户消息：{message}

请根据以上知识库内容回答问题："""
        else:
            user_prompt = message

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        try:
            history_list = json.loads(history)
            for h in history_list[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        except:
            pass

    messages.append({"role": "user", "content": user_prompt})

    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        answer = apply_disclaimer(answer)
    except Exception as e:
        answer = f"抱歉，AI 服务暂时不可用。错误信息：{str(e)}"

    return Response(data={
        "answer": answer,
        "notes": [{"id": n.id, "title": n.title} for n in unique_notes]
    })


@router.get("/vector")
async def vector_search(
    q: str = Query(..., min_length=1, description="搜索查询文本"),
    k: int = Query(5, ge=1, le=20, description="返回结果数量"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="相似度阈值"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not embedding_service.available:
        return Response(
            code=503,
            message="向量搜索服务不可用，模型未加载",
            data={"results": [], "engine": "unavailable"}
        )

    vector_store = get_vector_store()
    if not vector_store or vector_store.total_vectors == 0:
        return Response(
            data={
                "results": [],
                "engine": "vector",
                "total_vectors": 0,
                "message": "向量索引为空，请先添加笔记"
            }
        )

    try:
        vector_results = vector_search_notes(q, db, k=k, threshold=threshold)

        results = []
        for note, score in vector_results:
            results.append({
                "id": note.id,
                "title": note.title,
                "content": note.content[:200] + "..." if note.content and len(note.content) > 200 else note.content,
                "score": round(score, 4),
                "folder_id": note.folder_id,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            })

        return Response(data={
            "results": results,
            "engine": "vector",
            "total_vectors": vector_store.total_vectors,
            "query": q,
            "threshold": threshold
        })

    except VectorStoreError as e:
        return Response(
            code=500,
            message=f"向量搜索错误: {str(e)}",
            data={"results": [], "engine": "error"}
        )


@router.post("/vector/batch")
async def batch_vector_search(
    queries: List[str] = Body(..., description="查询文本列表"),
    k: int = Query(5, ge=1, le=20, description="每个查询返回结果数量"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="相似度阈值"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not embedding_service.available:
        return Response(
            code=503,
            message="向量搜索服务不可用，模型未加载",
            data={"results": [], "engine": "unavailable"}
        )

    vector_store = get_vector_store()
    if not vector_store or vector_store.total_vectors == 0:
        return Response(
            data={
                "results": [],
                "engine": "vector",
                "total_vectors": 0,
                "message": "向量索引为空"
            }
        )

    if not queries:
        return Response(
            code=400,
            message="查询列表不能为空",
            data={"results": []}
        )

    if len(queries) > 10:
        return Response(
            code=400,
            message="批量查询最多支持 10 个查询",
            data={"results": []}
        )

    try:
        query_vectors = embedding_service.embed_texts(queries)
        batch_results = vector_store.batch_search(query_vectors, k=k, threshold=threshold)

        all_results = []
        for i, query_results in enumerate(batch_results):
            query_item = {
                "query": queries[i],
                "results": []
            }

            for note_id, score in query_results:
                note = db.query(Note).filter(Note.id == note_id).first()
                if note:
                    query_item["results"].append({
                        "id": note.id,
                        "title": note.title,
                        "score": round(score, 4),
                        "content_preview": note.content[:100] + "..." if note.content and len(note.content) > 100 else note.content
                    })

            all_results.append(query_item)

        return Response(data={
            "results": all_results,
            "engine": "vector",
            "total_vectors": vector_store.total_vectors,
            "query_count": len(queries)
        })

    except VectorStoreError as e:
        return Response(
            code=500,
            message=f"批量向量搜索错误: {str(e)}",
            data={"results": [], "engine": "error"}
        )


@router.get("/vector/status")
async def vector_store_status(
    current_user: User = Depends(get_current_user)
):
    vector_store = get_vector_store()

    status = {
        "embedding_service": {
            "available": embedding_service.available,
            "dimension": embedding_service.dimension,
            "model": getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        },
        "vector_store": {
            "initialized": False,
            "total_vectors": 0,
            "dimension": 384
        }
    }

    if vector_store:
        stats = vector_store.get_stats()
        status["vector_store"] = {
            "initialized": vector_store.is_ready,
            "total_vectors": stats["total_vectors"],
            "dimension": stats["dimension"],
            "index_path": stats["index_path"],
            "stats": stats["stats"]
        }

    return Response(data=status)


@router.post("/vector/rebuild")
async def rebuild_vector_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not embedding_service.available:
        return Response(
            code=503,
            message="向量服务不可用，无法重建索引",
            data={}
        )

    vector_store = get_vector_store()
    if not vector_store:
        return Response(
            code=500,
            message="向量存储未初始化",
            data={}
        )

    try:
        notes = db.query(Note).all()

        if not notes:
            return Response(data={
                "message": "没有笔记需要重建索引",
                "total": 0,
                "success": 0
            })

        note_ids = []
        texts = []

        for note in notes:
            if note.content:
                note_ids.append(note.id)
                text = embedding_service.prepare_note_text(note.title, note.content)
                texts.append(text)

        if not texts:
            return Response(data={
                "message": "没有有效内容的笔记",
                "total": len(notes),
                "success": 0
            })

        vectors = embedding_service.embed_texts(texts)
        result = vector_store.rebuild_index(note_ids, vectors)
        vector_store.save()

        return Response(data={
            "message": "向量索引重建完成",
            "total": len(notes),
            "success": result["success"],
            "failed": result["failed"],
            "errors": result["errors"][:5] if result["errors"] else []
        })

    except Exception as e:
        return Response(
            code=500,
            message=f"重建索引失败: {str(e)}",
            data={}
        )


@router.get("/reranker/test")
async def test_reranker(
    q: str = Query(..., min_length=1, description="搜索查询文本"),
    k: int = Query(5, ge=1, le=20, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    测试 Reranker 效果，对比重排序前后的结果差异
    
    返回：
    - before: 重排序前的结果（按向量相似度排序）
    - after: 重排序后的结果（按 Reranker 分数排序）
    - reranker_available: Reranker 服务是否可用
    """
    reranker = get_reranker()
    
    if not embedding_service.available:
        return Response(
            code=503,
            message="向量搜索服务不可用",
            data={"before": [], "after": [], "reranker_available": False}
        )
    
    vector_store = get_vector_store()
    if not vector_store or vector_store.total_vectors == 0:
        return Response(
            data={
                "before": [],
                "after": [],
                "reranker_available": reranker.available,
                "message": "向量索引为空"
            }
        )
    
    try:
        candidates_k = max(k * 3, 15)
        before_results = vector_search_notes(q, db, k=candidates_k, threshold=0.2, use_reranker=False)
        
        before_data = []
        for i, (note, score) in enumerate(before_results[:k]):
            before_data.append({
                "rank": i + 1,
                "id": note.id,
                "title": note.title,
                "score": round(score, 4),
                "content_preview": note.content[:100] + "..." if note.content and len(note.content) > 100 else note.content
            })
        
        after_data = []
        if reranker.available and before_results:
            reranked = reranker.rerank_with_notes(q, before_results, top_k=k)
            
            for i, (note, score) in enumerate(reranked):
                after_data.append({
                    "rank": i + 1,
                    "id": note.id,
                    "title": note.title,
                    "rerank_score": round(score, 4),
                    "content_preview": note.content[:100] + "..." if note.content and len(note.content) > 100 else note.content
                })
        
        return Response(data={
            "query": q,
            "before": before_data,
            "after": after_data,
            "reranker_available": reranker.available,
            "use_reranker": settings.USE_RERANKER,
            "candidates_count": len(before_results)
        })
        
    except Exception as e:
        return Response(
            code=500,
            message=f"测试失败: {str(e)}",
            data={"before": [], "after": [], "reranker_available": reranker.available}
        )


@router.get("/reranker/status")
async def reranker_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取 Reranker 服务状态
    """
    reranker = get_reranker()
    
    return Response(data={
        "available": reranker.available,
        "model": reranker.model if reranker.available else None,
        "use_reranker": settings.USE_RERANKER,
        "top_k": settings.RERANKER_TOP_K,
        "candidates": settings.RERANKER_CANDIDATES,
        "api_configured": bool(settings.DASHSCOPE_API_KEY)
    })


@router.post("/chat/stream")
async def ai_chat_stream(
    message: str,
    history: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI对话流式输出接口 (SSE)
    
    返回格式：
    - data: {"type": "content", "text": "..."}  内容片段
    - data: {"type": "sources", "notes": [...]}  相关笔记
    - data: {"type": "disclaimer", "text": "..."}  免责声明
    - data: {"type": "error", "message": "..."}  错误信息
    - data: [DONE]  结束标记
    """
    vector_results = hybrid_search_notes(message, db, k=3, use_reranker=True)
    
    history_list = None
    if history:
        try:
            history_list = json.loads(history)
        except:
            pass
    
    stream_service = get_stream_service()
    
    return StreamingResponse(
        stream_service.stream_chat(
            message=message,
            context_docs=vector_results,
            history=history_list,
            current_user_id=current_user.id,
            db=db
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/ai/stream")
async def ai_search_stream(
    question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI搜索流式输出接口 (SSE)
    
    返回格式：
    - data: {"type": "content", "text": "..."}  内容片段
    - data: {"type": "sources", "notes": [...]}  相关笔记
    - data: {"type": "disclaimer", "text": "..."}  免责声明
    - data: {"type": "error", "message": "..."}  错误信息
    - data: [DONE]  结束标记
    """
    vector_results = hybrid_search_notes(question, db, k=5, use_reranker=True)
    
    stream_service = get_stream_service()
    
    return StreamingResponse(
        stream_service.stream_rag(
            question=question,
            context_docs=vector_results,
            current_user_id=current_user.id,
            db=db
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class RebuildStatus:
    _instances: dict = {}
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.is_running = False
        self.total = 0
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.started_at = None
        self.completed_at = None
        self.error = None
    
    @classmethod
    def get(cls, user_id: str):
        if user_id not in cls._instances:
            cls._instances[user_id] = cls(user_id)
        return cls._instances[user_id]
    
    def to_dict(self):
        return {
            "is_running": self.is_running,
            "total": self.total,
            "processed": self.processed,
            "success": self.success,
            "failed": self.failed,
            "progress_percent": round(self.processed / self.total * 100, 1) if self.total > 0 else 0,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


_rebuild_locks: dict = {}


def _rebuild_index_in_background(user_id: str, db_session_factory):
    from datetime import datetime
    from app.db.session import SessionLocal
    
    status = RebuildStatus.get(user_id)
    lock = _rebuild_locks.get(user_id)
    
    try:
        db = SessionLocal()
        vector_store = get_vector_store_adapter()
        
        notes = db.query(Note).filter(Note.user_id == user_id).all()
        status.total = len(notes)
        status.started_at = datetime.now()
        
        for i, note in enumerate(notes):
            if not status.is_running:
                break
            
            try:
                if note.content:
                    chunks, vectors = embedding_service.embed_chunks(
                        note.id, note.title, note.content
                    )
                    if chunks and len(vectors) > 0:
                        vector_store.add_note_chunks(note.id, chunks, vectors)
                        status.success += 1
                status.processed += 1
            except Exception as e:
                print(f"Failed to process note {note.id}: {e}")
                status.failed += 1
                status.processed += 1
        
        vector_store.save()
        status.completed_at = datetime.now()
    except Exception as e:
        status.error = str(e)
        print(f"Background rebuild failed: {e}")
    finally:
        status.is_running = False
        if user_id in _rebuild_locks:
            del _rebuild_locks[user_id]
        try:
            db.close()
        except:
            pass


@router.post("/vector/rebuild-chunks/background")
async def rebuild_vector_index_background(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    后台重建向量索引（使用语义分块）
    
    在后台线程中处理，不阻塞用户请求。
    可通过 GET /vector/rebuild-chunks/status 查询进度。
    """
    user_id = str(current_user.id)
    
    status = RebuildStatus.get(user_id)
    
    if status.is_running:
        return Response(
            code=409,
            message="索引重建正在进行中",
            data=status.to_dict()
        )
    
    notes = db.query(Note).filter(Note.user_id == user_id).all()
    
    if not notes:
        return Response(data={
            "message": "没有笔记需要重建索引",
            "total": 0,
            "success": 0
        })
    
    _rebuild_locks[user_id] = threading.Lock()
    status.is_running = True
    status.total = len(notes)
    status.processed = 0
    status.success = 0
    status.failed = 0
    status.error = None
    
    thread = threading.Thread(
        target=_rebuild_index_in_background,
        args=(user_id, None),
        daemon=True
    )
    thread.start()
    
    return Response(data={
        "message": "索引重建已在后台启动",
        "total": status.total,
        "status": status.to_dict()
    })


@router.get("/vector/rebuild-chunks/status")
async def get_rebuild_status(
    current_user: User = Depends(get_current_user)
):
    """查询后台索引重建进度"""
    user_id = str(current_user.id)
    status = RebuildStatus.get(user_id)
    
    return Response(data=status.to_dict())


@router.post("/vector/rebuild-chunks/stop")
async def stop_rebuild(
    current_user: User = Depends(get_current_user)
):
    """停止后台索引重建"""
    user_id = str(current_user.id)
    status = RebuildStatus.get(user_id)
    
    if not status.is_running:
        return Response(message="没有正在运行的重建任务")
    
    status.is_running = False
    
    return Response(message="已请求停止重建任务", data=status.to_dict())


# ==================== BM25 混合检索 API (V3.7) ====================

def hybrid_search_notes(
    query: str,
    db: Session,
    k: int = 10,
    use_reranker: bool = True
) -> List[tuple]:
    """
    混合检索笔记（向量 + BM25 融合）
    
    Args:
        query: 搜索查询
        db: 数据库会话
        k: 返回结果数量
        use_reranker: 是否使用 Reranker 重排序
        
    Returns:
        笔记列表，格式为 [(Note对象, score), ...]
    """
    if not settings.USE_HYBRID_SEARCH:
        return vector_search_notes(query, db, k=k, threshold=0.3, use_reranker=use_reranker)

    try:
        hybrid_service = get_hybrid_search_service()
        
        if not hybrid_service or not hybrid_service.is_ready:
            return vector_search_notes(query, db, k=k, threshold=0.3, use_reranker=use_reranker)

        results = hybrid_service.hybrid_search(
            query=query,
            db=db,
            k=k,
            use_reranker=use_reranker
        )

        return results

    except Exception as e:
        print(f"Hybrid search error, falling back to vector: {e}")
        return vector_search_notes(query, db, k=k, threshold=0.3, use_reranker=use_reranker)


@router.get("/hybrid", response_model=Response)
async def hybrid_search_endpoint(
    q: str = Query(..., min_length=1, description="搜索查询文本"),
    k: int = Query(10, ge=1, le=20, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    混合检索 API - 融合向量语义检索和BM25关键词检索
    
    使用RRF（Reciprocal Rank Fusion）算法融合两种检索结果，
    提供更全面的搜索结果。
    
    参数:
        q: 搜索查询文本
        k: 返回结果数量
        
    返回:
        {
            "results": [...],
            "engine": "hybrid",
            "vector_count": 10,
            "bm25_count": 8,
            "fusion_method": "RRF"
        }
    """
    try:
        results = hybrid_search_notes(q, db, k=k, use_reranker=False)

        result_data = []
        for note, score in results:
            result_data.append({
                "id": note.id,
                "title": note.title,
                "content": note.content[:200] + "..." if note.content and len(note.content) > 200 else note.content,
                "score": round(score, 4),
                "folder_id": note.folder_id,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            })

        return Response(data={
            "results": result_data,
            "engine": "hybrid",
            "query": q,
            "total": len(result_data),
            "fusion_method": "RRF",
            "vector_weight": settings.VECTOR_WEIGHT,
            "bm25_weight": settings.BM25_WEIGHT
        })

    except Exception as e:
        return Response(
            code=500,
            message=f"混合检索错误: {str(e)}",
            data={"results": [], "engine": "error"}
        )


@router.get("/bm25", response_model=Response)
async def bm25_search_endpoint(
    q: str = Query(..., min_length=1, description="搜索查询文本"),
    k: int = Query(15, ge=1, le=30, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    纯 BM25 关键词检索 API
    
    基于BM25算法的关键词匹配检索，适合精确术语搜索。
    
    参数:
        q: 搜索查询文本
        k: 返回结果数量
    """
    try:
        bm25_service = get_bm25_service()
        
        if not bm25_service or not bm25_service.is_ready:
            return Response(
                code=503,
                message="BM25 索引未就绪，请先构建索引",
                data={"results": [], "engine": "bm25_unavailable"}
            )

        results = bm25_service.search(query=q, top_k=k)

        result_data = []
        for doc_id, score in results:
            note = db.query(Note).filter(Note.id == doc_id).first()
            if note:
                result_data.append({
                    "id": note.id,
                    "title": note.title,
                    "content": note.content[:200] + "..." if note.content and len(note.content) > 200 else note.content,
                    "score": round(score, 4),
                    "folder_id": note.folder_id,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                    "updated_at": note.updated_at.isoformat() if note.updated_at else None
                })

        return Response(data={
            "results": result_data,
            "engine": "bm25",
            "query": q,
            "total": len(result_data),
            "index_stats": bm25_service.get_stats()
        })

    except Exception as e:
        return Response(
            code=500,
            message=f"BM25检索错误: {str(e)}",
            data={"results": [], "engine": "error"}
        )


@router.get("/bm25/status", response_model=Response)
async def bm25_status(current_user: User = Depends(get_current_user)):
    """获取 BM25 索引状态"""
    bm25_service = get_bm25_service()
    hybrid_service = get_hybrid_search_service()

    status = {
        "bm25": {
            "ready": False,
            "stats": {}
        },
        "hybrid": {
            "enabled": settings.USE_HYBRID_SEARCH,
            "vector_weight": settings.VECTOR_WEIGHT,
            "bm25_weight": settings.BM25_WEIGHT,
            "rrf_k": settings.RRF_K
        }
    }

    if bm25_service:
        status["bm25"]["ready"] = bm25_service.is_ready
        status["bm25"]["stats"] = bm25_service.get_stats()

    if hybrid_service:
        status.update(hybrid_service.get_status())

    return Response(data=status)


@router.post("/bm25/rebuild", response_model=Response)
async def rebuild_bm25_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重建 BM25 索引
    
    从数据库重新加载所有笔记并构建BM25索引。
    对于新增、修改或删除的笔记后，需要调用此接口更新索引。
    """
    try:
        bm25_service = get_bm25_service()
        
        if not bm25_service:
            return Response(
                code=500,
                message="BM25服务未初始化",
                data={}
            )

        result = bm25_service.rebuild_index(db)

        return Response(data=result)

    except Exception as e:
        return Response(
            code=500,
            message=f"重建BM25索引失败: {str(e)}",
            data={}
        )
