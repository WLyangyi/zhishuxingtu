import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from openai import OpenAI
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.skill import Skill, SkillExecution
from app.models.category import Content
from app.models.tag import Tag
from app.schemas.skill import (
    SkillCreate, SkillUpdate, SkillInDB, SkillListResponse,
    SkillExecutionCreate, SkillExecutionInDB, SkillTemplate
)
from app.core.config import settings
from app.api.routes.prompts import check_sensitive_words, apply_disclaimer

router = APIRouter(prefix="/skills", tags=["skills"])

SKILL_TEMPLATES = [
    {
        "name": "对话总结",
        "description": "总结对话内容并归档",
        "icon": "💬",
        "color": "#00d4ff",
        "input_schema": {
            "type": "object",
            "properties": {
                "conversation": {"type": "string", "title": "对话内容"},
                "summary_type": {"type": "string", "title": "总结类型"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "title": "总结内容"},
                "key_points": {"type": "array", "title": "关键要点"}
            }
        },
        "execution_logic": {
            "type": "conversation_summary",
            "prompt_category": "skill"
        },
        "trigger_type": "manual"
    },
    {
        "name": "每日资讯",
        "description": "定时汇总资讯并归档",
        "icon": "📰",
        "color": "#10b981",
        "input_schema": {
            "type": "object",
            "properties": {
                "sources": {"type": "array", "title": "资讯来源"},
                "keywords": {"type": "array", "title": "关键词"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "news_list": {"type": "array", "title": "资讯列表"}
            }
        },
        "execution_logic": {
            "type": "news_aggregate",
            "prompt_category": "skill",
            "sources": [],
            "keywords": []
        },
        "trigger_type": "scheduled",
        "schedule_config": {"cron": "0 9 * * *"}
    },
    {
        "name": "简历解析",
        "description": "解析简历内容，提取关键信息",
        "icon": "📄",
        "color": "#8b5cf6",
        "input_schema": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string", "title": "简历文本"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "skills": {"type": "array"},
                "experience": {"type": "array"}
            }
        },
        "execution_logic": {
            "type": "resume_parse",
            "prompt_category": "skill"
        },
        "trigger_type": "manual"
    },
    {
        "name": "知识卡片",
        "description": "自动生成知识点卡片",
        "icon": "🎴",
        "color": "#f59e0b",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "title": "知识内容"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {"type": "array"}
            }
        },
        "execution_logic": {
            "type": "knowledge_card",
            "prompt_category": "skill"
        },
        "trigger_type": "manual"
    }
]

SKILL_PROMPTS = {
    "conversation_summary": {
        "system_prompt": """你是一个专业的对话总结助手，负责将对话内容整理成结构化的总结。

## 总结要求
1. 提取对话的核心主题
2. 列出关键讨论点和结论
3. 记录待办事项（如果有）
4. 总结不超过500字

## 输出格式
请按以下格式输出：
- 主题：[对话主题]
- 关键要点：[3-5个要点]
- 待办事项：[如有]
- 总结：[总体总结]""",
        "user_template": "请总结以下对话内容，提取关键要点：\n\n{conversation}"
    },
    "news_aggregate": {
        "system_prompt": """你是一个专业的资讯聚合助手，负责从多个来源收集和整理每日资讯。

## 工作要求
1. 按类别整理资讯（技术、行业、热点等）
2. 每个咨询提供简短摘要（50字以内）
3. 标注信息来源
4. 整理成易读的列表格式

## 输出格式
请按以下格式输出：
## 技术资讯
- [标题] - [来源] - [摘要]

## 行业动态
- [标题] - [来源] - [摘要]

## 今日热点
- [标题] - [来源] - [摘要]""",
        "user_template": "请汇总以下资讯来源：\n\n来源：{sources}\n关键词：{keywords}\n\n请整理成每日报表格式："
    },
    "resume_parse": {
        "system_prompt": """你是一个专业的简历解析助手，负责从简历文本中提取关键信息。

## 解析要求
1. 提取基本信息（姓名、联系方式等）
2. 识别工作经历和技术技能
3. 提取教育背景
4. 识别关键优势和亮点

## 输出格式
请按以下JSON格式输出：
{
  "name": "姓名",
  "contact": "联系方式",
  "skills": ["技能1", "技能2"],
  "experience": [
    {"company": "公司名", "position": "职位", "duration": "时长", "highlights": ["亮点1", "亮点2"]}
  ],
  "education": {"school": "学校", "degree": "学位", "major": "专业"},
  "highlights": ["亮点1", "亮点2"]
}""",
        "user_template": "请解析以下简历内容：\n\n{resume_text}"
    },
    "knowledge_card": {
        "system_prompt": """你是一个专业的知识整理助手，负责将内容整理成知识卡片格式。

## 卡片要求
1. 提取核心知识点
2. 提供简明解释
3. 列出相关关键词
4. 提供使用场景或例子

## 输出格式
请按以下格式输出：
## 知识卡片

**标题**：[知识点名称]

**定义**：[简明定义]

**关键要点**
- [要点1]
- [要点2]
- [要点3]

**相关关键词**
[关键词1] [关键词2] [关键词3]

**使用场景**
[在什么场景下可以使用这个知识点]

**举例**
[简单例子说明]""",
        "user_template": "请将以下内容整理成知识卡片：\n\n{content}"
    }
}

