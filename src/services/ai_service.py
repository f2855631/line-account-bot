import os
from google import genai
from google.genai import types
from src.settings.config import GEMINI_API_KEY

# --- 1. 初始化最新的 Google GenAI Client ---
# 在 2026 版 SDK 中，我們直接實例化 Client 物件
client = genai.Client(api_key=GEMINI_API_KEY)

def get_ai_response(user_msg):
    """
    呼叫 Gemini API 取得幽默管家的回覆
    使用 2026 穩定別名 gemini-1.5-flash
    """
    try:
        # 使用 SDK v1.0+ 的標準語法
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"使用者說：{user_msg}",
            config=types.GenerateContentConfig(
                system_instruction="你是一個幽默、貼心的萬能管家，會根據使用者的訊息給予簡短有趣的對話。",
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        # 注意：我們已經在 saved info 設定不要包含 logger info，所以這裡使用 print 進行 Debug
        print(f"⚠️ AI 生成失敗: {e}")
        return "哎呀，管家剛剛去倒茶了，請稍後再跟我聊天吧！"