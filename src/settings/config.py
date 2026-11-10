import os
from linebot import LineBotApi, WebhookHandler

# --- 1. 環境變數 ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LIFF_ID = os.environ.get('LIFF_ID')

# --- 2. LINE Bot 實例化 ---
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 3. Google Sheets 配置 ---
# 試算表 ID：網址 /spreadsheets/d/<這一段>/edit
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
# Service Account 金鑰：整份 JSON 內容貼成一個環境變數
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
# 本機開發可改用金鑰檔路徑 (與上面擇一)
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
# 分頁名稱
SHEET_WORKSHEET = os.environ.get('SHEET_WORKSHEET', 'expenses')
# 快取存活秒數：在 Sheet 手動修改後，最多這麼久會同步進 bot
SHEET_CACHE_TTL = int(os.environ.get('SHEET_CACHE_TTL', 60))
# 選填：在 Sheet 手動輸入、line_user_id 留空的列，會歸屬到這個帳本 ID
DEFAULT_LINE_ID = os.environ.get('DEFAULT_LINE_ID', '')
