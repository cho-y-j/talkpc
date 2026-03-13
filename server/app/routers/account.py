"""계정 라우터 - 내 정보/잔액"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.middleware.auth import get_current_user
from app.services import credit_service

router = APIRouter(prefix="/account", tags=["계정"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    balance = await credit_service.get_balance(user.id, db)
    return UserResponse(
        id=user.id, username=user.username, name=user.name,
        phone=user.phone, email=user.email, role=user.role,
        is_active=user.is_active, created_at=user.created_at,
        balance=balance
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if req.name is not None:
        user.name = req.name
    if req.phone is not None:
        user.phone = req.phone
    if req.email is not None:
        user.email = req.email
    await db.commit()
    await db.refresh(user)

    balance = await credit_service.get_balance(user.id, db)
    return UserResponse(
        id=user.id, username=user.username, name=user.name,
        phone=user.phone, email=user.email, role=user.role,
        is_active=user.is_active, created_at=user.created_at,
        balance=balance
    )


@router.get("/balance")
async def get_balance(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    balance = await credit_service.get_balance(user.id, db)
    return {"balance": balance}


@router.get("/credits")
async def get_credits(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """내 크레딧 내역"""
    credits = await credit_service.get_history(user.id, db)
    return [
        {
            "id": c.id, "amount": c.amount, "type": c.type,
            "description": c.description,
            "created_at": c.created_at.isoformat()
        }
        for c in credits
    ]
