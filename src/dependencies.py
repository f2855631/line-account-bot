from src.repositories.expense_repository import ExpenseRepository

# 全域唯一的資料庫實例，供所有 router 共用
_db: ExpenseRepository = ExpenseRepository()


def get_db() -> ExpenseRepository:
    return _db
