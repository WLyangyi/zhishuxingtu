import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.prompt import Prompt
from app.schemas.prompt import (
    PromptCreate, PromptUpdate, PromptInDB, PromptListResponse, PromptTemplate, DEFAULT_PROMPT_TEMPLATES
)
from app.schemas.response import Response
from app.core.config import settings

router = APIRouter(prefix="/prompts", tags=["提示词管理"])

SENSITIVE_WORDS = [
    "暴力", "色情", "赌博", "毒品", "犯罪", "欺诈",
    " hacking", "hack", "virus", "malware",
    "枪", "刀", "杀", "死", "恐怖", "炸弹", "核",
    "赌博", "彩票", "赌", "麻将", "扑克",
    "毒品", "大麻", "海洛因", "可卡因", "冰毒",
    "诈骗", "钓鱼", "木马", "黑产", "跑分",
    "色情", "裸", "黄色", "成人", "性感",
    "分裂", "颠覆", "暴动", "示威", "抗议"
]

SENSITIVE_PATTERNS = [
    r'\b(http|ftp)://[^\s]+\.(xyz|tk|ml|ga|cf|gq)\b',
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b',
    r'eval\s*\(',
    r'exec\s*\(',
    r'system\s*\(',
    r'shell_exec\s*\(',
]

INPUT_MAX_LENGTH = 2000
MIN_MESSAGE_INTERVAL = 1

DISCLAIMER = """
---
**免责声明**：以上内容仅供参考，不构成任何专业意见。如有医疗、法律、金融等领域的具体问题，请咨询相关专业人士。"""

EMPTY_RESULT_RESPONSE = "抱歉，我在知识库中没有找到与您问题相关的内容。请尝试其他关键词或先添加相关笔记。"

def check_sensitive_words(text: str) -> tuple[bool, str]:
    text_lower = text.lower()
    for word in SENSITIVE_WORDS:
        if word.lower() in text_lower:
            return True, word
    return False, ""

def check_sensitive_patterns(text: str) -> tuple[bool, str]:
    for pattern in SENSITIVE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group()
    return False, ""

def multi_layer_content_check(text: str) -> Dict[str, Any]:
    if len(text) > INPUT_MAX_LENGTH:
        return {
            "passed": False,
            "reason": "内容超出最大长度限制",
            "layer": "length_check"
        }

    has_sensitive_word, matched_word = check_sensitive_words(text)
    if has_sensitive_word:
        return {
            "passed": False,
            "reason": f"内容包含敏感词: {matched_word}",
            "layer": "word_filter"
        }

    has_sensitive_pattern, matched_pattern = check_sensitive_patterns(text)
    if has_sensitive_pattern:
        return {
            "passed": False,
            "reason": "内容包含可疑模式",
            "layer": "pattern_filter"
        }

    return {"passed": True, "reason": None, "layer": None}

def filter_sensitive_content(text: str) -> str:
    for word in SENSITIVE_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub("***", text)
    return text

def apply_disclaimer(text: str) -> str:
    if not text.endswith(DISCLAIMER.strip()):
        return text + "\n\n" + DISCLAIMER.strip()
    return text

@router.get("/templates", response_model=List[PromptTemplate])
async def get_prompt_templates():
    return DEFAULT_PROMPT_TEMPLATES

