"""발송 서비스 - msg_queue INSERT + 과금"""
import json
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import SEJONG_SENDER_KEY, SEJONG_CALLBACK, SEJONG_TEMPLATE_CODE
from app.config import COST_SMS, COST_LMS, COST_ALIMTALK
from app.config import COST_RCS_SMS, COST_RCS_LMS, COST_RCS_MMS


def calculate_cost(message: str, msg_type: str) -> tuple[int, str]:
    """메시지 비용 계산 (기본값). returns (cost, actual_msg_type)"""
    if msg_type == "alimtalk":
        return COST_ALIMTALK, "alimtalk"
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
                'cost_rcs_sms', 'cost_rcs_lms', 'cost_rcs_mms'
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

    if msg_type == "alimtalk":
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


async def insert_msg_queue_sms(
    db: AsyncSession, phone: str, message: str,
    callback: str = None, subject: str = "알림"
) -> int:
    """SMS/LMS msg_queue INSERT → mseq 반환"""
    cb = callback or SEJONG_CALLBACK
    byte_len = len(message.encode("euc-kr", errors="replace"))
    msg_type = "1" if byte_len <= 90 else "3"

    if msg_type == "1":
        # SMS
        result = await db.execute(text("""
            INSERT INTO msg_queue (msg_type, dstaddr, callback, text, request_time)
            VALUES (:msg_type, :phone, :callback, :message, NOW())
            RETURNING mseq
        """), {"msg_type": msg_type, "phone": phone, "callback": cb, "message": message})
    else:
        # LMS
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

    # RCS 메시지 구성
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

    # msg_type='10' for RCS (세종텔레콤 규격 - 승인 후 확정)
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


async def check_result(db: AsyncSession, mseq: int) -> dict:
    """발송 결과 조회"""
    result = await db.execute(text("""
        SELECT mseq, stat, result, dstaddr, report_time
        FROM msg_queue WHERE mseq = :mseq
    """), {"mseq": mseq})
    row = result.mappings().first()

    if not row:
        # msg_result 테이블에서 조회
        from datetime import datetime
        table = f"msg_result_{datetime.now().strftime('%Y%m')}"
        try:
            result = await db.execute(text(f"""
                SELECT mseq, stat, result, dstaddr, report_time
                FROM {table} WHERE mseq = :mseq
            """), {"mseq": mseq})
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
