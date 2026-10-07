"""Facturas ya timbradas: archivos, lista, descarga, correo y cancelación — `04 §8-9`, H4.7-H4.10."""
import base64
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.models import utcnow
from app.integrations.facturama import FacturamaClient, FacturamaError
from app.modules.catalogos.models import Cliente, Lugar, ModoAcuse
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.servicios.models import Acuse, EstadoFacturacion, Servicio, Viaje

log = logging.getLogger(__name__)

MOTIVOS_CANCELACION = {"02", "03", "04"}  # 01 (sustitución) queda en backlog, `04 §8`
_MIME = {"pdf": "application/pdf", "xml": "application/xml"}


def get_factura(session: Session, factura_id: uuid.UUID) -> Factura:
    factura = session.get(Factura, factura_id)
    if factura is None:
        raise AppError("not_found", "Factura no encontrada", 404)
    return factura


def nombre_archivo(session: Session, factura: Factura, formato: str) -> str:
    servicio = session.get(Servicio, factura.servicio_id)
    cliente = session.get(Cliente, servicio.cliente_id)
    return f"{factura.serie or ''}{factura.folio or ''}_{cliente.rfc}.{formato}"


# --- Archivos (PDF/XML) ------------------------------------------------------


def _descargar_de_facturama(factura: Factura, formato: str) -> bytes:
    if not factura.facturama_id:
        raise AppError("not_found", "La factura no tiene id de Facturama", 404)
    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        data = client.get_file(factura.facturama_id, formato)  # type: ignore[arg-type]
    except FacturamaError as exc:
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()
    return base64.b64decode(data["Content"])


def guardar_archivos(session: Session, factura: Factura) -> bool:
    """Copia PDF y XML a R2. Nunca lanza: si falla, la factura queda timbrada y se
    reintenta con `reintentar-archivos` (`fase-4 H4.7`)."""
    from app.core import storage

    try:
        for formato in ("xml", "pdf"):
            if getattr(factura, f"{formato}_key"):
                continue
            contenido = _descargar_de_facturama(factura, formato)
            key = f"facturas/{factura.id}.{formato}"
            storage.subir_archivo(key, contenido, _MIME[formato])
            setattr(factura, f"{formato}_key", key)
            session.add(factura)
            session.commit()
    except Exception as exc:  # noqa: BLE001 — R2/PAC caídos no deben tumbar un timbrado ya hecho
        session.rollback()
        log.warning("No se pudieron guardar los archivos de la factura %s: %s", factura.id, exc)
        return False
    return True


def contenido_archivo(session: Session, factura: Factura, formato: str) -> bytes:
    """R2 si ya está copiado; si no, directo de Facturama."""
    if formato not in _MIME:
        raise AppError("validation_error", "formato debe ser pdf o xml", 422)
    key = getattr(factura, f"{formato}_key")
    if key:
        from app.core import storage

        try:
            return storage.leer_archivo(key)
        except Exception:  # noqa: BLE001 — cae a Facturama
            log.warning("R2 no respondió para %s; usando Facturama", key)
    return _descargar_de_facturama(factura, formato)


# --- Lista y detalle ---------------------------------------------------------


def listar(
    session: Session,
    estado: EstadoFactura | None,
    cliente_id: uuid.UUID | None,
    mes: str | None,
) -> list[dict]:
    stmt = select(Factura, Servicio, Cliente).join(Servicio, Factura.servicio_id == Servicio.id).join(
        Cliente, Servicio.cliente_id == Cliente.id
    )
    if estado:
        stmt = stmt.where(Factura.estado == estado)
    if cliente_id:
        stmt = stmt.where(Servicio.cliente_id == cliente_id)
    if mes:
        try:
            inicio = datetime.strptime(mes, "%Y-%m").replace(tzinfo=UTC)
        except ValueError as exc:
            raise AppError("validation_error", "mes debe tener formato YYYY-MM", 422) from exc
        fin = inicio.replace(year=inicio.year + (inicio.month == 12), month=inicio.month % 12 + 1)
        stmt = stmt.where(Factura.fecha_emision >= inicio, Factura.fecha_emision < fin)
    filas = session.exec(stmt.order_by(Factura.created_at.desc())).all()
    return [_resumen(f, s, c) for f, s, c in filas]


def _resumen(f: Factura, s: Servicio, c: Cliente) -> dict:
    return {
        "id": f.id,
        "servicio_id": s.id,
        "servicio_numero": s.numero,
        "cliente_nombre": c.nombre_comercial,
        "estado": f.estado,
        "estado_cobro": f.estado_cobro,
        "serie": f.serie,
        "folio": f.folio,
        "uuid_fiscal": f.uuid_fiscal,
        "fecha_emision": f.fecha_emision,
        "subtotal": f.subtotal,
        "total": f.total,
        "saldo_insoluto": f.saldo_insoluto,
    }


