"""`/dashboard/*` y `/export/*` — `03-api-contract §12`. Solo admin."""
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.models import utcnow
from app.modules.auth.models import RolUsuario
from app.modules.dashboard import exportar, service

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


@router.get("/dashboard/pendientes")
def pendientes(session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.pendientes(session)


@router.get("/dashboard/ingresos")
def ingresos(anio: int | None = None, mes: int | None = None, session: Session = Depends(get_session)) -> dict[str, Any]:
    hoy = utcnow()
    return service.ingresos(session, anio or hoy.year, mes or hoy.month)


@router.get("/dashboard/por-cobrar")
def por_cobrar(anio: str | None = None, limit: int | None = None, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.por_cobrar(session, anio, limit)


@router.get("/dashboard/cancelaciones-en-espera")
def cancelaciones(session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.cancelaciones_en_espera(session)


@router.get("/export/servicios.xlsx")
def export_servicios(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cliente_id: uuid.UUID | None = None,
    session: Session = Depends(get_session),
) -> Response:
    contenido = exportar.servicios_xlsx(session, fecha_desde, fecha_hasta, cliente_id)
    return Response(
        contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="servicios.xlsx"'},
    )
