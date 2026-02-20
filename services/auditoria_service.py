# services/auditoria_service.py
from __future__ import annotations
from psycopg.rows import dict_row
from core.db import get_conn
from datetime import datetime, timedelta
 
def search_auditoria(
    correo: str | None = None,
    accion: str | None = None,
    q: str | None = None,
    date_from: str | None = None,   # 'YYYY-MM-DD'
    date_to: str | None = None,     # 'YYYY-MM-DD'
    limit: int = 100,
    offset: int = 0,
) -> dict:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
 
    where = []
    params = []
 
    if correo:
        where.append("lower(a.correo) = lower(%s)")
        params.append(correo.strip())
 
    if accion:
        where.append("accion = %s")
        params.append(accion.strip()[:20])
 
    if q:
        where.append("(descripcion ILIKE %s OR log_accion ILIKE %s)")
        q_value = f"%{q.strip()}%"
        params.append(q_value)
        params.append(q_value)
 
    # rango fechas (incluye todo el día)
    if date_from:
        date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
        where.append("fecha_accion >= %s")
        params.append(date_from_dt)
 
    if date_to:
        date_to_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
        where.append("fecha_accion < %s")
        params.append(date_to_dt)
 
    #acciones = ['ALTA%', 'EDICION%', 'BAJA%']
    #where.append("accion LIKE ANY (%s)")
    #params.append(acciones)
 
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
   
    sql_count = f"SELECT COUNT(*) AS total FROM cat_facturas.auditoria a {where_sql};"
    sql_rows = f"""
        SELECT TO_CHAR(a.fecha_accion,'DD-MM-YYYY HH24:MI:SS')"FECHA", U.rol "ROL", u.nombre "RESPONSABLE" ,u.correo "CORREO",
            a.accion,a.descripcion "DESCRIPCION"
        FROM cat_facturas.auditoria a
            join cat_facturas.usuario u on(a.correo = u.correo)
        {where_sql}
        ORDER BY 1 desc
        LIMIT {limit} OFFSET {offset};
    """
    #print(sql_rows)
    #print(sql_count)
    #print(params)
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql_count,params)
            total = cur.fetchone()["total"]
            cur.execute(sql_rows,params)
            rows = cur.fetchall()
 
    return {"total": total, "rows": rows, "limit": limit, "offset": offset}