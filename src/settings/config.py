import os
from linebot import LineBotApi, WebhookHandler

# --- 1. 環境變數 ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LIFF_ID = os.environ.get('LIFF_ID')
# LINE_CHANNEL_ACCESS_TOKEN = "dummy_token"
# LINE_CHANNEL_SECRET = "dummy_secret"
# LIFF_ID = "dummy_liff_id"
# GEMINI_API_KEY = "dummy_gemini_key"

# 這樣這行就不會報錯了
# line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
# handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 2. LINE Bot 實例化 ---
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 3. 動態路徑處理 (憑證位置優化) ---
# 取得 config.py 所在的資料夾路徑
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 優先尋找同級目錄下的 ca.pem (既然你已經放過來了)
CA_CERT_PATH = os.path.join(CURRENT_DIR, "ca.pem")

# 如果同級目錄沒找到，再嘗試你原本設定的備用路徑
if not os.path.exists(CA_CERT_PATH):
    # 原本邏輯：向上跳兩層進入 src/certs/ca.pem
    PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
    ALT_PATH = os.path.join(PROJECT_ROOT, "src", "certs", "ca.pem")
    if os.path.exists(ALT_PATH):
        CA_CERT_PATH = ALT_PATH

# QA 偵錯輸出：確保你知道程式到底抓到哪裡的檔案
if os.path.exists(CA_CERT_PATH):
    print(f"✅ [Database] SSL Certificate found at: {CA_CERT_PATH}")
else:
    print(f"⚠️ [Database] SSL Certificate NOT FOUND. Please check: {CA_CERT_PATH}")

# --- 4. Aiven MySQL 配置 ---
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'), 
    'database': os.environ.get('DB_NAME', 'defaultdb'),
    # 當憑證存在時才載入 ssl 配置，否則設為 None 避免 Crash
    'ssl': {'ca': CA_CERT_PATH} if os.path.exists(CA_CERT_PATH) else None, 
    'connect_timeout': 10,
    'autocommit': True,
    'charset': 'utf8mb4'
}