"""Lógica de operación en campo — `fase-3`, `02 §3.11-3.13`."""
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import MercanciaFrecuente, Unidad
from app.modules.operacion.models import CargaCombustible, InspeccionSalida, ReporteCierre
from app.modules.operacion.schemas import (
    CerrarServicioIn,
    IniciarServicioIn,
    TerminarViajeOperadorIn,
)
from app.modules.operacion.validators import validar_lectura_medidor
from app.modules.servicios import service as servicios_service
from app.modules.servicios.models import EstadoServicio, EstadoViaje, Servicio, Viaje
from app.modules.servicios.schemas import AcuseOut, ServicioDetalleOut, ViajeMercanciaIn


def get_servicio_de_operador(session: Session, servicio_id: uuid.UUID, operador_id: uuid.UUID) -> Servicio:
    servicio = servicios_service.get_servicio(session, servicio_id)
    if servicio.operador_id != operador_id:
        raise AppError("forbidden", "Este servicio no es tuyo", 403)
    return servicio


def get_viaje_de_operador(session: Session, viaje_id: uuid.UUID, operador_id: uuid.UUID) -> Viaje:
    viaje = servicios_service.get_viaje(session, viaje_id)
    get_servicio_de_operador(session, viaje.servicio_id, operador_id)
    return viaje


# --- GET /operador/servicios --------------------------------------------------


def listar_servicios_operador(
    session: Session, operador_id: uuid.UUID, estados: list[str] | None, desde: date | None
) -> list[ServicioDetalleOut]:
    stmt = select(Servicio).where(Servicio.operador_id == operador_id)
    if estados:
        stmt = stmt.where(Servicio.estado.in_(estados))
    else:
        corte = desde or (datetime.now(UTC).date() - timedelta(days=7))
        stmt = stmt.where(
            (Servicio.estado != EstadoServicio.terminado) | (Servicio.fecha >= corte)
        )
    servicios = session.exec(stmt.order_by(Servicio.fecha.desc())).all()

    detalles = []
    for s in servicios:
        detalle = servicios_service.build_servicio_detalle(session, s)
        detalle = enriquecer_detalle_con_operacion(session, s.id, detalle)
        mercancias = session.exec(
            select(MercanciaFrecuente).where(
                MercanciaFrecuente.cliente_id == s.cliente_id, MercanciaFrecuente.activo == True
            )
        ).all()
        detalle.mercancias_cliente = [
            {
                "id": m.id,
                "nombre_humano": m.nombre_humano,
                "unidad_desc": m.unidad_desc,
                "peso_kg_sugerido": m.peso_kg_sugerido,
            }
            for m in mercancias
        ]
        detalles.append(detalle)
    return detalles


# --- Enriquecer con inspección/cierre/cargas (admin y operador) -------------


def enriquecer_detalle_con_operacion(
    session: Session, servicio_id: uuid.UUID, detalle: ServicioDetalleOut
) -> ServicioDetalleOut:
    inspeccion = session.exec(
        select(InspeccionSalida).where(InspeccionSalida.servicio_id == servicio_id)
    ).first()
    if inspeccion:
        detalle.inspeccion = {
            "todo_ok": inspeccion.todo_ok,
            "fallas": [
                campo
                for campo in (
                    "unidad_limpia",
                    "fumigacion_vigente",
                    "botiquin",
                    "casco_chaleco",
                    "aceite_ok",
                    "anticongelante_ok",
                    "neumaticos_ok",
                    "extintor_ok",
                )
                if not getattr(inspeccion, campo)
            ],
            "observaciones": inspeccion.observaciones,
            "nivel_combustible": inspeccion.nivel_combustible,
            "lectura_medidor": inspeccion.lectura_medidor,
            "odometro_km": inspeccion.odometro_km,
            "realizada_at": inspeccion.realizada_at,
        }

    cierre = session.exec(select(ReporteCierre).where(ReporteCierre.servicio_id == servicio_id)).first()
    if cierre:
        detalle.cierre = {
            "nivel_combustible": cierre.nivel_combustible,
            "lectura_medidor": cierre.lectura_medidor,
            "odometro_km": cierre.odometro_km,
            "cargo_combustible": cierre.cargo_combustible,
            "observaciones": cierre.observaciones,
            "cerrado_at": cierre.cerrado_at,
        }

    cargas = session.exec(
        select(CargaCombustible).where(CargaCombustible.servicio_id == servicio_id)
    ).all()
    if cargas:
        from app.core.storage import url_firmada

        def _ticket_url(key: str | None) -> str | None:
            if not key:
                return None
            try:
                return url_firmada(key)
            except AppError:
                return None

        detalle.cargas = [
            {
                "id": c.id,
                "litros": c.litros,
                "precio_litro": c.precio_litro,
                "importe": c.importe,
                "tipo_combustible": c.tipo_combustible,
                "ticket_url": _ticket_url(c.ticket_key),
                "cargada_at": c.cargada_at,
            }
            for c in cargas
        ]
        detalle.combustible_total = {
            "litros": sum((c.litros for c in cargas), Decimal(0)),
            "importe": sum((c.importe for c in cargas), Decimal(0)),
        }
    return detalle


