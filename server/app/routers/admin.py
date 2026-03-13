"""관리자 라우터 - 회원관리, 크레딧, 통계, 보안"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.send_log import SendLog
from app.models.device import Device, SecurityLog
from app.schemas.admin import CreditGrant, AdminUserUpdate
from app.middleware.auth import require_admin
from app.services import credit_service, stats_service
from app.services.security_service import unlock_user, log_security_event

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
            "is_active": u.is_active, "is_locked": u.is_locked,
            "locked_reason": u.locked_reason,
            "daily_limit": u.daily_limit, "hourly_limit": u.hourly_limit,
            "send_start_hour": u.send_start_hour, "send_end_hour": u.send_end_hour,
            "created_at": u.created_at.isoformat(),
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

    # 등록 기기
    device_result = await db.execute(
        select(Device).where(Device.user_id == user.id).order_by(Device.created_at.desc())
    )
    devices = device_result.scalars().all()

    # 보안 로그
    sec_result = await db.execute(
        select(SecurityLog).where(SecurityLog.user_id == user.id)
        .order_by(SecurityLog.created_at.desc()).limit(30)
    )
    sec_logs = sec_result.scalars().all()

    return {
        "user": {
            "id": user.id, "username": user.username, "name": user.name,
            "phone": user.phone, "email": user.email, "role": user.role,
            "is_active": user.is_active, "is_locked": user.is_locked,
            "locked_reason": user.locked_reason,
            "daily_limit": user.daily_limit, "hourly_limit": user.hourly_limit,
            "send_start_hour": user.send_start_hour, "send_end_hour": user.send_end_hour,
            "created_at": user.created_at.isoformat(),
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
        ],
        "devices": [
            {"id": d.id, "device_id": d.device_id, "device_name": d.device_name,
             "is_approved": d.is_approved, "created_at": d.created_at.isoformat()}
            for d in devices
        ],
        "security_logs": [
            {"id": s.id, "event_type": s.event_type, "detail": s.detail,
             "ip_address": s.ip_address, "created_at": s.created_at.isoformat()}
            for s in sec_logs
        ],
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
    if req.daily_limit is not None:
        user.daily_limit = req.daily_limit
    if req.hourly_limit is not None:
        user.hourly_limit = req.hourly_limit
    if req.send_start_hour is not None:
        user.send_start_hour = req.send_start_hour
    if req.send_end_hour is not None:
        user.send_end_hour = req.send_end_hour
    if req.is_locked is not None:
        if not req.is_locked and user.is_locked:
            await unlock_user(user, db)
            await log_security_event(user.id, "admin_unlock", f"관리자({admin.username})가 잠금 해제", db)
        elif req.is_locked:
            user.is_locked = True
            user.locked_reason = "관리자 잠금"
            await log_security_event(user.id, "admin_lock", f"관리자({admin.username})가 잠금", db)

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


@router.post("/users/{user_id}/approve-device")
async def approve_device(
    user_id: int, device_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자가 기기 승인"""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "기기를 찾을 수 없습니다")

    device.is_approved = True
    await log_security_event(user_id, "admin_device_approve",
                             f"관리자({admin.username})가 기기 승인: {device.device_name}", db)
    await db.commit()
    return {"message": f"기기 '{device.device_name}' 승인 완료"}


@router.delete("/users/{user_id}/devices/{device_id}")
async def delete_device(
    user_id: int, device_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자가 기기 삭제 (분실/탈취 대응)"""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "기기를 찾을 수 없습니다")

    device_name = device.device_name
    await db.delete(device)
    await log_security_event(user_id, "admin_device_delete",
                             f"관리자({admin.username})가 기기 삭제: {device_name}", db)
    await db.commit()
    return {"message": f"기기 '{device_name}' 삭제 완료"}


@router.get("/security-logs")
async def admin_security_logs(
    page: int = 1, size: int = 100,
    event_type: str = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """전체 보안 로그 (필터, 페이지네이션, 사용자명 포함)"""
    offset = (page - 1) * size
    conditions = []
    if event_type:
        conditions.append(SecurityLog.event_type == event_type)

    where_clause = and_(*conditions) if conditions else True

    # 총 개수
    count_result = await db.execute(
        select(func.count(SecurityLog.id)).where(where_clause)
    )
    total = count_result.scalar() or 0

    # 로그 + 사용자명 조인
    result = await db.execute(
        select(SecurityLog, User.username)
        .outerjoin(User, SecurityLog.user_id == User.id)
        .where(where_clause)
        .order_by(SecurityLog.created_at.desc())
        .offset(offset).limit(size)
    )
    rows = result.all()
    return {
        "total": total,
        "logs": [
            {
                "id": s.id, "user_id": s.user_id,
                "username": username or "",
                "event_type": s.event_type, "detail": s.detail,
                "ip_address": s.ip_address,
                "created_at": s.created_at.isoformat()
            }
            for s, username in rows
        ]
    }


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
