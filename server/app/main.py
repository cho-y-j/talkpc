"""TalkPC SaaS API 서버"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import user, credit, contact, template, send_log, device
from app.routers import auth, account, contacts, templates, send, usage, admin, web_admin

app = FastAPI(title="TalkPC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
