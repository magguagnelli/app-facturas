import re
import psycopg
from psycopg import errors
from core.db import get_conn
from core.security import hash_password

EMAIL_REGEX = re.compile(r"^[a-z0-9._%+-]+@imssbienestar\.gob\.mx$", re.IGNORECASE)
ALLOWED_ROLES = {"CAPTURISTA", "ADMIN"}
ALLOWED_STATUS = {"ACTIVO", "INACTIVO"}

def validate_email(correo: str) -> bool:
    return bool(EMAIL_REGEX.match(correo))

def list_users(q: str | None = None) -> list[dict]:
    if q:
        like = f"%{q.strip().lower()}%"
        sql = """l
            SELECT id, correo, nombre, rol, estatus
            FROM cat_facturas.usuario
            WHERE lower(correo) LIKE %s OR lower(nombre) LIKE %s
            ORDER BY id DESC;
        """
        params = (like, like)
    else:
        sql = """
            SELECT id, correo, nombre, rol, estatus
            FROM cat_facturas.usuario
            ORDER BY id DESC;
        """
        params = ()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def get_user_by_id(user_id: int) -> dict | None:
    sql = """
        SELECT id, correo, nombre, rol, estatus
        FROM cat_facturas.usuario
        WHERE id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()

def create_user(correo: str, nombre: str, rol: str, estatus: str, plain_password: str) -> int:
    correo = correo.strip().lower()
    nombre = nombre.strip()
    rol = rol.strip().upper()
    estatus = estatus.strip().upper()

    if not validate_email(correo):
        raise ValueError("El correo debe ser @imssbienestar.gob.mx")
    if rol not in ALLOWED_ROLES:
        raise ValueError("Rol inválido (solo CAPTURISTA o ADMIN).")
    if estatus not in ALLOWED_STATUS:
        raise ValueError("Estatus inválido (ACTIVO/INACTIVO).")
    if len(plain_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    pwd_hash = hash_password(plain_password)

    sql = """
        INSERT INTO cat_facturas.usuario (correo, nombre, rol, estatus, pwd)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (correo, nombre, rol, estatus, pwd_hash))
            row = cur.fetchone()
            new_id = row["id"] 
            conn.commit()
            return int(new_id)

def update_user(user_id: int, correo: str, nombre: str, rol: str, estatus: str) -> None:
    correo = correo.strip().lower()
    nombre = nombre.strip()
    rol = rol.strip().upper()
    estatus = estatus.strip().upper()

    if not validate_email(correo):
        raise ValueError("El correo debe ser @imssbienestar.gob.mx")
    if rol not in ALLOWED_ROLES:
        raise ValueError("Rol inválido (solo CAPTURISTA o ADMIN).")
    if estatus not in ALLOWED_STATUS:
        raise ValueError("Estatus inválido (ACTIVO/INACTIVO).")

    sql = """
        UPDATE cat_facturas.usuario
        SET correo = %s, nombre = %s, rol = %s, estatus = %s
        WHERE id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (correo, nombre, rol, estatus, user_id))
            conn.commit()

def reset_password(user_id: int, new_plain_password: str) -> None:
    if len(new_plain_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    pwd_hash = hash_password(new_plain_password)

    sql = """
        UPDATE cat_facturas.usuario
        SET pwd = %s
        WHERE id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pwd_hash, user_id))
            conn.commit()