# --- Inspección de salida -----------------------------------------------


def iniciar_servicio(
    session: Session, servicio_id: uuid.UUID, operador_id: uuid.UUID, data: IniciarServicioIn, current_user: Usuario
) -> ServicioDetalleOut:
    servicio = get_servicio_de_operador(session, servicio_id, operador_id)

    existente = session.exec(
        select(InspeccionSalida).where(InspeccionSalida.client_action_id == data.client_action_id)
    ).first()
    if existente is not None:
        return servicios_service.build_servicio_detalle(session, servicio)

    unidad = session.get(Unidad, servicio.unidad_id)
    nivel = validar_lectura_medidor(data.lectura_medidor, unidad)

    checklist = data.checklist.model_dump()
    inspeccion = InspeccionSalida(
        servicio_id=servicio.id,
        operador_id=operador_id,
        unidad_id=servicio.unidad_id,
        todo_ok=all(checklist.values()),
        observaciones=data.observaciones,
        nivel_combustible=nivel,
        lectura_medidor=data.lectura_medidor,
        odometro_km=data.odometro_km,
        realizada_at=data.realizada_at,
        registrada_por=current_user.id,
        client_action_id=data.client_action_id,
        **checklist,
    )
    session.add(inspeccion)

    if servicio.estado == EstadoServicio.programado:
        servicio.estado = EstadoServicio.en_curso
        servicio.iniciado_at = servicio.iniciado_at or utcnow()
        servicio.updated_at = utcnow()
        session.add(servicio)

    session.commit()
    return servicios_service.build_servicio_detalle(session, servicio)


# --- Terminar viaje / acuse ----------------------------------------------


def terminar_viaje_operador(
    session: Session,
    viaje_id: uuid.UUID,
    operador_id: uuid.UUID,
    data: TerminarViajeOperadorIn,
    current_user: Usuario,
):
    viaje = get_viaje_de_operador(session, viaje_id, operador_id)
    servicio = servicios_service.get_servicio(session, viaje.servicio_id)
    if servicio.estado == EstadoServicio.programado:
        raise AppError(
            "conflict",
            "El servicio todavía no se ha iniciado (falta la inspección de salida)",
            409,
            details=[{"field": "_", "issue": "servicio_no_iniciado"}],
        )

    mercancias: list[ViajeMercanciaIn] | None = data.mercancias or None
    if servicios_service.datos_fiscales_bloqueados(session, servicio):
        mercancias = None  # ya facturado: se conservan las mercancías capturadas

    from app.modules.servicios.schemas import TerminarViajeIn

    payload = TerminarViajeIn(
        mercancias=mercancias,
        hora_llegada=data.hora_llegada,
        notas_operador=data.notas,
        referencia_acuse=data.referencia_acuse,
        client_action_id=data.client_action_id,
    )
    return servicios_service.terminar_viaje(session, viaje_id, payload, current_user)


def agregar_acuse_operador_archivo(
    session: Session,
    viaje_id: uuid.UUID,
    operador_id: uuid.UUID,
    archivo_key: str,
    mime: str,
    pagina: int,
    client_action_id: uuid.UUID,
    current_user: Usuario,
) -> AcuseOut:
    get_viaje_de_operador(session, viaje_id, operador_id)

    from app.modules.servicios.models import Acuse

    existente = session.exec(select(Acuse).where(Acuse.client_action_id == client_action_id)).first()
    if existente is not None:
        return servicios_service.acuse_out(existente)

    acuse = Acuse(
        viaje_id=viaje_id,
        tipo="escaneo",
        archivo_key=archivo_key,
        mime=mime,
        pagina=pagina,
        subido_por=current_user.id,
        subido_at=utcnow(),
        client_action_id=client_action_id,
    )
    session.add(acuse)
    session.commit()
    session.refresh(acuse)
    return servicios_service.acuse_out(acuse)


