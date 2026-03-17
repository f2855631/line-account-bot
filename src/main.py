import asyncio
import os
import uvicorn
import traceback
from typing import Optional, List
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, QuickReply, 
    QuickReplyButton, MessageAction, TextSendMessage,
    LeaveEvent, PostbackEvent
)

# --- 1. 匯入設定與業務邏輯 ---
from src.settings.config import line_bot_api, handler, LIFF_ID
from src.services.accounting_service import handle_logic, get_db_instance

# 全域資料庫實例
db = None

# 模板路徑設定
templates = Jinja2Templates(directory="src/templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    print("🚀 App starting, connecting to DB...")
    
    # 重試邏輯：確保部署到雲端時 DB 連線不會因為啟動順序而失敗
    retries = 5
    while retries > 0:
        try:
            db = get_db_instance()
            # 簡單測試連線是否真的活著
            db.db.execute_query("SELECT 1", fetch=True)
            print("✅ DB Connected & Ready!")
            break
        except Exception as e:
            retries -= 1
            print(f"❌ DB connection failed. Retries left: {retries}. Error: {e}")
            if retries == 0:
                print("🚨 Could not connect to DB. Application might not work properly.")
            await asyncio.sleep(5)
            
    yield
    print("🛑 App shutting down...")

# 2. 統一定義 app
app = FastAPI(lifespan=lifespan)

# 掛載靜態檔案 (CSS/JS)
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# 跨域設定：只允許 LIFF 前端與 Render 網域調用 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://my-line-accounting-bot.onrender.com",
        "https://liff.line.me",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. API 資料模型 ---

class UpdateRequest(BaseModel):
    id: int
    contextId: str
    amount: float
    item: str = "未分類"
    date: str

class DeleteRequest(BaseModel):
    id: int
    contextId: str

class AddTargetRequest(BaseModel):
    contextId: str
    target_name: str

class DeleteTargetRequest(BaseModel):
    contextId: str
    target_name: str

class AddRecordRequest(BaseModel):
    target_name: str
    amount: float
    item: str = "手機即時記帳"
    contextId: str 
    user_name: str = "使用者"
    date: Optional[str] = None

# --- 3. 輔助邏輯：快速回覆按鈕 ---

def attach_quick_reply(reply_obj):
    """為回覆訊息掛載快速回覆按鈕，增加導流與互動性"""
    if not hasattr(reply_obj, 'quick_reply') or not isinstance(reply_obj, TextSendMessage):
        try:
            items = [
                QuickReplyButton(action=MessageAction(label="📊 查詢總帳", text="查帳")),
                QuickReplyButton(action=MessageAction(label="📜 功能選單", text="選單")),
                QuickReplyButton(action=MessageAction(label="📅 全對象本月", text="查詢全部對象本月總消費")),
                QuickReplyButton(action=MessageAction(label="👤 指定對象本月", text="查詢指定對象本月消費"))
            ]
            reply_obj.quick_reply = QuickReply(items=items)
        except: pass
    return reply_obj

# --- 4. Web 路由與 API 端點 ---

@app.get("/health")
async def health_check():
    return {"status": "ok", "db_ready": db is not None}

@app.get("/", response_class=HTMLResponse)
@app.get("/liff", response_class=HTMLResponse)
async def index_page(request: Request, bookId: Optional[str] = Query(None)):
    """渲染 LIFF 前端頁面"""
    # 注意：這裡的 bookId 會傳遞給 index.html 的模板變數
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "LIFF_ID": LIFF_ID,
        "bookId": bookId
    })

@app.get("/api/get-members")
async def get_members(contextId: str = Query(...)):
    """取得成員清單與本月累積金額"""
    if not db: return {"members": []}
    try:
        member_names = db.get_recent_targets(contextId) 
        stats = db.get_monthly_sums(contextId) or {}

        formatted_members = []
        for name in member_names:
            formatted_members.append({
                "target_name": name,
                "amount": stats.get(name, 0)
            })
            
        return {"members": formatted_members}
    except Exception as e:
        print(f"❌ API Error (get-members): {e}")
        return {"members": [], "error": str(e)}

