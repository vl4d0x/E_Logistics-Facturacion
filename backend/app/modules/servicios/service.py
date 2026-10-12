"""Lógica de negocio de servicios y viajes — `fase-2-servicios`, `02 §3.7-3.10/§4/§5`."""
import uuid
from typing import Any

from sqlmodel import Session, func, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, Lugar, MercanciaFrecuente, Operador, Unidad
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.servicios.models import (
    Acuse,
    EstadoFacturacion,
    EstadoServicio,
    EstadoViaje,
    Servicio,
    TipoAcuse,
    TipoViaje,
    Viaje,
    ViajeMercancia,
)
from app.modules.servicios.schemas import (
    CancelarServicioIn,
    ConteosOut,
    DuplicarServicioIn,
    ServicioCreate,
    ServicioDetalleOut,
    ServicioListItemOut,
    ServicioUpdate,
    TerminarViajeIn,
    ViajeCreate,
    ViajeMercanciaIn,
    ViajeUpdate,
)

# --- helpers genéricos -------------------------------------------------------


def _get_or_404(session: Session, model: type, obj_id: uuid.UUID, nombre: str) -> Any:
    obj = session.get(model, obj_id)
    if obj is None:
        raise AppError("not_found", f"{nombre} no encontrado", 404)
    return obj


def get_servicio(session: Session, servicio_id: uuid.UUID) -> Servicio:
    return _get_or_404(session, Servicio, servicio_id, "Servicio")


def get_viaje(session: Session, viaje_id: uuid.UUID) -> Viaje:
    return _get_or_404(session, Viaje, viaje_id, "Viaje")


def acuse_out(acuse: Acuse) -> dict:
    url = None
    if acuse.archivo_key:
        from app.core.storage import url_firmada  # import perezoso: R2 puede no estar configurado

        try:
            url = url_firmada(acuse.archivo_key)
        except AppError:
            url = None  # R2 no configurado en este entorno; no tumba la respuesta completa
    return {
        "id": acuse.id,
        "tipo": acuse.tipo.value,
        "url": url,
        "mime": acuse.mime,
        "pagina": acuse.pagina,
        "referencia": acuse.referencia,
        "subido_at": acuse.subido_at,
    }


def _next_numero(session: Session) -> int:
    actual = session.exec(select(func.max(Servicio.numero))).one()
    return (actual or 0) + 1


def _factura_vigente(session: Session, servicio: Servicio) -> dict | None:
    factura = session.exec(
        select(Factura).where(
            Factura.servicio_id == servicio.id,
            Factura.estado.in_([EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente]),
        )
    ).first()
    if factura is None:
        return None
    return {
        "id": factura.id,
        "estado": factura.estado.value,
        "uuid_fiscal": factura.uuid_fiscal,
        "serie": factura.serie,
        "folio": factura.folio,
        "total": factura.total,
        "estado_cobro": factura.estado_cobro.value,
    }


def datos_fiscales_bloqueados(session: Session, servicio: Servicio) -> bool:
    return _factura_vigente(session, servicio) is not None


def _check_editable(session: Session, servicio: Servicio, solo_notas: bool = False) -> None:
    if servicio.estado == EstadoServicio.cancelado:
        raise AppError("conflict", "El servicio está cancelado; es de solo lectura", 409)
    if not solo_notas and datos_fiscales_bloqueados(session, servicio):
        raise AppError(
            "conflict",
            "El servicio ya está facturado. Cancela la factura para modificar sus datos fiscales.",
            409,
            details=[{"field": "_", "issue": "servicio_facturado"}],
        )


def _acciones_permitidas(session: Session, servicio: Servicio) -> list[str]:
    if servicio.estado == EstadoServicio.cancelado:
        return []
    acciones = ["editar", "duplicar"]
    bloqueado = datos_fiscales_bloqueados(session, servicio)
    if not bloqueado:
        acciones.append("cancelar")
    todos_terminados = (
        session.exec(
            select(func.count())
            .select_from(Viaje)
            .where(Viaje.servicio_id == servicio.id, Viaje.estado != EstadoViaje.terminado)
        ).one()
        == 0
    )
    puede_facturar = servicio.estado_facturacion == EstadoFacturacion.pendiente and (
        servicio.estado == EstadoServicio.terminado or servicio.timbrado_anticipado
    )
    if puede_facturar:
        acciones.append("facturar")
    if servicio.estado != EstadoServicio.terminado and todos_terminados:
        acciones.append("marcar_terminado")
    return acciones


def _ruta_resumen(session: Session, viajes: list[Viaje]) -> str:
    lugares_ids = {v.origen_lugar_id for v in viajes if v.origen_lugar_id} | {
        v.destino_lugar_id for v in viajes if v.destino_lugar_id
    }
    if not lugares_ids:
        return "Sin ruta"
    nombres = {
        l.id: l.nombre for l in session.exec(select(Lugar).where(Lugar.id.in_(lugares_ids)))
    }
    origenes = [nombres[v.origen_lugar_id] for v in viajes if v.origen_lugar_id in nombres]
    destinos = [nombres[v.destino_lugar_id] for v in viajes if v.destino_lugar_id in nombres]
    origen = origenes[0] if origenes else "?"
    destino = " / ".join(dict.fromkeys(destinos)) if destinos else "?"
    return f"{origen} → {destino}"


