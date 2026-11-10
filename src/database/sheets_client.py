# src/database/sheets_client.py
"""
Google Sheets 資料層：以一個分頁當作資料表，並在記憶體中保留快取。

- 讀取：走快取 (超過 TTL 才重新讀整張表)，避免 LINE 回覆被 API 延遲拖慢。
- 寫入：先強制同步最新資料，再寫入 Sheet，並同步更新快取。
"""
import datetime
import json
import re
import threading
import time

import gspread
from google.oauth2.service_account import Credentials

from src.settings.config import (
    GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SERVICE_ACCOUNT_FILE,
    SHEET_WORKSHEET, SHEET_CACHE_TTL, DEFAULT_LINE_ID,
)

HEADERS = [
    "id", "line_user_id", "expense_date", "target_name",
    "item_name", "amount", "user_name", "created_at",
]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _norm_date(value):
    """把 Sheet 可能出現的日期格式 (2026-1-5 / 2026/01/05 / date 物件) 統一成 YYYY-MM-DD"""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s


def _to_float(value):
    try:
        return float(str(value).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def _num(x):
    """整數金額寫成 int，其餘維持 float，Sheet 內看起來才乾淨"""
    x = float(x)
    return int(x) if x == int(x) else x


class SheetsClient:
    def __init__(self):
        self._lock = threading.RLock()
        self._ws = None
        self._rows = []          # list[dict]，順序與 Sheet 第 2 列起一致
        self._loaded_at = 0.0

    # ------------------------------------------------------------------
    # 連線
    # ------------------------------------------------------------------
    def _connect(self):
        if self._ws is not None:
            return self._ws
        if not GOOGLE_SHEET_ID:
            raise RuntimeError("未設定 GOOGLE_SHEET_ID")
        if GOOGLE_SERVICE_ACCOUNT_JSON:
            creds = Credentials.from_service_account_info(
                json.loads(GOOGLE_SERVICE_ACCOUNT_JSON), scopes=SCOPES)
        elif GOOGLE_SERVICE_ACCOUNT_FILE:
            creds = Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        else:
            raise RuntimeError("未設定 GOOGLE_SERVICE_ACCOUNT_JSON 或 GOOGLE_SERVICE_ACCOUNT_FILE")

        sh = gspread.authorize(creds).open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(SHEET_WORKSHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_WORKSHEET, rows=1000, cols=len(HEADERS))
        if ws.row_values(1) != HEADERS:
            ws.update(range_name="A1:H1", values=[HEADERS])
        self._ws = ws
        print(f"✅ [Sheets] 已連線分頁 '{SHEET_WORKSHEET}'")
        return ws

    # ------------------------------------------------------------------
    # 讀取 / 快取
    # ------------------------------------------------------------------
    def load(self, force=False):
        """回傳全部資料列 (dict list)。快取未過期時不打 API。"""
        with self._lock:
            if not force and self._loaded_at and time.time() - self._loaded_at < SHEET_CACHE_TTL:
                return self._rows
            try:
                ws = self._connect()
                values = ws.get_all_values()
            except Exception as e:
                self._ws = None  # 下次重新連線
                if self._loaded_at:  # 有舊快取就先沿用，避免 Sheets 暫時故障時整個 bot 掛掉
                    print(f"⚠️ [Sheets] 讀取失敗，沿用舊快取: {e}")
                    return self._rows
                raise
            self._rows = self._parse(values[1:])
            self._loaded_at = time.time()
            return self._rows

    def _parse(self, body):
        rows, next_id = [], 0
        for raw in body:
            raw = list(raw) + [""] * (len(HEADERS) - len(raw))
            rec = dict(zip(HEADERS, raw[:len(HEADERS)]))
            if not str(rec["target_name"]).strip() and not str(rec["amount"]).strip():
                rows.append(None)  # 空白列：保留位置以維持列號對應
                continue
            try:
                rec["id"] = int(float(rec["id"]))
                next_id = max(next_id, rec["id"])
            except (ValueError, TypeError):
                rec["id"] = None
            rec["line_user_id"] = rec["line_user_id"].strip() or DEFAULT_LINE_ID
            rec["expense_date"] = _norm_date(rec["expense_date"])
            rec["amount"] = _to_float(rec["amount"])
            rec["item_name"] = rec["item_name"] or "未分類"
            rec["user_name"] = rec["user_name"] or "系統"
            rows.append(rec)

        # 手動輸入、沒填 id 的列：補號並寫回 Sheet
        fill = []
        for idx, rec in enumerate(rows):
            if rec is not None and rec["id"] is None:
                next_id += 1
                rec["id"] = next_id
                fill.append((idx + 2, next_id))
        if fill and self._ws is not None:
            try:
                data = [{"range": f"A{r}", "values": [[i]]} for r, i in fill]
                self._ws.batch_update(data, value_input_option="RAW")
            except Exception as e:
                print(f"⚠️ [Sheets] 補 id 寫回失敗: {e}")
        return rows

    def records(self):
        """有效資料列 (排除空白列)"""
        return [r for r in self.load() if r is not None]

    # ------------------------------------------------------------------
    # 寫入
    # ------------------------------------------------------------------
    def append(self, line_user_id, target_name, item_name, amount, user_name, expense_date):
        with self._lock:
            self.load(force=True)
            new_id = max([r["id"] for r in self._rows if r] or [0]) + 1
            date_s = _norm_date(expense_date)
            created = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
            amt = _num(amount)
            self._ws.append_row(
                [new_id, line_user_id, date_s, target_name, item_name, amt, user_name, created],
                value_input_option="RAW", table_range="A1")
            self._rows.append({
                "id": new_id, "line_user_id": line_user_id, "expense_date": date_s,
                "target_name": target_name, "item_name": item_name,
                "amount": float(amt), "user_name": user_name, "created_at": created,
            })
            return new_id

    def update(self, expense_id, line_user_id, amount, item_name, expense_date):
        with self._lock:
            self.load(force=True)
            for idx, rec in enumerate(self._rows):
                if rec and rec["id"] == expense_id and rec["line_user_id"] == line_user_id:
                    date_s = _norm_date(expense_date)
                    amt = _num(amount)
                    row = idx + 2
                    self._ws.batch_update([
                        {"range": f"C{row}", "values": [[date_s]]},
                        {"range": f"E{row}:F{row}", "values": [[item_name, amt]]},
                    ], value_input_option="RAW")
                    rec.update(expense_date=date_s, item_name=item_name, amount=float(amt))
                    return True
            return False

    def update_field_where(self, line_user_id, old_target, new_target):
        """批次改名：回傳是否成功 (沒有符合的列也視為成功)"""
        with self._lock:
            self.load(force=True)
            data = []
            for idx, rec in enumerate(self._rows):
                if rec and rec["line_user_id"] == line_user_id and rec["target_name"] == old_target:
                    data.append({"range": f"D{idx + 2}", "values": [[new_target]]})
                    rec["target_name"] = new_target
            if data:
                self._ws.batch_update(data, value_input_option="RAW")
            return True

    def delete_where(self, predicate):
        """刪除所有符合條件的列 (單次 batch 請求)，回傳刪除筆數"""
        with self._lock:
            self.load(force=True)
            targets = [idx for idx, rec in enumerate(self._rows) if rec and predicate(rec)]
            if not targets:
                return 0
            sheet_id = self._ws.id
            requests = [{
                "deleteDimension": {"range": {
                    "sheetId": sheet_id, "dimension": "ROWS",
                    "startIndex": idx + 1, "endIndex": idx + 2,  # 0-based，+1 跳過標題列
                }}
            } for idx in sorted(targets, reverse=True)]  # 由下往上刪，列號才不會位移
            self._ws.spreadsheet.batch_update({"requests": requests})
            for idx in sorted(targets, reverse=True):
                del self._rows[idx]
            return len(targets)


sheets_client = SheetsClient()
