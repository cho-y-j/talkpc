"""발송 서비스 - Wideshot HTTP REST API + msg_queue INSERT 폴백"""
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    SEJONG_SENDER_KEY, SEJONG_CALLBACK, SEJONG_TEMPLATE_CODE,
    COST_SMS, COST_LMS, COST_ALIMTALK,
    COST_RCS_SMS, COST_RCS_LMS, COST_RCS_MMS,
    COST_BRANDTALK,
    WIDESHOT_API_URL, WIDESHOT_API_KEY, WIDESHOT_CALLBACK,
    WIDESHOT_CHATBOT_ID, SEND_METHOD,
    BRAND_SENDER_KEY, BRAND_UNSUBSCRIBE_PHONE,
)

logger = logging.getLogger(__name__)


async def get_active_callback(user_id: int, db: AsyncSession) -> str:
    """사용자의 활성 발신번호를 조회. 없으면 WIDESHOT_CALLBACK 폴백."""
    from app.models.user_callback import UserCallback
    result = await db.execute(
        select(UserCallback).where(
            UserCallback.user_id == user_id,
            UserCallback.is_active == True,
        )
    )
    cb = result.scalar_one_or_none()
    if cb:
        return cb.phone
    return WIDESHOT_CALLBACK


def _generate_user_key() -> str:
    """고유 userKey 생성 (영문+숫자만, 최대 12자)"""
    return uuid.uuid4().hex[:12]


def _api_headers() -> dict:
    """Wideshot API 공통 헤더"""
    return {"sejongApiKey": WIDESHOT_API_KEY}


# ---------------------------------------------------------------------------
# 비용 계산 (기존 유지)
# ---------------------------------------------------------------------------

def calculate_cost(message: str, msg_type: str) -> tuple[int, str]:
    """메시지 비용 계산 (기본값). returns (cost, actual_msg_type)"""
    if msg_type == "alimtalk":
        return COST_ALIMTALK, "alimtalk"
    if msg_type == "brandtalk":
        return COST_BRANDTALK, "brandtalk"
    byte_len = len(message.encode("euc-kr", errors="replace"))
    if byte_len <= 90:
        return COST_SMS, "sms"
    else:
        return COST_LMS, "lms"


async def calculate_cost_from_db(message: str, msg_type: str, db: AsyncSession,
                                 has_image: bool = False) -> tuple[int, str]:
    """DB 설정 기반 비용 계산 (관리자 변경 반영)"""
    from app.models.charge_request import ServerSetting
    result = await db.execute(
        select(ServerSetting).where(
            ServerSetting.key.in_([
                'cost_sms', 'cost_lms', 'cost_alimtalk',
                'cost_rcs_sms', 'cost_rcs_lms', 'cost_rcs_mms',
                'cost_brandtalk'
            ])
        )
    )
    settings = {s.key: int(s.value) for s in result.scalars().all()}

    cost_sms = settings.get('cost_sms', COST_SMS)
    cost_lms = settings.get('cost_lms', COST_LMS)
    cost_alimtalk = settings.get('cost_alimtalk', COST_ALIMTALK)
    cost_rcs_sms = settings.get('cost_rcs_sms', COST_RCS_SMS)
    cost_rcs_lms = settings.get('cost_rcs_lms', COST_RCS_LMS)
    cost_rcs_mms = settings.get('cost_rcs_mms', COST_RCS_MMS)
    cost_brandtalk = settings.get('cost_brandtalk', COST_BRANDTALK)

    if msg_type == "brandtalk":
        return cost_brandtalk, "brandtalk"
    elif msg_type == "alimtalk":
        return cost_alimtalk, "alimtalk"
    elif msg_type == "rcs":
        if has_image:
            return cost_rcs_mms, "rcs_mms"
        byte_len = len(message.encode("euc-kr", errors="replace"))
        if byte_len <= 90:
            return cost_rcs_sms, "rcs_sms"
        else:
            return cost_rcs_lms, "rcs_lms"

    byte_len = len(message.encode("euc-kr", errors="replace"))
    if byte_len <= 90:
        return cost_sms, "sms"
    else:
        return cost_lms, "lms"