# --- mercancías de viaje (snapshot del catálogo) -----------------------------


def _build_viaje_mercancias(
    session: Session, viaje_id: uuid.UUID, items: list[ViajeMercanciaIn]
) -> list[ViajeMercancia]:
    resultado = []
    for item in items:
        catalogo = session.get(MercanciaFrecuente, item.mercancia_frecuente_id)
        if catalogo is None:
            raise AppError(
                "validation_error",
                "Mercancía frecuente no encontrada",
                422,
                details=[{"field": "mercancia_frecuente_id", "issue": "no encontrada"}],
            )
        resultado.append(
            ViajeMercancia(
                viaje_id=viaje_id,
                mercancia_frecuente_id=catalogo.id,
                descripcion=catalogo.nombre_humano,
                bienes_transp=catalogo.bienes_transp,
                clave_unidad=catalogo.clave_unidad,
                unidad_desc=catalogo.unidad_desc,
            declarar_material_peligroso=catalogo.declarar_material_peligroso,
                cantidad=item.cantidad,
                peso_kg=item.peso_kg,
            )
        )
    return resultado


# --- Servicio -----------------------------------------------------------


def create_servicio(session: Session, data: ServicioCreate, current_user: Usuario) -> Servicio:
    _get_or_404(session, Cliente, data.cliente_id, "Cliente")
    _get_or_404(session, Unidad, data.unidad_id, "Unidad")
    _get_or_404(session, Operador, data.operador_id, "Operador")

    servicio = Servicio(
        numero=_next_numero(session),
        cliente_id=data.cliente_id,
        unidad_id=data.unidad_id,
        operador_id=data.operador_id,
        fecha=data.fecha,
        subtotal=data.subtotal,
        notas=data.notas,
        timbrado_anticipado=data.timbrado_anticipado,
        timbrado_modo=data.timbrado_modo if data.timbrado_anticipado else "precio",
        created_by=current_user.id,
    )
    session.add(servicio)
    session.flush()  # asigna servicio.id sin cerrar la transacción

    for orden, viaje_in in enumerate(data.viajes, start=1):
        for lugar_id in (viaje_in.origen_lugar_id, viaje_in.destino_lugar_id):
            if lugar_id:
                _validar_lugar_del_cliente(session, lugar_id, data.cliente_id)
        viaje = Viaje(
            servicio_id=servicio.id,
            orden=orden,
            tipo=viaje_in.tipo,
            fecha=viaje_in.fecha or data.fecha,
            origen_lugar_id=viaje_in.origen_lugar_id,
            destino_lugar_id=viaje_in.destino_lugar_id,
            distancia_km=viaje_in.distancia_km,
            origen_cp=viaje_in.origen_cp,
            destino_cp=viaje_in.destino_cp,
            notas_admin=viaje_in.notas_admin,
            hora_salida_programada=viaje_in.hora_salida_programada,
            hora_llegada_programada=viaje_in.hora_llegada_programada,
        )
        session.add(viaje)
        session.flush()
        if viaje_in.mercancias:
            for vm in _build_viaje_mercancias(session, viaje.id, viaje_in.mercancias):
                session.add(vm)

    session.commit()
    session.refresh(servicio)
    if servicio.timbrado_anticipado and servicio.timbrado_modo == "cero":
        asegurar_mercancia_default(session, servicio)
        session.refresh(servicio)
    return servicio


