"""Registro y consulta del historial de movimientos de los admins."""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.core.errors import AppError
from app.core.tiempo import MX
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.catalogos.models import Cliente
from app.modules.facturacion.models import Factura
from app.modules.historial.models import ETIQUETAS, Movimiento
from app.modules.servicios.models import Servicio

log = logging.getLogger(__name__)


def registrar(
    session: Session,
    usuario: Usuario,
    tipo: str,
    descripcion: str,
    *,
    servicio_id: uuid.UUID | None = None,
    factura_id: uuid.UUID | None = None,
) -> None:
    """Anota un movimiento YA realizado. Nunca rompe la acción: si falla el registro solo se loguea."""
    try:
        session.add(
            Movimiento(
                usuario_id=usuario.id,
                tipo=tipo,
                descripcion=descripcion,
                servicio_id=servicio_id,
                factura_id=factura_id,
            )
        )
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        log.exception("No se pudo registrar el movimiento %s", tipo)


def describir_servicio(session: Session, servicio_id: uuid.UUID) -> str:
    servicio = session.get(Servicio, servicio_id)
    if servicio is None:
        return "Servicio"
    cliente = session.get(Cliente, servicio.cliente_id)
    return f"Servicio #{servicio.numero} · {cliente.nombre_comercial if cliente else '—'}"


def describir_factura(session: Session, factura: Factura) -> str:
    cliente = session.get(Cliente, factura.cliente_id) if factura.cliente_id else None
    folio = f"{factura.serie or ''}{factura.folio or ''}" or "sin folio"
    texto = f"Factura {folio} · {cliente.nombre_comercial if cliente else '—'} · ${factura.total:,.2f}"
    if factura.servicio_id:
        servicio = session.get(Servicio, factura.servicio_id)
        if servicio:
            texto += f" (servicio #{servicio.numero})"
    return texto


def _inicio_dia_utc(texto: str, campo: str) -> datetime:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=MX).astimezone(UTC)
    except ValueError as exc:
        raise AppError("validation_error", f"{campo} debe tener formato YYYY-MM-DD", 422) from exc


def listar(
    session: Session,
    usuario_id: uuid.UUID | None,
    tipo: str | None,
    desde: str | None,
    hasta: str | None,
    page: int,
    size: int,
) -> tuple[list[dict], int]:
    cond = []
    if usuario_id:
        cond.append(Movimiento.usuario_id == usuario_id)
    if tipo:
        cond.append(Movimiento.tipo == tipo)
    if desde:  # días de México, ambos inclusivos
        cond.append(Movimiento.created_at >= _inicio_dia_utc(desde, "desde"))
    if hasta:
        cond.append(Movimiento.created_at < _inicio_dia_utc(hasta, "hasta") + timedelta(days=1))
    total = session.exec(select(func.count()).select_from(Movimiento).where(*cond)).one()
    filas = session.exec(
        select(Movimiento, Usuario)
        .join(Usuario, Movimiento.usuario_id == Usuario.id)
        .where(*cond)
        .order_by(Movimiento.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [
        {
            "id": m.id,
            "created_at": m.created_at,
            "usuario": {"id": u.id, "nombre": u.nombre},
            "tipo": m.tipo,
            "etiqueta": ETIQUETAS.get(m.tipo, m.tipo),
            "descripcion": m.descripcion,
            "servicio_id": m.servicio_id,
            "factura_id": m.factura_id,
        }
        for m, u in filas
    ]
    return items, total


def admins(session: Session) -> list[dict]:
    filas = session.exec(select(Usuario).where(Usuario.rol == RolUsuario.admin).order_by(Usuario.nombre)).all()
    return [{"id": u.id, "nombre": u.nombre} for u in filas]
