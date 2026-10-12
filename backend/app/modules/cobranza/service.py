"""Cobranza: registrar/aplicar/revertir pagos y emitir/enviar/cancelar el REP — `06-cobranza-rep`."""
import base64
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.models import utcnow
from app.core.tiempo import a_hora_mx
from app.integrations.facturama import FacturamaClient, FacturamaError
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, Lugar, RegimenReceptor
from app.modules.cobranza.conciliacion import Candidato, FacturaAbierta, conciliar
from app.modules.cobranza.models import EstadoPago, EstadoRep, Pago, PagoAplicacion, Rep
from app.modules.cobranza.rep_payload import (
    DocumentoRelacionado,
    ImpuestosParcialidad,
    construir_payload_rep,
    fecha_vencimiento_rep,
    impuestos_proporcionales,
)
from app.modules.configuracion.service import get_valor
from app.modules.facturacion.models import EstadoCobro, EstadoFactura, Factura
from app.modules.servicios.models import Servicio, Viaje

log = logging.getLogger(__name__)
_MX = ZoneInfo("America/Mexico_City")
_CENTAVO = Decimal("0.01")


def money(valor: Decimal | None) -> str | None:
    return None if valor is None else f"{Decimal(valor):.2f}"


def _cents(valor: Decimal) -> int:
    return int((Decimal(valor) / _CENTAVO).to_integral_value())


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _local_naive(dt: datetime) -> datetime:
    """Hora local de México sin zona, como la espera el REP (`Date`)."""
    return _aware(dt).astimezone(_MX).replace(tzinfo=None, microsecond=0)


# --- Lecturas ---------------------------------------------------------------


def get_pago(session: Session, pago_id: uuid.UUID) -> Pago:
    pago = session.get(Pago, pago_id)
    if pago is None:
        raise AppError("not_found", "Pago no encontrado", 404)
    return pago


def get_rep(session: Session, rep_id: uuid.UUID) -> Rep:
    rep = session.get(Rep, rep_id)
    if rep is None:
        raise AppError("not_found", "REP no encontrado", 404)
    return rep


def _rep_vigente(session: Session, pago_id: uuid.UUID) -> Rep | None:
    return session.exec(
        select(Rep).where(
            Rep.pago_id == pago_id, Rep.estado.in_([EstadoRep.timbrado, EstadoRep.cancelacion_pendiente])
        )
    ).first()


def _ruta_resumen(session: Session, servicio: Servicio) -> str:
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)).all()

    def nombre(lugar_id: uuid.UUID | None) -> str | None:
        lugar = session.get(Lugar, lugar_id) if lugar_id else None
        return lugar.nombre if lugar else None

    origen = next((n for v in viajes if (n := nombre(v.origen_lugar_id))), None)
    destinos = [n for v in viajes if (n := nombre(v.destino_lugar_id))]
    return f"{origen or '—'} → {', '.join(destinos) or '—'}"


def _factura_detalle(session: Session, f: Factura) -> dict[str, Any]:
    s = session.get(Servicio, f.servicio_id)
    return {
        "factura_id": f.id,
        "folio": f"{f.serie or ''}{f.folio or ''}",
        "fecha_emision": a_hora_mx(f.fecha_emision).date().isoformat() if f.fecha_emision else None,
        "total": money(f.total),
        "saldo": money(f.saldo_insoluto),
        "servicio": {
            "id": s.id,
            "numero": s.numero,
            "fecha": s.fecha.isoformat() if getattr(s, "fecha", None) else None,
            "ruta_resumen": _ruta_resumen(session, s),
        },
    }


def facturas_abiertas(session: Session, cliente_id: uuid.UUID) -> list[Factura]:
    return list(
        session.exec(
            select(Factura)
            .join(Servicio, Factura.servicio_id == Servicio.id)
            .where(
                Servicio.cliente_id == cliente_id,
                Factura.estado == EstadoFactura.timbrada,
                Factura.metodo_pago == "PPD",
                Factura.saldo_insoluto > 0,
            )
        ).all()
    )