# ===========================================================================
# Wideshot HTTP REST API 발송
# ===========================================================================

async def send_sms_api(
    phone: str, message: str,
    callback: str = None, subject: str = "알림"
) -> dict:
    """Wideshot HTTP API로 SMS/LMS 발송 → {"send_code": ..., "status": ...}"""
    cb = callback or WIDESHOT_CALLBACK
    user_key = _generate_user_key()
    byte_len = len(message.encode("euc-kr", errors="replace"))

    if byte_len <= 90:
        url = f"{WIDESHOT_API_URL}/api/v1/message/sms"
        form_data = {
            "callback": cb,
            "contents": message,
            "receiverTelNo": phone,
            "userKey": user_key,
        }
    else:
        url = f"{WIDESHOT_API_URL}/api/v1/message/lms"
        form_data = {
            "callback": cb,
            "contents": message,
            "receiverTelNo": phone,
            "title": subject,
            "userKey": user_key,
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form_data, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {"send_code": body.get("sendCode", user_key), "status": "sent"}
    else:
        raise RuntimeError(f"Wideshot API 오류: [{body.get('code')}] {body.get('message', '')}")


async def send_alimtalk_api(
    phone: str, message: str,
    template_code: str = None, buttons: list = None,
    fallback_type: str = "sms", callback: str = None,
    fallback_message: str = None, sender_key: str = None
) -> dict:
    """Wideshot HTTP API로 알림톡 발송"""
    cb = callback or WIDESHOT_CALLBACK
    sk = sender_key or SEJONG_SENDER_KEY
    tmpl_code = template_code or SEJONG_TEMPLATE_CODE
    user_key = _generate_user_key()

    url = f"{WIDESHOT_API_URL}/api/v3/message/alimtalk"

    # 대체 발송 타입 매핑
    resend_type_map = {"none": "NO", "sms": "SMS", "lms": "LMS", "mms": "MMS"}
    resend_type = resend_type_map.get(fallback_type, "SMS")

    form_data = {
        "senderKey": sk,
        "templateCode": tmpl_code,
        "contents": message,
        "receiverTelNo": phone,
        "userKey": user_key,
        "messageType": "AT",
    }

    # 버튼/첨부 JSON
    if buttons:
        attachment = {"button": buttons}
        form_data["attachment"] = json.dumps(attachment, ensure_ascii=False)

    # 대체 발송 설정
    if fallback_type != "none":
        form_data["resendType"] = resend_type
        form_data["resendCallback"] = cb
        form_data["resendContents"] = fallback_message or message

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form_data, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {"send_code": body.get("sendCode", user_key), "status": "sent"}
    else:
        raise RuntimeError(f"Wideshot API 오류: [{body.get('code')}] {body.get('message', '')}")


async def send_rcs_api(
    phone: str, message: str,
    msg_type: str = "standalone", title: str = "",
    image_url: str = "", buttons: list = None,
    cards: list = None, fallback_type: str = "sms",
    callback: str = None
) -> dict:
    """Wideshot HTTP API로 RCS 발송"""
    cb = callback or WIDESHOT_CALLBACK
    user_key = _generate_user_key()
    chatbot_id = WIDESHOT_CHATBOT_ID

    url = f"{WIDESHOT_API_URL}/api/v1/message/rcs"

    # RCS r_json 구성 (메시지 본문)
    rcs_body: dict = {}
    if title:
        rcs_body["title"] = title
    rcs_body["description"] = message
    if image_url:
        rcs_body["media"] = image_url
    if buttons:
        rcs_body["suggestions"] = buttons
    if cards:
        rcs_body["cards"] = cards

    # messagebaseId 결정
    byte_len = len(message.encode("euc-kr", errors="replace"))
    if cards:
        messagebase_id = "SS000000"  # carousel (예시, 실제 값은 확인 필요)
    elif image_url:
        messagebase_id = "SS000000"  # MMS 형태
    elif byte_len <= 90:
        messagebase_id = "SS000000"  # SMS 형태
    else:
        messagebase_id = "SL000000"  # LMS 형태

    # 대체 발송 타입
    resend_type_map = {"none": "NO", "sms": "SMS", "lms": "LMS"}
    resend_type = resend_type_map.get(fallback_type, "SMS")

    form_data = {
        "UserKey": user_key,
        "receiverTelNo": phone,
        "chatbotId": chatbot_id,
        "header": "0",
        "footer": "",
        "copyAllowed": "Y",
        "messagebaseId": messagebase_id,
        "r_json": json.dumps(rcs_body, ensure_ascii=False),
        "resendType": resend_type,
        "resendCallback": cb,
        "resendContents": message,
    }
    if title:
        form_data["title"] = title

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form_data, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {"send_code": body.get("sendCode", user_key), "status": "sent"}
    else:
        raise RuntimeError(f"Wideshot API 오류: [{body.get('code')}] {body.get('message', '')}")


# ===========================================================================
# 브랜드메시지 (카카오 브랜드톡) - Wideshot HTTP REST API
# ===========================================================================

async def send_brandtalk_api(
    phone: str, message: str,
    sender_key: str = None, targeting: str = "I",
    bubble_type: str = "TEXT", unsubscribe_phone: str = None,
    buttons: list = None, image_url: str = None,
    adult: str = "N"
) -> dict:
    """Wideshot HTTP API로 브랜드메시지 자유형 한건 발송"""
    sk = sender_key or BRAND_SENDER_KEY
    unsub = unsubscribe_phone or BRAND_UNSUBSCRIBE_PHONE
    user_key = _generate_user_key()

    url = f"{WIDESHOT_API_URL}/api/v1/message/freestyle"

    form_data = {
        "userKey": user_key,
        "receiverTelNo": phone,
        "senderKey": sk,
        "targeting": targeting,
        "chatBubbleType": bubble_type,
        "contents": message,
        "unsubscribePhoneNumber": unsub,
        "adult": adult,
    }

    # 첨부 (버튼/이미지)
    if buttons or image_url:
        attachment = {}
        if buttons:
            attachment["button"] = buttons
        if image_url:
            attachment["image"] = {"imgUrl": image_url, "imgLink": image_url}
        form_data["attachment"] = json.dumps(attachment, ensure_ascii=False)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form_data, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {"send_code": body.get("sendCode", user_key), "status": "sent"}
    else:
        raise RuntimeError(f"Wideshot API 오류: [{body.get('code')}] {body.get('message', '')}")


async def send_brandtalk_batch_api(
    targets: list, message: str,
    sender_key: str = None, targeting: str = "I",
    bubble_type: str = "TEXT", unsubscribe_phone: str = None,
    buttons: list = None, image_url: str = None,
    adult: str = "N"
) -> dict:
    """Wideshot HTTP API로 브랜드메시지 자유형 여러건 발송
    targets: [{"receiverTelNo": "01012345678"}, ...]
    """
    sk = sender_key or BRAND_SENDER_KEY
    unsub = unsubscribe_phone or BRAND_UNSUBSCRIBE_PHONE
    user_key = _generate_user_key()

    url = f"{WIDESHOT_API_URL}/api/v1/message/freestyle/batch"

    form_data = {
        "userKey": user_key,
        "senderKey": sk,
        "targeting": targeting,
        "chatBubbleType": bubble_type,
        "contents": message,
        "unsubscribePhoneNumber": unsub,
        "adult": adult,
        "targets": json.dumps(targets, ensure_ascii=False),
    }

    if buttons or image_url:
        attachment = {}
        if buttons:
            attachment["button"] = buttons
        if image_url:
            attachment["image"] = {"imgUrl": image_url, "imgLink": image_url}
        form_data["attachment"] = json.dumps(attachment, ensure_ascii=False)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form_data, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {"send_code": body.get("sendCode", user_key), "status": "sent"}
    else:
        raise RuntimeError(f"Wideshot API 오류: [{body.get('code')}] {body.get('message', '')}")


async def check_brandtalk_results_api() -> dict:
    """브랜드메시지 전용 결과 조회"""
    url = f"{WIDESHOT_API_URL}/api/v1/message/direct/results"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=_api_headers())

    return resp.json()


