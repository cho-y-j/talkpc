"""서버 설정 - 환경변수에서 로드 (시크릿은 반드시 환경변수로 설정)"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()


def _require_env(key: str) -> str:
    """필수 환경변수 - 없으면 서버 시작 실패"""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"필수 환경변수 '{key}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return val


# DB
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://jojo@localhost:5432/talkpc")

# JWT (필수)
JWT_SECRET = _require_env("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# 세종텔레콤 설정 (레거시 - msg_queue 방식)
SEJONG_SENDER_KEY = os.getenv("SEJONG_SENDER_KEY", "")
SEJONG_CALLBACK = os.getenv("SEJONG_CALLBACK", "")
SEJONG_TEMPLATE_CODE = os.getenv("SEJONG_TEMPLATE_CODE", "")

# 와이드샷 HTTP REST API
WIDESHOT_API_URL = os.getenv("WIDESHOT_API_URL", "https://apimsg.wideshot.co.kr")
WIDESHOT_API_KEY = os.getenv("WIDESHOT_API_KEY", "")
WIDESHOT_CALLBACK = os.getenv("WIDESHOT_CALLBACK", "")
WIDESHOT_CHATBOT_ID = os.getenv("WIDESHOT_CHATBOT_ID", "")
SEND_METHOD = os.getenv("SEND_METHOD", "api")

# 과금 단가 (원/건)
COST_SMS = int(os.getenv("COST_SMS", "8"))
COST_LMS = int(os.getenv("COST_LMS", "25"))
COST_ALIMTALK = int(os.getenv("COST_ALIMTALK", "7"))
COST_RCS_SMS = int(os.getenv("COST_RCS_SMS", "12"))
COST_RCS_LMS = int(os.getenv("COST_RCS_LMS", "30"))
COST_RCS_MMS = int(os.getenv("COST_RCS_MMS", "50"))
COST_BRANDTALK = int(os.getenv("COST_BRANDTALK", "15"))

# 브랜드메시지 (카카오 브랜드톡)
BRAND_SENDER_KEY = os.getenv("BRAND_SENDER_KEY", "")
BRAND_UNSUBSCRIBE_PHONE = os.getenv("BRAND_UNSUBSCRIBE_PHONE", "")

# 프로그램 내장 API 키 (필수)
API_SECRET_KEY = _require_env("API_SECRET_KEY")

# Gmail SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TalkPC")

# CORS 허용 도메인
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",") if o.strip()
]