def get_llm_client():
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL
    )

def skill_to_dict(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "user_id": skill.user_id,
        "name": skill.name,
        "description": skill.description,
        "icon": skill.icon,
        "color": skill.color,
        "input_schema": json.loads(skill.input_schema) if skill.input_schema else {},
        "output_schema": json.loads(skill.output_schema) if skill.output_schema else {},
        "execution_logic": json.loads(skill.execution_logic) if skill.execution_logic else {},
        "trigger_type": skill.trigger_type,
        "schedule_config": json.loads(skill.schedule_config) if skill.schedule_config else {},
        "output_category_id": skill.output_category_id,
        "output_type_id": skill.output_type_id,
        "output_tag_ids": json.loads(skill.output_tag_ids) if skill.output_tag_ids else [],
        "is_template": skill.is_template,
        "is_active": skill.is_active,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at
    }

def build_skill_prompt(skill_type: str, input_data: dict) -> tuple[str, str]:
    prompt_config = SKILL_PROMPTS.get(skill_type)
    if not prompt_config:
        return None, None

    system_prompt = prompt_config["system_prompt"]
    user_template = prompt_config["user_template"]

    user_prompt = user_template
    for key, value in input_data.items():
        placeholder = "{" + key + "}"
        user_prompt = user_prompt.replace(placeholder, str(value))

    return system_prompt, user_prompt

@router.get("/templates", response_model=List[SkillTemplate])
async def get_skill_templates():
    return SKILL_TEMPLATES

@router.get("", response_model=SkillListResponse)
async def get_skills(
    is_template: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Skill).filter(Skill.user_id == current_user.id)

    if is_template is not None:
        query = query.filter(Skill.is_template == is_template)

    total = query.count()
    items = query.order_by(Skill.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [skill_to_dict(item) for item in items],
        "total": total
    }

@router.get("/{skill_id}", response_model=SkillInDB)
async def get_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    return skill_to_dict(skill)

