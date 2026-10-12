"""Endpoints de servicios y viajes — `03-api-contract §6`. Todo solo-admin."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import AppError
from app.core.storage import nueva_key, subir_archivo
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.catalogos.schemas import Page
from app.modules.operacion.schemas import CargaUpdate
from app.modules.servicios import service
from app.modules.servicios.schemas import (
    AcuseOut,
    CancelarServicioIn,
    ConteosOut,
    DistanciaSugeridaOut,
    FolioViajeIn,
    DuplicarServicioIn,
    OrdenViajesIn,
    ReescaneoIn,
    ServicioCreate,
    ServicioDetalleOut,
    ServicioListItemOut,
    ServicioUpdate,
    TerminarViajeIn,
    ViajeCreate,
    ViajeMercanciaIn,
    ViajeUpdate,
)

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


@router.post("/servicios", response_model=ServicioDetalleOut, status_code=201)
def crear_servicio(
    body: ServicioCreate,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> ServicioDetalleOut:
    servicio = service.create_servicio(session, body, user)
    return service.build_servicio_detalle(session, servicio)


@router.get("/servicios", response_model=Page[ServicioListItemOut])
def listar_servicios(
    vista: str | None = Query(default=None),
    cliente_id: uuid.UUID | None = Query(default=None),
    operador_id: uuid.UUID | None = Query(default=None),
    unidad_id: uuid.UUID | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None),
    acuses_pendientes: bool = Query(default=False),
    inspeccion_fallas: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Page[ServicioListItemOut]:
    items, total = service.list_servicios(
        session, vista, cliente_id, operador_id, unidad_id, fecha_desde, fecha_hasta, q, page, size,
        acuses_pendientes=acuses_pendientes, inspeccion_fallas=inspeccion_fallas,
    )
    return Page(items=items, total=total, page=page, size=size)


@router.get("/servicios/conteos", response_model=ConteosOut)
def conteos_servicios(
    cliente_id: uuid.UUID | None = Query(default=None),
    operador_id: uuid.UUID | None = Query(default=None),
    unidad_id: uuid.UUID | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ConteosOut:
    return service.conteos_servicios(
        session, cliente_id, operador_id, unidad_id, fecha_desde, fecha_hasta, q
    )


@router.get("/servicios/{servicio_id}", response_model=ServicioDetalleOut)
def obtener_servicio(
    servicio_id: uuid.UUID, session: Session = Depends(get_session)
) -> ServicioDetalleOut:
    from app.modules.operacion.service import enriquecer_detalle_con_operacion

    servicio = service.get_servicio(session, servicio_id)
    detalle = service.build_servicio_detalle(session, servicio)
    return enriquecer_detalle_con_operacion(session, servicio.id, detalle)


@router.patch("/servicios/{servicio_id}", response_model=ServicioDetalleOut)
def editar_servicio(
    servicio_id: uuid.UUID, body: ServicioUpdate, session: Session = Depends(get_session)
) -> ServicioDetalleOut:
    servicio = service.update_servicio(session, servicio_id, body)
    return service.build_servicio_detalle(session, servicio)


@router.post("/servicios/{servicio_id}/duplicar", response_model=ServicioDetalleOut, status_code=201)
def duplicar_servicio(
    servicio_id: uuid.UUID,
    body: DuplicarServicioIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> ServicioDetalleOut:
    nuevo = service.duplicar_servicio(session, servicio_id, body, user)
    return service.build_servicio_detalle(session, nuevo)


@router.post("/servicios/{servicio_id}/marcar-terminado", response_model=ServicioDetalleOut)
def marcar_terminado(
    servicio_id: uuid.UUID, session: Session = Depends(get_session)
) -> ServicioDetalleOut:
    servicio = service.marcar_terminado(session, servicio_id)
    return service.build_servicio_detalle(session, servicio)


@router.post("/servicios/{servicio_id}/cancelar", response_model=ServicioDetalleOut)
def cancelar_servicio(
    servicio_id: uuid.UUID, body: CancelarServicioIn, session: Session = Depends(get_session)
) -> ServicioDetalleOut:
    servicio = service.cancelar_servicio(session, servicio_id, body)
    return service.build_servicio_detalle(session, servicio)


# --- Viajes ------------------------------------------------------------------
@router.post("/servicios/{servicio_id}/viajes", status_code=201)
def agregar_viaje(
    servicio_id: uuid.UUID, body: ViajeCreate, session: Session = Depends(get_session)
):
    viaje = service.add_viaje(session, servicio_id, body)
    return viaje


@router.patch("/viajes/{viaje_id}")
def editar_viaje(viaje_id: uuid.UUID, body: ViajeUpdate, session: Session = Depends(get_session)):
    return service.update_viaje(session, viaje_id, body)


@router.delete("/viajes/{viaje_id}", status_code=204)
def eliminar_viaje(viaje_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    service.delete_viaje(session, viaje_id)


@router.post("/servicios/{servicio_id}/viajes/orden")
def ordenar_viajes(
    servicio_id: uuid.UUID, body: OrdenViajesIn, session: Session = Depends(get_session)
):
    return service.reordenar_viajes(session, servicio_id, body.viaje_ids)


@router.post("/viajes/{viaje_id}/terminar")
def terminar_viaje(
    viaje_id: uuid.UUID,
    body: TerminarViajeIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
):
    return service.terminar_viaje(session, viaje_id, body, user)


@router.post("/viajes/{viaje_id}/reabrir")
def reabrir_viaje(viaje_id: uuid.UUID, session: Session = Depends(get_session)):
    return service.reabrir_viaje(session, viaje_id)


@router.put("/viajes/{viaje_id}/mercancias")
def set_mercancias(
    viaje_id: uuid.UUID, body: list[ViajeMercanciaIn], session: Session = Depends(get_session)
):
    return service.set_mercancias_viaje(session, viaje_id, body)


@router.post("/viajes/{viaje_id}/reescaneo")
def solicitar_reescaneo(
    viaje_id: uuid.UUID,
    body: ReescaneoIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> dict:
    viaje = service.solicitar_reescaneo(session, viaje_id, body.motivo, user)
    return {"viaje_id": viaje.id, "reescaneo": service.reescaneo_out(session, viaje)}


@router.delete("/viajes/{viaje_id}/reescaneo")
def quitar_reescaneo(viaje_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    viaje = service.quitar_reescaneo(session, viaje_id)
    return {"viaje_id": viaje.id, "reescaneo": None}


@router.put("/viajes/{viaje_id}/folio")
def set_folio(
    viaje_id: uuid.UUID,
    body: FolioViajeIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> dict:
    return service.set_folio_viaje(session, viaje_id, body.folio, user)


@router.post("/viajes/{viaje_id}/acuses", response_model=AcuseOut, status_code=201)
async def agregar_acuse(
    viaje_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> AcuseOut:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        archivo = form.get("file")
        if archivo is None:
            raise AppError(
                "validation_error", "Falta el archivo", 422, details=[{"field": "file"}]
            )
        pagina = int(form.get("pagina", 1))
        contenido = await archivo.read()
        service.validar_acuse_pdf(contenido)
        key = nueva_key(f"acuses/{viaje_id}", archivo.filename or "acuse")
        subir_archivo(key, contenido, archivo.content_type or "application/octet-stream")
        acuse = service.agregar_acuse_archivo(
            session, viaje_id, key, archivo.content_type or "application/octet-stream", pagina, user
        )
    else:
        body = await request.json()
        referencia = body.get("referencia")
        if not referencia:
            raise AppError(
                "validation_error", "Falta 'referencia'", 422, details=[{"field": "referencia"}]
            )
        acuse = service.agregar_acuse_referencia(session, viaje_id, referencia, user)
    return service.acuse_out(acuse)


@router.delete("/acuses/{acuse_id}", status_code=204)
def eliminar_acuse(acuse_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    service.eliminar_acuse(session, acuse_id)


@router.get("/lugares/distancia-sugerida", response_model=DistanciaSugeridaOut)
def distancia_sugerida(
    destino_lugar_id: uuid.UUID,
    origen_lugar_id: uuid.UUID | None = None,
    session: Session = Depends(get_session),
) -> DistanciaSugeridaOut:
    distancia, fuente, confirmado = service.distancia_sugerida(session, destino_lugar_id, origen_lugar_id)
    return DistanciaSugeridaOut(distancia_km=distancia, fuente=fuente, confirmado=confirmado)


# --- Cargas de combustible — corrección del admin (Fase 3, `03 §6`) ----------
@router.patch("/cargas/{carga_id}")
def editar_carga(carga_id: uuid.UUID, body: CargaUpdate, session: Session = Depends(get_session)):
    from app.modules.operacion.service import actualizar_carga

    return actualizar_carga(session, carga_id, body.model_dump(exclude_unset=True))


@router.delete("/cargas/{carga_id}", status_code=204)
def eliminar_carga(carga_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    from app.modules.operacion.service import eliminar_carga as _eliminar_carga

    _eliminar_carga(session, carga_id)
