# routers/catalogos_api_router.py
import os
import traceback
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse

from core.auth import require_login
from core.audit import audit, build_log
from services.catalogos_service import process_catalogos_excel

router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])

def require_admin(request: Request):
    user = require_login(request)
    if not user or user.rol != "ADMIN":
        return None
    return user

@router.post("/upload")
async def upload_catalogos(request: Request, file: UploadFile = File(...)):
    user = require_admin(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        return JSONResponse({"detail": "Solo se permiten archivos Excel (.xlsx/.xls)."}, status_code=400)

    content = await file.read()

    try:
        result = process_catalogos_excel(
            excel_bytes=content,
            filename=file.filename or "catalogos.xlsx",
            actor_email=user.correo,
            request_log=build_log(request)
        )

        audit(
            user.correo,
            "BULK_UPLOAD_CATALOGOS",
            f"Carga masiva de catálogos: {file.filename}",
            build_log(request, extra=f"ok={result.get('ok')} total={result.get('total_sheets')}")
        )

        return JSONResponse(result, status_code=200)

    except Exception as e:
        tb = traceback.format_exc()
        debug = os.getenv("DEBUG", "0") == "1"

        payload = {
            "ok": False,
            "message": "Error inesperado procesando Excel.",
            "error": str(e),
        }
        if debug:
            payload["traceback"] = tb

        return JSONResponse(payload, status_code=500)
