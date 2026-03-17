# src/database/mysql_client.py
from src.settings.config import DB_CONFIG
import pymysql
import time
import datetime

class MySQLClient:
    def __init__(self):
        self.conn = self.init_db()

    def init_db(self):
        """初始化連線並執行基礎 Table Migration (含自動補欄位與外鍵修復)"""
        for i in range(3):
            try:
                conn = pymysql.connect(
                    **DB_CONFIG, 
                    cursorclass=pymysql.cursors.DictCursor  # 保持字典格式
                )
                with conn.cursor() as cursor:
                    # 1. 建立名冊表 (群組或個人)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS defaultdb.groups_list (
                            line_user_id VARCHAR(100) PRIMARY KEY,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """)

                    # 2. 建立帳目表
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS defaultdb.expenses (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            line_user_id VARCHAR(100),
                            target_name VARCHAR(50), 
                            amount INT NOT NULL,
                            expense_date DATE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """)
                    
                    # 3. 自動檢查並補齊缺失欄位
                    cursor.execute("SHOW COLUMNS FROM defaultdb.expenses")
                    raw_rows = cursor.fetchall()
                    
                    # ✅ 關鍵修正：針對 DictCursor，改用 col['Field'] 取得欄位名稱
                    columns = [col['Field'] for col in raw_rows]
                    
                    if 'item_name' not in columns:
                        print("➕ [Migration] 補齊 item_name 欄位")
                        cursor.execute("ALTER TABLE defaultdb.expenses ADD COLUMN item_name VARCHAR(255) DEFAULT '未分類' AFTER target_name")
                    
                    if 'user_name' not in columns:
                        print("➕ [Migration] 補齊 user_name 欄位")
                        cursor.execute("ALTER TABLE defaultdb.expenses ADD COLUMN user_name VARCHAR(50) DEFAULT '系統' AFTER amount")

                    # 4. 處理外鍵約束
                    cursor.execute("""
                        SELECT CONSTRAINT_NAME 
                        FROM information_schema.KEY_COLUMN_USAGE 
                        WHERE TABLE_SCHEMA = 'defaultdb' 
                          AND TABLE_NAME = 'expenses' 
                          AND CONSTRAINT_NAME = 'fk_line_group_new';
                    """)
                    
                    if not cursor.fetchone():
                        print("🔗 正在建立資料庫外鍵約束 (ON DELETE CASCADE)...")
                        try:
                            cursor.execute("""
                                ALTER TABLE defaultdb.expenses 
                                ADD CONSTRAINT fk_line_group_new 
                                FOREIGN KEY (line_user_id) 
                                REFERENCES defaultdb.groups_list(line_user_id) 
                                ON DELETE CASCADE;
                            """)
                        except Exception as fk_e:
                            print(f"⚠️ 外鍵建立失敗: {fk_e}")

                conn.commit()
                print("✅ [Database] defaultdb 初始化與 Migration 完成")
                return conn
            except Exception as e:
                # 這裡印出完整的 e，方便你在 Render Log 看到具體錯誤
                print(f"❌ 資料庫初始化失敗，第 {i+1} 次重試... Error: {str(e)}")
                time.sleep(2)  # 縮短等待時間，避免觸發 Gunicorn Timeout
        return None

    def _ensure_connection(self):
        """確保連線依然活著，若斷開則重連"""
        try:
            if not self.conn:
                self.conn = self.init_db()
            else:
                self.conn.ping(reconnect=True)
        except Exception:
            print("🔄 資料庫連線中斷，嘗試重新連線...")
            self.conn = self.init_db()

    def execute_query(self, sql, params=(), fetch=False):
        self._ensure_connection()
        if not self.conn:
            print("🚫 無法執行 SQL：資料庫連線未就緒")
            return None if fetch else False
            
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                if fetch:
                    return cursor.fetchall()
                self.conn.commit()
                return True
        except Exception as e:
            if self.conn:
                try: self.conn.rollback()
                except: pass
            print(f"❌ SQL 執行錯誤: {e}")
            return None if fetch else False

db_client = MySQLClient()