"""사용량 라우터"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
from app.services import credit_service, stats_service

router = APIRouter(prefix="/usage", tags=["사용량"])


@router.get("/daily")
async def daily_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    daily = await stats_service.get_user_daily(user.id, db)
    balance = await credit_service.get_balance(user.id, db)
    return {**daily, "balance": balance}


@router.get("/monthly")
async def monthly_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await stats_service.get_user_monthly(user.id, db)


@router.get("/stats")
async def usage_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stats = await stats_service.get_user_stats(user.id, db)
    balance = await credit_service.get_balance(user.id, db)
    return {**stats, "balance": balance}
