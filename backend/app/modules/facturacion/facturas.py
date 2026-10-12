"""Facturas ya timbradas: archivos, lista, descarga, correo y cancelación — `04 §8-9`, H4.7-H4.10."""
import base64
import html
import io
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.models import utcnow
from app.core.tiempo import MX
from app.integrations.facturama import FacturamaClient, FacturamaError
from app.modules.catalogos.models import Cliente, Lugar, ModoAcuse, Operador, Unidad
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.facturacion.validar import desglose_por_destino
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
    else:  # un intento de timbrado rechazado no es una factura: solo con el filtro "Error"
        stmt = stmt.where(Factura.estado != EstadoFactura.error)
    if cliente_id:
        stmt = stmt.where(Servicio.cliente_id == cliente_id)
    if mes:
        try:
            inicio = datetime.strptime(mes, "%Y-%m").replace(tzinfo=MX)  # el mes es de México
        except ValueError as exc:
            raise AppError("validation_error", "mes debe tener formato YYYY-MM", 422) from exc
        fin = inicio.replace(year=inicio.year + (inicio.month == 12), month=inicio.month % 12 + 1)
        inicio, fin = inicio.astimezone(UTC), fin.astimezone(UTC)
        stmt = stmt.where(Factura.fecha_emision >= inicio, Factura.fecha_emision < fin)
    filas = session.exec(stmt.order_by(Factura.created_at.desc())).all()
    return [_resumen(f, s, c) for f, s, c in filas]


