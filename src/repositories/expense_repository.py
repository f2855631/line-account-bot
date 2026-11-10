import datetime
from datetime import timedelta, timezone
from src.database.sheets_client import sheets_client

class ExpenseRepository:
    def __init__(self):
        # 初始化時，內部持有 Google Sheets 客戶端實例
        self.db = sheets_client

    # ---------------------------------------------------------
    # 1. 輔助工具函式
    # ---------------------------------------------------------
    def _get_taiwan_today(self):
        """取得台灣時區 (UTC+8) 的今天日期"""
        tz = timezone(timedelta(hours=8))
        return datetime.datetime.now(tz).date()

    def _normalize_month(self, month_str):
        """
        確保月份格式為 YYYY-MM (補零並自動補年份)
        支援：'01' -> '2026-01', '2026-3' -> '2026-03'
        """
        if not month_str or not isinstance(month_str, str) or month_str.lower() == "null":
            return None
        
        try:
            # 如果只傳入月份數字 (例如 '01' 或 '1')
            if '-' not in month_str:
                month_val = month_str.zfill(2)
                current_year = self._get_taiwan_today().year
                return f"{current_year}-{month_val}"
            
            # 如果傳入 YYYY-MM (例如 '2026-3')
            parts = month_str.split('-')
            if len(parts) == 2:
                year = parts[0]
                month = parts[1].zfill(2)
                return f"{year}-{month}"
            
            return month_str
        except:
            return month_str

    def _format_rows(self, rows):
        """統一將資料庫 rows 格式化為前端需要的 JSON 格式"""
        if not rows: return []
        return [
            {
                "id": r['id'], 
                "expense_date": r['expense_date'].strftime('%Y-%m-%d') if hasattr(r['expense_date'], 'strftime') else str(r['expense_date']), 
                "target_name": r.get('target_name', '未知'), 
                "item_name": r['item_name'], 
                "amount": float(r['amount']) if r['amount'] is not None else 0.0, 
                "user_name": r['user_name']
            } for r in rows
        ]

    # ---------------------------------------------------------
    # 2. 帳務紀錄 CRUD
    # ---------------------------------------------------------
    def add_expense(self, line_user_id, target_name, amount, item_name="未分類", user_name="系統", expense_date=None):
        """新增帳務紀錄"""
        final_date = expense_date if expense_date else self._get_taiwan_today()
        try:
            self.db.append(line_user_id, target_name, item_name, amount, user_name, final_date)
            return True
        except Exception as e:
            print(f"❌ Sheets 新增失敗: {e}")
            return False

    def update_expense_by_id(self, expense_id, line_user_id, amount, item_name, date):
        """編輯單筆紀錄"""
        try:
            return self.db.update(expense_id, line_user_id, amount, item_name, date)
        except Exception as e:
            print(f"❌ Sheets 更新失敗: {e}")
            return False

    def delete_expense_by_id(self, expense_id, line_user_id):
        """刪除單筆紀錄"""
        try:
            return self.db.delete_where(
                lambda r: r["id"] == expense_id and r["line_user_id"] == line_user_id) > 0
        except Exception as e:
            print(f"❌ Sheets 刪除失敗: {e}")
            return False

    def delete_target_records(self, line_user_id, target_name):
        """刪除整個對象的紀錄 (沒有符合的紀錄時回傳 False)"""
        try:
            return self.db.delete_where(
                lambda r: r["line_user_id"] == line_user_id and r["target_name"] == target_name) > 0
        except Exception as e:
            print(f"❌ Sheets 刪除對象失敗: {e}")
            return False

    def rename_target(self, line_user_id, old_name, new_name):
        """重新命名成員：將所有該成員的紀錄 target_name 更新為新名稱"""
        try:
            return self.db.update_field_where(line_user_id, old_name, new_name)
        except Exception as e:
            print(f"❌ Sheets 改名失敗: {e}")
            return False

    def add_target_member(self, line_user_id, target_name):
        """新增成員 (初始化 0 元紀錄，用於讓該成員出現在清單中)"""
        try:
            return self.add_expense(line_user_id, target_name, 0, "初始化成員", "系統", self._get_taiwan_today())
        except Exception as e:
            print(f"⚠️ Error adding target member: {e}")
            return False

    # ---------------------------------------------------------
    # 3. 查詢與統計 (LIFF 前端 & 機器人共用) — 皆讀取記憶體快取，於 Python 內彙總
    # ---------------------------------------------------------
    def _book(self, line_user_id):
        """某帳本的所有紀錄"""
        return [r for r in self.db.records() if r["line_user_id"] == line_user_id]

    @staticmethod
    def _sorted_desc(rows):
        return sorted(rows, key=lambda r: (r["expense_date"], r["id"]), reverse=True)

    def get_all_records(self, line_user_id):
        """取得該帳本最近 100 筆歷史紀錄"""
        return self._format_rows(self._sorted_desc(self._book(line_user_id))[:100])

    def get_records_by_month(self, line_user_id, month, target_name=None):
        """根據月份篩選紀錄 (含補年份邏輯)"""
        clean_month = self._normalize_month(month)
        if not clean_month:
            return self.get_all_records(line_user_id)

        rows = [r for r in self._book(line_user_id) if r["expense_date"][:7] == clean_month]
        if target_name and target_name.strip():
            rows = [r for r in rows if r["target_name"] == target_name]
        return self._format_rows(self._sorted_desc(rows))

    def get_target_detail(self, line_user_id, target_name, month=None):
        """取得特定對象的詳細紀錄"""
        if month:
            return self.get_records_by_month(line_user_id, month, target_name)
        rows = [r for r in self._book(line_user_id) if r["target_name"] == target_name]
        return self._format_rows(self._sorted_desc(rows))

    def _sums_by_target(self, rows):
        sums = {}
        for r in rows:
            sums[r["target_name"]] = sums.get(r["target_name"], 0) + r["amount"]
        return {k: int(v) for k, v in sums.items()}

    def _current_month_rows(self, line_user_id):
        current_month = self._get_taiwan_today().strftime('%Y-%m')
        return [r for r in self._book(line_user_id) if r["expense_date"][:7] == current_month]

    def get_monthly_sums(self, line_user_id):
        """取得本月各成員統計 (用於 Flex 報表，排除總額 <= 0 的成員)"""
        sums = self._sums_by_target(self._current_month_rows(line_user_id))
        return {k: v for k, v in sums.items() if v > 0}

    def get_monthly_total_all(self, line_user_id):
        """取得整個帳本在本月的消費總額"""
        return int(sum(r["amount"] for r in self._current_month_rows(line_user_id)))

    def get_all_sums(self, line_user_id):
        """取得所有對象的歷史累計金額 (用於「查帳」功能)"""
        return self._sums_by_target(self._book(line_user_id))

    def get_recent_targets(self, line_user_id, limit=50):
        """取得最近有紀錄的人員名單 (用於 LIFF 下拉選單)，依最新紀錄 id 由新到舊"""
        latest = {}
        for r in self._book(line_user_id):
            latest[r["target_name"]] = max(latest.get(r["target_name"], 0), r["id"])
        return sorted(latest, key=latest.get, reverse=True)[:limit]
