"""통계 서비스 - 사용량 집계"""
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.send_log import SendLog
from app.models.user import User
from app.models.credit import Credit


async def get_user_daily(user_id: int, db: AsyncSession) -> dict:
    """오늘 사용량"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(
            func.count(SendLog.id).label("count"),
            func.coalesce(func.sum(SendLog.cost), 0).label("cost")
        ).where(SendLog.user_id == user_id, SendLog.created_at >= today)
    )
    row = result.first()
    return {"date": today.strftime("%Y-%m-%d"), "count": row.count, "cost": row.cost}


async def get_user_monthly(user_id: int, db: AsyncSession) -> dict:
    """이번 달 사용량"""
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(
            func.count(SendLog.id).label("count"),
            func.coalesce(func.sum(SendLog.cost), 0).label("cost")
        ).where(SendLog.user_id == user_id, SendLog.created_at >= month_start)
    )
    row = result.first()
    return {"month": month_start.strftime("%Y-%m"), "count": row.count, "cost": row.cost}


async def get_user_stats(user_id: int, db: AsyncSession) -> dict:
    """일별 통계 (최근 30일)"""
    since = datetime.now() - timedelta(days=30)
    result = await db.execute(text("""
        SELECT DATE(created_at) as date, COUNT(*) as count, COALESCE(SUM(cost), 0) as cost
        FROM send_logs
        WHERE user_id = :user_id AND created_at >= :since
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """), {"user_id": user_id, "since": since})
    rows = result.mappings().all()
    return {
        "daily": [{"date": str(r["date"]), "count": r["count"], "cost": r["cost"]} for r in rows]
    }


async def get_admin_stats(db: AsyncSession) -> dict:
    """관리자 전체 통계"""
    # 총 사용자 수
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    active_count = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar()

    # 오늘 발송 건수
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(
            func.count(SendLog.id).label("count"),
            func.coalesce(func.sum(SendLog.cost), 0).label("revenue")
        ).where(SendLog.created_at >= today)
    )
    today_row = today_result.first()

    # 이번 달
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(
            func.count(SendLog.id).label("count"),
            func.coalesce(func.sum(SendLog.cost), 0).label("revenue")
        ).where(SendLog.created_at >= month_start)
    )
    month_row = month_result.first()

    return {
        "total_users": user_count,
        "active_users": active_count,
        "today_sends": today_row.count,
        "today_revenue": today_row.revenue,
        "month_sends": month_row.count,
        "month_revenue": month_row.revenue,
    }