def build_servicio_detalle(session: Session, servicio: Servicio) -> ServicioDetalleOut:
    cliente = session.get(Cliente, servicio.cliente_id)
    unidad = session.get(Unidad, servicio.unidad_id)
    operador = session.get(Operador, servicio.operador_id)
    viajes = session.exec(
        select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)
    ).all()

    lugares_ids = {v.origen_lugar_id for v in viajes if v.origen_lugar_id} | {
        v.destino_lugar_id for v in viajes if v.destino_lugar_id
    }
    lugares = {
        l.id: l for l in session.exec(select(Lugar).where(Lugar.id.in_(lugares_ids)))
    } if lugares_ids else {}

    viajes_out = []
    for v in viajes:
        mercancias = session.exec(
            select(ViajeMercancia).where(ViajeMercancia.viaje_id == v.id)
        ).all()
        acuses = session.exec(select(Acuse).where(Acuse.viaje_id == v.id)).all()
        requiere_acuse = v.tipo in (TipoViaje.entrega, TipoViaje.recoleccion_entrega) and (
            cliente.modo_acuse.value != "ninguno"
        )
        if cliente.modo_acuse.value == "escaneo":
            completo = any(a.archivo_key for a in acuses)
        elif cliente.modo_acuse.value == "referencia":
            completo = any(a.referencia for a in acuses)
        else:
            completo = True

        def _lugar_resumen(lugar_id: uuid.UUID | None) -> dict | None:
            if lugar_id is None or lugar_id not in lugares:
                return None
            l = lugares[lugar_id]
            return {
                "id": l.id,
                "nombre": l.nombre,
                "codigo_postal": l.codigo_postal,
                "calle": l.calle,
                "num_exterior": l.num_exterior,
                "colonia": l.colonia,
                "municipio": l.municipio,
                "estado": l.estado,
                "referencia": l.referencia,
                "rfc_remitente_destinatario": l.rfc_remitente_destinatario,
                "nombre_remitente_destinatario": l.nombre_remitente_destinatario,
            }

        viajes_out.append(
            {
                "id": v.id,
                "orden": v.orden,
                "tipo": v.tipo,
                "estado": v.estado,
                "fecha": v.fecha,
                "origen": _lugar_resumen(v.origen_lugar_id),
                "destino": _lugar_resumen(v.destino_lugar_id),
                "hora_salida_programada": v.hora_salida_programada,
                "hora_llegada_programada": v.hora_llegada_programada,
                "distancia_km": v.distancia_km,
                "origen_cp": v.origen_cp,
                "destino_cp": v.destino_cp,
                "km_reportado": v.km_reportado,
                "hora_llegada": v.hora_llegada,
                "terminado_at": v.terminado_at,
                "notas_admin": v.notas_admin,
                "notas_operador": v.notas_operador,
                "mercancias": mercancias,
                "acuses": [acuse_out(a) for a in acuses],
                "acuse_requerido": requiere_acuse,
                "acuse_completo": completo if requiere_acuse else True,
            }
        )

    return ServicioDetalleOut(
        id=servicio.id,
        numero=servicio.numero,
        fecha=servicio.fecha,
        estado=servicio.estado,
        estado_facturacion=servicio.estado_facturacion,
        timbrado_anticipado=servicio.timbrado_anticipado,
        timbrado_modo=servicio.timbrado_modo,
        cliente={
            "id": cliente.id,
            "nombre_comercial": cliente.nombre_comercial,
            "modo_acuse": cliente.modo_acuse.value,
            "regimen_receptor": cliente.regimen_receptor.value,
        },
        unidad={
            "id": unidad.id,
            "apodo": unidad.apodo,
            "tipo_medidor": unidad.tipo_medidor.value,
            "num_barras": unidad.num_barras,
        },
        operador={"id": operador.id, "nombre": operador.nombre},
        subtotal=servicio.subtotal,
        notas=servicio.notas,
        viajes=viajes_out,
        factura_vigente=_factura_vigente(session, servicio),
        datos_fiscales_bloqueados=datos_fiscales_bloqueados(session, servicio),
        acciones_permitidas=_acciones_permitidas(session, servicio),
    )


