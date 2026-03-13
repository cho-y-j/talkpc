"""인증 라우터 - 가입/로그인/비번변경"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, ChangePasswordRequest, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_token
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["인증"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
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

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token, user_id=user.id,
        username=user.username, name=user.name, role=user.role
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token, user_id=user.id,
        username=user.username, name=user.name, role=user.role
    )


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다")

    user.password_hash = hash_password(req.new_password)
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다"}
