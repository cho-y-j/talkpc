"""관리자 라우터 - 회원관리, 크레딧, 통계, 보안, 충전 승인, 설정"""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.credit import Credit
from app.models.send_log import SendLog
from app.models.device import Device, SecurityLog
from app.models.charge_request import ChargeRequest, ServerSetting
from app.models.user_callback import UserCallback
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

    # 발신번호
    cb_result = await db.execute(
        select(UserCallback).where(UserCallback.user_id == user.id)
        .order_by(UserCallback.created_at.desc())
    )
    callbacks = cb_result.scalars().all()

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
        "callbacks": [
            {"id": cb.id, "phone": cb.phone, "is_active": cb.is_active,
             "memo": cb.memo, "created_at": cb.created_at.isoformat()}
            for cb in callbacks
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


# ══════════════════════════════════════════════
#  발신번호 관리 (관리자)
# ══════════════════════════════════════════════

class AdminCallbackCreate(BaseModel):
    phone: str
    memo: str = ""


@router.post("/users/{user_id}/callbacks")
async def admin_add_callback(
    user_id: int, body: AdminCallbackCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자가 사용자의 발신번호 추가"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    phone = body.phone.strip().replace("-", "")
    if not phone:
        raise HTTPException(400, "전화번호를 입력하세요")

    # 중복 확인
    existing = await db.execute(
        select(UserCallback).where(
            UserCallback.user_id == user_id,
            UserCallback.phone == phone
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "이미 등록된 발신번호입니다")

    cb = UserCallback(user_id=user_id, phone=phone, memo=body.memo)
    db.add(cb)
    await db.commit()
    await db.refresh(cb)
    return {
        "id": cb.id, "phone": cb.phone, "is_active": cb.is_active,
        "memo": cb.memo, "message": "발신번호가 추가되었습니다"
    }


@router.put("/users/{user_id}/callbacks/{cb_id}/activate")
async def admin_activate_callback(
    user_id: int, cb_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자가 사용자의 발신번호 활성화"""
    result = await db.execute(
        select(UserCallback).where(
            UserCallback.id == cb_id,
            UserCallback.user_id == user_id
        )
    )
    cb = result.scalar_one_or_none()
    if not cb:
        raise HTTPException(404, "발신번호를 찾을 수 없습니다")

    # 기존 활성 발신번호 비활성화
    all_result = await db.execute(
        select(UserCallback).where(
            UserCallback.user_id == user_id,
            UserCallback.is_active == True
        )
    )
    for active_cb in all_result.scalars().all():
        active_cb.is_active = False

    cb.is_active = True
    await db.commit()
    return {"message": f"발신번호 {cb.phone}이(가) 활성화되었습니다"}


@router.delete("/users/{user_id}/callbacks/{cb_id}")
async def admin_delete_callback(
    user_id: int, cb_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자가 사용자의 발신번호 삭제"""
    result = await db.execute(
        select(UserCallback).where(
            UserCallback.id == cb_id,
            UserCallback.user_id == user_id
        )
    )
    cb = result.scalar_one_or_none()
    if not cb:
        raise HTTPException(404, "발신번호를 찾을 수 없습니다")

    await db.delete(cb)
    await db.commit()
    return {"message": "발신번호가 삭제되었습니다"}


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


# ══════════════════════════════════════════════
#  충전 요청 관리
# ══════════════════════════════════════════════

@router.get("/charge-requests")
async def admin_charge_requests(
    status: str = Query(None),
    page: int = 1, size: int = 50,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """충전 요청 목록 (필터: pending/approved/rejected)"""
    offset = (page - 1) * size
    conditions = []
    if status:
        conditions.append(ChargeRequest.status == status)
    where_clause = and_(*conditions) if conditions else True

    count_result = await db.execute(
        select(func.count(ChargeRequest.id)).where(where_clause)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(ChargeRequest, User.username, User.name)
        .outerjoin(User, ChargeRequest.user_id == User.id)
        .where(where_clause)
        .order_by(ChargeRequest.created_at.desc())
        .offset(offset).limit(size)
    )
    rows = result.all()
    return {
        "total": total,
        "requests": [
            {
                "id": r.id, "user_id": r.user_id,
                "username": username or "", "user_name": name or "",
                "amount": r.amount, "depositor": r.depositor,
                "method": r.method, "status": r.status,
                "admin_memo": r.admin_memo,
                "created_at": r.created_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r, username, name in rows
        ]
    }


class ChargeApprove(BaseModel):
    memo: str = ""


@router.post("/charge-requests/{req_id}/approve")
async def approve_charge(
    req_id: int, body: ChargeApprove,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """충전 요청 승인 → 크레딧 충전"""
    result = await db.execute(
        select(ChargeRequest).where(ChargeRequest.id == req_id)
    )
    charge_req = result.scalar_one_or_none()
    if not charge_req:
        raise HTTPException(404, "충전 요청을 찾을 수 없습니다")
    if charge_req.status != "pending":
        raise HTTPException(400, f"이미 처리된 요청입니다 (상태: {charge_req.status})")

    # 크레딧 충전
    await credit_service.charge(
        charge_req.user_id, charge_req.amount,
        f"계좌입금 충전 ({charge_req.depositor})",
        db, admin_id=admin.id, credit_type="charge"
    )

    charge_req.status = "approved"
    charge_req.admin_id = admin.id
    charge_req.admin_memo = body.memo
    charge_req.processed_at = datetime.now()

    await log_security_event(
        charge_req.user_id, "charge_approved",
        f"충전 승인: {charge_req.amount:,}원 (관리자: {admin.username})", db
    )
    await db.commit()

    balance = await credit_service.get_balance(charge_req.user_id, db)
    return {"message": f"{charge_req.amount:,}원 충전 승인 완료", "balance": balance}


@router.post("/charge-requests/{req_id}/reject")
async def reject_charge(
    req_id: int, body: ChargeApprove,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """충전 요청 거절"""
    result = await db.execute(
        select(ChargeRequest).where(ChargeRequest.id == req_id)
    )
    charge_req = result.scalar_one_or_none()
    if not charge_req:
        raise HTTPException(404, "충전 요청을 찾을 수 없습니다")
    if charge_req.status != "pending":
        raise HTTPException(400, f"이미 처리된 요청입니다 (상태: {charge_req.status})")

    charge_req.status = "rejected"
    charge_req.admin_id = admin.id
    charge_req.admin_memo = body.memo or "거절"
    charge_req.processed_at = datetime.now()

    await log_security_event(
        charge_req.user_id, "charge_rejected",
        f"충전 거절: {charge_req.amount:,}원 (관리자: {admin.username}, 사유: {body.memo})", db
    )
    await db.commit()
    return {"message": "충전 요청이 거절되었습니다"}


# ══════════════════════════════════════════════
#  전체 결제 내역
# ══════════════════════════════════════════════

@router.get("/credits")
async def admin_credits(
    page: int = 1, size: int = 100,
    credit_type: str = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """전체 크레딧 내역 (충전/사용/보너스)"""
    offset = (page - 1) * size
    conditions = []
    if credit_type:
        conditions.append(Credit.type == credit_type)
    where_clause = and_(*conditions) if conditions else True

    count_result = await db.execute(
        select(func.count(Credit.id)).where(where_clause)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Credit, User.username, User.name)
        .outerjoin(User, Credit.user_id == User.id)
        .where(where_clause)
        .order_by(Credit.created_at.desc())
        .offset(offset).limit(size)
    )
    rows = result.all()
    return {
        "total": total,
        "credits": [
            {
                "id": c.id, "user_id": c.user_id,
                "username": username or "", "user_name": name or "",
                "amount": c.amount, "type": c.type,
                "description": c.description,
                "created_at": c.created_at.isoformat()
            }
            for c, username, name in rows
        ]
    }


# ══════════════════════════════════════════════
#  서버 설정
# ══════════════════════════════════════════════

@router.get("/settings")
async def get_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """서버 설정 조회"""
    result = await db.execute(select(ServerSetting))
    settings = result.scalars().all()
    return {s.key: {"value": s.value, "description": s.description} for s in settings}


class SettingsUpdate(BaseModel):
    settings: dict


@router.put("/settings")
async def update_settings(
    body: SettingsUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """서버 설정 업데이트"""
    for key, value in body.settings.items():
        result = await db.execute(
            select(ServerSetting).where(ServerSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.now()

    await db.commit()
    return {"message": "설정이 저장되었습니다"}