@app.get("/api/get-history")
async def get_history(
    contextId: str = Query(...), 
    target: Optional[str] = Query(None),
    month: Optional[str] = Query(None)
):
    """取得歷史紀錄"""
    if not db: return {"records": []}
    try:
        # 🧪 強化分流：處理前端傳入的各種空值情況
        def clean(val):
            if not val or str(val).lower() in ["null", "undefined", ""]:
                return None
            return str(val).strip()

        clean_month = clean(month)
        clean_target = clean(target)

        # 分流判斷：
        # 1. 有月份時（無論有無成員），使用 get_records_by_month
        if clean_month:
            records = db.get_records_by_month(contextId, clean_month, target_name=clean_target)
        # 2. 只有成員時，使用 get_target_detail
        elif clean_target:
            records = db.get_target_detail(contextId, clean_target)
        # 3. 預設全體最近紀錄
        else:
            records = db.get_all_records(contextId)

        # 統一過濾掉「初始化成員」的系統紀錄，避免干擾明細
        formatted_records = [
            r for r in (records or []) 
            if r and "初始化成員" not in (r.get("item_name") or "")
        ]

        return {"records": formatted_records}
    except Exception as e:
        print(f"❌ API Error (get-history): {e}")
        return {"records": []}

@app.post("/api/add-target")
async def api_add_target(req: AddTargetRequest):
    if not db: return {"success": False}
    try:
        success = db.add_target_member(req.contextId, req.target_name)
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (add-target): {e}")
        return {"success": False}

@app.post("/api/add")
async def api_add_record(req: AddRecordRequest):
    if not db: return {"success": False}
    try:
        success = db.add_expense(
            line_user_id=req.contextId, 
            target_name=req.target_name,
            amount=req.amount,
            item_name=req.item,
            user_name=req.user_name,
            expense_date=req.date
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (add): {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/update")
async def api_update_record(req: UpdateRequest):
    if not db: return {"success": False}
    try:
        success = db.update_expense_by_id(
            expense_id=req.id,
            line_user_id=req.contextId,
            amount=req.amount,
            item_name=req.item,
            date=req.date
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (update): {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/delete")
async def api_delete_record(req: DeleteRequest):
    if not db: return {"success": False}
    try:
        success = db.delete_expense_by_id(
            expense_id=req.id,
            line_user_id=req.contextId
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (delete): {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/delete-target")
async def api_delete_target(req: DeleteTargetRequest):
    if not db: return {"success": False}
    try:
        success = db.delete_target_records(req.contextId, req.target_name)
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (delete-target): {e}")
        return {"success": False}

# --- 5. LINE 訊息處理 ---

async def process_event_task(reply_token, event_type, payload, user_id, context_id):
    try:
        user_name = "使用者"
        try:
            if context_id.startswith('U') or context_id.startswith('C'):
                profile = line_bot_api.get_group_member_profile(context_id, user_id)
            else:
                profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except: pass

        reply_content = await handle_logic(payload, context_id, user_name)

        if reply_content:
            if isinstance(reply_content, TextSendMessage):
                reply_content = attach_quick_reply(reply_content)
            line_bot_api.reply_message(reply_token, reply_content)

    except Exception:
        print(f"❌ Process Event Error:\n{traceback.format_exc()}")
        try:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="管家剛剛打瞌睡了，請再試一次吧 🍨"))
        except: pass

# --- 6. LINE Webhook ---

@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try: 
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError: 
        raise HTTPException(status_code=400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    context_id = event.source.group_id if event.source.type == 'group' else user_id
    asyncio.create_task(
        process_event_task(event.reply_token, "text", event.message.text.strip(), user_id, context_id)
    )

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    context_id = event.source.group_id if event.source.type == 'group' else user_id
    asyncio.create_task(
        process_event_task(event.reply_token, "postback", event.postback.data, user_id, context_id)
    )

@handler.add(LeaveEvent)
def handle_leave(event):
    if event.source.type == 'group':
        context_id = event.source.group_id
        try:
            db.db.execute_query("DELETE FROM groups_list WHERE line_user_id = %s", (context_id,))
        except Exception: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)