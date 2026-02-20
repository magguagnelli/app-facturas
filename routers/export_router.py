# routers/export_router.py
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse

from core.auth import require_login, require_admin
from core.audit import audit, build_log
from core.excel_export import export_xlsx

# Importa los services de reportes que quieras exportar
from services.auditoria_service import search_auditoria

router = APIRouter(prefix="/api/export")


def _filename(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.xlsx"


@router.get("/excel")
def export_excel(
    request: Request,
    report: str = Query(..., description="Nombre del reporte, ej: auditoria"),
    # filtros genéricos (algunos aplican, otros no según reporte)
    correo: str | None = Query(default=None),
    accion: str | None = Query(default=None),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    user = require_login(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    report = report.strip().lower()

    # -------- Reporte: auditoria (SOLO ADMIN) --------
    if report == "auditoria":
        admin = require_admin(request)
        if not admin:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)

        result = search_auditoria(
            correo=correo,
            accion=accion,
            q=q,
            date_from=date_from,
            date_to=date_to,
            limit=500,   # exportamos hasta 500 por default (puedes aumentar)
            offset=0,
        )
        rows = result["rows"]

        xlsx = export_xlsx(
            rows,
            sheet_name="Auditoria",
            title="Reporte de Auditoría",
            columns=[
                ("FECHA", "FECHA"),
                ("ROL", "ROL"),
                ("RESPONSABLE", "RESPONSABLE"),
                ("CORREO", "CORREO"),
                ("accion", "ACCION"),
                ("DESCRIPCION", "DESCRIPCION"),
            ],
        )

        audit(
            correo=admin.correo,
            accion="EXPORT_XLSX",
            descripcion="Exportación Excel - Auditoría",
            log_accion=build_log(request, extra=f"rows={len(rows)}"),
        )

        return Response(
            content=xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{_filename("auditoria")}"'
            },
        )

    # --------- agrega aquí más reportes ---------
    return JSONResponse({"detail": f"Reporte no soportado: {report}"}, status_code=400)