def _candidato_out(session: Session, c: Candidato, por_id: dict[str, Factura]) -> dict[str, Any]:
    return {
        "factura_ids": c.factura_ids,
        "facturas": [_factura_detalle(session, por_id[i]) for i in c.factura_ids],
        "aplicaciones": [{"factura_id": i, "monto": f"{m / 100:.2f}"} for i, m in c.aplicaciones],
        "suma": f"{c.suma_cents / 100:.2f}",
        "etiquetas": c.etiquetas,
        "explicacion": c.explicacion,
        "diferencia": f"{c.diferencia_cents / 100:.2f}" if c.diferencia_cents else None,
        "factura_parcial_id": c.factura_parcial_id,
    }


def sugerencias(session: Session, cliente_id: uuid.UUID, monto: Decimal) -> dict[str, Any]:
    abiertas = facturas_abiertas(session, cliente_id)
    por_id = {str(f.id): f for f in abiertas}
    resultado = conciliar(
        [
            FacturaAbierta(str(f.id), f"{f.serie or ''}{f.folio or ''}", a_hora_mx(f.fecha_emision or utcnow()).date(), _cents(f.saldo_insoluto))
            for f in abiertas
        ],
        _cents(monto),
        tolerancia_cents=_cents(Decimal(str(get_valor(session, "conciliacion.tolerancia") or "1.00"))),
        max_facturas=int(get_valor(session, "conciliacion.max_facturas_busqueda") or 60),
        tiempo_max_ms=int(get_valor(session, "conciliacion.tiempo_max_ms") or 1500),
    )
    return {
        "objetivo": money(monto),
        "saldo_total_cliente": f"{resultado.saldo_total_cents / 100:.2f}",
        "exactas": [_candidato_out(session, c, por_id) for c in resultado.exactas],
        "total_exactas": len(resultado.exactas),
        "ambigua": resultado.ambigua,
        "nota_montos_iguales": resultado.nota_montos_iguales,
        "aproximadas": [_candidato_out(session, c, por_id) for c in resultado.aproximadas],
        "fifo_parcial": _candidato_out(session, resultado.fifo_parcial, por_id) if resultado.fifo_parcial else None,
        "excede_saldo": f"{resultado.excede_saldo_cents / 100:.2f}" if resultado.excede_saldo_cents else None,
        "busqueda_completa": resultado.busqueda_completa,
        "facturas_consideradas": resultado.facturas_consideradas,
    }


def _vencida(f: Factura, dias_credito: int) -> tuple[int, bool]:
    emitida = _aware(f.fecha_emision) if f.fecha_emision else utcnow()
    dias = (utcnow() - emitida).days
    return dias, dias > dias_credito


def resumen_clientes(session: Session, anio: int | None) -> list[dict[str, Any]]:
    filas: dict[uuid.UUID, dict[str, Any]] = {}
    stmt = (
        select(Factura, Servicio, Cliente)
        .join(Servicio, Factura.servicio_id == Servicio.id)
        .join(Cliente, Servicio.cliente_id == Cliente.id)
        .where(Factura.estado == EstadoFactura.timbrada, Factura.saldo_insoluto > 0)
    )
    for f, _s, c in session.exec(stmt).all():
        if anio and f.fecha_emision and a_hora_mx(f.fecha_emision).year != anio:
            continue
        fila = filas.setdefault(
            c.id,
            {
                "cliente": {"id": c.id, "nombre_comercial": c.nombre_comercial},
                "saldo": Decimal(0),
                "facturas_abiertas": 0,
                "saldo_vencido": Decimal(0),
                "factura_mas_antigua": None,
            },
        )
        fila["saldo"] += f.saldo_insoluto
        fila["facturas_abiertas"] += 1
        if _vencida(f, c.dias_credito)[1]:
            fila["saldo_vencido"] += f.saldo_insoluto
        if f.fecha_emision:
            dia = a_hora_mx(f.fecha_emision).date().isoformat()
            if fila["factura_mas_antigua"] is None or dia < fila["factura_mas_antigua"]:
                fila["factura_mas_antigua"] = dia
    for fila in filas.values():
        fila["saldo"], fila["saldo_vencido"] = money(fila["saldo"]), money(fila["saldo_vencido"])
    return sorted(filas.values(), key=lambda r: Decimal(r["saldo"]), reverse=True)


