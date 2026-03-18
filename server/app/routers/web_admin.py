"""관리자 웹 페이지 라우터 (Jinja2 HTML)"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import API_SECRET_KEY
import os

router = APIRouter(prefix="/web/admin", tags=["관리자웹"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


def _ctx(request: Request) -> dict:
    """템플릿 공통 컨텍스트 (API 키를 서버사이드 주입)"""
    return {"request": request, "api_key": API_SECRET_KEY}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", _ctx(request))


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", _ctx(request))


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return templates.TemplateResponse("admin/users.html", _ctx(request))


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail_page(request: Request, user_id: int):
    return templates.TemplateResponse("admin/user_detail.html", _ctx(request))


@router.get("/send-logs", response_class=HTMLResponse)
async def send_logs_page(request: Request):
    return templates.TemplateResponse("admin/send_logs.html", _ctx(request))


@router.get("/security-logs", response_class=HTMLResponse)
async def security_logs_page(request: Request):
    return templates.TemplateResponse("admin/security_logs.html", _ctx(request))


@router.get("/charge-requests", response_class=HTMLResponse)
async def charge_requests_page(request: Request):
    return templates.TemplateResponse("admin/charge_requests.html", _ctx(request))


@router.get("/credits", response_class=HTMLResponse)
async def credits_page(request: Request):
    return templates.TemplateResponse("admin/credits.html", _ctx(request))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("admin/settings.html", _ctx(request))