async def send_brandtalk(
    db: AsyncSession, phone: str, message: str,
    sender_key: str = None, targeting: str = "I",
    bubble_type: str = "TEXT", unsubscribe_phone: str = None,
    buttons: list = None, image_url: str = None,
    user_id: int = None
) -> dict:
    """브랜드메시지 발송 - API만 (msg_queue 폴백 없음)
    Returns: {"send_code": str, "mseq": int|None, "status": str, "method": str}
    """
    if SEND_METHOD == "api" and WIDESHOT_API_KEY:
        result = await send_brandtalk_api(
            phone, message, sender_key=sender_key,
            targeting=targeting, bubble_type=bubble_type,
            unsubscribe_phone=unsubscribe_phone,
            buttons=buttons, image_url=image_url,
        )
        return {
            "send_code": result["send_code"],
            "mseq": None,
            "status": result["status"],
            "method": "api",
        }
    else:
        raise RuntimeError("브랜드메시지는 Wideshot API 모드에서만 발송 가능합니다. WIDESHOT_API_KEY를 설정하세요.")


# ===========================================================================
# 결과 조회 - Wideshot HTTP API
# ===========================================================================

async def check_result_api(send_code: str) -> dict:
    """Wideshot API로 발송 결과 조회"""
    url = f"{WIDESHOT_API_URL}/api/v3/message/result"
    params = {"sendCode": send_code}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params, headers=_api_headers())

    body = resp.json()
    if body.get("code") == "200":
        return {
            "found": True,
            "send_code": send_code,
            "status": "완료",
            "detail": body,
        }
    else:
        return {
            "found": True,
            "send_code": send_code,
            "status": body.get("code", "unknown"),
            "message": body.get("message", ""),
        }


