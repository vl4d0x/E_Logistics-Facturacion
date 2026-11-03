"""Facturar con el Excel de registros — solo admin."""
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import AppError
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.registro_excel import service
from app.modules.registro_excel.schemas import CrearDesdeFilaIn

router = APIRouter(prefix="/registro-excel", dependencies=[Depends(require_role(RolUsuario.admin))])

_MAX_BYTES = 20 * 1024 * 1024
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def obtener(session: Session = Depends(get_session)) -> dict:
    return {"registro": service.resumen(session, service.registro_vigente(session))}


@router.post("")
async def subir(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> dict:
    contenido = await file.read()
    if len(contenido) > _MAX_BYTES:
        raise AppError("validation_error", "El archivo pesa más de 20 MB", 422, details=[{"field": "file", "issue": "tamano"}])
    if not contenido.startswith(b"PK"):
        raise AppError("validation_error", "Sube el Excel en formato .xlsx", 422, details=[{"field": "file", "issue": "formato"}])
    return {"registro": service.subir(session, file.filename or "registros.xlsx", contenido, user)}


@router.get("/filas")
def listar_filas(
    pendientes: bool = Query(default=True),
    limite: int = Query(default=30, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": service.listar_filas(session, pendientes, limite)}


@router.get("/filas/{fila}")
def propuesta(
    fila: int, cliente_id: uuid.UUID | None = Query(default=None), session: Session = Depends(get_session)
) -> dict:
    return service.propuesta(session, fila, cliente_id)


@router.post("/filas/{fila}/servicio", status_code=201)
def crear_servicio(
    fila: int,
    body: CrearDesdeFilaIn,
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> dict:
    from app.modules.servicios.service import build_servicio_detalle

    servicio = service.crear_servicio(session, fila, body, user)
    return build_servicio_detalle(session, servicio).model_dump(mode="json")


@router.get("/descargar")
def descargar(session: Session = Depends(get_session)) -> Response:
    contenido, nombre, escritas = service.descargar(session)
    return Response(
        content=contenido,
        media_type=_XLSX,
        headers={
            "Content-Disposition": f"attachment; filename=\"{nombre}\"; filename*=UTF-8''{quote(nombre)}",
            "X-Facturas-Escritas": str(len(escritas)),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Facturas-Escritas",
        },
    )
