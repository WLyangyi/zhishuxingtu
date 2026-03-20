import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body
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
from app.api.routes.prompts import get_prompt_by_category, render_prompt, check_sensitive_words, filter_sensitive_content, apply_disclaimer, DISCLAIMER, EMPTY_RESULT_RESPONSE, multi_layer_content_check
from app.services.rag_chain import get_rag_chain
from app.services.chat_chain import get_chat_chain


def vector_search_notes(query: str, db: Session, k: int = 5, threshold: float = 0.3) -> List[tuple]:
    if not embedding_service.available:
        return []

    vector_store = get_vector_store()
    if not vector_store or vector_store.total_vectors == 0:
        return []

    try:
        query_vector = embedding_service.embed_text(query)
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

    vector_results = vector_search_notes(question, db, k=5, threshold=0.3)

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

    vector_results = vector_search_notes(question, db, k=5, threshold=0.3)

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

    vector_results = vector_search_notes(message, db, k=3, threshold=0.3)

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

    vector_results = vector_search_notes(message, db, k=3, threshold=0.3)

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
