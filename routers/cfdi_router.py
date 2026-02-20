# routers/cfdi_router.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import require_login
from core.audit import audit, build_log
from typing import Optional
from routers.cfdi_api_router import api_detalle, api_estado_orden

router = APIRouter(tags=["cfdi_pages"])

templates = Jinja2Templates(directory="templates")

@router.get("/cfdi", response_class=HTMLResponse)
def cfdi_page(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    if user.rol not in {"CAPTURISTA", "ADMIN"}:
        return RedirectResponse(url="/home", status_code=302)
    
    audit(
        correo=user.correo,
        accion="VIEW_CFDIs",
        descripcion="Acceso a listado de CFDIs",
        log_accion=build_log(request),
    )

    # roles: admin/capturista
    return templates.TemplateResponse(
        "cfdi.html", {
            "request": request,
            "user_role": user.rol,
            "user_name": user.nombre,
            "user_email": user.correo,
        }
    )

@router.get("/cfdi/nuevo", response_class=HTMLResponse)
def cfdi_alta_page(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    if user.rol not in {"CAPTURISTA", "ADMIN"}:
        return RedirectResponse(url="/home", status_code=302)
    estados_siaf = {
        "items": [
            {
                "id": "Estatus 1",
                "estatus": "Estatus 1"
            },
            {
                "id": "Estatus 2",
                "estatus": "Estatus 2"
            },
            {
                "id": "Estatus 3",
                "estatus": "Estatus 3"
            },
            {
                "id": "Estatus 4",
                "estatus": "Estatus 4"
            },
            {
                "id": "Estatus 5",
                "estatus":"Estatus 5"
            }
        ]
    }
    audit(
        correo=user.correo,
        accion="Alta_CFDIs",
        descripcion="Acceso a nuevo CFDI",
        log_accion=build_log(request),
    )

    return templates.TemplateResponse(
        "cfdi_alta.html", {
            "request": request,
            "user_role": user.rol,
            "user_name": user.nombre,
            "user_email": user.correo,
            "estados_siaf":estados_siaf
        }
    )

@router.api_route("/cfdi/edit", methods=["GET", "POST"], response_class=HTMLResponse)
def cfdi_edit_page(
        request: Request, 
        id_cfdi: Optional [int] = Form(1)
    ):
    id_cfdi = 1;
    user = require_login(request)
    if id_cfdi ==0:
        return RedirectResponse(url="/cfd/nuevo", status_code=302)
    
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    if user.rol not in {"CAPTURISTA", "ADMIN"}:
        return RedirectResponse(url="/home", status_code=302)

    cfdi = api_detalle(request,id_cfdi)
    cfdi["estados_os"] = api_estado_orden(request)
    cfdi["estados_siaf"] = {
        "items": [
            {
                "id": "Estatus 1",
                "estatus": "Estatus 1"
            },
            {
                "id": "Estatus 2",
                "estatus": "Estatus 2"
            },
            {
                "id": "Estatus 3",
                "estatus": "Estatus 3"
            },
            {
                "id": "Estatus 4",
                "estatus": "Estatus 4"
            },
            {
                "id": "Estatus 5",
                "estatus":"Estatus 5"
            }
        ]
    }
    #print(cfdi["item"])
    audit(
        correo=user.correo,
        accion="EDICION_CFDI",
        descripcion=f"Acceso a edición CFDI id={id_cfdi}",
        log_accion=build_log(request)
    )

    return templates.TemplateResponse(
        "cfdi_edit.html",
        {
            "request": request,
            "user_role": user.rol,
            "user_name": user.nombre,
            "user_email": user.correo,
            "data": cfdi
        }
    )
