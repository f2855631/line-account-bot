from fastapi import APIRouter

from src.models import AddTargetRequest, DeleteTargetRequest, RenameTargetRequest
from src.dependencies import get_db

router = APIRouter(prefix="/api")


@router.post("/add-target")
async def api_add_target(req: AddTargetRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        success = db.add_target_member(req.contextId, req.target_name)
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (add-target): {e}")
        return {"success": False}


@router.post("/delete-target")
async def api_delete_target(req: DeleteTargetRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        success = db.delete_target_records(req.contextId, req.target_name)
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (delete-target): {e}")
        return {"success": False}


@router.post("/rename-target")
async def api_rename_target(req: RenameTargetRequest):
    db = get_db()
    if not db:
        return {"success": False}
    try:
        if not req.new_name or not req.new_name.strip():
            return {"success": False, "message": "新名稱不能為空"}
        success = db.rename_target(req.contextId, req.old_name, req.new_name.strip())
        return {"success": success}
    except Exception as e:
        print(f"❌ API Error (rename-target): {e}")
        return {"success": False, "message": str(e)}
