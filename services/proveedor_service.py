# services/proveedor_service.py
from __future__ import annotations
import re
import psycopg
from psycopg.rows import dict_row
from core.db import get_conn

RFC_REGEX = re.compile(r"^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$", re.IGNORECASE)
TIPOS = {"FISICA", "MORAL", "CONSORCIO"}
ESTATUS = {"ACTIVO", "INACTIVO"}

def _norm_rfc(rfc: str) -> str:
    return (rfc or "").strip().upper()

def validate_proveedor(data: dict, *, for_update: bool = False) -> None:
    rfc = _norm_rfc(data.get("rfc", ""))
    razon = (data.get("razon_social") or "").strip()
    tipo = (data.get("tipo_persona") or "").strip().upper()
    estatus = (data.get("estatus") or "ACTIVO").strip().upper()

    if not rfc or not RFC_REGEX.match(rfc):
        raise ValueError("RFC inválido (formato).")
    if not razon:
        raise ValueError("Razón social es obligatoria.")
    if tipo not in TIPOS:
        raise ValueError("Tipo de persona inválido (FISICA, MORAL, CONSORCIO).")
    if estatus not in ESTATUS:
        raise ValueError("Estatus inválido (ACTIVO/INACTIVO).")

def list_proveedores(q: str | None = None) -> list[dict]:
    if q:
        like = f"%{q.strip().lower()}%"
        sql = """
          SELECT id, rfc, razon_social, nombre_comercial, tipo_persona, telefono, email, estatus
          FROM cat_facturas.proveedor
          WHERE lower(rfc) LIKE %s OR lower(razon_social) LIKE %s OR lower(nombre_comercial) LIKE %s
          ORDER BY razon_social;
        """
        params = (like, like, like)
    else:
        sql = """
          SELECT id, rfc, razon_social, nombre_comercial, tipo_persona, telefono, email, estatus
          FROM cat_facturas.proveedor
          ORDER BY razon_social;
        """
        params = ()

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def get_proveedor(prov_id: int) -> dict | None:
    sql = """
      SELECT id, rfc, razon_social, nombre_comercial, tipo_persona, telefono, email, estatus
      FROM cat_facturas.proveedor
      WHERE id = %s;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (prov_id,))
            return cur.fetchone()

def create_proveedor(data: dict) -> int:
    validate_proveedor(data)

    payload = {
        "rfc": _norm_rfc(data["rfc"]),
        "razon_social": (data.get("razon_social") or "").strip(),
        "nombre_comercial": (data.get("nombre_comercial") or "").strip() or None,
        "tipo_persona": (data.get("tipo_persona") or "").strip().upper(),
        "telefono": (data.get("telefono") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "estatus": (data.get("estatus") or "ACTIVO").strip().upper(),
    }

    sql = """
      INSERT INTO cat_facturas.proveedor
        (rfc, razon_social, nombre_comercial, tipo_persona, telefono, email, estatus)
      VALUES
        (%(rfc)s, %(razon_social)s, %(nombre_comercial)s, %(tipo_persona)s, %(telefono)s, %(email)s, %(estatus)s)
      RETURNING id;
    """

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, payload)
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

def update_proveedor(prov_id: int, data: dict) -> None:
    # Para update permitimos cambiar rfc también, pero respetando UNIQUE
    validate_proveedor(data, for_update=True)

    payload = {
        "id": prov_id,
        "rfc": _norm_rfc(data["rfc"]),
        "razon_social": (data.get("razon_social") or "").strip(),
        "nombre_comercial": (data.get("nombre_comercial") or "").strip() or None,
        "tipo_persona": (data.get("tipo_persona") or "").strip().upper(),
        "telefono": (data.get("telefono") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "estatus": (data.get("estatus") or "ACTIVO").strip().upper(),
    }

    sql = """
      UPDATE cat_facturas.proveedor SET
        rfc = %(rfc)s,
        razon_social = %(razon_social)s,
        nombre_comercial = %(nombre_comercial)s,
        tipo_persona = %(tipo_persona)s,
        telefono = %(telefono)s,
        email = %(email)s,
        estatus = %(estatus)s
      WHERE id = %(id)s;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()
