"""TalkPC SaaS API 서버"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine
from app.models import user, credit, contact, template, send_log, device
from app.routers import auth, account, contacts, templates, send, usage, admin, web_admin
from app.config import API_SECRET_KEY

app = FastAPI(title="TalkPC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    """API 키 검증 - /api 경로만 체크, /web과 /docs 등은 패스"""
    path = request.url.path

    # API 경로만 키 검증 (/web, /docs, /health, / 는 제외)
    if path.startswith("/api"):
        api_key = request.headers.get("X-API-Key", "")
        if api_key != API_SECRET_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "유효하지 않은 API 키입니다"}
            )

    return await call_next(request)


# API 라우터 (/api prefix)
app.include_router(auth.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(send.router, prefix="/api")
app.include_router(usage.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# 웹 관리자 페이지
app.include_router(web_admin.router)


@app.get("/")
async def root():
    return {"service": "TalkPC API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