def listar_facturas(
    session: Session, cliente_id: uuid.UUID | None, estados: list[EstadoCobro], mes_emision: str | None, anio: int | None
) -> list[dict[str, Any]]:
    stmt = (
        select(Factura, Servicio, Cliente)
        .join(Servicio, Factura.servicio_id == Servicio.id)
        .join(Cliente, Servicio.cliente_id == Cliente.id)
        .where(Factura.estado == EstadoFactura.timbrada)
    )
    if cliente_id:
        stmt = stmt.where(Servicio.cliente_id == cliente_id)
    if estados:
        stmt = stmt.where(Factura.estado_cobro.in_(estados))
    filas = []
    for f, s, c in session.exec(stmt.order_by(Factura.fecha_emision)).all():
        if mes_emision and (not f.fecha_emision or a_hora_mx(f.fecha_emision).strftime("%Y-%m") != mes_emision):
            continue
        if anio and (not f.fecha_emision or a_hora_mx(f.fecha_emision).year != anio):
            continue
        dias, vencida = _vencida(f, c.dias_credito)
        filas.append(
            {
                "id": f.id,
                "folio": f"{f.serie or ''}{f.folio or ''}",
                "uuid_fiscal": f.uuid_fiscal,
                "cliente_nombre": c.nombre_comercial,
                "fecha_emision": f.fecha_emision,
                "servicio": {"id": s.id, "numero": s.numero, "ruta_resumen": _ruta_resumen(session, s)},
                "total": money(f.total),
                "saldo_insoluto": money(f.saldo_insoluto),
                "estado_cobro": f.estado_cobro,
                "dias_transcurridos": dias,
                "vencida": vencida and f.saldo_insoluto > 0,
            }
        )
    return filas


# --- Aplicar / revertir -----------------------------------------------------


def _estado_cobro_de(f: Factura) -> EstadoCobro:
    if f.saldo_insoluto <= 0:
        return EstadoCobro.pagada
    return EstadoCobro.pendiente if f.saldo_insoluto == f.total else EstadoCobro.parcial


def aplicar(session: Session, pago: Pago, aplicaciones: list[tuple[uuid.UUID, Decimal]]) -> Pago:
    """`06 §2.3-2.4`: una transacción con lock; Σ aplicaciones = monto del pago, al centavo."""
    if pago.estado != EstadoPago.registrado:
        raise AppError("conflict", "El pago ya está aplicado", 409)
    if not aplicaciones:
        raise AppError("validation_error", "Selecciona al menos una factura", 422)
    ids = [fid for fid, _ in aplicaciones]
    if len(set(ids)) != len(ids):
        raise AppError("validation_error", "Una factura no puede repetirse en el mismo pago", 422)
    suma = sum((m for _, m in aplicaciones), Decimal(0))
    if suma != pago.monto:
        raise AppError(
            "aplicacion_no_cuadra",
            f"Lo aplicado (${suma:,.2f}) no coincide con el monto del pago (${pago.monto:,.2f})",
            422,
            details=[{"field": "aplicaciones", "issue": "aplicacion_no_cuadra"}],
        )
    cliente = session.get(Cliente, pago.cliente_id)
    moral = cliente.regimen_receptor == RegimenReceptor.moral

    facturas = {
        f.id: f
        for f in session.exec(select(Factura).where(Factura.id.in_(ids)).with_for_update()).all()  # lock
    }
    for fid, monto in aplicaciones:
        f = facturas.get(fid)
        if f is None:
            raise AppError("not_found", "Factura no encontrada", 404)
        servicio = session.get(Servicio, f.servicio_id)
        if servicio.cliente_id != pago.cliente_id:
            raise AppError("validation_error", "Las facturas deben ser del mismo cliente que el pago", 422)
        if f.estado != EstadoFactura.timbrada or f.metodo_pago != "PPD":
            raise AppError("conflict", "Solo se aplican pagos a facturas PPD vigentes", 409)
        if monto <= 0 or monto > f.saldo_insoluto:
            raise AppError(
                "conflict",
                f"El monto para la factura {f.serie}{f.folio} excede su saldo actual (${f.saldo_insoluto:,.2f})",
                409,
                details=[{"field": str(fid), "issue": "excede_saldo"}],
            )

    for fid, monto in aplicaciones:
        f = facturas[fid]
        previas = session.exec(select(PagoAplicacion).where(PagoAplicacion.factura_id == fid)).all()
        saldo_ant = f.saldo_insoluto
        saldo = saldo_ant - monto
        imp = impuestos_proporcionales(
            subtotal=f.subtotal,
            total=f.total,
            iva_trasladado=f.iva_trasladado,
            iva_retenido=f.iva_retenido,
            pagado=monto,
            saldo_insoluto=saldo,
            previas=[ImpuestosParcialidad(p.base, p.traslado, p.retencion) for p in previas],
            receptor_moral=moral,
        )
        session.add(
            PagoAplicacion(
                pago_id=pago.id,
                factura_id=fid,
                monto=monto,
                num_parcialidad=len(previas) + 1,
                saldo_anterior=saldo_ant,
                saldo_insoluto=saldo,
                base=imp.base,
                traslado=imp.traslado,
                retencion=imp.retencion,
            )
        )
        f.saldo_insoluto = saldo
        f.estado_cobro = _estado_cobro_de(f)
        session.add(f)
    pago.estado = EstadoPago.aplicado
    pago.aplicado_at = utcnow()
    session.add(pago)
    session.commit()
    session.refresh(pago)
    return pago


