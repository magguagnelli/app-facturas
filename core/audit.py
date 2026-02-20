from fastapi import Request
from core.db import get_conn
from typing import Optional

def build_log(request: Request, extra: str = "") -> str:
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
    ua = request.headers.get("user-agent", "unknown")
    base = f"{request.method} {request.url.path} ip={ip} ua={ua}"
    if extra:
        base = f"{base} {extra}"
    return base[:255]

def audit(
    correo: str,
    accion: str,
    descripcion: str,
    log_accion: str,
    seccion: Optional[str] = None,
    id_sec: Optional[str] = None
) -> None:

    sql = """
        INSERT INTO cat_facturas.auditoria 
        (correo, descripcion, accion, log_accion, seccion, id_sec)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        (correo or "ANONIMO")[:100],
                        (descripcion or "")[:200],
                        (accion or "")[:20],
                        (log_accion or "")[:255],
                        (seccion[:50] if seccion else None),
                        (id_sec[:200] if id_sec else None),
                    ),
                )
            conn.commit()

    except Exception as e:
        print("Error en audit():", str(e))
        raise