def list_servicios(
    session: Session,
    vista: str | None,
    cliente_id: uuid.UUID | None,
    operador_id: uuid.UUID | None,
    unidad_id: uuid.UUID | None,
    fecha_desde,
    fecha_hasta,
    q: str | None,
    page: int,
    size: int,
) -> tuple[list[ServicioListItemOut], int]:
    stmt = _filtrar_servicios(
        select(Servicio), vista, cliente_id, operador_id, unidad_id, fecha_desde, fecha_hasta, q
    )
    total = len(session.exec(stmt).all())
    servicios = session.exec(
        stmt.order_by(Servicio.fecha.desc(), Servicio.numero.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items = []
    for s in servicios:
        cliente = session.get(Cliente, s.cliente_id)
        unidad = session.get(Unidad, s.unidad_id)
        operador = session.get(Operador, s.operador_id)
        viajes = session.exec(select(Viaje).where(Viaje.servicio_id == s.id)).all()
        terminados = sum(1 for v in viajes if v.estado == EstadoViaje.terminado)
        acuses_req = 0
        acuses_comp = 0
        if cliente.modo_acuse.value != "ninguno":
            for v in viajes:
                if v.tipo in (TipoViaje.entrega, TipoViaje.recoleccion_entrega):
                    acuses_req += 1
                    acuses = session.exec(select(Acuse).where(Acuse.viaje_id == v.id)).all()
                    if cliente.modo_acuse.value == "escaneo" and any(
                        a.archivo_key for a in acuses
                    ) or cliente.modo_acuse.value == "referencia" and any(
                        a.referencia for a in acuses
                    ):
                        acuses_comp += 1
        items.append(
            ServicioListItemOut(
                id=s.id,
                numero=s.numero,
                fecha=s.fecha,
                estado=s.estado,
                estado_facturacion=s.estado_facturacion,
                timbrado_anticipado=s.timbrado_anticipado,
                cliente=cliente.nombre_comercial,
                unidad_apodo=unidad.apodo,
                operador_nombre=operador.nombre,
                ruta_resumen=_ruta_resumen(session, viajes),
                viajes_total=len(viajes),
                viajes_terminados=terminados,
                acuses_requeridos=acuses_req,
                acuses_completos=acuses_comp,
                subtotal=s.subtotal,
            )
        )
    return items, total


def _filtrar_servicios(
    stmt, vista, cliente_id, operador_id, unidad_id, fecha_desde, fecha_hasta, q
):
    if vista == "programados":
        stmt = stmt.where(Servicio.estado == EstadoServicio.programado)
    elif vista == "en_curso":
        stmt = stmt.where(Servicio.estado == EstadoServicio.en_curso)
    elif vista == "por_facturar":
        stmt = stmt.where(
            Servicio.estado_facturacion == EstadoFacturacion.pendiente,
            (Servicio.estado == EstadoServicio.terminado)
            | (Servicio.timbrado_anticipado == True),
            Servicio.estado != EstadoServicio.cancelado,
        )
    elif vista == "facturados":
        stmt = stmt.where(Servicio.estado_facturacion == EstadoFacturacion.facturado)
    elif vista == "cancelados":
        stmt = stmt.where(Servicio.estado == EstadoServicio.cancelado)
    if cliente_id:
        stmt = stmt.where(Servicio.cliente_id == cliente_id)
    if operador_id:
        stmt = stmt.where(Servicio.operador_id == operador_id)
    if unidad_id:
        stmt = stmt.where(Servicio.unidad_id == unidad_id)
    if fecha_desde:
        stmt = stmt.where(Servicio.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(Servicio.fecha <= fecha_hasta)
    return stmt


def conteos_servicios(
    session: Session, cliente_id, operador_id, unidad_id, fecha_desde, fecha_hasta, q
) -> ConteosOut:
    valores = {}
    for vista in ("programados", "en_curso", "por_facturar", "facturados", "cancelados"):
        stmt = _filtrar_servicios(
            select(func.count()).select_from(Servicio),
            vista,
            cliente_id,
            operador_id,
            unidad_id,
            fecha_desde,
            fecha_hasta,
            q,
        )
        valores[vista] = session.exec(stmt).one()
    return ConteosOut(**valores)


def update_servicio(session: Session, servicio_id: uuid.UUID, data: ServicioUpdate) -> Servicio:
    servicio = get_servicio(session, servicio_id)
    payload = data.model_dump(exclude_unset=True)
    solo_notas = set(payload.keys()) <= {"notas"}
    _check_editable(session, servicio, solo_notas=solo_notas)

    nuevo_subtotal = payload.get("subtotal", servicio.subtotal)
    nuevo_anticipado = payload.get("timbrado_anticipado", servicio.timbrado_anticipado)
    nuevo_modo = payload.get("timbrado_modo") or servicio.timbrado_modo
    if nuevo_anticipado and nuevo_modo == "precio" and not (nuevo_subtotal and nuevo_subtotal > 0):
        raise AppError(
            "validation_error",
            "timbrado_anticipado exige subtotal > 0",
            422,
            details=[{"field": "subtotal", "issue": "requerido"}],
        )

    for field_name in ("unidad_id", "operador_id"):
        if field_name in payload:
            _get_or_404(
                session,
                Unidad if field_name == "unidad_id" else Operador,
                payload[field_name],
                "Unidad" if field_name == "unidad_id" else "Operador",
            )

    for k, v in payload.items():
        setattr(servicio, k, v)
    servicio.updated_at = utcnow()
    session.add(servicio)
    session.commit()
    session.refresh(servicio)
    return servicio


def duplicar_servicio(
    session: Session, servicio_id: uuid.UUID, data: DuplicarServicioIn, current_user: Usuario
) -> Servicio:
    original = get_servicio(session, servicio_id)
    viajes = session.exec(
        select(Viaje).where(Viaje.servicio_id == original.id).order_by(Viaje.orden)
    ).all()

    nuevo = Servicio(
        numero=_next_numero(session),
        cliente_id=original.cliente_id,
        unidad_id=original.unidad_id,
        operador_id=original.operador_id,
        fecha=data.fecha,
        created_by=current_user.id,
    )
    session.add(nuevo)
    session.flush()
    for v in viajes:
        copia = Viaje(
            servicio_id=nuevo.id,
            orden=v.orden,
            tipo=v.tipo,
            fecha=data.fecha,
            origen_lugar_id=v.origen_lugar_id,
            destino_lugar_id=v.destino_lugar_id,
            distancia_km=v.distancia_km,
            origen_cp=v.origen_cp,
            destino_cp=v.destino_cp,
            notas_admin=v.notas_admin,
        )
        session.add(copia)
    session.commit()
    session.refresh(nuevo)
    return nuevo


def marcar_terminado(session: Session, servicio_id: uuid.UUID) -> Servicio:
    servicio = get_servicio(session, servicio_id)
    _check_editable(session, servicio)
    pendientes = session.exec(
        select(func.count())
        .select_from(Viaje)
        .where(Viaje.servicio_id == servicio.id, Viaje.estado != EstadoViaje.terminado)
    ).one()
    if pendientes:
        raise AppError(
            "conflict", "Todavía hay viajes sin terminar", 409, details=[{"field": "viajes"}]
        )
    servicio.estado = EstadoServicio.terminado
    servicio.terminado_por_admin = True
    servicio.terminado_at = utcnow()
    servicio.updated_at = utcnow()
    session.add(servicio)
    session.commit()
    session.refresh(servicio)
    return servicio


def cancelar_servicio(
    session: Session, servicio_id: uuid.UUID, data: CancelarServicioIn
) -> Servicio:
    servicio = get_servicio(session, servicio_id)
    if datos_fiscales_bloqueados(session, servicio):
        raise AppError("conflict", "No se puede cancelar un servicio facturado", 409)
    servicio.estado = EstadoServicio.cancelado
    servicio.cancelado_motivo = data.motivo
    servicio.updated_at = utcnow()
    session.add(servicio)
    session.commit()
    session.refresh(servicio)
    return servicio


# --- Viajes -------------------------------------------------------------


def _validar_un_solo_origen(
    session: Session, servicio_id: uuid.UUID, tipo: TipoViaje, excluir: uuid.UUID | None = None
) -> None:
    """Un servicio tiene un solo origen: no se acepta otra recolección (ni "recolección y entrega")."""
    if tipo not in (TipoViaje.recoleccion, TipoViaje.recoleccion_entrega):
        return
    stmt = select(func.count()).select_from(Viaje).where(
        Viaje.servicio_id == servicio_id,
        Viaje.tipo.in_([TipoViaje.recoleccion, TipoViaje.recoleccion_entrega]),
    )
    if excluir is not None:
        stmt = stmt.where(Viaje.id != excluir)
    if session.exec(stmt).one():
        raise AppError(
            "validation_error",
            "Un servicio solo puede tener un origen",
            422,
            details=[{"field": "tipo", "issue": "un_solo_origen"}],
        )


def add_viaje(session: Session, servicio_id: uuid.UUID, data: ViajeCreate) -> Viaje:
    servicio = get_servicio(session, servicio_id)
    _check_editable(session, servicio)
    _validar_un_solo_origen(session, servicio_id, data.tipo)
    if data.origen_lugar_id:
        _validar_lugar_del_cliente(session, data.origen_lugar_id, servicio.cliente_id)
    if data.destino_lugar_id:
        _validar_lugar_del_cliente(session, data.destino_lugar_id, servicio.cliente_id)
    max_orden = session.exec(
        select(func.max(Viaje.orden)).where(Viaje.servicio_id == servicio_id)
    ).one()
    viaje = Viaje(
        servicio_id=servicio_id,
        orden=(max_orden or 0) + 1,
        tipo=data.tipo,
        fecha=data.fecha or servicio.fecha,
        origen_lugar_id=data.origen_lugar_id,
        destino_lugar_id=data.destino_lugar_id,
        distancia_km=data.distancia_km,
        origen_cp=data.origen_cp,
        destino_cp=data.destino_cp,
        notas_admin=data.notas_admin,
        hora_salida_programada=data.hora_salida_programada,
        hora_llegada_programada=data.hora_llegada_programada,
    )
    session.add(viaje)
    session.commit()
    if data.tipo in (TipoViaje.recoleccion, TipoViaje.recoleccion_entrega):
        # El origen va primero en la ruta (Carta Porte): el viaje nuevo pasa al principio.
        otros = session.exec(
            select(Viaje.id).where(Viaje.servicio_id == servicio_id, Viaje.id != viaje.id).order_by(Viaje.orden)
        ).all()
        reordenar_viajes(session, servicio_id, [viaje.id, *otros])
    session.refresh(viaje)
    return viaje


def _validar_lugar_del_cliente(session: Session, lugar_id: uuid.UUID, cliente_id: uuid.UUID) -> None:
    from app.modules.catalogos.service import clientes_del_catalogo

    lugar = _get_or_404(session, Lugar, lugar_id, "Lugar")
    if lugar.cliente_id is not None and lugar.cliente_id not in clientes_del_catalogo(session, cliente_id):
        raise AppError(
            "validation_error",
            "Ese lugar pertenece a otro cliente",
            422,
            details=[{"field": "lugar_id", "issue": "cliente distinto"}],
        )


def update_viaje(session: Session, viaje_id: uuid.UUID, data: ViajeUpdate) -> Viaje:
    viaje = get_viaje(session, viaje_id)
    servicio = get_servicio(session, viaje.servicio_id)
    payload = data.model_dump(exclude_unset=True)
    solo_notas = set(payload.keys()) <= {"notas_admin"}
    _check_editable(session, servicio, solo_notas=solo_notas)
    if payload.get("tipo") is not None:
        _validar_un_solo_origen(session, servicio.id, payload["tipo"], excluir=viaje.id)

    if payload.get("origen_lugar_id"):
        _validar_lugar_del_cliente(session, payload["origen_lugar_id"], servicio.cliente_id)
    if payload.get("destino_lugar_id"):
        _validar_lugar_del_cliente(session, payload["destino_lugar_id"], servicio.cliente_id)

    for k, v in payload.items():
        setattr(viaje, k, v)
    viaje.updated_at = utcnow()
    session.add(viaje)
    session.commit()
    session.refresh(viaje)
    return viaje


def delete_viaje(session: Session, viaje_id: uuid.UUID) -> None:
    viaje = get_viaje(session, viaje_id)
    servicio = get_servicio(session, viaje.servicio_id)
    _check_editable(session, servicio)
    # Un viaje terminado también se puede quitar (el admin corrige desde Facturar): se borran
    # sus mercancías y acuses (los archivos del acuse se conservan en el almacenamiento).
    for dependiente in (ViajeMercancia, Acuse):
        for fila in session.exec(select(dependiente).where(dependiente.viaje_id == viaje_id)).all():
            session.delete(fila)
    session.flush()
    session.delete(viaje)
    session.commit()


def reordenar_viajes(
    session: Session, servicio_id: uuid.UUID, viaje_ids: list[uuid.UUID]
) -> list[Viaje]:
    servicio = get_servicio(session, servicio_id)
    _check_editable(session, servicio)
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio_id)).all()
    ids_existentes = {v.id for v in viajes}
    if set(viaje_ids) != ids_existentes:
        raise AppError(
            "validation_error",
            "La lista de viajes no coincide con los del servicio",
            422,
            details=[{"field": "viaje_ids", "issue": "no coincide"}],
        )
    por_id = {v.id: v for v in viajes}
    # Dos pasadas: el UNIQUE(servicio_id, orden) se valida de inmediato (no es
    # "deferrable"), así que escribir los órdenes finales de una sola pasada puede
    # chocar a mitad de camino con un valor que todavía tiene otra fila (p.ej. swap
    # 1↔2). Se pasa primero por órdenes temporales fuera de rango y garantizado-únicos.
    for offset, viaje in enumerate(viajes):
        viaje.orden = -(offset + 1)
        session.add(viaje)
    session.flush()
    for i, viaje_id in enumerate(viaje_ids, start=1):
        por_id[viaje_id].orden = i
        por_id[viaje_id].updated_at = utcnow()
        session.add(por_id[viaje_id])
    session.commit()
    return session.exec(
        select(Viaje).where(Viaje.servicio_id == servicio_id).order_by(Viaje.orden)
    ).all()


def terminar_viaje(
    session: Session, viaje_id: uuid.UUID, data: TerminarViajeIn, current_user: Usuario
) -> Viaje:
    viaje = get_viaje(session, viaje_id)
    if data.client_action_id is not None:
        existente = session.exec(
            select(Viaje).where(Viaje.client_action_id == data.client_action_id)
        ).first()
        if existente is not None:
            return existente  # idempotencia: reintento offline

    if data.mercancias:
        for vm in _build_viaje_mercancias(session, viaje.id, data.mercancias):
            session.add(vm)
    if data.hora_llegada is not None:
        viaje.hora_llegada = data.hora_llegada
    if data.notas_operador is not None:
        viaje.notas_operador = data.notas_operador
    if data.referencia_acuse:
        session.add(
            Acuse(
                viaje_id=viaje.id,
                tipo=TipoAcuse.referencia,
                referencia=data.referencia_acuse,
                subido_por=current_user.id,
                subido_at=utcnow(),
            )
        )
    viaje.estado = EstadoViaje.terminado
    viaje.terminado_at = utcnow()
    viaje.terminado_por = current_user.id
    viaje.client_action_id = data.client_action_id
    viaje.updated_at = utcnow()
    session.add(viaje)

    servicio = get_servicio(session, viaje.servicio_id)
    if servicio.estado == EstadoServicio.programado:
        servicio.estado = EstadoServicio.en_curso
        servicio.iniciado_at = servicio.iniciado_at or utcnow()
        servicio.updated_at = utcnow()
        session.add(servicio)

    session.commit()
    session.refresh(viaje)
    return viaje


def reabrir_viaje(session: Session, viaje_id: uuid.UUID) -> Viaje:
    viaje = get_viaje(session, viaje_id)
    servicio = get_servicio(session, viaje.servicio_id)
    if servicio.estado == EstadoServicio.terminado and datos_fiscales_bloqueados(
        session, servicio
    ):
        raise AppError("conflict", "El servicio ya está facturado", 409)
    viaje.estado = EstadoViaje.pendiente
    viaje.terminado_at = None
    viaje.terminado_por = None
    viaje.updated_at = utcnow()
    session.add(viaje)
    if servicio.estado == EstadoServicio.terminado:
        servicio.estado = EstadoServicio.en_curso
        servicio.terminado_at = None
        servicio.terminado_por_admin = False
        servicio.updated_at = utcnow()
        session.add(servicio)
    session.commit()
    session.refresh(viaje)
    return viaje


def set_mercancias_viaje(
    session: Session, viaje_id: uuid.UUID, items: list[ViajeMercanciaIn]
) -> list[ViajeMercancia]:
    viaje = get_viaje(session, viaje_id)
    servicio = get_servicio(session, viaje.servicio_id)
    _check_editable(session, servicio)
    existentes = session.exec(
        select(ViajeMercancia).where(ViajeMercancia.viaje_id == viaje_id)
    ).all()
    for e in existentes:
        session.delete(e)
    session.flush()
    nuevas = _build_viaje_mercancias(session, viaje_id, items)
    for n in nuevas:
        session.add(n)
    session.commit()
    return session.exec(select(ViajeMercancia).where(ViajeMercancia.viaje_id == viaje_id)).all()


# --- Acuses -------------------------------------------------------------


def agregar_acuse_referencia(
    session: Session, viaje_id: uuid.UUID, referencia: str, current_user: Usuario
) -> Acuse:
    get_viaje(session, viaje_id)  # 404 si no existe
    acuse = Acuse(
        viaje_id=viaje_id,
        tipo=TipoAcuse.referencia,
        referencia=referencia,
        subido_por=current_user.id,
        subido_at=utcnow(),
    )
    session.add(acuse)
    session.commit()
    session.refresh(acuse)
    return acuse


def set_folio_viaje(
    session: Session, viaje_id: uuid.UUID, folio: str | None, current_user: Usuario
) -> dict:
    """Fija o corrige el folio del cliente de un viaje (clientes que lo llevan en el concepto):
    es la referencia de su acuse. Vacío = se quita. Con factura vigente no se puede (409)."""
    viaje = get_viaje(session, viaje_id)
    servicio = get_servicio(session, viaje.servicio_id)
    _check_editable(session, servicio)
    folio = (folio or "").strip() or None
    existentes = session.exec(
        select(Acuse).where(Acuse.viaje_id == viaje_id, Acuse.tipo == TipoAcuse.referencia).order_by(Acuse.pagina)
    ).all()
    if folio is None:
        for a in existentes:
            session.delete(a)
    elif existentes:
        existentes[0].referencia = folio
        session.add(existentes[0])
        for sobrante in existentes[1:]:
            session.delete(sobrante)
    else:
        session.add(
            Acuse(
                viaje_id=viaje_id,
                tipo=TipoAcuse.referencia,
                referencia=folio,
                subido_por=current_user.id,
                subido_at=utcnow(),
            )
        )
    session.commit()
    return {"viaje_id": viaje_id, "folio": folio}


def validar_acuse_pdf(contenido: bytes) -> None:
    """El acuse escaneado es UN solo PDF (no fotos): se revisa la firma del archivo."""
    if not contenido.startswith(b"%PDF"):
        raise AppError(
            "validation_error",
            "El acuse debe ser un solo archivo PDF escaneado",
            422,
            details=[{"field": "file", "issue": "solo_pdf"}],
        )


def reemplazar_acuses_escaneo(session: Session, viaje_id: uuid.UUID, nuevo_id: uuid.UUID) -> None:
    """Un viaje guarda un solo acuse escaneado: al subir otro, el anterior se quita."""
    for viejo in session.exec(
        select(Acuse).where(
            Acuse.viaje_id == viaje_id, Acuse.tipo == TipoAcuse.escaneo, Acuse.id != nuevo_id
        )
    ).all():
        session.delete(viejo)
    session.commit()


def agregar_acuse_archivo(
    session: Session,
    viaje_id: uuid.UUID,
    archivo_key: str,
    mime: str,
    pagina: int,
    current_user: Usuario,
) -> Acuse:
    get_viaje(session, viaje_id)
    acuse = Acuse(
        viaje_id=viaje_id,
        tipo=TipoAcuse.escaneo,
        archivo_key=archivo_key,
        mime=mime,
        pagina=pagina,
        subido_por=current_user.id,
        subido_at=utcnow(),
    )
    session.add(acuse)
    session.commit()
    session.refresh(acuse)
    reemplazar_acuses_escaneo(session, viaje_id, acuse.id)
    session.refresh(acuse)
    return acuse


def eliminar_acuse(session: Session, acuse_id: uuid.UUID) -> None:
    acuse = _get_or_404(session, Acuse, acuse_id, "Acuse")
    archivo_key = acuse.archivo_key
    session.delete(acuse)
    session.commit()
    if archivo_key:
        from app.core.storage import eliminar_archivo

        try:
            eliminar_archivo(archivo_key)
        except AppError:
            pass  # el registro ya se borró; limpiar R2 es best-effort



# --- Mercancía por defecto del timbrado en $0 --------------------------------
MERCANCIA_DEFAULT = {
    "nombre": "Preservativos de alimentos",
    "bienes_transp": "12164501",
    "clave_unidad": "X4G",
}


def asegurar_mercancia_default(session: Session, servicio: Servicio) -> bool:
    """Timbrado anticipado en $0: si el servicio no tiene mercancías, agrega 1 kg de
    "Preservativos de alimentos" al primer viaje con destino (la toma del catálogo del
    cliente, o la crea ahí si aún no existe). Devuelve True si agregó algo."""
    viajes = session.exec(
        select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)
    ).all()
    if not viajes:
        return False
    ids = [v.id for v in viajes]
    hay = session.exec(select(ViajeMercancia).where(ViajeMercancia.viaje_id.in_(ids))).first()
    destino = next((v for v in viajes if v.destino_lugar_id), None)
    if hay is not None or destino is None:
        return False
    from app.modules.catalogos.service import clientes_del_catalogo

    nombre = MERCANCIA_DEFAULT["nombre"]
    catalogo = session.exec(
        select(MercanciaFrecuente).where(
            MercanciaFrecuente.cliente_id.in_(clientes_del_catalogo(session, servicio.cliente_id)),
            func.lower(MercanciaFrecuente.nombre_humano) == nombre.lower(),
        )
    ).first()
    if catalogo is None:
        catalogo = MercanciaFrecuente(
            cliente_id=servicio.cliente_id,
            nombre_humano=nombre,
            bienes_transp=MERCANCIA_DEFAULT["bienes_transp"],
            clave_unidad=MERCANCIA_DEFAULT["clave_unidad"],
        )
        session.add(catalogo)
        session.flush()
    session.add(
        ViajeMercancia(
            viaje_id=destino.id,
            mercancia_frecuente_id=catalogo.id,
            descripcion=catalogo.nombre_humano,
            bienes_transp=catalogo.bienes_transp,
            clave_unidad=catalogo.clave_unidad,
            unidad_desc=catalogo.unidad_desc,
            declarar_material_peligroso=catalogo.declarar_material_peligroso,
            cantidad=1,
            peso_kg=1.0,
        )
    )
    session.commit()
    return True

