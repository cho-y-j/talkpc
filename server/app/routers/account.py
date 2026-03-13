"""계정 라우터 - 내 정보/잔액/충전 요청"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.charge_request import ChargeRequest, ServerSetting
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


# ── 충전 요청 ──

class ChargeRequestCreate(BaseModel):
    amount: int
    depositor: str = ""
    method: str = "bank"


@router.post("/charge-request")
async def create_charge_request(
    req: ChargeRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """충전 요청 (계좌 입금 후)"""
    if req.amount not in [10000, 50000, 100000, 500000, 1000000]:
        raise HTTPException(400, "허용된 충전 금액: 1만, 5만, 10만, 50만, 100만원")

    charge_req = ChargeRequest(
        user_id=user.id,
        amount=req.amount,
        depositor=req.depositor or user.name,
        method=req.method,
    )
    db.add(charge_req)
    await db.commit()
    await db.refresh(charge_req)
    return {
        "id": charge_req.id,
        "amount": charge_req.amount,
        "status": charge_req.status,
        "message": f"{req.amount:,}원 충전 요청이 접수되었습니다. 관리자 확인 후 충전됩니다."
    }


@router.get("/charge-requests")
async def get_my_charge_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내 충전 요청 목록"""
    result = await db.execute(
        select(ChargeRequest)
        .where(ChargeRequest.user_id == user.id)
        .order_by(ChargeRequest.created_at.desc())
        .limit(50)
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id, "amount": r.amount, "depositor": r.depositor,
            "method": r.method, "status": r.status,
            "admin_memo": r.admin_memo,
            "created_at": r.created_at.isoformat(),
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in reqs
    ]


@router.get("/pricing")
async def get_pricing(db: AsyncSession = Depends(get_db)):
    """현재 과금 단가 조회 (로그인 불필요하지만 API키는 필요)"""
    result = await db.execute(
        select(ServerSetting).where(
            ServerSetting.key.in_([
                'cost_sms', 'cost_lms', 'cost_alimtalk',
                'cost_rcs_sms', 'cost_rcs_lms', 'cost_rcs_mms',
                'bank_account'
            ])
        )
    )
    settings = {s.key: s.value for s in result.scalars().all()}
    return {
        "sms": int(settings.get("cost_sms", "8")),
        "lms": int(settings.get("cost_lms", "25")),
        "alimtalk": int(settings.get("cost_alimtalk", "7")),
        "rcs_sms": int(settings.get("cost_rcs_sms", "12")),
        "rcs_lms": int(settings.get("cost_rcs_lms", "30")),
        "rcs_mms": int(settings.get("cost_rcs_mms", "50")),
        "bank_account": settings.get("bank_account", ""),
    }
