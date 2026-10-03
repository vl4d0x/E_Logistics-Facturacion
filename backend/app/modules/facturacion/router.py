"""Endpoints de facturación — `03-api-contract §9`. Solo admin."""
import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.modules.auth.models import RolUsuario
from app.modules.facturacion import service
from app.modules.facturacion.schemas import ImpuestosPreviewIn, MontosOut, ValidacionOut

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


@router.post("/impuestos/preview", response_model=MontosOut)
def impuestos_preview(body: ImpuestosPreviewIn) -> MontosOut:
    return service.preview_impuestos(body)


@router.get("/servicios/{servicio_id}/validar", response_model=ValidacionOut)
def validar_servicio(servicio_id: uuid.UUID, session: Session = Depends(get_session)) -> ValidacionOut:
    return service.validar(session, servicio_id)
