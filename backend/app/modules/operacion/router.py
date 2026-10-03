"""Endpoints de operación en campo — `03-api-contract §7`. Solo operador."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import AppError
from app.core.storage import nueva_key, subir_archivo
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.operacion import service
from app.modules.operacion.schemas import (
    CerrarServicioIn,
    IniciarServicioIn,
    TerminarViajeOperadorIn,
)
from app.modules.servicios.schemas import ServicioDetalleOut

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.operador))])


def _operador_id(user: Usuario) -> uuid.UUID:
    if user.operador_id is None:
        raise AppError("forbidden", "Este usuario no está ligado a un operador", 403)
    return user.operador_id


@router.get("/operador/servicios", response_model=list[ServicioDetalleOut])
def mis_servicios(
    estado: str | None = Query(default=None, description="Lista separada por comas"),
    desde: date | None = Query(default=None),
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.operador)),
) -> list[ServicioDetalleOut]:
    estados = estado.split(",") if estado else None
    return service.listar_servicios_operador(session, _operador_id(user), estados, desde)


@router.post("/operador/servicios/{servicio_id}/iniciar", response_model=ServicioDetalleOut)
def iniciar_servicio(
    servicio_id: uuid.UUID,
    body: IniciarServicioIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.operador)),
) -> ServicioDetalleOut:
    return service.iniciar_servicio(session, servicio_id, _operador_id(user), body, user)


@router.post("/operador/viajes/{viaje_id}/terminar")
def terminar_viaje(
    viaje_id: uuid.UUID,
    body: TerminarViajeOperadorIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.operador)),
):
    return service.terminar_viaje_operador(session, viaje_id, _operador_id(user), body, user)


@router.post("/operador/viajes/{viaje_id}/acuses")
async def agregar_acuse(
    viaje_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.operador)),
) -> dict:
    form = await request.form()
    archivo = form.get("file")
    if archivo is None:
        raise AppError("validation_error", "Falta el archivo", 422, details=[{"field": "file"}])
    client_action_id = form.get("client_action_id")
    if not client_action_id:
        raise AppError(
            "validation_error", "Falta client_action_id", 422, details=[{"field": "client_action_id"}]
        )
    pagina = int(form.get("pagina", 1))
    contenido = await archivo.read()
    key = nueva_key(f"acuses/{viaje_id}", archivo.filename or "acuse")
    subir_archivo(key, contenido, archivo.content_type or "application/octet-stream")
    acuse = service.agregar_acuse_operador_archivo(
        session,
        viaje_id,
        _operador_id(user),
        key,
        archivo.content_type or "application/octet-stream",
        pagina,
        uuid.UUID(str(client_action_id)),
        user,
    )
    return {"acuse": acuse}


@router.post("/operador/servicios/{servicio_id}/cerrar", response_model=ServicioDetalleOut)
def cerrar_servicio(
    servicio_id: uuid.UUID,
    body: CerrarServicioIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.operador)),
) -> ServicioDetalleOut:
    return service.cerrar_servicio(session, servicio_id, _operador_id(user), body, user)


@router.post("/operador/cargas/{carga_id}/ticket")
async def subir_ticket(
    carga_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    form = await request.form()
    archivo = form.get("file")
    if archivo is None:
        raise AppError("validation_error", "Falta el archivo", 422, details=[{"field": "file"}])
    contenido = await archivo.read()
    key = nueva_key(f"tickets/{carga_id}", archivo.filename or "ticket")
    subir_archivo(key, contenido, archivo.content_type or "application/octet-stream")
    service.subir_ticket_carga(session, carga_id, key)
    from app.core.storage import url_firmada

    return {"ticket_url": url_firmada(key)}
