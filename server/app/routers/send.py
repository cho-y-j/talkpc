"""발송 라우터 - Wideshot HTTP API + msg_queue 폴백, 과금, 보안"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.contact import Contact
from app.models.send_log import SendLog
from app.schemas.send import SendSMSRequest, SendAlimtalkRequest, SendRCSRequest, SendBrandtalkRequest, BatchSendResponse
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
    result = await db.execute(
        select(Contact).where(Contact.id.in_(req.contact_ids), Contact.user_id == user.id)
    )
    contacts = list(result.scalars().all())
    if not contacts:
        raise HTTPException(400, "발송 대상이 없습니다")

    # 총 비용 계산 (DB 단가 반영)
    total_cost = 0
    send_items = []
    for c in contacts:
        if not c.phone:
            continue
        cost, msg_type = await send_service.calculate_cost_from_db(req.message, "sms", db)
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
            send_result = await send_service.send_sms(
                db, contact.phone, req.message, subject=req.subject,
                user_id=user.id
            )

            tracking_id = send_result["send_code"] or str(send_result["mseq"])
            await credit_service.deduct(
                user.id, cost, f"{msg_type} {send_result['method']}={tracking_id}", db
            )

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type=msg_type, message_preview=req.message[:100],
                mseq=send_result["mseq"],
                send_code=send_result["send_code"],
                status=send_result["status"], cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({
                "name": contact.name,
                "send_code": send_result["send_code"],
                "mseq": send_result["mseq"],
                "status": send_result["status"],
                "method": send_result["method"],
                "cost": cost,
            })
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

    # 알림톡 단가 (DB 반영)
    alimtalk_cost, _ = await send_service.calculate_cost_from_db("", "alimtalk", db)
    send_items = [(c, alimtalk_cost) for c in contacts if c.phone]
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
            send_result = await send_service.send_alimtalk(
                db, contact.phone, req.message,
                template_code=req.template_code,
                buttons=req.buttons, fallback_type=req.fallback_type,
                user_id=user.id
            )

            tracking_id = send_result["send_code"] or str(send_result["mseq"])
            await credit_service.deduct(
                user.id, cost, f"alimtalk {send_result['method']}={tracking_id}", db
            )

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type="alimtalk", message_preview=req.message[:100],
                mseq=send_result["mseq"],
                send_code=send_result["send_code"],
                status=send_result["status"], cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({
                "name": contact.name,
                "send_code": send_result["send_code"],
                "mseq": send_result["mseq"],
                "status": send_result["status"],
                "method": send_result["method"],
                "cost": cost,
            })
            success += 1
        except Exception as e:
            results.append({"name": contact.name, "status": "failed", "detail": str(e)})
            failed += 1

    await db.commit()
    return BatchSendResponse(
        total=len(send_items), success=success, failed=failed,
        results=results, total_cost=total_cost
    )


@router.post("/rcs", response_model=BatchSendResponse)
async def send_rcs(
    req: SendRCSRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RCS 리치 메시지 발송"""
    result = await db.execute(
        select(Contact).where(Contact.id.in_(req.contact_ids), Contact.user_id == user.id)
    )
    contacts = list(result.scalars().all())
    if not contacts:
        raise HTTPException(400, "발송 대상이 없습니다")

    has_image = bool(req.image_url or req.cards)
    rcs_cost, rcs_type = await send_service.calculate_cost_from_db(
        req.message, "rcs", db, has_image=has_image
    )
    send_items = [(c, rcs_cost) for c in contacts if c.phone]
    if not send_items:
        raise HTTPException(400, "전화번호가 있는 연락처가 없습니다")

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
            send_result = await send_service.send_rcs(
                db, contact.phone, req.message,
                msg_type=req.msg_type, title=req.title,
                image_url=req.image_url, buttons=req.buttons,
                cards=req.cards, fallback_type=req.fallback_type,
                user_id=user.id
            )

            tracking_id = send_result["send_code"] or str(send_result["mseq"])
            await credit_service.deduct(
                user.id, cost, f"{rcs_type} {send_result['method']}={tracking_id}", db
            )

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type=rcs_type, message_preview=req.message[:100],
                mseq=send_result["mseq"],
                send_code=send_result["send_code"],
                status=send_result["status"], cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({
                "name": contact.name,
                "send_code": send_result["send_code"],
                "mseq": send_result["mseq"],
                "status": send_result["status"],
                "method": send_result["method"],
                "cost": cost,
            })
            success += 1
        except Exception as e:
            results.append({"name": contact.name, "status": "failed", "detail": str(e)})
            failed += 1

    await db.commit()
    return BatchSendResponse(
        total=len(send_items), success=success, failed=failed,
        results=results, total_cost=total_cost
    )


@router.post("/brandtalk", response_model=BatchSendResponse)
async def send_brandtalk(
    req: SendBrandtalkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """브랜드메시지 (카카오 브랜드톡) 일괄 발송"""
    result = await db.execute(
        select(Contact).where(Contact.id.in_(req.contact_ids), Contact.user_id == user.id)
    )
    contacts = list(result.scalars().all())
    if not contacts:
        raise HTTPException(400, "발송 대상이 없습니다")

    # 브랜드톡 단가 (DB 반영)
    brandtalk_cost, _ = await send_service.calculate_cost_from_db("", "brandtalk", db)
    send_items = [(c, brandtalk_cost) for c in contacts if c.phone]
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
            send_result = await send_service.send_brandtalk(
                db, contact.phone, req.message,
                targeting=req.targeting, bubble_type=req.bubble_type,
                buttons=req.buttons, image_url=req.image_url,
                user_id=user.id
            )

            tracking_id = send_result["send_code"] or str(send_result["mseq"])
            await credit_service.deduct(
                user.id, cost, f"brandtalk {send_result['method']}={tracking_id}", db
            )

            log = SendLog(
                user_id=user.id, contact_id=contact.id,
                contact_name=contact.name, contact_phone=contact.phone,
                msg_type="brandtalk", message_preview=req.message[:100],
                mseq=send_result["mseq"],
                send_code=send_result["send_code"],
                status=send_result["status"], cost=cost
            )
            db.add(log)

            contact.last_sent = datetime.now()
            contact.send_count += 1

            results.append({
                "name": contact.name,
                "send_code": send_result["send_code"],
                "mseq": send_result["mseq"],
                "status": send_result["status"],
                "method": send_result["method"],
                "cost": cost,
            })
            success += 1
        except Exception as e:
            results.append({"name": contact.name, "status": "failed", "detail": str(e)})
            failed += 1

    await db.commit()
    return BatchSendResponse(
        total=len(send_items), success=success, failed=failed,
        results=results, total_cost=total_cost
    )


@router.get("/brandtalk/results")
async def get_brandtalk_results():
    """브랜드메시지 전용 결과 조회"""
    return await send_service.check_brandtalk_results_api()


@router.get("/result/{identifier}")
async def get_result(
    identifier: str,
    db: AsyncSession = Depends(get_db)
):
    """발송 결과 조회 - send_code(API) 또는 mseq(큐) 지원"""
    # send_code 형식이면 API 조회
    if not identifier.isdigit():
        return await send_service.check_result_api(identifier)

    # 숫자면 기존 mseq 조회
    return await send_service.check_result(db, int(identifier))


@router.get("/results")
async def get_results_all():
    """Wideshot API 전체 결과 조회"""
    return await send_service.check_results_all_api()


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
            "mseq": l.mseq, "send_code": l.send_code,
            "status": l.status, "cost": l.cost,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
