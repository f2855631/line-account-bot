import datetime
from linebot.models import TextSendMessage

from src.dependencies import get_db
from src.services.ai_service import get_ai_response
from src.services.parser_service import parse_accounting_content
from src import flex_templates as flex


async def handle_logic(user_msg, context_id, user_name):
    """
    核心業務邏輯：處理 LINE 訊息、Postback 指令及自動記帳解析
    """
    db = get_db()
    clean_msg = user_msg.strip()

    # --- 0. 處理 Postback 點擊邏輯 (例如來自 Flex 卡片按鈕) ---
    if "action=" in clean_msg:
        try:
            params = dict(item.split("=") for item in clean_msg.split("&"))
            action = params.get("action")

            if action == "query_target_month":
                target_name = params.get("target")
                if target_name:
                    monthly_data = db.get_monthly_sums(context_id)
                    monthly_val = monthly_data.get(target_name, 0)
                    return flex.get_monthly_report_flex(
                        {target_name: monthly_val},
                        monthly_val,
                        context_id=context_id
                    )
        except Exception as e:
            print(f"⚠️ Postback Error: {e}")
            return TextSendMessage(text="指令解析失敗，請稍後再試")

    # --- A. 選單與功能切換 ---
    if clean_msg in ["選單", "menu", "功能"]:
        return flex.get_menu_flex(context_id=context_id)

    if clean_msg == "查帳":
        debt_data = db.get_all_sums(context_id)
        if debt_data:
            return flex.get_all_debts_flex(debt_data, context_id=context_id)
        return TextSendMessage(text="目前尚無帳務紀錄")

    # --- B. 彈出成員選擇清單 ---
    if clean_msg == "查詢指定對象本月消費":
        targets = db.get_recent_targets(context_id)
        if not targets:
            return TextSendMessage(text="目前名單為空，請先輸入指令記帳（例如：小明 100 午餐）")
        return flex.get_target_selection_flex(targets, context_id=context_id)

    # --- C. 全體月報表 ---
    if clean_msg == "查詢全部對象本月總消費":
        monthly_data = db.get_monthly_sums(context_id)
        total_sum = db.get_monthly_total_all(context_id)
        if not monthly_data:
            return TextSendMessage(text="本月尚無開銷紀錄")
        return flex.get_monthly_report_flex(monthly_data, total_sum, context_id=context_id)

    # --- D. 解析記帳 (正規表達式或空白分割處理) ---
    parsed_results = parse_accounting_content(clean_msg)

    if not parsed_results:
        parts = clean_msg.split()
        if len(parts) >= 2:
            try:
                amount_val = float(parts[1].replace(',', ''))
                parsed_results = [{
                    'name': parts[0],
                    'amount': amount_val,
                    'item': parts[2] if len(parts) > 2 else "一般消費",
                    'date': datetime.datetime.now().strftime('%Y-%m-%d')
                }]
            except ValueError:
                pass

    if parsed_results:
        debt_results = []
        all_current_sums = db.get_all_sums(context_id)

        for res in parsed_results:
            target = res.get('name')
            amount = res.get('amount')
            item = res.get('item') or "一般消費"
            record_date = res.get('date')

            if db.add_expense(context_id, target, amount, item, user_name, expense_date=record_date):
                current_sum = all_current_sums.get(target, 0)
                debt_results.append({
                    "name": target,
                    "total": current_sum + amount,
                    "diff": f"{amount:+}",
                    "item": item
                })

        if debt_results:
            return flex.get_debt_report_flex(debt_results, context_id=context_id)

    # --- E. 指令式刪除 ---
    if clean_msg.startswith("刪除"):
        target_to_del = clean_msg.replace("刪除", "").strip()
        if target_to_del:
            if db.delete_target_records(context_id, target_to_del):
                return TextSendMessage(text=f"已成功刪除 {target_to_del} 的所有相關紀錄")
            return TextSendMessage(text=f"找不到成員或該成員無紀錄: {target_to_del}")

    # --- F. AI 萬用閒聊 ---
    ai_msg = get_ai_response(user_msg)
    return TextSendMessage(text=ai_msg)