async def check_results_all_api() -> dict:
    """Wideshot API로 전체 결과 조회"""
    url = f"{WIDESHOT_API_URL}/api/v3/message/results"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=_api_headers())

    return resp.json()


# ===========================================================================
# msg_queue INSERT 폴백 (기존 방식)
# ===========================================================================

async def insert_msg_queue_sms(
    db: AsyncSession, phone: str, message: str,
    callback: str = None, subject: str = "알림"
) -> int:
    """SMS/LMS msg_queue INSERT → mseq 반환"""
    cb = callback or SEJONG_CALLBACK
    byte_len = len(message.encode("euc-kr", errors="replace"))
    msg_type = "1" if byte_len <= 90 else "3"

    if msg_type == "1":
        result = await db.execute(text("""
            INSERT INTO msg_queue (msg_type, dstaddr, callback, text, request_time)
            VALUES (:msg_type, :phone, :callback, :message, NOW())
            RETURNING mseq
        """), {"msg_type": msg_type, "phone": phone, "callback": cb, "message": message})
    else:
        result = await db.execute(text("""
            INSERT INTO msg_queue (msg_type, dstaddr, callback, subject, text, request_time)
            VALUES (:msg_type, :phone, :callback, :subject, :message, NOW())
            RETURNING mseq
        """), {"msg_type": msg_type, "phone": phone, "callback": cb,
               "subject": subject, "message": message})

    return result.scalar()


