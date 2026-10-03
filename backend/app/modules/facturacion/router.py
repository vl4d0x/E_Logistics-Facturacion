"""Endpoints de facturación — `03-api-contract §9`. Solo admin."""
import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.facturacion import service
from app.modules.facturacion.schemas import (
    FacturacionDetalleOut,
    FacturacionUpdateIn,
    FacturarIn,
    ImpuestosPreviewIn,
    MontosOut,
    ValidacionOut,
)

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


@router.post("/impuestos/preview", response_model=MontosOut)
def impuestos_preview(body: ImpuestosPreviewIn) -> MontosOut:
    return service.preview_impuestos(body)


@router.get("/servicios/{servicio_id}/validar", response_model=ValidacionOut)
def validar_servicio(servicio_id: uuid.UUID, session: Session = Depends(get_session)) -> ValidacionOut:
    return service.validar(session, servicio_id)


@router.get("/servicios/{servicio_id}/facturacion", response_model=FacturacionDetalleOut)
def obtener_facturacion(servicio_id: uuid.UUID, session: Session = Depends(get_session)) -> FacturacionDetalleOut:
    return service.construir_detalle_facturacion(session, servicio_id)


@router.patch("/servicios/{servicio_id}/facturacion", response_model=FacturacionDetalleOut)
def editar_facturacion(
    servicio_id: uuid.UUID, body: FacturacionUpdateIn, session: Session = Depends(get_session)
) -> FacturacionDetalleOut:
    return service.actualizar_facturacion(session, servicio_id, body)


@router.post("/servicios/{servicio_id}/facturar", status_code=204)
def facturar_servicio(
    servicio_id: uuid.UUID,
    body: FacturarIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> None:
    service.facturar(session, servicio_id, body, user)
