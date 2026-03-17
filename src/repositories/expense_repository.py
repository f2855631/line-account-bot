import datetime
from datetime import timedelta, timezone
from src.database.mysql_client import db_client

class ExpenseRepository:
    def __init__(self):
        # 初始化時，內部持有資料庫客戶端實例
        self.db = db_client

    # ---------------------------------------------------------
    # 0. 核心底層介面 (補上給 main.py 使用的轉發接口)
    # ---------------------------------------------------------
    def execute_query(self, sql, params=None, fetch=False):
        """
        轉發接口：讓外部 (如 main.py) 可以直接透過 repository 執行自訂 SQL。
        身為 QA，這能確保資料庫存取的進入點統一。
        """
        return self.db.execute_query(sql, params, fetch)

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
        """新增帳務紀錄 (含自動註冊群組邏輯)"""
        # 確保群組清單中存在此 ID
        reg_sql = "INSERT IGNORE INTO defaultdb.groups_list (line_user_id) VALUES (%s)"
        self.db.execute_query(reg_sql, (line_user_id,))
        
        sql = """
            INSERT INTO defaultdb.expenses (line_user_id, target_name, item_name, amount, user_name, expense_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        final_date = expense_date if expense_date else self._get_taiwan_today()
        return self.db.execute_query(sql, (line_user_id, target_name, item_name, amount, user_name, final_date))

    def update_expense_by_id(self, expense_id, line_user_id, amount, item_name, date):
        """編輯單筆紀錄"""
        sql = """
            UPDATE defaultdb.expenses 
            SET amount = %s, item_name = %s, expense_date = %s 
            WHERE id = %s AND line_user_id = %s
        """
        return self.db.execute_query(sql, (amount, item_name, date, expense_id, line_user_id))

    def delete_expense_by_id(self, expense_id, line_user_id):
        """刪除單筆紀錄"""
        sql = "DELETE FROM defaultdb.expenses WHERE id = %s AND line_user_id = %s"
        return self.db.execute_query(sql, (expense_id, line_user_id))

    def delete_target_records(self, line_user_id, target_name):
        """刪除整個對象的紀錄"""
        sql = "DELETE FROM defaultdb.expenses WHERE line_user_id = %s AND target_name = %s"
        return self.db.execute_query(sql, (line_user_id, target_name))

    def add_target_member(self, line_user_id, target_name):
        """新增成員 (初始化 0 元紀錄，用於讓該成員出現在清單中)"""
        try:
            reg_sql = "INSERT IGNORE INTO defaultdb.groups_list (line_user_id) VALUES (%s)"
            self.db.execute_query(reg_sql, (line_user_id,))
            today = self._get_taiwan_today()
            # 建立一筆 0 元紀錄作為初始化指標
            return self.add_expense(line_user_id, target_name, 0, "初始化成員", "系統", today)
        except Exception as e:
            print(f"⚠️ Error adding target member: {e}")
            return False

    # ---------------------------------------------------------
    # 3. 查詢與統計 (LIFF 前端 & 機器人共用)
    # ---------------------------------------------------------
    def get_all_records(self, line_user_id):
        """取得該帳本最近 100 筆歷史紀錄"""
        sql = """
            SELECT id, expense_date, target_name, item_name, amount, user_name 
            FROM defaultdb.expenses 
            WHERE line_user_id = %s 
            ORDER BY expense_date DESC, id DESC 
            LIMIT 100
        """
        rows = self.db.execute_query(sql, (line_user_id,), fetch=True)
        return self._format_rows(rows)

    def get_records_by_month(self, line_user_id, month, target_name=None):
        """根據月份篩選紀錄 (含補年份邏輯)"""
        clean_month = self._normalize_month(month)
        if not clean_month:
            return self.get_all_records(line_user_id)

        sql = """
            SELECT id, expense_date, target_name, item_name, amount, user_name 
            FROM defaultdb.expenses 
            WHERE line_user_id = %s 
              AND LEFT(expense_date, 7) = %s
        """
        params = [line_user_id, clean_month]

        if target_name and target_name.strip():
            sql += " AND target_name = %s "
            params.append(target_name)

        sql += " ORDER BY expense_date DESC, id DESC"
        rows = self.db.execute_query(sql, tuple(params), fetch=True)
        return self._format_rows(rows)

    def get_target_detail(self, line_user_id, target_name, month=None):
        """取得特定對象的詳細紀錄"""
        if month:
            return self.get_records_by_month(line_user_id, month, target_name)
            
        sql = """
            SELECT id, expense_date, target_name, item_name, amount, user_name 
            FROM defaultdb.expenses 
            WHERE line_user_id = %s AND target_name = %s
            ORDER BY expense_date DESC, id DESC
        """
        rows = self.db.execute_query(sql, (line_user_id, target_name), fetch=True)
        return self._format_rows(rows)

    def get_monthly_sums(self, line_user_id):
        """取得本月各成員統計 (用於 Flex 報表，排除 0 元紀錄)"""
        today = self._get_taiwan_today()
        current_month = today.strftime('%Y-%m')
        
        sql = """
            SELECT target_name, SUM(amount) AS total
            FROM defaultdb.expenses 
            WHERE line_user_id = %s 
            AND LEFT(expense_date, 7) = %s
            GROUP BY target_name
            HAVING total > 0
        """
        rows = self.db.execute_query(sql, (line_user_id, current_month), fetch=True)
        if not rows: return {}
        return {row['target_name']: int(row['total'] or 0) for row in rows}
    
    def get_monthly_total_all(self, line_user_id):
        """取得整個帳本在本月的消費總額"""
        today = self._get_taiwan_today()
        current_month = today.strftime('%Y-%m')
        
        sql = """
            SELECT SUM(amount) AS grand_total
            FROM defaultdb.expenses 
            WHERE line_user_id = %s 
              AND LEFT(expense_date, 7) = %s
        """
        result = self.db.execute_query(sql, (line_user_id, current_month), fetch=True)
        
        if result and result[0]['grand_total']:
            return int(result[0]['grand_total'])
        return 0

    def get_all_sums(self, line_user_id):
        """取得所有對象的歷史累計金額 (用於「查帳」功能)"""
        sql = """
            SELECT target_name, SUM(amount) AS total 
            FROM defaultdb.expenses 
            WHERE line_user_id = %s 
            GROUP BY target_name
        """
        rows = self.db.execute_query(sql, (line_user_id,), fetch=True)
        if not rows: return {}
        return {row['target_name']: int(row['total'] or 0) for row in rows}

    def get_recent_targets(self, line_user_id, limit=50):
        """取得最近有紀錄的人員名單 (用於 LIFF 下拉選單)"""
        sql = """
            SELECT target_name FROM defaultdb.expenses 
            WHERE line_user_id = %s 
            GROUP BY target_name 
            ORDER BY MAX(id) DESC 
            LIMIT %s
        """
        rows = self.db.execute_query(sql, (line_user_id, limit), fetch=True)
        return [row['target_name'] for row in rows] if rows else []