async def insert_msg_queue_alimtalk(
    db: AsyncSession, phone: str, message: str,
    template_code: str = None, buttons: list = None,
    fallback_type: str = "sms", callback: str = None,
    fallback_message: str = None
) -> int:
    """알림톡 msg_queue INSERT → mseq 반환"""
    cb = callback or SEJONG_CALLBACK
    sender_key = SEJONG_SENDER_KEY
    tmpl_code = template_code or SEJONG_TEMPLATE_CODE

    next_type_map = {"none": 0, "sms": 7, "lms": 8, "mms": 9}
    k_next_type = next_type_map.get(fallback_type, 7)

    attach = {"message_type": "AT"}
    if buttons:
        attach["attachment"] = {"button": buttons}

    text2 = fallback_message or message

    result = await db.execute(text("""
        INSERT INTO msg_queue (
            msg_type, dstaddr, callback, subject, text, text2,
            request_time, k_template_code, k_next_type,
            sender_key, k_at_send_type, k_attach
        ) VALUES (
            '6', :phone, :callback, '알림톡', :message, :text2,
            NOW(), :template_code, :k_next_type,
            :sender_key, '0', :k_attach
        )
        RETURNING mseq
    """), {
        "phone": phone, "callback": cb, "message": message, "text2": text2,
        "template_code": tmpl_code, "k_next_type": k_next_type,
        "sender_key": sender_key,
        "k_attach": json.dumps(attach, ensure_ascii=False),
    })

    return result.scalar()


async def insert_msg_queue_rcs(
    db: AsyncSession, phone: str, message: str,
    msg_type: str = "standalone", title: str = "",
    image_url: str = "", buttons: list = None,
    cards: list = None, fallback_type: str = "sms",
    callback: str = None
) -> int:
    """RCS msg_queue INSERT → mseq 반환 (세종텔레콤 RCS 승인 후 활성화)"""
    cb = callback or SEJONG_CALLBACK

    rcs_body = {"messageType": msg_type}
    if title:
        rcs_body["title"] = title
    if image_url:
        rcs_body["media"] = image_url
    if buttons:
        rcs_body["suggestions"] = buttons
    if cards:
        rcs_body["cards"] = cards

    next_type_map = {"none": 0, "sms": 7, "lms": 8}
    rcs_next_type = next_type_map.get(fallback_type, 7)

    result = await db.execute(text("""
        INSERT INTO msg_queue (
            msg_type, dstaddr, callback, subject, text, text2,
            request_time, k_next_type, k_attach
        ) VALUES (
            '10', :phone, :callback, :subject, :message, :message,
            NOW(), :k_next_type, :k_attach
        )
        RETURNING mseq
    """), {
        "phone": phone, "callback": cb, "subject": title or "RCS",
        "message": message, "k_next_type": rcs_next_type,
        "k_attach": json.dumps(rcs_body, ensure_ascii=False),
    })

    return result.scalar()


# ===========================================================================
# 결과 조회 - msg_queue 폴백 (기존 방식)
# ===========================================================================

async def check_result(db: AsyncSession, mseq: int) -> dict:
    """발송 결과 조회 (msg_queue 폴백)"""
    result = await db.execute(text("""
        SELECT mseq, stat, result, dstaddr, report_time
        FROM msg_queue WHERE mseq = :mseq
    """), {"mseq": mseq})
    row = result.mappings().first()

    if not row:
        # 테이블명은 날짜 기반으로 안전하게 생성 (SQL 인젝션 방지)
        yyyymm = datetime.now().strftime('%Y%m')
        if not yyyymm.isdigit() or len(yyyymm) != 6:
            return {"found": False}
        table = f"msg_result_{yyyymm}"
        try:
            result = await db.execute(text(
                f"SELECT mseq, stat, result, dstaddr, report_time "
                f"FROM {table} WHERE mseq = :mseq"
            ), {"mseq": mseq})
            row = result.mappings().first()
        except Exception:
            pass

    if row:
        stat_map = {"0": "대기", "1": "송신중", "2": "송신완료", "3": "결과수신"}
        return {
            "found": True,
            "mseq": row["mseq"],
            "stat": stat_map.get(row["stat"], row["stat"]),
            "result": row.get("result", ""),
            "phone": row["dstaddr"],
        }
    return {"found": False}


