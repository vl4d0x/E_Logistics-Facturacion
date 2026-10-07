"""Dashboard (`03 §12`, `fase-6`): pendientes operativos, ingresos por periodo y por cobrar."""
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.modules.catalogos.models import Cliente, ModoAcuse
from app.modules.cobranza import service as cobranza
from app.modules.cobranza.models import EstadoPago, EstadoRep, Pago, Rep
from app.modules.facturacion import facturas as facturas_service
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.operacion.models import InspeccionSalida
from app.modules.servicios.models import (
    Acuse,
    EstadoFacturacion,
    EstadoServicio,
    EstadoViaje,
    Servicio,
    TipoViaje,
    Viaje,
)

_VIGENTES = (EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente)  # pendiente cuenta como vigente


def _stamp() -> str:
    return utcnow().isoformat()


def _money(v: Decimal) -> str:
    return f"{v:.2f}"


def pendientes(session: Session) -> dict[str, Any]:
    servicios = session.exec(
        select(Servicio).where(
            Servicio.estado != EstadoServicio.cancelado, Servicio.estado_facturacion == EstadoFacturacion.pendiente
        )
    ).all()
    por_facturar = [s for s in servicios if s.estado == EstadoServicio.terminado or s.timbrado_anticipado]
    anticipados = [s for s in por_facturar if s.timbrado_anticipado and s.estado != EstadoServicio.terminado]

    # Acuses faltantes: entregas terminadas de clientes que los exigen y todavía sin acuse (`00 §5.1`).
    faltantes = 0
    viajes = session.exec(
        select(Viaje, Servicio, Cliente)
        .join(Servicio, Viaje.servicio_id == Servicio.id)
        .join(Cliente, Servicio.cliente_id == Cliente.id)
        .where(
            Viaje.estado == EstadoViaje.terminado,
            Viaje.tipo.in_([TipoViaje.entrega, TipoViaje.recoleccion_entrega]),
            Servicio.estado != EstadoServicio.cancelado,
            Cliente.modo_acuse != ModoAcuse.ninguno,
        )
    ).all()
    for v, _s, c in viajes:
        acuses = session.exec(select(Acuse).where(Acuse.viaje_id == v.id)).all()
        ok = any(a.archivo_key for a in acuses) if c.modo_acuse == ModoAcuse.escaneo else any(a.referencia for a in acuses)
        faltantes += 0 if ok else 1

    fallas = len(session.exec(select(InspeccionSalida).where(InspeccionSalida.todo_ok == False)).all())

    pagos = [p for p in session.exec(select(Pago).where(Pago.estado == EstadoPago.aplicado)).all()]
    sin_rep = [p for p in pagos if cobranza._rep_vigente(session, p.id) is None]
    vence = None
    if sin_rep:
        from app.modules.cobranza.rep_payload import fecha_vencimiento_rep

        vence = min(fecha_vencimiento_rep(cobranza._local_naive(p.fecha_pago)) for p in sin_rep)
    return {
        "por_facturar": len(por_facturar),
        "por_facturar_anticipados": len(anticipados),
        "acuses_faltantes": faltantes,
        "inspecciones_con_fallas": fallas,
        "costos_pendientes": False,  # el tarifario de Chemital está en `configuracion`; sin fórmula que exigir
        "rep_por_emitir": {
            "pagos": len(sin_rep),
            "monto": _money(sum((p.monto for p in sin_rep), Decimal(0))),
            "vence": vence.isoformat() if vence else None,
        },
        "actualizado_at": _stamp(),
    }


def _vacio() -> dict[str, Decimal]:
    return {"facturado": Decimal(0), "cobrado": Decimal(0), "por_cobrar": Decimal(0)}


def _out(mes: str, d: dict[str, Decimal]) -> dict[str, str]:
    return {"mes": mes, **{k: _money(v) for k, v in d.items()}}


def ingresos(session: Session, anio: int, mes: int) -> dict[str, Any]:
    """Ingresos atribuidos al MES DE EMISIÓN; facturado = cobrado + por_cobrar (`03 §12`)."""
    por_mes: dict[str, dict[str, Decimal]] = defaultdict(_vacio)
    facturas = session.exec(select(Factura).where(Factura.estado.in_(_VIGENTES), Factura.fecha_emision.is_not(None))).all()
    for f in facturas:
        clave = f.fecha_emision.strftime("%Y-%m")
        por_mes[clave]["facturado"] += f.total
        por_mes[clave]["por_cobrar"] += f.saldo_insoluto
        por_mes[clave]["cobrado"] += f.total - f.saldo_insoluto

    def get(a: int, m: int) -> dict[str, str]:
        return _out(f"{a:04d}-{m:02d}", por_mes.get(f"{a:04d}-{m:02d}", _vacio()))

    previos = []
    a, m = anio, mes
    for _ in range(2):
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
        previos.append(get(a, m))
    totales = _vacio()
    meses = []
    for m_ in range(1, 13):
        fila = get(anio, m_)
        meses.append(fila)
        for k in totales:
            totales[k] += Decimal(fila[k])
    return {
        "periodo": get(anio, mes),
        "meses_previos": previos,
        "por_mes": meses,
        "totales_anio": {k: _money(v) for k, v in totales.items()},
        "actualizado_at": _stamp(),
    }


def por_cobrar(session: Session, anio: str | None, limit: int | None) -> dict[str, Any]:
    filas = cobranza.resumen_clientes(session, int(anio) if anio and anio.isdigit() else None)
    items = [
        {"cliente": f["cliente"], "saldo": f["saldo"], "facturas_abiertas": f["facturas_abiertas"]}
        for f in (filas[:limit] if limit else filas)
    ]
    return {"total_clientes": len(filas), "items": items, "actualizado_at": _stamp()}


def cancelaciones_en_espera(session: Session) -> dict[str, Any]:
    """Refresca el estatus de cada solicitud (con el throttle de 5 min) y las lista."""
    items: list[dict[str, Any]] = []
    for f in session.exec(select(Factura).where(Factura.estado == EstadoFactura.cancelacion_pendiente)).all():
        try:
            facturas_service.actualizar_estatus(session, f)
        except AppError:
            session.rollback()  # throttle, Facturama caído o sin configurar: se muestra como está
    for f in session.exec(select(Factura).where(Factura.estado == EstadoFactura.cancelacion_pendiente)).all():
        s = session.get(Servicio, f.servicio_id)
        c = session.get(Cliente, s.cliente_id)
        items.append(
            {
                "tipo": "factura", "id": f.id, "factura_id": f.id, "folio": f"{f.serie or ''}{f.folio or ''}",
                "cliente": c.nombre_comercial, "total": _money(f.total),
                "solicitada_at": f.cancelacion_solicitada_at,
            }
        )
    for r in session.exec(select(Rep).where(Rep.estado == EstadoRep.cancelacion_pendiente)).all():
        try:
            cobranza.actualizar_estatus_rep(session, r)
        except AppError:
            session.rollback()
    for r in session.exec(select(Rep).where(Rep.estado == EstadoRep.cancelacion_pendiente)).all():
        p = session.get(Pago, r.pago_id)
        c = session.get(Cliente, p.cliente_id)
        items.append(
            {
                "tipo": "rep", "id": r.id, "pago_id": p.id, "folio": f"{r.serie or ''}{r.folio or ''}",
                "cliente": c.nombre_comercial, "total": _money(p.monto), "solicitada_at": r.cancelacion_solicitada_at,
            }
        )
    return {"total": len(items), "items": items, "actualizado_at": _stamp()}


def ahora_local() -> datetime:
    return datetime.now(UTC)
