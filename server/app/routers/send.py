"""발송 라우터 - SMS/알림톡 + 과금 + 보안"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.contact import Contact
from app.models.send_log import SendLog
from app.schemas.send import SendSMSRequest, SendAlimtalkRequest, BatchSendResponse
from app.middleware.auth import get_current_user
from app.services import credit_service, send_service
from app.services.security_service import check_send_limits, log_security_event
from datetime import datetime

router = APIRouter(prefix="/send", tags=["발송"])


@router.post("/sms", response_model=BatchSendResponse)
async def send_sms(
    req: SendSMSRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """SMS/LMS 일괄 발송"""
    # 연락처 조회
    result = await db.execute(
        select(Contact).where(Contact.id.in_(req.contact_ids), Contact.user_id == user.id)
    )
    contacts = list(result.scalars().all())
    if not contacts:
        raise HTTPException(400, "발송 대상이 없습니다")

    # 총 비용 계산
    total_cost = 0
    send_items = []
    for c in contacts:
        if not c.phone:
            continue
        cost, msg_type = send_service.calculate_cost(req.message, "sms")
        total_cost += cost
        send_items.append((c, cost, msg_type))

    if not send_items:
        raise HTTPException(400, "전화번호가 있는 연락처가 없습니다")

    # 발송 한도 체크
    limit_check = await check_send_limits(user, len(send_items), db)
    if not limit_check["allowed"]:
        await db.commit()
        raise HTTPException(403, limit_check["reason"])

    # 잔액 확인
    balance = await credit_service.get_balance(user.id, db)
    if balance < total_cost:
        raise HTTPException(402, f"잔액 부족 (필요: {total_cost}원, 잔액: {balance}원)")

    # 발송 + 과금 (트랜잭션)
    results = []
    success = 0
    failed = 0

    for contact, cost, msg_type in send_items:
        try:
            mseq = await send_service.insert_msg_queue_sms(
                db, contact.phone, req.message, subject=req.subject
            )
            await credit_service.deduct(user.id, cost, f"{msg_type} mseq={mseq}", db)

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type=msg_type, message_preview=req.message[:100],
                mseq=mseq, status="queued", cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({"name": contact.name, "mseq": mseq, "status": "queued", "cost": cost})
            success += 1
        except Exception as e:
            results.append({"name": contact.name, "status": "failed", "detail": str(e)})
            failed += 1

    await db.commit()
    return BatchSendResponse(
        total=len(send_items), success=success, failed=failed,
        results=results, total_cost=total_cost
    )


@router.post("/alimtalk", response_model=BatchSendResponse)
async def send_alimtalk(
    req: SendAlimtalkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """알림톡 일괄 발송"""
    result = await db.execute(
        select(Contact).where(Contact.id.in_(req.contact_ids), Contact.user_id == user.id)
    )
    contacts = list(result.scalars().all())
    if not contacts:
        raise HTTPException(400, "발송 대상이 없습니다")

    send_items = [(c, send_service.COST_ALIMTALK) for c in contacts if c.phone]
    if not send_items:
        raise HTTPException(400, "전화번호가 있는 연락처가 없습니다")

    # 발송 한도 체크
    limit_check = await check_send_limits(user, len(send_items), db)
    if not limit_check["allowed"]:
        await db.commit()
        raise HTTPException(403, limit_check["reason"])

    total_cost = sum(cost for _, cost in send_items)
    balance = await credit_service.get_balance(user.id, db)
    if balance < total_cost:
        raise HTTPException(402, f"잔액 부족 (필요: {total_cost}원, 잔액: {balance}원)")

    results = []
    success = 0
    failed = 0

    for contact, cost in send_items:
        try:
            mseq = await send_service.insert_msg_queue_alimtalk(
                db, contact.phone, req.message,
                template_code=req.template_code,
                buttons=req.buttons, fallback_type=req.fallback_type
            )
            await credit_service.deduct(user.id, cost, f"alimtalk mseq={mseq}", db)

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type="alimtalk", message_preview=req.message[:100],
                mseq=mseq, status="queued", cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({"name": contact.name, "mseq": mseq, "status": "queued", "cost": cost})
            success += 1
        except Exception as e:
            results.append({"name": contact.name, "status": "failed", "detail": str(e)})
            failed += 1

    await db.commit()
    return BatchSendResponse(
        total=len(send_items), success=success, failed=failed,
        results=results, total_cost=total_cost
    )


@router.get("/result/{mseq}")
async def get_result(mseq: int, db: AsyncSession = Depends(get_db)):
    return await send_service.check_result(db, mseq)


@router.get("/history")
async def get_history(
    page: int = 1, size: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * size
    result = await db.execute(
        select(SendLog)
        .where(SendLog.user_id == user.id)
        .order_by(SendLog.created_at.desc())
        .offset(offset).limit(size)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id, "contact_name": l.contact_name,
            "contact_phone": l.contact_phone, "msg_type": l.msg_type,
            "mseq": l.mseq, "status": l.status, "cost": l.cost,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