# ===========================================================================
# 통합 발송 함수 (SEND_METHOD에 따라 API 또는 큐 선택)
# ===========================================================================

async def send_sms(
    db: AsyncSession, phone: str, message: str,
    callback: str = None, subject: str = "알림",
    user_id: int = None
) -> dict:
    """SMS/LMS 발송 - 설정에 따라 API 또는 msg_queue 사용
    Returns: {"send_code": str, "mseq": int|None, "status": str, "method": str}
    """
    if callback is None and user_id:
        callback = await get_active_callback(user_id, db)
    if SEND_METHOD == "api" and WIDESHOT_API_KEY:
        try:
            result = await send_sms_api(phone, message, callback=callback, subject=subject)
            return {
                "send_code": result["send_code"],
                "mseq": None,
                "status": result["status"],
                "method": "api",
            }
        except Exception as e:
            logger.warning(f"Wideshot API 실패, msg_queue 폴백: {e}")

    # 폴백: msg_queue INSERT
    mseq = await insert_msg_queue_sms(db, phone, message, callback=callback, subject=subject)
    return {
        "send_code": None,
        "mseq": mseq,
        "status": "queued",
        "method": "queue",
    }


async def send_alimtalk(
    db: AsyncSession, phone: str, message: str,
    template_code: str = None, buttons: list = None,
    fallback_type: str = "sms", callback: str = None,
    fallback_message: str = None, sender_key: str = None,
    user_id: int = None
) -> dict:
    """알림톡 발송 - 설정에 따라 API 또는 msg_queue 사용"""
    if callback is None and user_id:
        callback = await get_active_callback(user_id, db)
    if SEND_METHOD == "api" and WIDESHOT_API_KEY:
        try:
            result = await send_alimtalk_api(
                phone, message, template_code=template_code,
                buttons=buttons, fallback_type=fallback_type,
                callback=callback, fallback_message=fallback_message,
                sender_key=sender_key,
            )
            return {
                "send_code": result["send_code"],
                "mseq": None,
                "status": result["status"],
                "method": "api",
            }
        except Exception as e:
            logger.warning(f"Wideshot API 실패, msg_queue 폴백: {e}")

    mseq = await insert_msg_queue_alimtalk(
        db, phone, message, template_code=template_code,
        buttons=buttons, fallback_type=fallback_type,
        callback=callback, fallback_message=fallback_message,
    )
    return {
        "send_code": None,
        "mseq": mseq,
        "status": "queued",
        "method": "queue",
    }


async def send_rcs(
    db: AsyncSession, phone: str, message: str,
    msg_type: str = "standalone", title: str = "",
    image_url: str = "", buttons: list = None,
    cards: list = None, fallback_type: str = "sms",
    callback: str = None, user_id: int = None
) -> dict:
    """RCS 발송 - 설정에 따라 API 또는 msg_queue 사용"""
    if callback is None and user_id:
        callback = await get_active_callback(user_id, db)
    if SEND_METHOD == "api" and WIDESHOT_API_KEY:
        try:
            result = await send_rcs_api(
                phone, message, msg_type=msg_type, title=title,
                image_url=image_url, buttons=buttons, cards=cards,
                fallback_type=fallback_type, callback=callback,
            )
            return {
                "send_code": result["send_code"],
                "mseq": None,
                "status": result["status"],
                "method": "api",
            }
        except Exception as e:
            logger.warning(f"Wideshot API 실패, msg_queue 폴백: {e}")

    mseq = await insert_msg_queue_rcs(
        db, phone, message, msg_type=msg_type, title=title,
        image_url=image_url, buttons=buttons, cards=cards,
        fallback_type=fallback_type, callback=callback,
    )
    return {
        "send_code": None,
        "mseq": mseq,
        "status": "queued",
        "method": "queue",
    }