# --- Distancia sugerida ----------------------------------------------------

KM_POR_DEFECTO = 70.0


def distancia_sugerida(
    session: Session, destino_lugar_id: uuid.UUID, origen_lugar_id: uuid.UUID | None = None
) -> tuple[float, str, bool]:
    """Km hacia el destino: el del Excel de Carta Porte del cliente (`lugar.distancia_km`,
    confirmado) o, si no hay, 70 km marcados como no confirmados. El origen
    no cuenta (aproximación a propósito; ver `specs/IDEAS-FUTURAS.md`)."""
    lugar = session.get(Lugar, destino_lugar_id)
    if lugar is not None and lugar.km_confirmado and lugar.distancia_km:
        return lugar.distancia_km, "cliente", True
    return KM_POR_DEFECTO, "por_defecto", False


# --- Hook para Fase 1: contar_uso de catálogos ------------------------------


def contar_servicios_activos_por(
    session: Session, **filtros: object
) -> list[dict]:
    """Servicios `programado`/`en_curso` que referencian un catálogo — para que
    `catalogos.service.contar_uso_*` bloquee archivar con servicios activos."""
    stmt = select(Servicio).where(
        Servicio.estado.in_([EstadoServicio.programado, EstadoServicio.en_curso])
    )
    for field_name, value in filtros.items():
        stmt = stmt.where(getattr(Servicio, field_name) == value)
    return [
        {"servicio_id": s.id, "numero": s.numero, "estado": s.estado.value}
        for s in session.exec(stmt)
    ]