def revertir(session: Session, pago: Pago) -> Pago:
    """`06 §2.5`: solo sin REP vigente; restaura saldos."""
    if pago.estado == EstadoPago.registrado:
        raise AppError("conflict", "El pago no está aplicado", 409)
    if _rep_vigente(session, pago.id):
        raise AppError("factura_con_rep", "El pago tiene un REP vigente: cancélalo primero", 409)
    aplicaciones = session.exec(select(PagoAplicacion).where(PagoAplicacion.pago_id == pago.id)).all()
    for a in aplicaciones:
        posteriores = session.exec(
            select(PagoAplicacion).where(
                PagoAplicacion.factura_id == a.factura_id, PagoAplicacion.num_parcialidad > a.num_parcialidad
            )
        ).first()
        if posteriores:
            raise AppError(
                "conflict", "Hay pagos posteriores sobre la misma factura: revierte primero el más reciente", 409
            )
    for a in aplicaciones:
        f = session.get(Factura, a.factura_id)
        f.saldo_insoluto = f.saldo_insoluto + a.monto
        f.estado_cobro = _estado_cobro_de(f)
        session.add(f)
        session.delete(a)
    pago.estado = EstadoPago.registrado
    pago.aplicado_at = None
    session.add(pago)
    session.commit()
    session.refresh(pago)
    return pago


# --- Registrar pago -----------------------------------------------------------


def registrar(session: Session, datos: dict[str, Any], user: Usuario) -> Pago:
    cliente = session.get(Cliente, datos["cliente_id"])
    if cliente is None:
        raise AppError("not_found", "Cliente no encontrado", 404)
    pago = Pago(created_by=user.id, **datos)
    session.add(pago)
    session.commit()
    session.refresh(pago)
    return pago


def subir_comprobante(session: Session, pago: Pago, nombre: str, contenido: bytes, content_type: str) -> Pago:
    from app.core import storage

    key = storage.nueva_key(f"pagos/{pago.id}", nombre)
    storage.subir_archivo(key, contenido, content_type)
    pago.comprobante_key = key
    session.add(pago)
    session.commit()
    session.refresh(pago)
    return pago


# --- REP ----------------------------------------------------------------------


def _documentos(session: Session, pago: Pago) -> list[DocumentoRelacionado]:
    docs = []
    for a in session.exec(select(PagoAplicacion).where(PagoAplicacion.pago_id == pago.id)).all():
        f = session.get(Factura, a.factura_id)
        docs.append(
            DocumentoRelacionado(
                uuid=f.uuid_fiscal or "",
                serie=f.serie,
                folio=f.folio,
                num_parcialidad=a.num_parcialidad,
                saldo_anterior=a.saldo_anterior,
                pagado=a.monto,
                saldo_insoluto=a.saldo_insoluto,
                impuestos=ImpuestosParcialidad(a.base, a.traslado, a.retencion),
            )
        )
    return docs