def _resumen(f: Factura, s: Servicio, c: Cliente) -> dict:
    return {
        "id": f.id,
        "servicio_id": s.id,
        "servicio_numero": s.numero,
        "cliente_id": c.id,
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
    from app.modules.cobranza.models import PagoAplicacion

    if session.exec(select(PagoAplicacion).where(PagoAplicacion.factura_id == factura.id)).first():
        raise AppError(
            "factura_con_rep",
            "La factura tiene pagos aplicados: cancela su REP, revierte el pago y luego cancela la factura",
            409,
        )
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
    factura.cancelacion_solicitada_at = utcnow()
    _aplicar_estatus(session, factura, str(resultado.get("Status", "")), resultado.get("AcuseXmlBase64"))
    session.add(factura)
    session.commit()
    session.refresh(factura)
    return factura


def _aplicar_estatus(session: Session, factura: Factura, estatus: str, acuse_xml_b64: str | None = None) -> None:
    """Refleja el `Status` de Facturama (`canceled|pending|active`), `04 §8`."""
    estatus = estatus.lower()
    if estatus in {"canceled", "cancelled"}:
        _marcar_cancelada(session, factura)
        _guardar_acuse_cancelacion(factura, acuse_xml_b64)
    elif estatus == "active":
        # El receptor rechazó (o no procedió): la factura sigue vigente, se informa al admin.
        factura.estado = EstadoFactura.timbrada
        factura.cancelacion_solicitada_at = None
    else:  # "pending": el receptor tiene hasta 72 h para aceptar o rechazar
        factura.estado = EstadoFactura.cancelacion_pendiente


def _guardar_acuse_cancelacion(factura: Factura, acuse_xml_b64: str | None) -> None:
    """Acuse del SAT a R2. Nunca lanza: la cancelación ya ocurrió."""
    if not acuse_xml_b64:
        return
    try:
        from app.core import storage

        key = f"facturas/{factura.id}_acuse_cancelacion.xml"
        storage.subir_archivo(key, base64.b64decode(acuse_xml_b64), "application/xml")
        factura.acuse_cancelacion_key = key
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo guardar el acuse de cancelación de %s: %s", factura.id, exc)


_THROTTLE_ESTATUS = timedelta(minutes=5)


def actualizar_estatus(session: Session, factura: Factura) -> Factura:
    """Consulta a Facturama una cancelación en espera; con throttle de 5 min (`04 §8`)."""
    if factura.estado != EstadoFactura.cancelacion_pendiente:
        raise AppError("conflict", "Solo aplica a facturas con cancelación en espera", 409)
    consultada = factura.estatus_consultado_at
    if consultada is not None:
        consultada = consultada if consultada.tzinfo else consultada.replace(tzinfo=UTC)
        if utcnow() - consultada < _THROTTLE_ESTATUS:
            raise AppError("conflict", "Ya se consultó hace menos de 5 minutos; intenta más tarde", 409)
    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc
    try:
        cfdi = client.get_cfdi(factura.facturama_id)
    except FacturamaError as exc:
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()
    _aplicar_estatus(session, factura, str(cfdi.get("Status", "")))
    factura.estatus_consultado_at = utcnow()
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


# Texto general del correo (Parautos y cualquier cliente sin plantilla propia).
PLANTILLA_CORREO_DEFAULT = "Buen día, envío la factura #{folio}, correspondiente al día {dia} de {mes} del {anio}."
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


class _Marcadores(dict):
    """Un marcador desconocido ({algo}) se deja tal cual en vez de romper el correo."""

    def __missing__(self, clave: str) -> str:
        return "{" + clave + "}"


def texto_correo(plantilla: str | None, valores: dict[str, str]) -> str:
    return (plantilla or PLANTILLA_CORREO_DEFAULT).format_map(_Marcadores(valores))


def tabla_desglose_html(filas: list[tuple[str, Decimal]], subtotal: Decimal) -> str:
    celda = 'style="border:1px solid #ccc;padding:6px 10px"'
    derecha = 'style="border:1px solid #ccc;padding:6px 10px;text-align:right"'
    cuerpo = "".join(
        f"<tr><td {celda}>{html.escape(destino)}</td><td {derecha}>${monto:,.2f}</td></tr>" for destino, monto in filas
    )
    return (
        '<table style="border-collapse:collapse;margin-top:12px">'
        f"<thead><tr><th {celda}>Destino</th><th {celda}>Monto</th></tr></thead>"
        f"<tbody>{cuerpo}</tbody>"
        f"<tfoot><tr><th {celda}>Subtotal</th><th {derecha}>${subtotal:,.2f}</th></tr></tfoot>"
        "</table>"
    )


def _cuerpo_correo(session: Session, factura: Factura, servicio: Servicio, cliente: Cliente) -> str:
    """Texto de la plantilla del cliente + la tabla del desglose de precio (si está completo)."""
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)).all()
    nombre_lugar = {}
    for v in viajes:
        for lugar_id in (v.origen_lugar_id, v.destino_lugar_id):
            if lugar_id and lugar_id not in nombre_lugar and (lugar := session.get(Lugar, lugar_id)):
                nombre_lugar[lugar_id] = lugar.nombre
    operador = session.get(Operador, servicio.operador_id)
    unidad = session.get(Unidad, servicio.unidad_id)
    valores = {
        "folio": factura.folio or "",
        "dia": str(servicio.fecha.day),
        "mes": _MESES[servicio.fecha.month - 1],
        "anio": str(servicio.fecha.year),
        "operador": (operador.nombre if operador else "").upper(),
        "unidad": (unidad.apodo if unidad else "").upper(),
        "origen": " / ".join(nombre_lugar[v.origen_lugar_id] for v in viajes if v.origen_lugar_id in nombre_lugar).upper(),
        "destinos": " / ".join(
            nombre_lugar[v.destino_lugar_id] for v in viajes if v.destino_lugar_id in nombre_lugar
        ).upper(),
    }
    texto = texto_correo(cliente.plantilla_correo, valores)
    cuerpo = "<p>" + html.escape(texto).replace("\n", "<br>") + "</p>"

    desglose = desglose_por_destino(viajes, Decimal(factura.subtotal))
    if desglose and all(m is not None for _v, m in desglose):
        filas = [(nombre_lugar.get(v.destino_lugar_id, "—"), m) for v, m in desglose]
        cuerpo += tabla_desglose_html(filas, Decimal(factura.subtotal))
    return cuerpo