def detalle(session: Session, factura: Factura) -> dict:
    s = session.get(Servicio, factura.servicio_id)
    c = session.get(Cliente, s.cliente_id)
    return {
        **_resumen(factura, s, c),
        "iva_trasladado": factura.iva_trasladado,
        "iva_retenido": factura.iva_retenido,
        "archivos_guardados": bool(factura.xml_key and factura.pdf_key),
        "error_detalle": factura.error_detalle,
        "motivo_cancelacion": factura.motivo_cancelacion,
        "cancelacion_solicitada_at": factura.cancelacion_solicitada_at,
        "cancelada_at": factura.cancelada_at,
        "enviado_at": factura.enviado_at,
        "envio_destinatarios": factura.envio_destinatarios,
        "envio_error": factura.envio_error,
        "emails_cliente": c.emails_facturacion,
        "ejercicio_anterior": bool(factura.fecha_emision and factura.fecha_emision.year < utcnow().year),
    }


# --- Cancelación -------------------------------------------------------------


def cancelar(session: Session, factura: Factura, motivo: str) -> Factura:
    if motivo not in MOTIVOS_CANCELACION:
        raise AppError("validation_error", "Motivo inválido: usa 02, 03 o 04", 422)
    if factura.estado != EstadoFactura.timbrada:
        raise AppError("conflict", "Solo se puede cancelar una factura timbrada", 409)
    # `409 factura_con_rep` (04 §8) se agrega en Fase 5, cuando existan los pagos aplicados.
    if not factura.facturama_id:
        raise AppError("conflict", "La factura no tiene id de Facturama", 409)
    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        resultado = client.cancel_cfdi(factura.facturama_id, motivo)
    except FacturamaError as exc:
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()

    factura.motivo_cancelacion = motivo
    estatus = str(resultado.get("Status", "")).lower()
    if estatus in {"canceled", "cancelled"}:
        _marcar_cancelada(session, factura)
    else:  # "pending": el receptor tiene 3 días hábiles para aceptar
        factura.estado = EstadoFactura.cancelacion_pendiente
        factura.cancelacion_solicitada_at = utcnow()
    session.add(factura)
    session.commit()
    session.refresh(factura)
    return factura


def _marcar_cancelada(session: Session, factura: Factura) -> None:
    factura.estado = EstadoFactura.cancelada
    factura.cancelada_at = utcnow()
    servicio = session.get(Servicio, factura.servicio_id)
    servicio.estado_facturacion = EstadoFacturacion.pendiente  # datos fiscales editables otra vez
    session.add(servicio)


# --- Correo ------------------------------------------------------------------


def _cuerpo_correo(session: Session, factura: Factura, servicio: Servicio, cliente: Cliente, folios: list[str]) -> str:
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)).all()
    ids = [v.destino_lugar_id for v in viajes if v.destino_lugar_id]
    destinos = [lugar.nombre for i in ids if (lugar := session.get(Lugar, i))]
    lineas = [
        f"Cliente: {cliente.nombre_comercial}",
        f"Servicio #{servicio.numero}",
        f"Destino(s): {', '.join(destinos) or '—'}",
        f"Total: ${Decimal(factura.total):,.2f}",
        f"UUID: {factura.uuid_fiscal}",
    ]
    if folios:
        lineas.append(f"Folio(s) de acuse: {', '.join(folios)}")
    return "<p>" + "<br>".join(lineas) + "</p>"


def enviar(session: Session, factura: Factura, para: list[str] | None) -> Factura:
    if factura.estado not in {EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente}:
        raise AppError("conflict", "Solo se envían facturas vigentes", 409)
    settings = get_settings()
    if not settings.resend_api_key:
        raise AppError("internal_error", "El correo (Resend) no está configurado en este entorno.", 500)

    servicio = session.get(Servicio, factura.servicio_id)
    cliente = session.get(Cliente, servicio.cliente_id)
    destinatarios = para or cliente.emails_facturacion
    if not destinatarios:
        raise AppError("validation_error", "No hay destinatarios: el cliente no tiene correos de facturación", 422)

    adjuntos = [
        {"filename": nombre_archivo(session, factura, f), "content": list(contenido_archivo(session, factura, f))}
        for f in ("xml", "pdf")
    ]
    viajes_ids = [v.id for v in session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id)).all()]
    acuses = session.exec(select(Acuse).where(Acuse.viaje_id.in_(viajes_ids))).all() if viajes_ids else []
    folios: list[str] = []
    if cliente.modo_acuse == ModoAcuse.escaneo:
        from app.core import storage

        for a in sorted(acuses, key=lambda a: (a.subido_at, a.pagina)):
            if a.archivo_key:
                ext = a.archivo_key.rsplit(".", 1)[-1]
                adjuntos.append(
                    {
                        "filename": f"acuse_{servicio.numero}_{a.pagina}.{ext}",
                        "content": list(storage.leer_archivo(a.archivo_key)),
                    }
                )
    elif cliente.modo_acuse == ModoAcuse.referencia:
        folios = [a.referencia for a in acuses if a.referencia]

    import resend

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "reply_to": settings.email_reply_to,
                "to": destinatarios,
                "subject": f"Factura {factura.serie or ''}{factura.folio or ''} · Servicio #{servicio.numero} · Elogistics",
                "html": _cuerpo_correo(session, factura, servicio, cliente, folios),
                "attachments": adjuntos,
            }
        )
    except Exception as exc:
        factura.envio_error = str(exc)
        session.add(factura)
        session.commit()
        raise AppError("internal_error", f"No se pudo enviar el correo: {exc}", 502) from exc

    factura.enviado_at = utcnow()
    factura.envio_destinatarios = destinatarios
    factura.envio_error = None
    session.add(factura)
    session.commit()
    session.refresh(factura)
    return factura
