"""인증 라우터 - 가입/로그인/비번변경 + 기기 인증"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, LoginResponse,
    ChangePasswordRequest, TokenResponse,
    DeviceVerifyRequest,
)
from app.services.auth_service import hash_password, verify_password, create_token
from app.services.security_service import (
    check_device, register_device, verify_device,
    send_verify_email, log_security_event, resend_verify_code,
)
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["인증"])


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # 중복 체크
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        phone=req.phone,
        email=req.email,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 첫 기기 자동 승인
    if req.device_id:
        device = await register_device(user.id, req.device_id, req.device_name, db)
        device.is_approved = True
        await db.commit()

    ip = _get_client_ip(request)
    await log_security_event(user.id, "register", f"회원가입 (IP: {ip})", db, ip)
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token, user_id=user.id,
        username=user.username, name=user.name, role=user.role
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    ip = _get_client_ip(request)

    if not user or not verify_password(req.password, user.password_hash):
        if user:
            await log_security_event(user.id, "login_fail", f"비밀번호 오류 (IP: {ip})", db, ip)
            await db.commit()
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

    if user.is_locked:
        raise HTTPException(status_code=403, detail=f"계정 잠금: {user.locked_reason}. 관리자에게 문의하세요.")

    # 기기 인증 체크
    if req.device_id:
        device_status = await check_device(user.id, req.device_id, db)

        if device_status["status"] == "new":
            # 새 기기 → 이메일 인증 필요
            if not user.email:
                # 이메일 미등록 시 관리자 승인 방식
                device = await register_device(user.id, req.device_id, req.device_name, db)
                await log_security_event(
                    user.id, "new_device",
                    f"새 기기 등록 대기 (이메일 미등록, 관리자 승인 필요): {req.device_name} (IP: {ip})", db, ip
                )
                await db.commit()
                return LoginResponse(
                    requires_verify=True,
                    verify_method="admin",
                    message="새 기기입니다. 관리자 승인이 필요합니다.",
                )

            device = await register_device(user.id, req.device_id, req.device_name, db)
            await send_verify_email(user.email, device.verify_code)
            await log_security_event(
                user.id, "new_device",
                f"새 기기 인증 요청: {req.device_name} (IP: {ip})", db, ip
            )
            await db.commit()
            return LoginResponse(
                requires_verify=True,
                verify_method="email",
                message=f"새 기기입니다. {user.email}로 인증 코드를 발송했습니다.",
            )

        elif device_status["status"] == "pending":
            # 인증 대기 중
            return LoginResponse(
                requires_verify=True,
                verify_method="email" if user.email else "admin",
                message="기기 인증이 완료되지 않았습니다. 인증 코드를 입력해주세요.",
            )

    # 기기 인증 통과 (또는 device_id 미제공)
    await log_security_event(user.id, "login", f"로그인 성공 (IP: {ip})", db, ip)
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    return LoginResponse(
        requires_verify=False,
        access_token=token, user_id=user.id,
        username=user.username, name=user.name, role=user.role
    )


@router.post("/verify-device", response_model=TokenResponse)
async def verify_device_endpoint(
    req: DeviceVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """기기 인증 코드 확인"""
    # 사용자 찾기
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")

    verified = await verify_device(user.id, req.device_id, req.code, db)
    if not verified:
        ip = _get_client_ip(request)
        await log_security_event(user.id, "verify_fail", f"기기 인증 실패 (IP: {ip})", db, ip)
        await db.commit()
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않거나 만료되었습니다")

    ip = _get_client_ip(request)
    await log_security_event(user.id, "device_verified", f"기기 인증 완료 (IP: {ip})", db, ip)
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token, user_id=user.id,
        username=user.username, name=user.name, role=user.role
    )


@router.post("/resend-code")
async def resend_code(req: DeviceVerifyRequest, db: AsyncSession = Depends(get_db)):
    """인증 코드 재발송"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not user.email:
        raise HTTPException(400, "이메일이 등록되지 않았습니다")

    code = await resend_verify_code(user.id, req.device_id, db)
    if not code:
        raise HTTPException(400, "등록된 기기를 찾을 수 없습니다")

    await send_verify_email(user.email, code)
    await db.commit()
    return {"message": f"{user.email}로 인증 코드를 재발송했습니다"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다")

    user.password_hash = hash_password(req.new_password)
    await log_security_event(user.id, "password_change", "비밀번호 변경", db)
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다"}
