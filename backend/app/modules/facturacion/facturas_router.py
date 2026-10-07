"""Endpoints de facturas timbradas — `03-api-contract §9`. Solo admin."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.modules.auth.models import RolUsuario
from app.modules.facturacion import facturas as svc
from app.modules.facturacion.models import EstadoFactura

router = APIRouter(prefix="/facturas", dependencies=[Depends(require_role(RolUsuario.admin))])


class CancelarIn(BaseModel):
    motivo: str


class EnviarIn(BaseModel):
    to: list[str] | None = None


@router.get("")
def listar(
    estado: EstadoFactura | None = None,
    cliente_id: uuid.UUID | None = None,
    mes: str | None = Query(default=None, description="YYYY-MM de emisión"),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return svc.listar(session, estado, cliente_id, mes)


@router.get("/{factura_id}")
def obtener(factura_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    return svc.detalle(session, svc.get_factura(session, factura_id))


@router.get("/{factura_id}/descargar")
def descargar(factura_id: uuid.UUID, formato: str = "pdf", session: Session = Depends(get_session)) -> Response:
    factura = svc.get_factura(session, factura_id)
    contenido = svc.contenido_archivo(session, factura, formato)
    nombre = svc.nombre_archivo(session, factura, formato)
    return Response(
        contenido,
        media_type=svc._MIME[formato],
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/{factura_id}/reintentar-archivos")
def reintentar_archivos(factura_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    factura = svc.get_factura(session, factura_id)
    ok = svc.guardar_archivos(session, factura)
    return {"archivos_guardados": ok}


@router.post("/{factura_id}/enviar")
def enviar(factura_id: uuid.UUID, body: EnviarIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    factura = svc.enviar(session, svc.get_factura(session, factura_id), body.to)
    return svc.detalle(session, factura)


@router.post("/{factura_id}/cancelar")
def cancelar(factura_id: uuid.UUID, body: CancelarIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    factura = svc.cancelar(session, svc.get_factura(session, factura_id), body.motivo)
    return svc.detalle(session, factura)
