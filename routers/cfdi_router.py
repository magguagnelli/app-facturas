# routers/cfdi_router.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import require_login
from core.audit import audit, build_log
from typing import Optional
from routers.cfdi_api_router import api_detalle, api_estado_orden, api_estado_siaf, api_fiscalizador

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
    estados_siaf = api_estado_siaf(request)
    fiscalizadores = api_fiscalizador(request)

    audit(
        correo=user.correo,
        accion="Acceso_Alta_CFDIs",
        descripcion="Acceso a nuevo CFDI",
        log_accion=build_log(request),
    )

    return templates.TemplateResponse(
        "cfdi_alta.html", {
            "request": request,
            "user_role": user.rol,
            "user_name": user.nombre,
            "user_email": user.correo,
            "estados_siaf":estados_siaf,
            "fiscalizadores":fiscalizadores
        }
    )

@router.api_route("/cfdi/edit", methods=["GET", "POST"], response_class=HTMLResponse)
def cfdi_edit_page(
        request: Request, 
        id_cfdi: int = Form(...)
    ):
    #print(f"Api_router, CFDI: {id_cfdi}")
    user = require_login(request)
    if id_cfdi ==0:
        return RedirectResponse(url="/cfd/nuevo", status_code=302)
    
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    if user.rol not in {"CAPTURISTA", "ADMIN"}:
        return RedirectResponse(url="/home", status_code=302)

    cfdi = api_detalle(request,id_cfdi)
    cfdi["estados_os"] = api_estado_orden(request)
    cfdi["estados_siaf"] = api_estado_siaf(request)
    cfdi["fiscalizadores"] = api_fiscalizador(request)
    #print(cfdi["item"])
    
    audit(
        correo=user.correo,
        accion="ACCESO_EDICION_CFDI",
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
