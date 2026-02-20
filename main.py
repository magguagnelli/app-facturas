##Imports
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers.auth_router import router as auth_router
from routers.user_router import router as users_router
from routers.pages_router import router as pages_router

from routers.orden_suministro_api_router import router as os_api_router

from routers.auditoria_router import router as auditoria_router
from routers.auditoria_api_router import router as auditoria_api_router

from routers.proveedor_router import router as proveedor_router
from routers.proveedor_api_router import router as proveedor_api_router

from routers.export_router import router as export_router

from routers.entidad_router import router as entidad_router
from routers.entidad_api_router import router as entidad_api_router
from routers.estado_orden_router import router as estado_orden_router
from routers.estado_orden_api_router import router as estado_orden_api_router

from routers.area_router import router as area_router
from routers.area_api_router import router as area_api_router

from routers.catalogos_router import router as catalogos_router
from routers.catalogos_api_router import router as catalogos_api_router

from routers.cfdi_router import router as cfdi_router
from routers.cfdi_api_router import router as cfdi_api_router

from routers.facturas_listado_api_router import router as facturas_listado_api_router
from routers.facturas_listado_router  import router as facturas_listado_router

app = FastAPI(title="Sistema de Facturas - IMSS Bienestar")
app.mount("/static", StaticFiles(directory="static"), name="static")

##routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(pages_router)

app.include_router(os_api_router)

app.include_router(auditoria_router)
app.include_router(auditoria_api_router)

app.include_router(proveedor_router)
app.include_router(proveedor_api_router)

app.include_router(export_router)

app.include_router(entidad_router)
app.include_router(entidad_api_router)

app.include_router(estado_orden_router)
app.include_router(estado_orden_api_router)

app.include_router(area_router)

app.include_router(area_router)
app.include_router(area_api_router)

app.include_router(catalogos_router)
app.include_router(catalogos_api_router)

app.include_router(cfdi_router)
app.include_router(cfdi_api_router)

app.include_router(facturas_listado_api_router)
app.include_router(facturas_listado_router)