"""관리자 라우터 - 회원관리, 크레딧, 통계"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.send_log import SendLog
from app.schemas.admin import CreditGrant, AdminUserUpdate
from app.middleware.auth import require_admin
from app.services import credit_service, stats_service

router = APIRouter(prefix="/admin", tags=["관리자"])


@router.get("/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    user_list = []
    for u in users:
        balance = await credit_service.get_balance(u.id, db)
        user_list.append({
            "id": u.id, "username": u.username, "name": u.name,
            "phone": u.phone, "email": u.email, "role": u.role,
            "is_active": u.is_active, "created_at": u.created_at.isoformat(),
            "balance": balance
        })
    return user_list


@router.get("/users/{user_id}")
async def get_user(user_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    balance = await credit_service.get_balance(user.id, db)
    credits = await credit_service.get_history(user.id, db)

    # 최근 발송 로그
    log_result = await db.execute(
        select(SendLog).where(SendLog.user_id == user.id)
        .order_by(SendLog.created_at.desc()).limit(50)
    )
    logs = log_result.scalars().all()

    return {
        "user": {
            "id": user.id, "username": user.username, "name": user.name,
            "phone": user.phone, "email": user.email, "role": user.role,
            "is_active": user.is_active, "created_at": user.created_at.isoformat(),
            "balance": balance
        },
        "credits": [
            {"id": c.id, "amount": c.amount, "type": c.type,
             "description": c.description, "created_at": c.created_at.isoformat()}
            for c in credits
        ],
        "send_logs": [
            {"id": l.id, "contact_name": l.contact_name, "msg_type": l.msg_type,
             "mseq": l.mseq, "status": l.status, "cost": l.cost,
             "created_at": l.created_at.isoformat()}
            for l in logs
        ]
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int, req: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    if req.is_active is not None:
        user.is_active = req.is_active
    if req.role is not None:
        user.role = req.role
    if req.name is not None:
        user.name = req.name
    await db.commit()
    return {"message": "수정되었습니다"}


@router.post("/users/{user_id}/credit")
async def grant_credit(
    user_id: int, req: CreditGrant,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """크레딧 부여 (양수=충전, 음수=차감)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    credit_type = "bonus" if req.amount > 0 else "use"
    desc = req.description or ("관리자 충전" if req.amount > 0 else "관리자 차감")
    await credit_service.charge(
        user_id, req.amount, desc, db,
        admin_id=admin.id, credit_type=credit_type
    )
    await db.commit()

    balance = await credit_service.get_balance(user_id, db)
    return {"message": f"{user.name}에게 {req.amount}원 처리 완료", "balance": balance}


@router.get("/stats")
async def admin_stats(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await stats_service.get_admin_stats(db)


@router.get("/send-logs")
async def admin_send_logs(
    page: int = 1, size: int = 100,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select as sel
    offset = (page - 1) * size
    result = await db.execute(
        sel(SendLog).order_by(SendLog.created_at.desc()).offset(offset).limit(size)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id, "user_id": l.user_id,
            "contact_name": l.contact_name, "contact_phone": l.contact_phone,
            "msg_type": l.msg_type, "mseq": l.mseq,
            "status": l.status, "cost": l.cost,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
