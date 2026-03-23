from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.settings.config import LIFF_ID
from src.dependencies import get_db

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/health")
async def health_check():
    db = get_db()
    return {"status": "ok", "db_ready": db is not None}


@router.get("/", response_class=HTMLResponse)
@router.get("/liff", response_class=HTMLResponse)
async def index_page(request: Request, bookId: Optional[str] = Query(None)):
    """渲染 LIFF 前端頁面"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "LIFF_ID": LIFF_ID,
        "bookId": bookId
    })