def _guardar_archivos_rep(session: Session, rep: Rep) -> None:
    """PDF/XML a R2; nunca lanza (el REP ya está timbrado)."""
    try:
        from app.core import storage

        with FacturamaClient() as client:
            for formato, mime in (("xml", "application/xml"), ("pdf", "application/pdf")):
                contenido = base64.b64decode(client.get_file(rep.facturama_id, formato)["Content"])  # type: ignore[arg-type]
                key = f"reps/{rep.id}.{formato}"
                storage.subir_archivo(key, contenido, mime)
                setattr(rep, f"{formato}_key", key)
        session.add(rep)
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        log.warning("No se pudieron guardar los archivos del REP %s: %s", rep.id, exc)


def emitir_rep(session: Session, pago: Pago) -> Rep:
    """`06 §4-5`. Idempotente por pago: con REP vigente lo devuelve tal cual."""
    vigente = _rep_vigente(session, pago.id)
    if vigente:
        return vigente
    if pago.estado == EstadoPago.registrado:
        raise AppError("conflict", "Aplica el pago a sus facturas antes de emitir el REP", 409)
    settings = get_settings()
    if not (settings.facturama_user and settings.facturama_password):
        raise AppError("facturama_no_configurado", "Facturama no está configurado en este entorno.", 503)
    if not (settings.emisor_lugar_expedicion):
        raise AppError("facturama_no_configurado", "Falta EMISOR_LUGAR_EXPEDICION.", 503)

    cliente = session.get(Cliente, pago.cliente_id)
    payload = construir_payload_rep(
        serie=None,
        expedition_place=settings.emisor_lugar_expedicion,
        receptor={
            "razon_social": cliente.razon_social,
            "rfc": cliente.rfc,
            "cp_fiscal": cliente.cp_fiscal,
            "regimen_fiscal": cliente.regimen_fiscal,
        },
        pago={
            "fecha": _local_naive(pago.fecha_pago),
            "forma_pago": pago.forma_pago,
            "monto": pago.monto,
            "num_operacion": pago.num_operacion,
            "rfc_emisor_cta_ord": pago.rfc_emisor_cta_ord,
            "cta_ordenante": pago.cta_ordenante,
            "rfc_emisor_cta_ben": pago.rfc_emisor_cta_ben,
            "cta_beneficiario": pago.cta_beneficiario,
        },
        documentos=_documentos(session, pago),
    )
    rep = session.exec(select(Rep).where(Rep.pago_id == pago.id, Rep.estado == EstadoRep.error)).first() or Rep(
        pago_id=pago.id, estado=EstadoRep.error
    )
    rep.payload = payload
    session.add(rep)
    session.commit()

    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        resultado = client.create_cfdi(payload)
    except FacturamaError as exc:
        rep.error_detalle = str(exc)
        session.add(rep)
        session.commit()
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()

    rep.estado = EstadoRep.timbrado
    rep.uuid_fiscal = resultado.get("Complement", {}).get("TaxStamp", {}).get("Uuid")
    rep.serie = resultado.get("Serie")
    rep.folio = str(resultado["Folio"]) if resultado.get("Folio") is not None else None
    rep.facturama_id = resultado.get("Id")
    rep.fecha_emision = utcnow()
    rep.timbrado_at = utcnow()
    rep.error_detalle = None
    pago.estado = EstadoPago.rep_emitido
    session.add(rep)
    session.add(pago)
    session.commit()
    session.refresh(rep)
    _guardar_archivos_rep(session, rep)
    session.refresh(rep)
    return rep


