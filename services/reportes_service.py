# services/reportes_service.py
from __future__ import annotations
from psycopg.rows import dict_row
from core.db import get_conn

def _q_one(sql: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchone() or {}

def _q_many(sql: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()

def reportes_capturista() -> list[dict]:
    r1 = _q_one("""
      SELECT COUNT(*) AS total
      FROM cat_facturas.orden_suministro os
      LEFT JOIN cat_facturas.cfdi c ON c.orden_suministro = os.id
      WHERE c.id IS NULL;
    """)["total"]

    r2 = _q_one("""
      SELECT COUNT(DISTINCT os.id) AS total
      FROM cat_facturas.orden_suministro os
      JOIN cat_facturas.cfdi c ON c.orden_suministro = os.id;
    """)["total"]

    r3 = _q_one("""
      SELECT
        SUM(CASE WHEN os.fecha_pago IS NOT NULL THEN 1 ELSE 0 END) AS pagadas,
        SUM(CASE WHEN os.fecha_pago IS NULL THEN 1 ELSE 0 END) AS pendientes
      FROM cat_facturas.orden_suministro os;
    """)

    r4 = _q_one("""
      SELECT COALESCE(SUM(os.importe_pago), 0) AS total_pendiente
      FROM cat_facturas.orden_suministro os
      WHERE os.fecha_pago IS NULL;
    """)["total_pendiente"]

    return [
        {"reporte": "Órdenes sin CFDI", "valor": r1, "detalle": "Pendientes de captura CFDI"},
        {"reporte": "Órdenes con CFDI", "valor": r2, "detalle": "CFDI ACTIVO asociado"},
        {"reporte": "Órdenes pagadas", "valor": r3.get("pagadas", 0), "detalle": "Con fecha_pago"},
        {"reporte": "Órdenes pendientes de pago", "valor": r3.get("pendientes", 0), "detalle": "Sin fecha_pago"},
        {"reporte": "Importe pendiente de pago", "valor": r4, "detalle": "Suma importe_pago sin fecha_pago"},
    ]

def reportes_admin() -> dict:
    usuarios = _q_one("""
      SELECT
        SUM(CASE WHEN u.estatus = 'ACTIVO' THEN 1 ELSE 0 END) AS activos,
        SUM(CASE WHEN u.estatus = 'INACTIVO' THEN 1 ELSE 0 END) AS inactivos
      FROM cat_facturas.usuario u;
    """)

    prov_inactivos = _q_one("""
      SELECT COUNT(*) AS total
      FROM cat_facturas.proveedor
      WHERE estatus = 'INACTIVO';
    """)["total"]

    contratos_por_vencer = _q_one("""
      SELECT COUNT(*) AS total
      FROM cat_facturas.contrato
      WHERE estatus = 'ACTIVO'
        AND f_fin <= (CURRENT_DATE + INTERVAL '30 days');
    """)["total"]

    os_por_estatus = _q_many("""
      SELECT eo.estado_resumen AS estatus, COUNT(*) AS total
      FROM cat_facturas.orden_suministro os
      JOIN cat_facturas.estado_orden eo ON eo.id = os.estatus
      GROUP BY eo.estado_resumen
      ORDER BY total DESC;
    """)

    cfdi_dups = _q_one("""
      SELECT COUNT(*) AS duplicados
      FROM (
        SELECT uuid
        FROM cat_facturas.cfdi
        GROUP BY uuid
        HAVING COUNT(*) > 1
      ) t;
    """)["duplicados"]

    return {
        "kpis": [
            {"reporte": "Usuarios activos", "valor": usuarios.get("activos", 0), "detalle": "estatus=ACTIVO"},
            {"reporte": "Usuarios inactivos", "valor": usuarios.get("inactivos", 0), "detalle": "estatus=INACTIVO"},
            {"reporte": "Proveedores inactivos", "valor": prov_inactivos, "detalle": "estatus=INACTIVO"},
            {"reporte": "Contratos por vencer (30 días)", "valor": contratos_por_vencer, "detalle": "f_fin <= hoy+30"},
            {"reporte": "CFDI UUID duplicados", "valor": cfdi_dups, "detalle": "uuid repetido"},
        ],
        "os_por_estatus": os_por_estatus,
    }
