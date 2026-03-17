import urllib.parse
from linebot.models import FlexSendMessage, TextSendMessage
from linebot.models.flex_message import BubbleContainer, CarouselContainer
from src.settings.config import LIFF_ID

# --- 配色設定 ---
COLOR_BG = "#E8E7E3"
COLOR_CARD = "#F5F5F5"
COLOR_MAIN = "#FFBD59"
COLOR_ACCENT = "#88C170"  # 抹茶綠
COLOR_TEXT_BLACK = "#333333"
COLOR_TEXT_LIGHT = "#8E8E8E"
COLOR_WHITE = "#FFFFFF"

def get_safe_liff_url(context_id=None, params=""):
    """ 生成帶有 bookId 的 LIFF URL """
    base_url = f"https://liff.line.me/{LIFF_ID}"
    if context_id:
        connector = "&" if "?" in base_url else "?"
        final_url = f"{base_url}{connector}bookId={context_id}"
        if params: 
            final_url += f"&{params}"
        return final_url
    return base_url

def get_ad_bubble():
    """ 生成廣告卡片 """
    return {
        "type": "bubble", "size": "mega",
        "header": {
            "type": "box", "layout": "vertical", 
            "contents": [{"type": "text", "text": "SPONSORED", "size": "xxs", "color": "#aaaaaa", "weight": "bold"}],
            "paddingBottom": "0px",
            "paddingStart": "20px"
        },
        "hero": {
            "type": "image", "url": "https://img.oeya.com/images/202107/1626774903634400507.png",
            "size": "full", "aspectRatio": "20:13", "aspectMode": "fit",
            "action": {"type": "uri", "uri": "https://greenmall.info/3QAHT"}
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "精選推薦廣告", "weight": "bold", "size": "sm", "color": COLOR_TEXT_BLACK},
                {"type": "text", "text": "點擊上方圖片了解更多優惠資訊", "size": "xxs", "color": COLOR_TEXT_LIGHT, "wrap": True}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "button", "style": "link", "height": "sm", "action": {"type": "uri", "label": "查看更多", "uri": "https://greenmall.info/3QAHT"}}]
        }
    }

def get_menu_flex(context_id=None):
    """ 主選單 """
    liff_url = get_safe_liff_url(context_id=context_id)
    menu_bubble = {
        "type": "bubble", "size": "mega",
        "styles": {"body": {"backgroundColor": COLOR_BG}},
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": COLOR_ACCENT, "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "ACCOUNTING", "weight": "bold", "color": COLOR_WHITE, "size": "sm", "letterSpacing": "2px"},
                {"type": "text", "text": "帳務管家", "weight": "bold", "color": COLOR_WHITE, "size": "xl", "margin": "sm"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "xl", "paddingAll": "25px",
            "contents": [{
                "type": "box", "layout": "vertical", "spacing": "sm",
                "contents": [
                    # 💡 修正：更改為抹茶綠底、白色字體
                    {"type": "button", "style": "primary", "height": "sm", "color": COLOR_ACCENT, "action": {"type": "message", "label": "總帳目", "text": "查帳"}},
                    {"type": "button", "style": "primary", "height": "sm", "color": COLOR_ACCENT, "action": {"type": "message", "label": "指定對象月消費", "text": "查詢指定對象本月消費"}},
                    {"type": "button", "style": "primary", "height": "sm", "color": COLOR_ACCENT, "action": {"type": "message", "label": "全部對象總月消費", "text": "查詢全部對象本月總消費"}}
                ]
            }]
        },
        "footer": {
            "type": "box", "layout": "vertical", "backgroundColor": COLOR_WHITE, "paddingAll": "15px",
            "contents": [{"type": "button", "style": "primary", "color": COLOR_MAIN, "action": {"type": "uri", "label": "開啟管理面板", "uri": liff_url}}]
        }
    }
    carousel = {"type": "carousel", "contents": [menu_bubble, get_ad_bubble()]}
    return FlexSendMessage(alt_text="請查看選單", contents=CarouselContainer.new_from_json_dict(carousel))

# --- [關鍵修正區] 歷史總帳函數 ---
def get_all_debts_flex(debts, context_id=None):
    if not debts: return TextSendMessage(text="尚無任何帳務紀錄")
    
    item_contents = []
    grand_total = 0 
    for name, total in debts.items():
        val = int(total) if total else 0
        grand_total += val
        encoded_name = urllib.parse.quote(str(name))
        liff_url = get_safe_liff_url(context_id=context_id, params=f"target={encoded_name}")
        item_contents.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": name, "size": "sm", "flex": 4, "color": COLOR_TEXT_BLACK, "weight": "bold", "action": {"type": "uri", "uri": liff_url}},
                {"type": "text", "text": f"{val:,}", "size": "sm", "align": "end", "flex": 4, "color": COLOR_TEXT_LIGHT}
            ]
        })

    debt_bubble = {
        "type": "bubble", "size": "mega",
        "styles": {"body": {"backgroundColor": COLOR_CARD}},
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "25px",
            "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": "BALANCE", "weight": "bold", "size": "xl", "color": COLOR_ACCENT, "flex": 1},
                    {"type": "text", "text": "總結算", "align": "end", "color": COLOR_TEXT_LIGHT, "size": "sm", "gravity": "bottom"}
                ]},
                {"type": "separator", "margin": "md", "color": COLOR_ACCENT},
                {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": item_contents},
                {"type": "box", "layout": "vertical", "margin": "xl", "paddingTop": "15px", "borderWidth": "1px", "borderColor": "#CCCCCC", "borderStyle": "dashed", "contents": []},
                {"type": "text", "text": "累積總額", "size": "xs", "color": COLOR_TEXT_LIGHT, "margin": "lg"},
                {"type": "text", "text": f"TWD {grand_total:,}", "size": "xl", "weight": "bold", "color": "#CC6666"}
            ]
        }
    }
    carousel = {"type": "carousel", "contents": [debt_bubble, get_ad_bubble()]}
    return FlexSendMessage(alt_text="結算報表", contents=CarouselContainer.new_from_json_dict(carousel))