def rep_out(rep: Rep) -> dict[str, Any]:
    from app.core.storage import url_firmada

    def url(key: str | None) -> str | None:
        try:
            return url_firmada(key) if key else None
        except AppError:
            return None

    return {
        "id": rep.id,
        "pago_id": rep.pago_id,
        "estado": rep.estado,
        "uuid_fiscal": rep.uuid_fiscal,
        "serie": rep.serie,
        "folio": rep.folio,
        "fecha_emision": rep.fecha_emision,
        "pdf_url": url(rep.pdf_key),
        "xml_url": url(rep.xml_key),
        "error_detalle": rep.error_detalle,
        "motivo_cancelacion": rep.motivo_cancelacion,
        "cancelacion_solicitada_at": rep.cancelacion_solicitada_at,
        "cancelado_at": rep.cancelado_at,
        "enviado_at": rep.enviado_at,
    }


def enviar_rep(session: Session, rep: Rep, para: list[str] | None) -> Rep:
    from app.modules.facturacion.facturas import enviar_correo

    if rep.estado not in {EstadoRep.timbrado, EstadoRep.cancelacion_pendiente}:
        raise AppError("conflict", "Solo se envían REP vigentes", 409)
    pago = session.get(Pago, rep.pago_id)
    cliente = session.get(Cliente, pago.cliente_id)
    nombre = f"{rep.serie or ''}{rep.folio or ''}_{cliente.rfc}"
    adjuntos = []
    for formato in ("xml", "pdf"):
        key = getattr(rep, f"{formato}_key")
        if key:
            from app.core import storage

            contenido = storage.leer_archivo(key)
        else:
            with FacturamaClient() as client:
                contenido = base64.b64decode(client.get_file(rep.facturama_id, formato)["Content"])  # type: ignore[arg-type]
        adjuntos.append({"filename": f"{nombre}.{formato}", "content": list(contenido)})
    fecha = _local_naive(pago.fecha_pago).strftime("%d/%m/%Y")
    enviar_correo(
        destinatarios=para or cliente.emails_facturacion,
        asunto=f"Complemento de pago {rep.serie or ''}{rep.folio or ''} · Pago del {fecha} · Elogistics",
        html=(
            f"<p>Cliente: {cliente.nombre_comercial}<br>Pago del {fecha} por ${pago.monto:,.2f}<br>"
            f"UUID: {rep.uuid_fiscal}</p>"
        ),
        adjuntos=adjuntos,
    )
    rep.enviado_at = utcnow()
    session.add(rep)
    session.commit()
    session.refresh(rep)
    return rep


def _aplicar_estatus_rep(session: Session, rep: Rep, estatus: str) -> None:
    estatus = estatus.lower()
    if estatus in {"canceled", "cancelled"}:
        rep.estado = EstadoRep.cancelado
        rep.cancelado_at = utcnow()
        pago = session.get(Pago, rep.pago_id)
        pago.estado = EstadoPago.aplicado  # los saldos no cambian (`06 §6`)
        session.add(pago)
    elif estatus == "active":
        rep.estado = EstadoRep.timbrado
        rep.cancelacion_solicitada_at = None
    else:
        rep.estado = EstadoRep.cancelacion_pendiente


def cancelar_rep(session: Session, rep: Rep, motivo: str, uuid_sustitucion: str | None) -> Rep:
    if motivo not in {"02", "03", "04"} and not (motivo == "01" and uuid_sustitucion):
        raise AppError("validation_error", "Motivo inválido", 422)
    if rep.estado != EstadoRep.timbrado or not rep.facturama_id:
        raise AppError("conflict", "Solo se cancela un REP timbrado", 409)
    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        resultado = client.cancel_cfdi(rep.facturama_id, motivo, uuid_sustitucion)
    except FacturamaError as exc:
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()
    rep.motivo_cancelacion = motivo
    rep.uuid_sustitucion = uuid_sustitucion
    rep.cancelacion_solicitada_at = utcnow()
    _aplicar_estatus_rep(session, rep, str(resultado.get("Status", "")))
    session.add(rep)
    session.commit()
    session.refresh(rep)
    return rep