def enviar_correo(*, destinatarios: list[str], asunto: str, html: str, adjuntos: list[dict]) -> list[str]:
    """Envío por Resend con `reply_to` al buzón de Elogistics. Lanza `AppError` si falla.

    En modo prueba (`EMAIL_MODO_PRUEBA`) el correo NO sale a los destinatarios reales: va al
    correo de prueba, con "[PRUEBA]" en el asunto y un aviso de a quién iba dirigido.
    Devuelve los destinatarios a los que realmente se envió.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        raise AppError("internal_error", "El correo (Resend) no está configurado en este entorno.", 500)
    if not destinatarios:
        raise AppError("validation_error", "No hay destinatarios: el cliente no tiene correos de facturación", 422)
    if getattr(settings, "email_modo_prueba", False):
        prueba = getattr(settings, "email_prueba_destino", None) or settings.email_reply_to
        aviso = (
            '<p style="background:#fff3cd;padding:8px"><strong>MODO PRUEBA</strong> — este correo iba '
            f"dirigido a: {', '.join(destinatarios)}. No se envió al cliente.</p>"
        )
        html = aviso + html
        asunto = f"[PRUEBA] {asunto}"
        destinatarios = [prueba]
    import resend

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "reply_to": settings.email_reply_to,
                "to": destinatarios,
                "subject": asunto,
                "html": html,
                "attachments": adjuntos,
            }
        )
    except Exception as exc:
        raise AppError("internal_error", f"No se pudo enviar el correo: {exc}", 502) from exc
    return destinatarios



def nombre_evidencia(factura: Factura, cliente: Cliente) -> str:
    """`FACT #<folio Elogistics>-<CLIENTE>_EVIDENCIA.pdf` (sin caracteres que rompan un nombre de archivo)."""
    nombre = re.sub(r'[\/:*?"<>|]+', " ", (cliente.nombre_comercial or cliente.razon_social).upper()).strip()
    return f"FACT #{factura.folio or ''}-{nombre}_EVIDENCIA.pdf"


def unir_pdfs(contenidos: list[bytes]) -> bytes:
    """Une varios PDF en uno solo, en el orden recibido."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for contenido in contenidos:
        writer.append(io.BytesIO(contenido))
    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()


def _adjuntos_evidencia(
    session: Session, factura: Factura, servicio: Servicio, cliente: Cliente, acuses: list[Acuse]
) -> list[dict]:
    """Los acuses escaneados del servicio, en orden de viaje, unidos en UN solo PDF de evidencia.
    Acuses viejos que no son PDF (fotos) se adjuntan aparte, como antes."""
    from app.core import storage

    orden = {v.id: v.orden for v in session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id)).all()}
    pdfs: list[bytes] = []
    otros: list[dict] = []
    for a in sorted(acuses, key=lambda a: (orden.get(a.viaje_id, 0), a.pagina, a.subido_at)):
        if not a.archivo_key:
            continue
        contenido = storage.leer_archivo(a.archivo_key)
        if contenido.startswith(b"%PDF"):
            pdfs.append(contenido)
        else:
            ext = a.archivo_key.rsplit(".", 1)[-1]
            otros.append({"filename": f"acuse_{servicio.numero}_{len(otros) + 1}.{ext}", "content": list(contenido)})
    adjuntos: list[dict] = []
    if pdfs:
        evidencia = pdfs[0] if len(pdfs) == 1 else unir_pdfs(pdfs)
        adjuntos.append({"filename": nombre_evidencia(factura, cliente), "content": list(evidencia)})
    return adjuntos + otros


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
    if cliente.modo_acuse == ModoAcuse.escaneo:
        adjuntos.extend(_adjuntos_evidencia(session, factura, servicio, cliente, acuses))

    try:
        enviados = enviar_correo(
            destinatarios=destinatarios,
            asunto=f"Factura {factura.serie or ''}{factura.folio or ''} · Servicio #{servicio.numero} · Elogistics",
            html=_cuerpo_correo(session, factura, servicio, cliente),
            adjuntos=adjuntos,
        )
    except AppError as exc:
        factura.envio_error = exc.message
        session.add(factura)
        session.commit()
        raise

    factura.enviado_at = utcnow()
    factura.envio_destinatarios = enviados or destinatarios  # en modo prueba: el correo de prueba
    factura.envio_error = None
    session.add(factura)
    session.commit()
    session.refresh(factura)
    return factura
