"""REF repetida y servicios de días cercanos (3 nov 2026, pedido de Vlad para Chemital).

Errores comunes al capturar: poner una REF que ya se usó en otro servicio del mismo cliente, o
confundir REFs de servicios de días cercanos. Aquí solo se avisa (warning), no se bloquea.
"""
import uuid
from datetime import date, timedelta

from sqlmodel import Session, select

from app.modules.catalogos.models import Lugar
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.servicios.models import Acuse, EstadoServicio, Servicio, TipoAcuse, Viaje

DIAS_CERCANOS = 3
_VIGENTES = (EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente)


def normalizar_ref(ref: object) -> str:
    """"05151 " = "5151": sin espacios, en mayúsculas y sin ceros a la izquierda."""
    s = "".join(str(ref or "").split()).upper()
    return s.lstrip("0") or s


def _factura_folio(session: Session, servicio_id: uuid.UUID) -> str | None:
    f = session.exec(
        select(Factura).where(Factura.servicio_id == servicio_id, Factura.estado.in_(_VIGENTES))
    ).first()
    return f.folio if f else None


def refs_repetidas(
    session: Session,
    cliente_id: uuid.UUID,
    refs: list[str],
    excluir_servicio_id: uuid.UUID | None = None,
    excluir_viaje_id: uuid.UUID | None = None,
) -> dict[str, list[dict]]:
    """{ref normalizada: [servicios del cliente donde ya aparece]} solo para las que se repiten.
    No cuenta servicios cancelados ni el propio servicio/viaje."""
    buscadas = {normalizar_ref(r) for r in refs if normalizar_ref(r)}
    if not buscadas:
        return {}
    filas = session.exec(
        select(Acuse.referencia, Viaje, Servicio)
        .join(Viaje, Acuse.viaje_id == Viaje.id)
        .join(Servicio, Viaje.servicio_id == Servicio.id)
        .where(
            Servicio.cliente_id == cliente_id,
            Servicio.estado != EstadoServicio.cancelado,
            Acuse.tipo == TipoAcuse.referencia,
            Acuse.referencia.is_not(None),
        )
    ).all()
    encontrados: dict[str, dict[uuid.UUID, dict]] = {}

    def _agregar(ref: str, servicio: Servicio, viaje: Viaje | None) -> None:
        if excluir_servicio_id is not None and servicio.id == excluir_servicio_id:
            return
        if excluir_viaje_id is not None and viaje is not None and viaje.id == excluir_viaje_id:
            return
        por_servicio = encontrados.setdefault(ref, {})
        item = por_servicio.setdefault(
            servicio.id,
            {"servicio_id": servicio.id, "numero": servicio.numero, "fecha": servicio.fecha, "destinos": []},
        )
        if viaje is not None and viaje.destino_lugar_id:
            lugar = session.get(Lugar, viaje.destino_lugar_id)
            if lugar is not None and lugar.nombre not in item["destinos"]:
                item["destinos"].append(lugar.nombre)

    for referencia, viaje, servicio in filas:
        n = normalizar_ref(referencia)
        if n in buscadas:
            _agregar(n, servicio, viaje)
    # Servicios viejos: el folio vivía en `servicio.folio_cliente`.
    for servicio in session.exec(
        select(Servicio).where(
            Servicio.cliente_id == cliente_id,
            Servicio.estado != EstadoServicio.cancelado,
            Servicio.folio_cliente.is_not(None),
        )
    ).all():
        n = normalizar_ref(servicio.folio_cliente)
        if n in buscadas:
            _agregar(n, servicio, None)

    res: dict[str, list[dict]] = {}
    for ref, por_servicio in encontrados.items():
        items = sorted(por_servicio.values(), key=lambda x: x["fecha"], reverse=True)
        for it in items:
            it["factura_folio"] = _factura_folio(session, it["servicio_id"])
        res[ref] = items
    return res


def texto_repetida(ref: str, items: list[dict]) -> str:
    otros = ", ".join(f"#{i['numero']} del {i['fecha'].strftime('%d/%m/%Y')}" for i in items[:3])
    return f"La REF {ref} ya está en el servicio {otros}"


def servicios_cercanos(
    session: Session,
    cliente_id: uuid.UUID,
    fecha: date,
    excluir_servicio_id: uuid.UUID | None = None,
    dias: int = DIAS_CERCANOS,
) -> list[dict]:
    """Servicios del mismo cliente a ±`dias` de la fecha, con sus destinos y REFs."""
    servicios = session.exec(
        select(Servicio)
        .where(
            Servicio.cliente_id == cliente_id,
            Servicio.estado != EstadoServicio.cancelado,
            Servicio.fecha >= fecha - timedelta(days=dias),
            Servicio.fecha <= fecha + timedelta(days=dias),
        )
        .order_by(Servicio.fecha.desc(), Servicio.numero.desc())
    ).all()
    res = []
    for s in servicios:
        if excluir_servicio_id is not None and s.id == excluir_servicio_id:
            continue
        viajes = session.exec(select(Viaje).where(Viaje.servicio_id == s.id).order_by(Viaje.orden)).all()
        destinos, refs = [], []
        for v in viajes:
            if v.destino_lugar_id:
                lugar = session.get(Lugar, v.destino_lugar_id)
                if lugar is not None:
                    destinos.append(lugar.nombre)
            for a in session.exec(
                select(Acuse).where(Acuse.viaje_id == v.id, Acuse.tipo == TipoAcuse.referencia)
            ).all():
                if a.referencia:
                    refs.append(a.referencia)
        if not refs and s.folio_cliente:
            refs.append(s.folio_cliente)
        res.append({
            "servicio_id": s.id,
            "numero": s.numero,
            "fecha": s.fecha,
            "dias": (s.fecha - fecha).days,
            "destinos": destinos,
            "refs": refs,
            "factura_folio": _factura_folio(session, s.id),
        })
    return res