def get_monthly_report_flex(monthly_data, total_sum, context_id=None):
    if not monthly_data: return TextSendMessage(text="本月尚無開銷紀錄")
    item_contents = []
    for name, amount in monthly_data.items():
        item_contents.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": str(name), "size": "sm", "color": COLOR_TEXT_BLACK, "flex": 4},
                {"type": "text", "text": f"{int(amount):,}", "size": "sm", "align": "end", "color": COLOR_TEXT_LIGHT, "flex": 4}
            ]
        })
    report_bubble = {
        "type": "bubble", "size": "mega",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": COLOR_ACCENT,
            "contents": [{"type": "text", "text": "本月消費統計", "color": COLOR_WHITE, "weight": "bold"}]
        },
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "box", "layout": "vertical", "contents": item_contents},
                {"type": "separator", "margin": "xl"},
                {"type": "text", "text": f"本月總計: TWD {int(total_sum):,}", "margin": "md", "weight": "bold", "color": "#CC6666"}
            ]
        }
    }
    carousel = {"type": "carousel", "contents": [report_bubble, get_ad_bubble()]}
    return FlexSendMessage(alt_text="月報表已送達", contents=CarouselContainer.new_from_json_dict(carousel))

def get_target_selection_flex(targets, context_id=None):
    buttons = []
    for name in targets:
        postback_data = f"action=query_target_month&target={name}"
        buttons.append({
            "type": "button", "style": "primary", "margin": "sm", "height": "sm", "color": COLOR_ACCENT,
            "action": {"type": "postback", "label": name, "data": postback_data, "displayText": f"查詢 {name} 本月消費"}
        })
    selection_bubble = {
        "type": "bubble", "size": "mega",
        "body": {
            "type": "box", "layout": "vertical", "spacing": "md",
            "contents": [
                {"type": "text", "text": "請選擇要查詢的成員", "weight": "bold", "size": "md"},
                {"type": "box", "layout": "vertical", "contents": buttons}
            ]
        }
    }
    return FlexSendMessage(alt_text="請選擇成員", contents=BubbleContainer.new_from_json_dict(selection_bubble))

def get_debt_report_flex(results, context_id=None):
    """ 記帳成功後的收據卡片 - 樣式與月統計同步 """
    if not results: return TextSendMessage(text="記帳失敗")
    
    main_res = results[0]
    
    item_contents = []
    for res in results:
        diff_val = int(res['diff'])
        signed_diff = f"+{diff_val:,}" if diff_val >= 0 else f"{diff_val:,}"
        display_diff = f"TWD {signed_diff}"
        
        diff_color = "#CC6666" if diff_val >= 0 else "#31A05F"

        item_contents.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": f"項目: {res['item']}", "size": "sm", "color": COLOR_TEXT_BLACK, "flex": 4},
                {"type": "text", "text": display_diff, "size": "sm", "align": "end", "color": diff_color, "weight": "bold", "flex": 4}
            ]
        })
        item_contents.append({"type": "separator", "margin": "md"})
        item_contents.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": "個人累計總額", "size": "xs", "color": COLOR_TEXT_LIGHT, "flex": 4},
                {"type": "text", "text": f"TWD {int(res['total']):,}", "size": "sm", "align": "end", "color": COLOR_ACCENT, "weight": "bold", "flex": 4}
            ]
        })

    report_bubble = {
        "type": "bubble", "size": "mega",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": COLOR_ACCENT, "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "SUCCESS", "weight": "bold", "color": COLOR_WHITE, "size": "sm", "letterSpacing": "2px"},
                {"type": "text", "text": f"記帳成功：{main_res['name']}", "color": COLOR_WHITE, "weight": "bold", "size": "xl", "margin": "sm"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "20px",
            "contents": item_contents
        },
        "footer": {
            "type": "box", "layout": "vertical", "paddingAll": "10px",
            "contents": [
                {"type": "text", "text": "請至管理面板查看完整明細", "size": "xxs", "color": COLOR_TEXT_LIGHT, "align": "center"}
            ]
        }
    }
    
    return FlexSendMessage(
        alt_text=f"記帳成功: {main_res['name']}", 
        contents=BubbleContainer.new_from_json_dict(report_bubble)
    )
