"""Orquesta impuestos y validación — `04-facturacion-cfdi §3,§5`."""
import uuid
from decimal import Decimal

from sqlmodel import Session

from app.modules.catalogos.models import Cliente
from app.modules.facturacion.schemas import ImpuestosPreviewIn, MontosOut, ValidacionOut
from app.modules.facturacion.taxes import calcular_impuestos, subtotal_desde_total
from app.modules.facturacion.validar import validar_servicio
from app.modules.servicios.service import get_servicio


def preview_impuestos(body: ImpuestosPreviewIn) -> MontosOut:
    subtotal = body.subtotal
    if subtotal is None:
        subtotal = subtotal_desde_total(body.total, body.regimen_receptor)
    montos = calcular_impuestos(subtotal, body.regimen_receptor)
    return MontosOut(**montos._asdict())


def validar(session: Session, servicio_id: uuid.UUID) -> ValidacionOut:
    servicio = get_servicio(session, servicio_id)
    cliente = session.get(Cliente, servicio.cliente_id)
    checks = validar_servicio(session, servicio)
    ok = not any(c.nivel == "error" for c in checks)

    preview = None
    if servicio.subtotal and servicio.subtotal > Decimal(0):
        montos = calcular_impuestos(servicio.subtotal, cliente.regimen_receptor)
        preview = MontosOut(**montos._asdict())

    return ValidacionOut(ok=ok, checks=checks, preview=preview)