def contar_referencias_catalogo(session: Session, **filtros: object) -> int:
    stmt = select(func.count()).select_from(Servicio)
    for field_name, value in filtros.items():
        stmt = stmt.where(getattr(Servicio, field_name) == value)
    return session.exec(stmt).one()


def contar_referencias_lugar(session: Session, lugar_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count())
        .select_from(Viaje)
        .where((Viaje.origen_lugar_id == lugar_id) | (Viaje.destino_lugar_id == lugar_id))
    ).one()


def contar_referencias_mercancia(session: Session, mercancia_frecuente_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count())
        .select_from(ViajeMercancia)
        .where(ViajeMercancia.mercancia_frecuente_id == mercancia_frecuente_id)
    ).one()


def _servicios_activos_con_viajes_de(session: Session, viaje_ids_stmt) -> list[dict]:
    servicio_ids = set(
        session.exec(select(Viaje.servicio_id).where(Viaje.id.in_(viaje_ids_stmt)))
    )
    if not servicio_ids:
        return []
    stmt = select(Servicio).where(
        Servicio.id.in_(servicio_ids),
        Servicio.estado.in_([EstadoServicio.programado, EstadoServicio.en_curso]),
    )
    return [
        {"servicio_id": s.id, "numero": s.numero, "estado": s.estado.value}
        for s in session.exec(stmt)
    ]


def servicios_activos_con_lugar(session: Session, lugar_id: uuid.UUID) -> list[dict]:
    viaje_ids = select(Viaje.id).where(
        (Viaje.origen_lugar_id == lugar_id) | (Viaje.destino_lugar_id == lugar_id)
    )
    return _servicios_activos_con_viajes_de(session, viaje_ids)


def servicios_activos_con_mercancia(
    session: Session, mercancia_frecuente_id: uuid.UUID
) -> list[dict]:
    viaje_ids = select(ViajeMercancia.viaje_id).where(
        ViajeMercancia.mercancia_frecuente_id == mercancia_frecuente_id
    )
    return _servicios_activos_con_viajes_de(session, viaje_ids)
