"""관리자 웹 페이지 라우터 (Jinja2 HTML)"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter(prefix="/web/admin", tags=["관리자웹"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request})


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail_page(request: Request, user_id: int):
    return templates.TemplateResponse("admin/user_detail.html", {"request": request})


@router.get("/send-logs", response_class=HTMLResponse)
async def send_logs_page(request: Request):
    return templates.TemplateResponse("admin/send_logs.html", {"request": request})


@router.get("/security-logs", response_class=HTMLResponse)
async def security_logs_page(request: Request):
    return templates.TemplateResponse("admin/security_logs.html", {"request": request})
