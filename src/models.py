from typing import Optional
from pydantic import BaseModel


class UpdateRequest(BaseModel):
    id: int
    contextId: str
    amount: float
    item: str = "未分類"
    date: str


class DeleteRequest(BaseModel):
    id: int
    contextId: str


class AddTargetRequest(BaseModel):
    contextId: str
    target_name: str


class DeleteTargetRequest(BaseModel):
    contextId: str
    target_name: str


class RenameTargetRequest(BaseModel):
    contextId: str
    old_name: str
    new_name: str


class AddRecordRequest(BaseModel):
    target_name: str
    amount: float
    item: str = "手機即時記帳"
    contextId: str
    user_name: str = "使用者"
    date: Optional[str] = None
