import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Query
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
    keywords = extract_keywords(question, max_keywords=5)
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
    unique_notes = unique_notes[:5]
    
    if not unique_notes:
        return Response(data={
            "answer": "抱歉，我在知识库中没有找到与您问题相关的内容。请尝试其他关键词或先添加相关笔记。",
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
    
    system_prompt = f"""你是一个智能知识助手，帮助用户基于他们的个人知识库回答问题。

当前日期：{current_date}，{current_weekday}

请根据提供的笔记内容来回答用户的问题。如果笔记内容与问题相关，请综合整理后给出答案。
如果笔记内容与问题不太相关，请如实告知用户，并给出你的一般性建议。

回答要求：
1. 简洁明了，直接回答问题
2. 如果引用了笔记内容，请标注来源
3. 如果知识库中没有相关信息，请诚实说明"""

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    keywords = extract_keywords(message, max_keywords=5)
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
    unique_notes = unique_notes[:3]
    
    context = ""
    if unique_notes:
        context = "\n\n".join([
            f"【笔记: {n.title}】\n{n.content or '(无内容)'}" 
            for n in unique_notes
        ])
    
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    current_date = datetime.now().strftime("%Y年%m月%d日")
    current_weekday = weekdays[datetime.now().weekday()]
    
    system_prompt = f"""你是知枢星图的 AI 助手，一个友好、专业的知识管理助手。

当前日期：{current_date}，{current_weekday}

你可以帮助用户：
- 回答关于知识库内容的问题
- 帮助整理和总结笔记
- 提供学习和知识管理的建议
- 进行一般性的对话

请用简洁、友好的方式回答。如果引用了知识库内容，请标注来源。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        try:
            history_list = json.loads(history)
            for h in history_list[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        except:
            pass
    
    user_message = message
    if context:
        user_message = f"知识库相关内容：\n{context}\n\n用户消息：{message}"
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"抱歉，AI 服务暂时不可用。错误信息：{str(e)}"
    
    return Response(data={
        "answer": answer,
        "notes": [{"id": n.id, "title": n.title} for n in unique_notes]
    })
