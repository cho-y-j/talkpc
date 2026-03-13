"""보안 서비스 - 발송 한도, 자동 차단, 기기 인증, 시간 제한"""
import random
import string
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.send_log import SendLog
from app.models.device import Device, SecurityLog


# ─── 발송 한도 체크 + 자동 차단 ───

async def check_send_limits(user: User, send_count: int, db: AsyncSession) -> dict:
    """발송 한도 체크. 초과 시 계정 자동 잠금.
    Returns: {"allowed": bool, "reason": str}
    """
    # 계정 잠금 상태 확인
    if user.is_locked:
        return {"allowed": False, "reason": f"계정 잠금: {user.locked_reason}"}

    now = datetime.now()

    # 야간 발송 차단
    current_hour = now.hour
    if user.send_start_hour < user.send_end_hour:
        # 일반: 8~21시 허용
        if current_hour < user.send_start_hour or current_hour >= user.send_end_hour:
            return {
                "allowed": False,
                "reason": f"발송 가능 시간: {user.send_start_hour}시 ~ {user.send_end_hour}시"
            }
    else:
        # 야간 포함 (예: 22~6시 차단 → start=6, end=22)
        if current_hour >= user.send_end_hour and current_hour < user.send_start_hour:
            return {
                "allowed": False,
                "reason": f"발송 가능 시간: {user.send_start_hour}시 ~ {user.send_end_hour}시"
            }

    # 시간당 발송량 체크
    one_hour_ago = now - timedelta(hours=1)
    hourly_result = await db.execute(
        select(func.count(SendLog.id)).where(
            and_(SendLog.user_id == user.id, SendLog.created_at >= one_hour_ago)
        )
    )
    hourly_count = hourly_result.scalar() or 0

    if hourly_count + send_count > user.hourly_limit:
        # 자동 잠금
        await lock_user(user, f"시간당 한도 초과 ({hourly_count + send_count}/{user.hourly_limit})", db)
        await log_security_event(user.id, "auto_lock", f"시간당 한도 초과: {hourly_count + send_count}건", db)
        return {
            "allowed": False,
            "reason": f"시간당 발송 한도 초과 ({user.hourly_limit}건). 계정이 자동 잠금되었습니다. 관리자에게 문의하세요."
        }

    # 일일 발송량 체크
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_result = await db.execute(
        select(func.count(SendLog.id)).where(
            and_(SendLog.user_id == user.id, SendLog.created_at >= today_start)
        )
    )
    daily_count = daily_result.scalar() or 0

    if daily_count + send_count > user.daily_limit:
        await lock_user(user, f"일일 한도 초과 ({daily_count + send_count}/{user.daily_limit})", db)
        await log_security_event(user.id, "auto_lock", f"일일 한도 초과: {daily_count + send_count}건", db)
        return {
            "allowed": False,
            "reason": f"일일 발송 한도 초과 ({user.daily_limit}건). 계정이 자동 잠금되었습니다. 관리자에게 문의하세요."
        }

    return {"allowed": True, "reason": ""}


async def lock_user(user: User, reason: str, db: AsyncSession):
    """계정 자동 잠금"""
    user.is_locked = True
    user.locked_reason = reason


async def unlock_user(user: User, db: AsyncSession):
    """계정 잠금 해제 (관리자)"""
    user.is_locked = False
    user.locked_reason = ""


# ─── 기기 등록 + 이메일 인증 ───

def generate_verify_code() -> str:
    """6자리 인증 코드 생성"""
    return "".join(random.choices(string.digits, k=6))


async def check_device(user_id: int, device_id: str, db: AsyncSession) -> dict:
    """기기 등록 상태 확인.
    Returns: {"status": "approved"|"pending"|"new", "device": Device|None}
    """
    result = await db.execute(
        select(Device).where(
            and_(Device.user_id == user_id, Device.device_id == device_id)
        )
    )
    device = result.scalar_one_or_none()

    if device and device.is_approved:
        return {"status": "approved", "device": device}
    elif device:
        return {"status": "pending", "device": device}
    else:
        return {"status": "new", "device": None}


async def register_device(
    user_id: int, device_id: str, device_name: str, db: AsyncSession
) -> Device:
    """새 기기 등록 + 인증 코드 생성"""
    code = generate_verify_code()
    expires = datetime.now() + timedelta(minutes=10)

    device = Device(
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        verify_code=code,
        verify_expires=expires,
    )
    db.add(device)
    await db.flush()
    return device


async def verify_device(user_id: int, device_id: str, code: str, db: AsyncSession) -> bool:
    """이메일 인증 코드 확인"""
    result = await db.execute(
        select(Device).where(
            and_(Device.user_id == user_id, Device.device_id == device_id)
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        return False

    if device.verify_code != code:
        return False

    if device.verify_expires and datetime.now() > device.verify_expires:
        return False

    device.is_approved = True
    device.verify_code = ""
    return True


async def resend_verify_code(user_id: int, device_id: str, db: AsyncSession) -> str:
    """인증 코드 재발송"""
    result = await db.execute(
        select(Device).where(
            and_(Device.user_id == user_id, Device.device_id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return ""

    code = generate_verify_code()
    device.verify_code = code
    device.verify_expires = datetime.now() + timedelta(minutes=10)
    return code


# ─── 보안 로그 ───

async def log_security_event(
    user_id: int, event_type: str, detail: str, db: AsyncSession, ip: str = ""
):
    """보안 이벤트 기록"""
    log = SecurityLog(
        user_id=user_id,
        event_type=event_type,
        detail=detail,
        ip_address=ip,
    )
    db.add(log)


async def get_security_logs(
    user_id: int, db: AsyncSession, limit: int = 50
) -> list:
    """보안 로그 조회"""
    result = await db.execute(
        select(SecurityLog)
        .where(SecurityLog.user_id == user_id)
        .order_by(SecurityLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── 이메일 발송 ───

async def send_verify_email(email: str, code: str):
    """인증 코드 이메일 발송
    TODO: 실제 이메일 서비스 연동 (SMTP, SES 등)
    현재는 로그로 대체
    """
    import logging
    logger = logging.getLogger("security")
    logger.info(f"[이메일 인증] {email} → 코드: {code}")
    # 실제 서비스에서는 여기에 SMTP/SES 연동
    return True