@router.get("", response_model=PromptListResponse)
async def get_prompts(
    category: Optional[str] = Query(None, description="按分类筛选"),
    is_system: Optional[bool] = Query(None, description="筛选系统预设"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Prompt)

    query = query.filter(
        (Prompt.user_id == current_user.id) | (Prompt.is_system == True)
    )

    if category is not None:
        query = query.filter(Prompt.category == category)

    if is_system is not None:
        query = query.filter(Prompt.is_system == is_system)

    total = query.count()
    items = query.order_by(Prompt.is_system.desc(), Prompt.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PromptListResponse(
        items=[prompt_to_dict(p) for p in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/categories", response_model=List[dict])
async def get_prompt_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Prompt.category).filter(
        (Prompt.user_id == current_user.id) | (Prompt.is_system == True)
    ).distinct()

    categories = query.all()
    category_list = [
        {"value": c[0], "label": get_category_label(c[0])}
        for c in categories
    ]
    return category_list

@router.get("/{prompt_id}", response_model=PromptInDB)
async def get_prompt(
    prompt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        ((Prompt.user_id == current_user.id) | (Prompt.is_system == True))
    ).first()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    return prompt_to_dict(prompt)

@router.post("", response_model=PromptInDB)
async def create_prompt(
    data: PromptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt = Prompt(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        category=data.category,
        system_prompt=data.system_prompt,
        user_prompt_template=data.user_prompt_template,
        output_format=data.output_format,
        variables=json.dumps(data.variables),
        is_system=data.is_system,
        is_active=data.is_active,
        is_default=data.is_default,
        priority=data.priority
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return prompt_to_dict(prompt)

@router.post("/from-template/{template_index}", response_model=PromptInDB)
async def create_prompt_from_template(
    template_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if template_index < 0 or template_index >= len(DEFAULT_PROMPT_TEMPLATES):
        raise HTTPException(status_code=400, detail="模板索引无效")

    template = DEFAULT_PROMPT_TEMPLATES[template_index]

    prompt = Prompt(
        user_id=current_user.id,
        name=template["name"],
        description=template["description"],
        category=template["category"],
        system_prompt=template["system_prompt"],
        user_prompt_template=template["user_prompt_template"],
        output_format=template["output_format"],
        variables=json.dumps(template["variables"]),
        is_system=False,
        is_active=True,
        is_default=False,
        priority="normal"
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return prompt_to_dict(prompt)

@router.put("/{prompt_id}", response_model=PromptInDB)
async def update_prompt(
    prompt_id: str,
    data: PromptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在或无权修改")

    if prompt.is_system:
        raise HTTPException(status_code=400, detail="系统预设提示词不可直接修改")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "variables":
            value = json.dumps(value)
        setattr(prompt, key, value)

    db.commit()
    db.refresh(prompt)

    return prompt_to_dict(prompt)

@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在或无权删除")

    if prompt.is_system:
        raise HTTPException(status_code=400, detail="系统预设提示词不可删除")

    db.delete(prompt)
    db.commit()

    return {"success": True, "message": "提示词已删除"}

@router.post("/initialize")
async def initialize_default_prompts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    created_count = 0
    for template in DEFAULT_PROMPT_TEMPLATES:
        existing = db.query(Prompt).filter(
            Prompt.name == template["name"],
            Prompt.user_id == current_user.id
        ).first()

        if not existing:
            prompt = Prompt(
                user_id=current_user.id,
                name=template["name"],
                description=template["description"],
                category=template["category"],
                system_prompt=template["system_prompt"],
                user_prompt_template=template["user_prompt_template"],
                output_format=template["output_format"],
                variables=json.dumps(template["variables"]),
                is_system=False,
                is_active=True,
                is_default=True,
                priority="normal"
            )
            db.add(prompt)
            created_count += 1

    if created_count > 0:
        db.commit()

    return {"success": True, "message": f"已创建 {created_count} 个默认提示词"}

def get_prompt_by_category(category: str, user_id: str, db: Session) -> Optional[Prompt]:
    prompt = db.query(Prompt).filter(
        Prompt.category == category,
        Prompt.user_id == user_id,
        Prompt.is_active == True
    ).first()

    if not prompt:
        prompt = db.query(Prompt).filter(
            Prompt.category == category,
            Prompt.is_system == True,
            Prompt.is_active == True
        ).first()

    return prompt

def render_prompt(prompt: Prompt, **kwargs) -> tuple[str, str]:
    if settings.USE_LANGCHAIN_PROMPT:
        return render_prompt_langchain_impl(prompt, **kwargs)
    return render_prompt_original(prompt, **kwargs)


def render_prompt_original(prompt: Prompt, **kwargs) -> tuple[str, str]:
    system_prompt = prompt.system_prompt
    user_prompt = prompt.user_prompt_template

    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        system_prompt = system_prompt.replace(placeholder, str(value))
        user_prompt = user_prompt.replace(placeholder, str(value))

    return system_prompt, user_prompt


def render_prompt_langchain_impl(prompt: Prompt, **kwargs) -> tuple[str, str]:
    from app.services.prompt_service import get_prompt_service
    
    service = get_prompt_service()
    return service.render(
        prompt.system_prompt,
        prompt.user_prompt_template,
        **kwargs
    )

def prompt_to_dict(prompt: Prompt) -> dict:
    variables = []
    if prompt.variables:
        try:
            variables = json.loads(prompt.variables)
        except:
            variables = []

    return {
        "id": prompt.id,
        "user_id": prompt.user_id,
        "name": prompt.name,
        "description": prompt.description,
        "category": prompt.category,
        "system_prompt": prompt.system_prompt,
        "user_prompt_template": prompt.user_prompt_template,
        "output_format": prompt.output_format,
        "variables": variables,
        "is_system": prompt.is_system,
        "is_active": prompt.is_active,
        "is_default": prompt.is_default,
        "priority": prompt.priority,
        "created_at": prompt.created_at,
        "updated_at": prompt.updated_at
    }

def get_category_label(category: str) -> str:
    labels = {
        "ai_chat": "AI 对话",
        "ai_search": "AI 搜索",
        "skill": "技能模板",
        "custom": "自定义"
    }
    return labels.get(category, category)
