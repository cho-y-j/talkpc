"""크레딧 서비스 - 잔액 조회, 충전, 차감"""
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.credit import Credit


async def get_balance(user_id: int, db: AsyncSession) -> int:
    """사용자 잔액 계산"""
    result = await db.execute(
        select(func.coalesce(func.sum(Credit.amount), 0))
        .where(Credit.user_id == user_id)
    )
    return result.scalar()


async def charge(user_id: int, amount: int, description: str,
                 db: AsyncSession, admin_id: int = None, credit_type: str = "charge") -> Credit:
    """크레딧 충전/보너스"""
    credit = Credit(
        user_id=user_id,
        amount=amount,
        type=credit_type,
        description=description,
        admin_id=admin_id,
    )
    db.add(credit)
    await db.flush()
    return credit


async def deduct(user_id: int, amount: int, description: str,
                 db: AsyncSession) -> Credit:
    """크레딧 차감 (음수로 저장)"""
    credit = Credit(
        user_id=user_id,
        amount=-amount,
        type="use",
        description=description,
    )
    db.add(credit)
    await db.flush()
    return credit


async def get_history(user_id: int, db: AsyncSession, limit: int = 50) -> List[Credit]:
    """크레딧 이력 조회"""
    result = await db.execute(
        select(Credit)
        .where(Credit.user_id == user_id)
        .order_by(Credit.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
