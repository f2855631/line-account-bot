from typing import Optional
from fastapi import APIRouter, Query

from src.models import AddRecordRequest, UpdateRequest, DeleteRequest
from src.dependencies import get_db

router = APIRouter(prefix="/api")


@router.get("/get-members")
async def get_members(contextId: str = Query(...)):
    """取得成員清單與本月累積金額"""
    db = get_db()
    if not db:
        return {"members": []}
    try:
        member_names = db.get_recent_targets(contextId)
        stats = db.get_monthly_sums(contextId) or {}
        return {
            "members": [
                {"target_name": name, "amount": stats.get(name, 0)}
                for name in member_names
            ]
        }
    except Exception as e:
        print(f"❌ API Error (get-members): {e}")
        return {"members": [], "error": str(e)}


@router.get("/get-history")
async def get_history(
    contextId: str = Query(...),
    target: Optional[str] = Query(None),
    month: Optional[str] = Query(None)
):
    """取得歷史紀錄"""
    db = get_db()
    if not db:
        return {"records": []}
    try:
        def clean(val):
            if not val or str(val).lower() in ["null", "undefined", ""]:
                return None
            return str(val).strip()

        clean_month = clean(month)
        clean_target = clean(target)

        if clean_month:
            records = db.get_records_by_month(contextId, clean_month, target_name=clean_target)
        elif clean_target:
            records = db.get_target_detail(contextId, clean_target)
        else:
            records = db.get_all_records(contextId)

        formatted_records = [
            r for r in (records or [])
            if r and "初始化成員" not in (r.get("item_name") or "")
        ]
        return {"records": formatted_records}
    except Exception as e:
        print(f"❌ API Error (get-history): {e}")
        return {"records": []}


@router.post("/add")
async def api_add_record(req: AddRecordRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        success = db.add_expense(
            line_user_id=req.contextId,
            target_name=req.target_name,
            amount=req.amount,
            item_name=req.item,
            user_name=req.user_name,
            expense_date=req.date
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (add): {e}")
        return {"success": False, "message": str(e)}


@router.post("/update")
async def api_update_record(req: UpdateRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        success = db.update_expense_by_id(
            expense_id=req.id,
            line_user_id=req.contextId,
            amount=req.amount,
            item_name=req.item,
            date=req.date
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (update): {e}")
        return {"success": False, "message": str(e)}


@router.post("/delete")
async def api_delete_record(req: DeleteRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        success = db.delete_expense_by_id(
            expense_id=req.id,
            line_user_id=req.contextId
        )
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (delete): {e}")
        return {"success": False, "message": str(e)}
