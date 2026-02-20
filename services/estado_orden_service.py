# services/estado_orden_service.py
from __future__ import annotations
from psycopg.rows import dict_row
from core.db import get_conn

def validate_estado_orden(data: dict) -> dict:
    eg = (data.get("estatus_general") or "").strip()
    er = (data.get("estatus_reporte") or "").strip()
    res = (data.get("estado_resumen") or "").strip()

    if not eg:
        raise ValueError("estatus_general es obligatorio.")
    if not er:
        raise ValueError("estatus_reporte es obligatorio.")
    if not res:
        raise ValueError("estado_resumen es obligatorio.")

    # recortes por tamaño de columna
    return {
        "estatus_general": eg[:30],
        "estatus_reporte": er[:30],
        "estado_resumen": res[:30],
    }

def list_estado_orden() -> list[dict]:
    sql = """
      SELECT id, estatus_general, estatus_reporte, estado_resumen
      FROM cat_facturas.estado_orden
      ORDER BY id;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()

def get_estado_orden(eid: int) -> dict | None:
    sql = """
      SELECT id, estatus_general, estatus_reporte, estado_resumen
      FROM cat_facturas.estado_orden
      WHERE id = %s;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (eid,))
            return cur.fetchone()

def create_estado_orden(data: dict) -> int:
    payload = validate_estado_orden(data)
    sql = """
      INSERT INTO cat_facturas.estado_orden (estatus_general, estatus_reporte, estado_resumen)
      VALUES (%(estatus_general)s, %(estatus_reporte)s, %(estado_resumen)s)
      RETURNING id;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, payload)
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

def update_estado_orden(eid: int, data: dict) -> None:
    payload = validate_estado_orden(data)
    payload["id"] = eid
    sql = """
      UPDATE cat_facturas.estado_orden
      SET estatus_general=%(estatus_general)s,
          estatus_reporte=%(estatus_reporte)s,
          estado_resumen=%(estado_resumen)s
      WHERE id=%(id)s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()