def actualizar_estatus_rep(session: Session, rep: Rep) -> Rep:
    if rep.estado != EstadoRep.cancelacion_pendiente:
        raise AppError("conflict", "Solo aplica a un REP con cancelación en espera", 409)
    if rep.estatus_consultado_at and utcnow() - _aware(rep.estatus_consultado_at) < timedelta(minutes=5):
        raise AppError("conflict", "Ya se consultó hace menos de 5 minutos; intenta más tarde", 409)
    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        cfdi = client.get_cfdi(rep.facturama_id)
    except FacturamaError as exc:
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()
    _aplicar_estatus_rep(session, rep, str(cfdi.get("Status", "")))
    rep.estatus_consultado_at = utcnow()
    session.add(rep)
    session.commit()
    session.refresh(rep)
    return rep


# --- Detalle y listados de pagos -------------------------------------------------


def _folio(f: Factura) -> str:
    return f"{f.serie or ''}{f.folio or ''}"


def _acciones(pago: Pago, vigente: Rep | None) -> list[str]:
    if pago.estado == EstadoPago.registrado:
        return ["aplicar", "aplicar_y_generar_rep"]
    acciones = []
    if vigente is None:
        acciones += ["generar_rep", "revertir"]
    elif vigente.estado == EstadoRep.timbrado:
        acciones += ["enviar_rep", "cancelar_rep"]
    return acciones


def pago_out(session: Session, pago: Pago, detalle: bool = False) -> dict[str, Any]:
    cliente = session.get(Cliente, pago.cliente_id)
    vigente = _rep_vigente(session, pago.id)
    vence = fecha_vencimiento_rep(_local_naive(pago.fecha_pago))
    rep_pendiente = pago.estado == EstadoPago.aplicado and vigente is None
    salida: dict[str, Any] = {
        "id": pago.id,
        "cliente": {"id": cliente.id, "nombre_comercial": cliente.nombre_comercial},
        "fecha_pago": pago.fecha_pago,
        "monto": money(pago.monto),
        "forma_pago": pago.forma_pago,
        "num_operacion": pago.num_operacion,
        "estado": pago.estado,
        "notas": pago.notas,
        "vence_rep": vence.isoformat(),
        "rep_pendiente": rep_pendiente,
        "dias_para_vencer": (vence - _local_naive(utcnow()).date()).days if rep_pendiente else None,
        "rep_vigente": rep_out(vigente) if vigente else None,
        "acciones_permitidas": _acciones(pago, vigente),
    }
    if detalle:
        aplicaciones = session.exec(select(PagoAplicacion).where(PagoAplicacion.pago_id == pago.id)).all()
        salida["aplicaciones"] = [
            {
                "factura_id": a.factura_id,
                "folio": _folio(session.get(Factura, a.factura_id)),
                "monto": money(a.monto),
                "num_parcialidad": a.num_parcialidad,
                "saldo_anterior": money(a.saldo_anterior),
                "saldo_insoluto": money(a.saldo_insoluto),
            }
            for a in aplicaciones
        ]
        salida["reps"] = [rep_out(r) for r in session.exec(select(Rep).where(Rep.pago_id == pago.id)).all()]
        salida["rfc_emisor_cta_ord"] = pago.rfc_emisor_cta_ord
        salida["cta_ordenante"] = pago.cta_ordenante
        salida["rfc_emisor_cta_ben"] = pago.rfc_emisor_cta_ben
        salida["cta_beneficiario"] = pago.cta_beneficiario
        salida["tiene_comprobante"] = bool(pago.comprobante_key)
    return salida


def listar_pagos(
    session: Session, cliente_id: uuid.UUID | None, estado: EstadoPago | None, rep_pendiente: bool | None
) -> list[dict[str, Any]]:
    stmt = select(Pago)
    if cliente_id:
        stmt = stmt.where(Pago.cliente_id == cliente_id)
    if estado:
        stmt = stmt.where(Pago.estado == estado)
    salida = [pago_out(session, p) for p in session.exec(stmt.order_by(Pago.fecha_pago.desc())).all()]
    if rep_pendiente is not None:
        salida = [p for p in salida if p["rep_pendiente"] == rep_pendiente]
    # REP pendientes primero, los más urgentes arriba (`fase-5 H5.7`)
    salida.sort(key=lambda p: (not p["rep_pendiente"], p["vence_rep"] if p["rep_pendiente"] else ""))
    return salida
