"""서버 설정 - 환경변수에서 로드"""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://jojo@localhost:5432/talkpc")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "postgresql://jojo@localhost:5432/talkpc")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production-abc123xyz")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# 세종텔레콤 설정 (서버 전역)
SEJONG_SENDER_KEY = os.getenv("SEJONG_SENDER_KEY", "")
SEJONG_CALLBACK = os.getenv("SEJONG_CALLBACK", "")
SEJONG_TEMPLATE_CODE = os.getenv("SEJONG_TEMPLATE_CODE", "")

# 과금 단가 (원/건)
COST_SMS = int(os.getenv("COST_SMS", "8"))
COST_LMS = int(os.getenv("COST_LMS", "25"))
COST_ALIMTALK = int(os.getenv("COST_ALIMTALK", "7"))

# API 키 - 프로그램에 내장, 이 키 없으면 API 호출 차단
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "tpc-k8x2m9vQfR7wLpN3jY6sT0dA4hE1cU5b")

# Gmail SMTP (기기 인증 이메일 발송)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "pcon1613@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "avgjldspsiykvsnm")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TalkPC")
