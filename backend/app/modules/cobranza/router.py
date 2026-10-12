"""Endpoints de cobranza y REP — `03-api-contract §11`. Solo admin."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import AppError
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.cobranza import service
from app.modules.cobranza.models import EstadoPago
from app.modules.facturacion.models import EstadoCobro

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


class AplicacionIn(BaseModel):
    factura_id: uuid.UUID
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SugerenciasIn(BaseModel):
    cliente_id: uuid.UUID
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PagoIn(BaseModel):
    cliente_id: uuid.UUID
    fecha_pago: datetime
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    forma_pago: str = Field(default="03", min_length=2, max_length=2)
    num_operacion: str | None = None
    rfc_emisor_cta_ord: str | None = None
    cta_ordenante: str | None = None
    rfc_emisor_cta_ben: str | None = None
    cta_beneficiario: str | None = None
    notas: str | None = None
    aplicaciones: list[AplicacionIn] | None = None
    emitir_rep: bool = False


class AplicarIn(BaseModel):
    aplicaciones: list[AplicacionIn]


class EnviarIn(BaseModel):
    to: list[str] | None = None


class CancelarRepIn(BaseModel):
    motivo: str
    uuid_sustitucion: str | None = None


@router.get("/cobranza/clientes")
def cobranza_clientes(
    anio: str | None = Query(default=None, description="YYYY o 'todos'"), session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    return service.resumen_clientes(session, int(anio) if anio and anio.isdigit() else None)


@router.get("/cobranza/facturas")
def cobranza_facturas(
    cliente_id: uuid.UUID | None = None,
    estado_cobro: Annotated[str | None, Query(description="coma-separado: pendiente,parcial,pagada")] = None,
    mes_emision: str | None = None,
    anio: int | None = None,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    estados = [EstadoCobro(e) for e in estado_cobro.split(",") if e] if estado_cobro else []
    return service.listar_facturas(session, cliente_id, estados, mes_emision, anio)


@router.post("/cobranza/sugerencias")
def cobranza_sugerencias(body: SugerenciasIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.sugerencias(session, body.cliente_id, body.monto)


@router.post("/pagos", status_code=201)
def crear_pago(
    body: PagoIn, session: Session = Depends(get_session), user: Usuario = Depends(require_role(RolUsuario.admin))
) -> dict[str, Any]:
    datos = body.model_dump(exclude={"aplicaciones", "emitir_rep"})
    pago = service.registrar(session, datos, user)
    rep = None
    rep_error = None
    if body.aplicaciones:
        service.aplicar(session, pago, [(a.factura_id, a.monto) for a in body.aplicaciones])
        if body.emitir_rep:
            # El pago ya quedó registrado y aplicado: si el PAC falla no se responde error (el
            # admin creería que no se guardó y lo capturaría otra vez); se avisa y se reintenta
            # el REP desde "Pagos y REP".
            try:
                rep = service.emitir_rep(session, pago)
            except AppError as exc:
                session.rollback()
                rep_error = exc.message
    salida = service.pago_out(session, pago, detalle=True)
    if rep:
        salida["rep"] = service.rep_out(rep)
    if rep_error:
        salida["rep_error"] = rep_error
    return salida


@router.post("/pagos/{pago_id}/comprobante")
def subir_comprobante(
    pago_id: uuid.UUID, file: UploadFile = File(...), session: Session = Depends(get_session)
) -> dict[str, Any]:
    pago = service.get_pago(session, pago_id)
    service.subir_comprobante(session, pago, file.filename or "comprobante", file.file.read(), file.content_type or "application/octet-stream")
    return service.pago_out(session, pago, detalle=True)


@router.get("/pagos")
def listar_pagos(
    cliente_id: uuid.UUID | None = None,
    estado: EstadoPago | None = None,
    rep_pendiente: bool | None = None,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return service.listar_pagos(session, cliente_id, estado, rep_pendiente)


@router.get("/pagos/{pago_id}")
def obtener_pago(pago_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.pago_out(session, service.get_pago(session, pago_id), detalle=True)


@router.post("/pagos/{pago_id}/aplicar")
def aplicar_pago(pago_id: uuid.UUID, body: AplicarIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    pago = service.aplicar(session, service.get_pago(session, pago_id), [(a.factura_id, a.monto) for a in body.aplicaciones])
    return service.pago_out(session, pago, detalle=True)


@router.post("/pagos/{pago_id}/revertir")
def revertir_pago(pago_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.pago_out(session, service.revertir(session, service.get_pago(session, pago_id)), detalle=True)


@router.post("/pagos/{pago_id}/rep")
def emitir_rep(pago_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    rep = service.emitir_rep(session, service.get_pago(session, pago_id))
    return {"rep": service.rep_out(rep)}


@router.get("/reps/{rep_id}")
def obtener_rep(rep_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.rep_out(service.get_rep(session, rep_id))


@router.post("/reps/{rep_id}/enviar")
def enviar_rep(rep_id: uuid.UUID, body: EnviarIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.rep_out(service.enviar_rep(session, service.get_rep(session, rep_id), body.to))


@router.post("/reps/{rep_id}/cancelar")
def cancelar_rep(rep_id: uuid.UUID, body: CancelarRepIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.rep_out(service.cancelar_rep(session, service.get_rep(session, rep_id), body.motivo, body.uuid_sustitucion))


@router.post("/reps/{rep_id}/actualizar-estatus")
def actualizar_estatus_rep(rep_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.rep_out(service.actualizar_estatus_rep(session, service.get_rep(session, rep_id)))
