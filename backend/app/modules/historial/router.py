"""Historial de movimientos de los admins — solo admin."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.modules.auth.models import RolUsuario
from app.modules.historial import service
from app.modules.historial.models import ETIQUETAS

router = APIRouter(prefix="/historial", dependencies=[Depends(require_role(RolUsuario.admin))])


@router.get("")
def listar(
    usuario_id: uuid.UUID | None = None,
    tipo: str | None = Query(default=None),
    desde: str | None = None,
    hasta: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    items, total = service.listar(session, usuario_id, tipo, desde, hasta, page, size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/filtros")
def filtros(session: Session = Depends(get_session)) -> dict:
    return {
        "admins": service.admins(session),
        "tipos": [{"value": k, "label": v} for k, v in ETIQUETAS.items()],
    }
