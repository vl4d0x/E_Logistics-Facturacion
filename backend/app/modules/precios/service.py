"""Capa delgada que arma el historial real para el sugeridor — `07-precio-sugerido §1`."""
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.core.models import utcnow
from app.modules.configuracion.service import get_valor
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.precios.sugeridor import PuntoHistorial, PuntoKm, Sugerencia, sugerir_precio
from app.modules.servicios.models import Servicio, Viaje


def _destinos_de(session: Session, servicio_id: uuid.UUID) -> frozenset[uuid.UUID]:
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio_id)).all()
    return frozenset(v.destino_lugar_id for v in viajes if v.destino_lugar_id)


def _km_de(session: Session, servicio_id: uuid.UUID) -> float | None:
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio_id)).all()
    con_destino = [v for v in viajes if v.destino_lugar_id]
    km = sum((v.distancia_km or 0) for v in con_destino)
    if km > 0:
        return km
    km_reportado = sum((v.km_reportado or 0) for v in con_destino)
    return km_reportado or None


def sugerir_para_servicio(session: Session, servicio: Servicio) -> Sugerencia:
    destinos = _destinos_de(session, servicio.id)
    km = _km_de(session, servicio.id)
    ventana_dias = get_valor(session, "precio.ventana_historial_dias") or 365
    corte = utcnow() - timedelta(days=ventana_dias)

    facturas_cliente = session.exec(
        select(Factura, Servicio)
        .join(Servicio, Factura.servicio_id == Servicio.id)
        .where(
            Servicio.cliente_id == servicio.cliente_id,
            Servicio.id != servicio.id,
            Factura.estado != EstadoFactura.cancelada,
            Factura.fecha_emision.is_not(None),
            Factura.fecha_emision >= corte,
        )
    ).all()

    historial_ruta: list[PuntoHistorial] = []
    historial_km: list[PuntoKm] = []
    for factura, s in facturas_cliente:
        s_destinos = _destinos_de(session, s.id)
        s_km = _km_de(session, s.id)
        if s_destinos == destinos and destinos:
            historial_ruta.append(
                PuntoHistorial(
                    servicio_numero=s.numero, fecha=factura.fecha_emision.date(), subtotal=factura.subtotal
                )
            )
        if s_km and s_km > 0:
            historial_km.append(PuntoKm(subtotal=factura.subtotal, km=s_km))

    historial_km = sorted(historial_km, key=lambda p: p.km, reverse=True)[:10]

    tarifa_base = get_valor(session, "precio.tarifa_base")
    tarifa_km = get_valor(session, "precio.tarifa_km")
    redondeo = get_valor(session, "precio.redondeo") or 50

    return sugerir_precio(
        n_destinos=len(destinos),
        km=km,
        historial_ruta=historial_ruta,
        historial_km_cliente=historial_km,
        tarifa_base=Decimal(str(tarifa_base)) if tarifa_base is not None else None,
        tarifa_km=Decimal(str(tarifa_km)) if tarifa_km is not None else None,
        redondeo=Decimal(str(redondeo)),
    )
