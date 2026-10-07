"""Export de servicios a Excel — `fase-6 H6.7`. Columnas provisionales hasta que el contador pida otras."""
import io
import uuid
from datetime import date

from openpyxl import Workbook
from sqlmodel import Session, select

from app.modules.catalogos.models import Cliente, Lugar, Operador, Unidad
from app.modules.cobranza.models import Pago, PagoAplicacion, Rep
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.servicios.models import Servicio, Viaje

COLUMNAS = [
    "Fecha", "Servicio #", "Cliente", "Ruta", "Unidad", "Operador", "Km", "Subtotal", "IVA", "Retención", "Total",
    "Estado", "UUID", "Estado de cobro", "Saldo", "Fechas de pago", "UUID REP",
]


def _ruta(session: Session, viajes: list[Viaje]) -> str:
    def nombre(i: uuid.UUID | None) -> str | None:
        lugar = session.get(Lugar, i) if i else None
        return lugar.nombre if lugar else None

    origen = next((n for v in viajes if (n := nombre(v.origen_lugar_id))), "—")
    destinos = [n for v in viajes if (n := nombre(v.destino_lugar_id))]
    return f"{origen} → {', '.join(destinos) or '—'}"


def servicios_xlsx(
    session: Session, desde: date | None, hasta: date | None, cliente_id: uuid.UUID | None
) -> bytes:
    stmt = select(Servicio).order_by(Servicio.fecha, Servicio.numero)
    if desde:
        stmt = stmt.where(Servicio.fecha >= desde)
    if hasta:
        stmt = stmt.where(Servicio.fecha <= hasta)
    if cliente_id:
        stmt = stmt.where(Servicio.cliente_id == cliente_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Servicios"
    ws.append(COLUMNAS)
    for s in session.exec(stmt).all():
        cliente = session.get(Cliente, s.cliente_id)
        unidad = session.get(Unidad, s.unidad_id)
        operador = session.get(Operador, s.operador_id)
        viajes = session.exec(select(Viaje).where(Viaje.servicio_id == s.id).order_by(Viaje.orden)).all()
        km = sum((v.km_reportado or v.distancia_km or 0) for v in viajes)
        f = session.exec(
            select(Factura).where(
                Factura.servicio_id == s.id,
                Factura.estado.in_([EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente]),
            )
        ).first()
        pagos, reps = [], []
        if f:
            for a in session.exec(select(PagoAplicacion).where(PagoAplicacion.factura_id == f.id)).all():
                pago = session.get(Pago, a.pago_id)
                pagos.append(pago.fecha_pago.strftime("%Y-%m-%d"))
                reps += [r.uuid_fiscal for r in session.exec(select(Rep).where(Rep.pago_id == pago.id)).all() if r.uuid_fiscal]
        ws.append(
            [
                s.fecha, s.numero, cliente.nombre_comercial, _ruta(session, list(viajes)),
                unidad.apodo if unidad else None, operador.nombre if operador else None, km or None,
                float(f.subtotal) if f else (float(s.subtotal) if s.subtotal else None),
                float(f.iva_trasladado) if f else None, float(f.iva_retenido) if f else None,
                float(f.total) if f else None,
                s.estado.value, f.uuid_fiscal if f else None, f.estado_cobro.value if f else None,
                float(f.saldo_insoluto) if f else None, ", ".join(pagos) or None, ", ".join(reps) or None,
            ]
        )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
