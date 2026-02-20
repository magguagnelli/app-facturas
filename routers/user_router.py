from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg

from core.auth import require_admin, require_login
from core.audit import audit, build_log
from core.security import generate_temp_password, verify_password, hash_password
from routers.auth_router import fetch_user_auth_by_email

from services.users_service import (
    list_users, get_user_by_id, create_user, update_user, reset_password
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Leer imágenes base64 (ya generadas)
with open("top_base64.txt") as f:
    image_top = f.read()

def admin_ctx(request: Request, admin, **extra):
    return {
        "request": request,
        "user_role": admin.rol,
        "user_name": admin.nombre,
        "user_email": admin.correo,
        **extra,
    }

@router.get("/usuarios", response_class=HTMLResponse)
def usuarios_list(request: Request, q: str | None = Query(default=None)):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    users = list_users(q)

    audit(
        correo=admin.correo,
        accion="VIEW_USERS",
        descripcion="Visualización de lista de usuarios",
        log_accion=build_log(request, extra=f"q={q or ''} count={len(users)}"),
    )

    return templates.TemplateResponse(
        "usuarios_list.html",
        admin_ctx(request, admin, users=users, q=q or ""),
    )

@router.get("/usuarios/nuevo", response_class=HTMLResponse)
def usuario_new_form(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    return templates.TemplateResponse(
        "usuario_form.html",
        admin_ctx(
            request, admin,
            mode="create",
            error=None,
            success=None,
            form={"correo":"", "nombre":"", "rol":"CAPTURISTA", "estatus":"ACTIVO"},
        ),
    )

@router.post("/usuarios/nuevo", response_class=HTMLResponse)
def usuario_new_create(
    request: Request,
    correo: str = Form(...),
    nombre: str = Form(...),
    rol: str = Form(...),
    estatus: str = Form(...),
    password: str = Form(...),
):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    try:
        new_id = create_user(correo, nombre, rol, estatus, password)
    except psycopg.errors.UniqueViolation:
        return templates.TemplateResponse(
            "usuario_form.html",
            admin_ctx(
                request, admin,
                mode="create",
                error="Ya existe un usuario con ese correo.",
                success=None,
                form={"correo":correo, "nombre":nombre, "rol":rol, "estatus":estatus},
            ),
            status_code=409,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "usuario_form.html",
            admin_ctx(
                request, admin,
                mode="create",
                error=str(e),
                success=None,
                form={"correo":correo, "nombre":nombre, "rol":rol, "estatus":estatus},
            ),
            status_code=400,
        )
    # Enviar correo al nuevo usuario
    try:
        from services.email_service import send_user_creation_email
        send_user_creation_email(
            to_email=correo,
            temp_password=password
        )
    except Exception as e:
        print(f"Error enviando correo a {correo}: {e}")
        # No detenemos la creación; solo logueamos el error   
        
    audit(
        correo=admin.correo,
        accion="CREATE_USER",
        descripcion="Registro de nuevo usuario",
        log_accion=build_log(request, extra=f"id={new_id} correo={correo.strip().lower()}"),
    )

    return RedirectResponse(url="/usuarios", status_code=302)

@router.get("/usuarios/{user_id}/editar", response_class=HTMLResponse)
def usuario_edit_form(request: Request, user_id: int):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    u = get_user_by_id(user_id)
    if not u:
        return RedirectResponse(url="/usuarios", status_code=302)

    return templates.TemplateResponse(
        "usuario_form.html",
        admin_ctx(
            request, admin,
            mode="edit",
            user_id=user_id,
            error=None,
            success=None,
            form={"correo":u["correo"], "nombre":u["nombre"], "rol":u["rol"], "estatus":u["estatus"]},
        ),
    )

@router.post("/usuarios/{user_id}/editar", response_class=HTMLResponse)
def usuario_edit_save(
    request: Request,
    user_id: int,
    correo: str = Form(...),
    nombre: str = Form(...),
    rol: str = Form(...),
    estatus: str = Form(...),
):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    try:
        update_user(user_id, correo, nombre, rol, estatus)
    except psycopg.errors.UniqueViolation:
        return templates.TemplateResponse(
            "usuario_form.html",
            admin_ctx(
                request, admin,
                mode="edit",
                user_id=user_id,
                error="Ya existe un usuario con ese correo.",
                success=None,
                form={"correo":correo, "nombre":nombre, "rol":rol, "estatus":estatus},
            ),
            status_code=409,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "usuario_form.html",
            admin_ctx(
                request, admin,
                mode="edit",
                user_id=user_id,
                error=str(e),
                success=None,
                form={"correo":correo, "nombre":nombre, "rol":rol, "estatus":estatus},
            ),
            status_code=400,
        )

    audit(
        correo=admin.correo,
        accion="UPDATE_USER",
        descripcion="Actualización de usuario",
        log_accion=build_log(request, extra=f"id={user_id} correo={correo.strip().lower()}"),
    )

    return RedirectResponse(url="/usuarios", status_code=302)

@router.post("/usuarios/{user_id}/reset-password", response_class=HTMLResponse)
def usuario_reset_password(request: Request, user_id: int):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    u = get_user_by_id(user_id)
    if not u:
        return RedirectResponse(url="/usuarios", status_code=302)

    temp_pwd = generate_temp_password(12)
    try:
        reset_password(user_id, temp_pwd)
    except ValueError as e:
        return RedirectResponse(url=f"/usuarios/{user_id}/editar", status_code=302)
        # Enviar correo al usuario con la contraseña temporal
    try:
        from services.email_service import send_password_email  # tu función de envío
        #send_password_email(u["correo"], temp_pwd)
        send_password_email(u["correo"], temp_pwd)
    except Exception as e:
        # Opcional: loguear error de correo pero no cancelar proceso
        print(f"Error enviando correo a {u['correo']}: {e}")


    audit(
        correo=admin.correo,
        accion="RESET_PWD",
        descripcion="Reset de contraseña",
        log_accion=build_log(request, extra=f"id={user_id} correo={u['correo']}"),
    )

    return templates.TemplateResponse(
        "password_reset_result.html",
        admin_ctx(request, admin, target_user=u, temp_password=temp_pwd),
    )

#@router.get("/usuarios/{user_id}/cambiar-password", response_class=HTMLResponse)
#def cambiar_password_get(request: Request, user_id: int):
#    # Validar sesión activa
#    user_session = require_login(request)
#    if not user_session:
#        return RedirectResponse(url="/login", status_code=302)
#
#    # Obtener info del usuario
#    target_user = get_user_by_id(user_id)
#    if not target_user:
#        return RedirectResponse(url="/usuarios", status_code=302)
#
#    return templates.TemplateResponse(
#        "cambio_contraseña.html",
#        {
#            "request": request,
#            "target_user": target_user
#        }
#    )
