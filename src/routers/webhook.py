import asyncio
import traceback
from fastapi import APIRouter, Request, Header, HTTPException
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, QuickReply,
    QuickReplyButton, MessageAction, TextSendMessage,
    LeaveEvent, PostbackEvent
)

from src.settings.config import line_bot_api, handler
from src.services.accounting_service import handle_logic
from src.dependencies import get_db

router = APIRouter()


def attach_quick_reply(reply_obj):
    """為回覆訊息掛載快速回覆按鈕"""
    if not hasattr(reply_obj, 'quick_reply') or not isinstance(reply_obj, TextSendMessage):
        try:
            items = [
                QuickReplyButton(action=MessageAction(label="📊 查詢總帳", text="查帳")),
                QuickReplyButton(action=MessageAction(label="📜 功能選單", text="選單")),
                QuickReplyButton(action=MessageAction(label="📅 全對象本月", text="查詢全部對象本月總消費")),
                QuickReplyButton(action=MessageAction(label="👤 指定對象本月", text="查詢指定對象本月消費"))
            ]
            reply_obj.quick_reply = QuickReply(items=items)
        except:
            pass
    return reply_obj


async def process_event_task(reply_token, event_type, payload, user_id, context_id):
    try:
        user_name = "使用者"
        try:
            if context_id.startswith('U') or context_id.startswith('C'):
                profile = line_bot_api.get_group_member_profile(context_id, user_id)
            else:
                profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except:
            pass

        reply_content = await handle_logic(payload, context_id, user_name)

        if reply_content:
            if isinstance(reply_content, TextSendMessage):
                reply_content = attach_quick_reply(reply_content)
            line_bot_api.reply_message(reply_token, reply_content)

    except Exception:
        print(f"❌ Process Event Error:\n{traceback.format_exc()}")
        try:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="管家剛剛打瞌睡了，請再試一次吧 🍨"))
        except:
            pass


def _create_task_safe(coro):
    """安全地在現有事件迴圈中建立 Task"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


@router.post("/callback")
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
    _create_task_safe(
        process_event_task(event.reply_token, "text", event.message.text.strip(), user_id, context_id)
    )


@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    context_id = event.source.group_id if event.source.type == 'group' else user_id
    _create_task_safe(
        process_event_task(event.reply_token, "postback", event.postback.data, user_id, context_id)
    )


@handler.add(LeaveEvent)
def handle_leave(event):
    if event.source.type == 'group':
        context_id = event.source.group_id
        try:
            db = get_db()
            db.db.execute_query(
                "DELETE FROM groups_list WHERE line_user_id = %s", (context_id,)
            )
        except Exception:
            pass
