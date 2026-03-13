"""템플릿 라우터 - CRUD"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["템플릿"])


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    category: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Template).where(Template.user_id == user.id)
    if category and category != "all":
        query = query.where(Template.category == category)
    result = await db.execute(query.order_by(Template.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=TemplateResponse)
async def create_template(
    req: TemplateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tmpl = Template(user_id=user.id, **req.model_dump())
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int, req: TemplateUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.user_id == user.id)
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(404, "템플릿을 찾을 수 없습니다")

    for key, val in req.model_dump(exclude_none=True).items():
        setattr(tmpl, key, val)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.user_id == user.id)
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(404, "템플릿을 찾을 수 없습니다")
    await db.delete(tmpl)
    await db.commit()
    return {"message": "삭제되었습니다"}