@router.post("", response_model=SkillInDB)
async def create_skill(
    data: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = Skill(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        input_schema=json.dumps(data.input_schema),
        output_schema=json.dumps(data.output_schema),
        execution_logic=json.dumps(data.execution_logic),
        trigger_type=data.trigger_type,
        schedule_config=json.dumps(data.schedule_config),
        output_category_id=data.output_category_id,
        output_type_id=data.output_type_id,
        output_tag_ids=json.dumps(data.output_tag_ids)
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    return skill_to_dict(skill)

@router.post("/from-template/{template_index}", response_model=SkillInDB)
async def create_skill_from_template(
    template_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if template_index < 0 or template_index >= len(SKILL_TEMPLATES):
        raise HTTPException(status_code=400, detail="模板索引无效")

    template = SKILL_TEMPLATES[template_index]

    skill = Skill(
        user_id=current_user.id,
        name=template["name"],
        description=template["description"],
        icon=template["icon"],
        color=template["color"],
        input_schema=json.dumps(template["input_schema"]),
        output_schema=json.dumps(template["output_schema"]),
        execution_logic=json.dumps(template["execution_logic"]),
        trigger_type=template["trigger_type"],
        schedule_config=json.dumps(template.get("schedule_config", {})),
        is_template=False
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    return skill_to_dict(skill)

@router.put("/{skill_id}", response_model=SkillInDB)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key in ["input_schema", "output_schema", "execution_logic", "schedule_config", "output_tag_ids"]:
            if value is not None:
                value = json.dumps(value)
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)

    return skill_to_dict(skill)

@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    db.delete(skill)
    db.commit()

    return {"success": True, "message": "Skill已删除"}

@router.post("/{skill_id}/execute", response_model=SkillExecutionInDB)
async def execute_skill(
    skill_id: str,
    data: SkillExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    if not skill.is_active:
        raise HTTPException(status_code=400, detail="Skill未激活")

    execution = SkillExecution(
        skill_id=skill_id,
        user_id=current_user.id,
        input_data=json.dumps(data.input_data) if data.input_data else None,
        status="running"
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    execution_logic = json.loads(skill.execution_logic)
    skill_type = execution_logic.get("type", "unknown")

    input_data = data.input_data or {}

    input_str = json.dumps(input_data, ensure_ascii=False)
    if check_sensitive_words(input_str)[0]:
        execution.status = "failed"
        execution.error_message = "输入包含不当内容"
        db.commit()
        raise HTTPException(status_code=400, detail="输入包含不当内容，请调整后重试")

    system_prompt, user_prompt = build_skill_prompt(skill_type, input_data)

    output_data = {"type": skill_type, "status": "simulated", "message": "Skill执行完成（模拟）"}

    if system_prompt and user_prompt:
        try:
            client = get_llm_client()
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            result = response.choices[0].message.content
            result = apply_disclaimer(result)
            output_data = {
                "type": skill_type,
                "status": "success",
                "result": result
            }
        except Exception as e:
            output_data = {
                "type": skill_type,
                "status": "error",
                "message": f"AI 服务调用失败: {str(e)}"
            }
    else:
        output_data = {
            "type": skill_type,
            "status": "error",
            "message": f"未找到 Skill 类型 '{skill_type}' 的提示词配置"
        }

    execution.status = "success"
    execution.output_data = json.dumps(output_data, ensure_ascii=False)

    if skill.output_category_id and skill.output_type_id:
        content = Content(
            type_id=skill.output_type_id,
            category_id=skill.output_category_id,
            user_id=current_user.id,
            title=f"[Skill] {skill.name} - {execution.started_at.strftime('%Y-%m-%d %H:%M')}",
            content=output_data.get("result", json.dumps(output_data, ensure_ascii=False))
        )
        db.add(content)
        db.flush()

        execution.output_content_id = content.id

        tag_ids = json.loads(skill.output_tag_ids) if skill.output_tag_ids else []
        for tag_id in tag_ids:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                content.tags.append(tag)

    from datetime import datetime
    execution.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(execution)

    return {
        "id": execution.id,
        "skill_id": execution.skill_id,
        "user_id": execution.user_id,
        "input_data": json.loads(execution.input_data) if execution.input_data else None,
        "output_data": json.loads(execution.output_data) if execution.output_data else None,
        "output_content_id": execution.output_content_id,
        "status": execution.status,
        "error_message": execution.error_message,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at
    }

@router.get("/{skill_id}/executions", response_model=List[SkillExecutionInDB])
async def get_skill_executions(
    skill_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    executions = db.query(SkillExecution).filter(
        SkillExecution.skill_id == skill_id
    ).order_by(SkillExecution.started_at.desc()).limit(limit).all()

    return [{
        "id": e.id,
        "skill_id": e.skill_id,
        "user_id": e.user_id,
        "input_data": json.loads(e.input_data) if e.input_data else None,
        "output_data": json.loads(e.output_data) if e.output_data else None,
        "output_content_id": e.output_content_id,
        "status": e.status,
        "error_message": e.error_message,
        "started_at": e.started_at,
        "completed_at": e.completed_at
    } for e in executions]
