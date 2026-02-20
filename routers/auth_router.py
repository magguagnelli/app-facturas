from __future__ import annotations

import re
from fastapi import APIRouter, Request, Form, FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from core.db import get_conn
from core.security import verify_password
from core.audit import audit, build_log
from core.auth import serializer, SESSION_COOKIE, get_current_user, require_login
from services.reportes_service import reportes_capturista, reportes_admin
from core.audit import audit, build_log



templates = Jinja2Templates(directory="templates")
router = APIRouter()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

EMAIL_REGEX = re.compile(r"^[a-z0-9._%+-]+@imssbienestar\.gob\.mx$", re.IGNORECASE)


def is_allowed_email(correo: str) -> bool:
    return bool(EMAIL_REGEX.match(correo or ""))


def fetch_user_auth_by_email(correo: str) -> dict | None:
    # Trae lo necesario para login + sesión
    sql = """
        SELECT id, correo, nombre, rol, estatus, pwd
        FROM cat_facturas.usuario
        WHERE correo = %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (correo,))
            return cur.fetchone()


def set_session_cookie(resp: RedirectResponse, row: dict) -> None:
    # Token firmado con datos mínimos para sesión
    token = serializer.dumps(
        {
            "id": row["id"],
            "correo": row["correo"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "estatus": row["estatus"],
        }
    )
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=False,  # True en HTTPS
        samesite="lax",
        max_age=60 * 60 * 8,  # 8 horas
    )


@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    user = get_current_user(request)
    if user and user.estatus == "ACTIVO":
        return RedirectResponse(url="/home", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def do_login(
    request: Request,
    correo: str = Form(...),
    password: str = Form(...),
):
    correo = (correo or "").strip().lower()
    #print(f"[DEBUG] Inicio login - correo recibido: {correo}")

    # 1) Dominio permitido
    if not is_allowed_email(correo):
        #print("[DEBUG] Paso 1: correo no permitido")
        audit(
            correo="ANONIMO",
            accion="LOGIN_FAIL",
            descripcion="Intento login con correo no permitido",
            log_accion=build_log(request, extra=f"correo={correo}"),
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Solo se permite acceso con correo @imssbienestar.gob.mx"},
            status_code=400,
        )
    #print("[DEBUG] Paso 1: dominio permitido OK")

    # 2) Buscar usuario
    try:
        row = fetch_user_auth_by_email(correo)
        #print(f"[DEBUG] Paso 2: usuario encontrado: {row}")
    except Exception as e:
        print(f"[DEBUG] Paso 2: ERROR conexión a BD: {e}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Error de conexión a la base de datos."},
            status_code=500,
        )

    if not row:
        #print("[DEBUG] Paso 2: usuario no existe")
        audit(
            correo=correo,
            accion="LOGIN_FAIL",
            descripcion="Intento login: usuario no existe",
            log_accion=build_log(request),
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos."},
            status_code=401,
        )

    # 3) Estatus ACTIVO
    estatus = (row.get("estatus") or "").upper()
    if estatus != "ACTIVO":
        #print(f"[DEBUG] Paso 3: usuario INACTIVO - estatus={estatus}")
        audit(
            correo=correo,
            accion="LOGIN_FAIL",
            descripcion="Intento login: usuario INACTIVO",
            log_accion=build_log(request),
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Tu usuario está INACTIVO. Contacta al administrador."},
            status_code=403,
        )
    #print("[DEBUG] Paso 3: estatus ACTIVO OK")

    # 4) Verificar password
    stored_hash = row.get("pwd") or ""
    if not stored_hash or not verify_password(password, stored_hash):
        #print("[DEBUG] Paso 4: contraseña incorrecta")
        audit(
            correo=correo,
            accion="LOGIN_FAIL",
            descripcion="Intento login: contraseña incorrecta",
            log_accion=build_log(request),
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos."},
            status_code=401,
        )
   # print("[DEBUG] Paso 4: contraseña OK")

    # 5) Login OK: crear sesión
    resp = RedirectResponse(url="/home", status_code=302)
    set_session_cookie(resp, row)
    #print("[DEBUG] Paso 5: sesión creada, login OK")

    audit(
        correo=correo,
        accion="LOGIN",
        descripcion="Inicio de sesión exitoso",
        log_accion=build_log(request, extra=f"rol={row.get('rol')}"),
    )
    return resp



@router.get("/home", response_class=HTMLResponse)
def home(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    # Solo CAPTURISTA y ADMIN
    if user.rol == "ADMIN":
        data = reportes_admin()
        audit(user.correo, "VIEW", "Home Admin (reportes)", build_log(request))
        return templates.TemplateResponse(
            "facturas_listado.html",
            {"request": request, "user_role": user.rol, "user_name": user.nombre, "user_email": user.correo, **data},
        )
    
    if user.rol == "CAPTURISTA":
        reportes = reportes_capturista()
        audit(user.correo, "VIEW", "Home Capturista (reportes)", build_log(request))
        return templates.TemplateResponse(
            "facturas_listado.html",
            {"request": request, "user_role": user.rol, "user_name": user.nombre, "user_email": user.correo, "reportes": reportes},
        )
    
    return RedirectResponse(url="/logout", status_code=302)


@router.post("/logout")
def logout(request: Request):
    user = get_current_user(request)
    if user:
        audit(
            correo=user.correo,
            accion="LOGOUT",
            descripcion="Cierre de sesión",
            log_accion=build_log(request),
        )

    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