# --- Cierre del servicio ---------------------------------------------------


def cerrar_servicio(
    session: Session, servicio_id: uuid.UUID, operador_id: uuid.UUID, data: CerrarServicioIn, current_user: Usuario
) -> ServicioDetalleOut:
    servicio = get_servicio_de_operador(session, servicio_id, operador_id)

    existente = session.exec(
        select(ReporteCierre).where(ReporteCierre.client_action_id == data.client_action_id)
    ).first()
    if existente is not None:
        return servicios_service.build_servicio_detalle(session, servicio)

    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio_id)).all()
    pendientes = [v for v in viajes if v.estado != EstadoViaje.terminado]
    if pendientes:
        raise AppError(
            "conflict", "Hay viajes sin terminar", 409, details=[{"field": "viajes"}]
        )

    viajes_por_id = {v.id: v for v in viajes}
    ids_esperados = set(viajes_por_id)
    ids_recibidos = {k.viaje_id for k in data.km_por_viaje}
    if ids_esperados != ids_recibidos:
        raise AppError(
            "validation_error",
            "km_por_viaje debe traer exactamente los viajes del servicio",
            422,
            details=[{"field": "km_por_viaje"}],
        )
    for k in data.km_por_viaje:
        viajes_por_id[k.viaje_id].km_reportado = k.km
        viajes_por_id[k.viaje_id].updated_at = utcnow()
        session.add(viajes_por_id[k.viaje_id])

    unidad = session.get(Unidad, servicio.unidad_id)
    nivel = validar_lectura_medidor(data.lectura_medidor, unidad)

    cierre = ReporteCierre(
        servicio_id=servicio.id,
        operador_id=operador_id,
        nivel_combustible=nivel,
        lectura_medidor=data.lectura_medidor,
        odometro_km=data.odometro_km,
        cargo_combustible=data.cargo_combustible,
        observaciones=data.observaciones,
        cerrado_at=data.cerrado_at,
        client_action_id=data.client_action_id,
    )
    session.add(cierre)

    for c in data.cargas:
        existente_carga = session.get(CargaCombustible, c.id)
        if existente_carga is not None:
            continue  # idempotencia: ya se registró esta carga
        session.add(
            CargaCombustible(
                id=c.id,
                servicio_id=servicio.id,
                unidad_id=servicio.unidad_id,
                operador_id=operador_id,
                litros=c.litros,
                precio_litro=c.precio_litro,
                importe=c.importe,
                tipo_combustible=c.tipo_combustible,
                cargada_at=c.cargada_at,
                registrada_por=current_user.id,
            )
        )

    servicio.estado = EstadoServicio.terminado
    servicio.terminado_at = utcnow()
    servicio.updated_at = utcnow()
    session.add(servicio)

    session.commit()
    detalle = servicios_service.build_servicio_detalle(session, servicio)
    return enriquecer_detalle_con_operacion(session, servicio.id, detalle)


def subir_ticket_carga(session: Session, carga_id: uuid.UUID, archivo_key: str) -> CargaCombustible:
    carga = session.get(CargaCombustible, carga_id)
    if carga is None:
        raise AppError("not_found", "Carga no encontrada", 404)
    carga.ticket_key = archivo_key
    carga.updated_at = utcnow()
    session.add(carga)
    session.commit()
    session.refresh(carga)
    return carga


# --- Corrección del admin (`03 §6`) -----------------------------------------


def actualizar_carga(session: Session, carga_id: uuid.UUID, payload: dict) -> CargaCombustible:
    carga = session.get(CargaCombustible, carga_id)
    if carga is None:
        raise AppError("not_found", "Carga no encontrada", 404)
    for k, v in payload.items():
        setattr(carga, k, v)
    carga.updated_at = utcnow()
    session.add(carga)
    session.commit()
    session.refresh(carga)
    return carga


def eliminar_carga(session: Session, carga_id: uuid.UUID) -> None:
    carga = session.get(CargaCombustible, carga_id)
    if carga is None:
        raise AppError("not_found", "Carga no encontrada", 404)
    session.delete(carga)
    session.commit()
