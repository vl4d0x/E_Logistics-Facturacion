"""Orquesta impuestos, validación y la pantalla "Facturar" — `04 §3,§5,§6`."""
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.models import utcnow
from app.integrations.facturama import FacturamaClient, FacturamaError
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, Lugar, Operador, Unidad
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.facturacion.payload import construir_payload_cfdi
from app.modules.facturacion.schemas import (
    AcuseFacturarOut,
    AutotransporteOut,
    ConceptoOut,
    DesgloseDestinoIn,
    DesgloseDestinoOut,
    DesgloseLineaOut,
    FacturacionDetalleOut,
    FacturacionUpdateIn,
    FacturarIn,
    FiguraOut,
    FolioViajeOut,
    ImpuestosPreviewIn,
    MercanciaFacturarOut,
    MontosOut,
    PrecioSugeridoOut,
    ReceptorOut,
    UbicacionOut,
    ValidacionOut,
)
from app.modules.facturacion.taxes import calcular_impuestos, subtotal_desde_total
from app.modules.facturacion.validar import (
    desglose_por_destino,
    folios_por_viaje,
    modo_timbrado,
    subtotal_efectivo,
    validar_servicio,
)
from app.modules.precios.service import sugerir_para_servicio
from app.modules.servicios.models import (
    Acuse,
    EstadoFacturacion,
    EstadoServicio,
    TipoViaje,
    Viaje,
    ViajeMercancia,
)
from app.modules.servicios.service import (
    asegurar_mercancia_default,
    datos_fiscales_bloqueados,
    get_servicio,
)


def _url_o_none(key: str | None) -> str | None:
    if not key:
        return None
    from app.core.storage import url_firmada

    return url_firmada(key)


def preview_impuestos(body: ImpuestosPreviewIn) -> MontosOut:
    subtotal = body.subtotal
    if subtotal is None:
        subtotal = subtotal_desde_total(body.total, body.regimen_receptor)
    montos = calcular_impuestos(subtotal, body.regimen_receptor)
    return MontosOut(**montos._asdict())


def validar(session: Session, servicio_id: uuid.UUID) -> ValidacionOut:
    servicio = get_servicio(session, servicio_id)
    cliente = session.get(Cliente, servicio.cliente_id)
    checks = validar_servicio(session, servicio)
    ok = not any(c.nivel == "error" for c in checks)

    preview = None
    subtotal_timbrar = subtotal_efectivo(servicio)
    if subtotal_timbrar and subtotal_timbrar > Decimal(0):
        montos = calcular_impuestos(subtotal_timbrar, cliente.regimen_receptor)
        preview = MontosOut(**montos._asdict())

    return ValidacionOut(ok=ok, checks=checks, preview=preview)


# --- Pantalla "Facturar" (H4.4) ---------------------------------------------


def _salida_viaje(viaje: Viaje) -> tuple[datetime | None, str]:
    """`04-facturacion-cfdi §4.2` — fuente de la fecha/hora de salida de un origen."""
    if viaje.terminado_at is not None:
        return viaje.terminado_at, "real"
    if viaje.hora_salida_programada is not None:
        return datetime.combine(viaje.fecha, viaje.hora_salida_programada), "programada"
    return None, "programada"


def _llegada_viaje(viaje: Viaje) -> tuple[datetime | None, str]:
    """`04-facturacion-cfdi §4.2` — fuente de la fecha/hora de llegada de un destino."""
    if viaje.terminado_at is not None:
        if viaje.hora_llegada is not None:
            return datetime.combine(viaje.fecha, viaje.hora_llegada), "real"
        return viaje.terminado_at, "real"
    if viaje.hora_llegada_programada is not None:
        return datetime.combine(viaje.fecha, viaje.hora_llegada_programada), "programada"
    return None, "programada"


def _lugar_dict(lugar: Lugar | None, cp: str | None = None) -> dict:
    """`cp`: código postal propio del viaje (si difiere del del lugar)."""
    if lugar is None:
        return {}
    return {
        "id": lugar.id,
        "nombre": lugar.nombre,
        "rfc_remitente_destinatario": lugar.rfc_remitente_destinatario,
        "nombre_remitente_destinatario": lugar.nombre_remitente_destinatario,
        "calle": lugar.calle,
        "num_exterior": lugar.num_exterior,
        "colonia": lugar.colonia,
        "municipio": lugar.municipio,
        "estado": lugar.estado,
        "pais": lugar.pais,
        "codigo_postal": cp or lugar.codigo_postal,
        "cp_modificado": bool(cp and cp != lugar.codigo_postal),
    }


_MESES_ABREV = (
    "ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC",
)


def _fecha_concepto(fecha: date) -> str:
    """`{día} {MES} {aa}`, ej. "11 AGO 26" -- formato confirmado contra una factura
    real de Chemital (`.misc/CME091007LG1_SS_5318_20260820.xml`)."""
    return f"{fecha.day} {_MESES_ABREV[fecha.month - 1]} {fecha.strftime('%y')}"


def _capacidad_txt(unidad: Unidad) -> str:
    """Capacidad de carga de la unidad en toneladas, con un decimal ("1.0 TON", "0.5 TON"); no el apodo.
    Sin `capacidad_carga_kg` usa el peso bruto vehicular (que ya está en toneladas)."""
    toneladas = unidad.capacidad_carga_kg / 1000 if unidad.capacidad_carga_kg else unidad.peso_bruto_vehicular
    return f"{toneladas:.1f} TON"


def _descripcion_autogenerada(
    unidad: Unidad,
    viajes: list[Viaje],
    lugares: dict[uuid.UUID, Lugar],
    cliente: Cliente,
    folios: dict[uuid.UUID, str | None],
) -> str:
    """`04-facturacion-cfdi §2`. Los clientes con `requiere_folio_concepto` (caso real:
    Chemital) llevan al final un renglón "REF: folio1, folio2" con el folio de cada destino."""
    origenes = [lugares[v.origen_lugar_id].nombre for v in viajes if v.origen_lugar_id in lugares]
    destinos = [lugares[v.destino_lugar_id].nombre for v in viajes if v.destino_lugar_id in lugares]
    lineas_ref: list[str] = []
    if cliente.requiere_folio_concepto:
        refs = [folios.get(v.id) or "—" for v in viajes if v.destino_lugar_id in lugares]
        lineas_ref = [f"REF: {', '.join(refs) or '—'}"]
    fechas = sorted({v.fecha for v in viajes})
    if len(fechas) <= 1:
        fecha_txt = _fecha_concepto(fechas[0] if fechas else datetime.now(UTC).date())
    else:
        fecha_txt = f"{_fecha_concepto(fechas[0])} – {_fecha_concepto(fechas[-1])}"
    lineas = [
        f"UNIDAD: {_capacidad_txt(unidad)}",
        f"ORIGEN: {' / '.join(origenes) or '—'}",
        f"DESTINO: {' / '.join(destinos) or '—'}",
        f"FECHA: {fecha_txt}",
        *lineas_ref,
    ]
    return "\n".join(lineas)


def _ubicaciones(viajes: list[Viaje], lugares: dict[uuid.UUID, Lugar]) -> list[UbicacionOut]:
    ubicaciones = []
    n_origen = n_destino = 0
    for v in viajes:
        if v.tipo in (TipoViaje.recoleccion, TipoViaje.recoleccion_entrega) and v.origen_lugar_id:
            n_origen += 1
            fecha_hora, fuente = _salida_viaje(v)
            ubicaciones.append(
                UbicacionOut(
                    id_ubicacion=f"OR{n_origen:06d}",
                    tipo="Origen",
                    viaje_id=v.id,
                    viaje_tipo=v.tipo.value,
                    lugar=_lugar_dict(lugares.get(v.origen_lugar_id), v.origen_cp),
                    fecha_hora=fecha_hora,
                    fecha_hora_fuente=fuente,
                    hora_programada=v.hora_salida_programada,
                    distancia_km=None,
                    km_reportado=None,
                )
            )
        if v.tipo in (TipoViaje.entrega, TipoViaje.recoleccion_entrega) and v.destino_lugar_id:
            n_destino += 1
            fecha_hora, fuente = _llegada_viaje(v)
            ubicaciones.append(
                UbicacionOut(
                    id_ubicacion=f"DE{n_destino:06d}",
                    tipo="Destino",
                    viaje_id=v.id,
                    viaje_tipo=v.tipo.value,
                    lugar=_lugar_dict(lugares.get(v.destino_lugar_id), v.destino_cp),
                    fecha_hora=fecha_hora,
                    fecha_hora_fuente=fuente,
                    hora_programada=v.hora_llegada_programada,
                    distancia_km=v.distancia_km,
                    km_reportado=v.km_reportado,
                )
            )
    return ubicaciones


def construir_detalle_facturacion(session: Session, servicio_id: uuid.UUID) -> FacturacionDetalleOut:
    servicio = get_servicio(session, servicio_id)
    if modo_timbrado(servicio) == "cero":
        asegurar_mercancia_default(session, servicio)  # 1 kg de preservativos de alimentos
    cliente = session.get(Cliente, servicio.cliente_id)
    unidad = session.get(Unidad, servicio.unidad_id)
    operador = session.get(Operador, servicio.operador_id)
    viajes = session.exec(
        select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)
    ).all()
    lugares_ids = {v.origen_lugar_id for v in viajes if v.origen_lugar_id} | {
        v.destino_lugar_id for v in viajes if v.destino_lugar_id
    }
    lugares = {l.id: l for l in session.exec(select(Lugar).where(Lugar.id.in_(lugares_ids)))} if lugares_ids else {}

    mercancias = [
        MercanciaFacturarOut(
            viaje_id=m.viaje_id,
            id=m.id,
            mercancia_frecuente_id=m.mercancia_frecuente_id,
            descripcion=m.descripcion,
            bienes_transp=m.bienes_transp,
            clave_unidad=m.clave_unidad,
            cantidad=m.cantidad,
            peso_kg=m.peso_kg,
        )
        for v in viajes
        for m in session.exec(select(ViajeMercancia).where(ViajeMercancia.viaje_id == v.id)).all()
    ]

    def _acuse_url(key: str | None) -> str | None:
        if not key:
            return None
        from app.core.storage import url_firmada

        try:
            return url_firmada(key)
        except AppError:
            return None

    acuses = [
        AcuseFacturarOut(
            viaje_id=a.viaje_id,
            tipo=a.tipo.value,
            url=_acuse_url(a.archivo_key),
            referencia=a.referencia,
            pagina=a.pagina,
        )
        for v in viajes
        for a in session.exec(select(Acuse).where(Acuse.viaje_id == v.id)).all()
    ]

    descripcion_autogenerada = servicio.descripcion_concepto is None
    descripcion = servicio.descripcion_concepto or _descripcion_autogenerada(
        unidad, viajes, lugares, cliente, folios_por_viaje(session, servicio, viajes)
    )

    montos = None
    subtotal_timbrar = subtotal_efectivo(servicio)
    if subtotal_timbrar and subtotal_timbrar > Decimal(0):
        montos = MontosOut(**calcular_impuestos(subtotal_timbrar, cliente.regimen_receptor)._asdict())

    sugerencia = sugerir_para_servicio(session, servicio)
    precio_sugerido = PrecioSugeridoOut(
        monto=sugerencia.monto,
        desglose=[DesgloseLineaOut(concepto=l.concepto, monto=l.monto) for l in sugerencia.desglose],
        confianza=sugerencia.confianza,
        fuente=sugerencia.fuente,
        explicacion=sugerencia.explicacion,
        referencias=sugerencia.referencias,
        ultimos_precios_ruta=[
            {"fecha": p.fecha.isoformat(), "subtotal": str(p.subtotal)} for p in sugerencia.ultimos_precios_ruta
        ],
        rango=sugerencia.rango,
        configuracion_pendiente=sugerencia.configuracion_pendiente,
    )

    anticipado = servicio.timbrado_anticipado and servicio.estado != EstadoServicio.terminado
    checks = validar_servicio(session, servicio)
    validacion = ValidacionOut(ok=not any(c.nivel == "error" for c in checks), checks=checks, preview=montos)

    settings = get_settings()

    return FacturacionDetalleOut(
        cliente_id=cliente.id,
        unidad_id=unidad.id,
        operador_id=operador.id,
        modo="anticipado" if anticipado else "normal",
        timbrado_modo=modo_timbrado(servicio),
        servicio_id=servicio.id,
        receptor=ReceptorOut(
            razon_social=cliente.razon_social,
            rfc=cliente.rfc,
            cp_fiscal=cliente.cp_fiscal,
            regimen_fiscal=cliente.regimen_fiscal,
            regimen_receptor=cliente.regimen_receptor,
            uso_cfdi=servicio.uso_cfdi or cliente.uso_cfdi,
            metodo_pago=servicio.metodo_pago or cliente.metodo_pago_default.value,
        ),
        concepto=ConceptoOut(
            descripcion=descripcion,
            descripcion_autogenerada=descripcion_autogenerada,
            requiere_folio=cliente.requiere_folio_concepto,
            folio_cliente=servicio.folio_cliente,
            folios=[
                FolioViajeOut(
                    viaje_id=v.id,
                    destino=lugares[v.destino_lugar_id].nombre if v.destino_lugar_id in lugares else "—",
                    folio=folios_por_viaje(session, servicio, viajes).get(v.id),
                )
                for v in viajes
                if v.destino_lugar_id is not None
            ],
        ),
        desglose_precio=[
            DesgloseDestinoOut(
                viaje_id=v.id,
                destino=lugares[v.destino_lugar_id].nombre if v.destino_lugar_id in lugares else "—",
                monto=monto,
                capturado=v.monto_desglose is not None,
            )
            for v, monto in desglose_por_destino(viajes, servicio.subtotal)
        ],
        ubicaciones=_ubicaciones(viajes, lugares),
        mercancias=mercancias,
        autotransporte=AutotransporteOut(
            apodo=unidad.apodo,
            placa=unidad.placa,
            config_vehicular=unidad.config_vehicular,
            peso_bruto_vehicular=unidad.peso_bruto_vehicular,
            anio_modelo=unidad.anio_modelo,
            perm_sct=unidad.perm_sct,
            num_permiso_sct=unidad.num_permiso_sct,
            aseguradora=unidad.aseguradora_resp_civil,
            poliza=unidad.poliza_resp_civil,
        ),
        figura=FiguraOut(nombre=operador.nombre, rfc=operador.rfc, num_licencia=operador.num_licencia),
        montos=montos,
        precio_sugerido=precio_sugerido,
        acuses=acuses,
        validacion=validacion,
        facturama_configurado=bool(settings.facturama_user and settings.facturama_password),
    )


def actualizar_facturacion(
    session: Session, servicio_id: uuid.UUID, body: FacturacionUpdateIn
) -> FacturacionDetalleOut:
    servicio = get_servicio(session, servicio_id)
    if datos_fiscales_bloqueados(session, servicio):
        raise AppError(
            "conflict",
            "El servicio ya está facturado. Cancela la factura para modificar sus datos fiscales.",
            409,
            details=[{"field": "_", "issue": "servicio_facturado"}],
        )
    datos = body.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(servicio, campo, valor)
    session.add(servicio)
    session.commit()
    return construir_detalle_facturacion(session, servicio_id)


def guardar_desglose(
    session: Session, servicio_id: uuid.UUID, items: list[DesgloseDestinoIn]
) -> FacturacionDetalleOut:
    """Monto de cada destino. No es dato fiscal (no va al CFDI), así que se puede corregir
    aun con factura vigente, siempre que cuadre con el subtotal ya timbrado."""
    servicio = get_servicio(session, servicio_id)
    if servicio.estado == EstadoServicio.cancelado:
        raise AppError("conflict", "El servicio está cancelado", 409)
    viajes = {v.id: v for v in session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id)).all()}
    for item in items:
        viaje = viajes.get(item.viaje_id)
        if viaje is None or viaje.destino_lugar_id is None:
            raise AppError(
                "validation_error",
                "El viaje no es un destino de este servicio",
                422,
                details=[{"field": "viaje_id", "issue": str(item.viaje_id)}],
            )
        viaje.monto_desglose = item.monto
        session.add(viaje)
    if datos_fiscales_bloqueados(session, servicio):
        montos = [m for _v, m in desglose_por_destino(list(viajes.values()), servicio.subtotal)]
        if any(m is not None for m in montos) and (
            None in montos or sum(montos, Decimal(0)) != servicio.subtotal
        ):
            raise AppError(
                "validation_error",
                f"La factura ya está timbrada: el desglose debe sumar ${servicio.subtotal:,.2f}",
                422,
                details=[{"field": "desglose", "issue": "no_cuadra"}],
            )
    session.commit()
    return construir_detalle_facturacion(session, servicio_id)


def _resolver_clave_municipio(client: FacturamaClient, session: Session, lugar: Lugar) -> None:
    """Cachea `municipio_clave`/`localidad_clave` en el `lugar` la primera vez que se
    usa en una factura (`backend/NOTES.md` — claves numéricas del catálogo SAT).

    `flush`, no `commit`: un commit aquí expira la instancia (`expire_on_commit`) y
    el siguiente `lugar.model_dump()` devuelve un dict a medio llenar -- el commit
    real que vuelve esto durable llega más adelante en `facturar()`.
    """
    if lugar.municipio_clave:
        return
    resultado = client.resolve_postal_code(lugar.codigo_postal)
    if resultado:
        lugar.municipio_clave = resultado.get("MunicipalityCode") or None
        lugar.localidad_clave = resultado.get("LocationCode") or None
        session.add(lugar)
        session.flush()


def _lugar_para_ubicacion(
    client: FacturamaClient, session: Session, lugar: Lugar, cp: str | None
) -> dict:
    """Datos del lugar para la Carta Porte. Con un CP propio del viaje (distinto al del
    lugar) se resuelven estado, municipio y localidad de ESE CP en el catálogo del SAT y se
    omiten calle, número y colonia, que ya no corresponden."""
    if not cp or cp == lugar.codigo_postal:
        _resolver_clave_municipio(client, session, lugar)
        return lugar.model_dump()
    resultado = client.resolve_postal_code(cp)
    if not resultado or not resultado.get("StateCode"):
        raise AppError(
            "validation_error",
            f"El código postal {cp} no existe en el catálogo del SAT",
            422,
            details=[{"field": "codigo_postal", "issue": cp}],
        )
    datos = lugar.model_dump()
    datos.update(
        codigo_postal=cp,
        estado=resultado["StateCode"],
        municipio_clave=resultado.get("MunicipalityCode") or None,
        localidad_clave=resultado.get("LocationCode") or None,
        calle=None,
        num_exterior=None,
        colonia=None,
        municipio=None,
        localidad=None,
    )
    return datos


def _ubicaciones_payload(
    client: FacturamaClient, session: Session, viajes: list[Viaje], lugares: dict[uuid.UUID, Lugar]
) -> list[dict]:
    ubicaciones = []
    for v in viajes:
        if v.tipo in (TipoViaje.recoleccion, TipoViaje.recoleccion_entrega) and v.origen_lugar_id:
            lugar = lugares[v.origen_lugar_id]
            fecha_hora, _fuente = _salida_viaje(v)
            ubicaciones.append(
                {
                    "tipo": "Origen",
                    "lugar": _lugar_para_ubicacion(client, session, lugar, v.origen_cp),
                    "fecha_hora": fecha_hora,
                }
            )
        if v.tipo in (TipoViaje.entrega, TipoViaje.recoleccion_entrega) and v.destino_lugar_id:
            lugar = lugares[v.destino_lugar_id]
            fecha_hora, _fuente = _llegada_viaje(v)
            ubicaciones.append(
                {
                    "tipo": "Destino",
                    "lugar": _lugar_para_ubicacion(client, session, lugar, v.destino_cp),
                    "fecha_hora": fecha_hora,
                    "distancia_km": v.distancia_km,
                }
            )
    return ubicaciones


def facturar(session: Session, servicio_id: uuid.UUID, body: FacturarIn, current_user: Usuario) -> dict:
    """`04-facturacion-cfdi §6`."""
    servicio = get_servicio(session, servicio_id)
    if modo_timbrado(servicio) == "cero":
        asegurar_mercancia_default(session, servicio)

    factura_vigente = session.exec(
        select(Factura).where(
            Factura.servicio_id == servicio.id,
            Factura.estado.in_([EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente]),
        )
    ).first()
    if factura_vigente is not None:
        raise AppError("conflict", "Ya existe una factura vigente para este servicio", 409)

    checks = validar_servicio(session, servicio)
    if any(c.nivel == "error" for c in checks):
        raise AppError(
            "conflict",
            "El servicio tiene errores de validación pendientes",
            409,
            details=[{"field": c.campo or "_", "issue": c.regla} for c in checks if c.nivel == "error"],
        )

    cliente = session.get(Cliente, servicio.cliente_id)
    unidad = session.get(Unidad, servicio.unidad_id)
    operador = session.get(Operador, servicio.operador_id)
    montos = calcular_impuestos(subtotal_efectivo(servicio), cliente.regimen_receptor)
    if montos.total != body.total_esperado:
        raise AppError(
            "conflict",
            "El total cambió desde que abriste esta pantalla; revísalo de nuevo",
            409,
            details=[{"field": "_", "issue": "total_no_coincide"}],
        )

    settings = get_settings()
    if not (settings.facturama_user and settings.facturama_password):
        raise AppError(
            "facturama_no_configurado",
            "Todavía no hay credenciales del sandbox de Facturama configuradas; "
            "esta factura no se puede timbrar por ahora.",
            503,
        )
    if not (settings.emisor_rfc and settings.emisor_nombre and settings.emisor_lugar_expedicion):
        raise AppError(
            "facturama_no_configurado",
            "Todavía no están configurados los datos fiscales del emisor (EMISOR_RFC/"
            "EMISOR_NOMBRE/EMISOR_LUGAR_EXPEDICION).",
            503,
        )

    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)).all()
    lugares_ids = {v.origen_lugar_id for v in viajes if v.origen_lugar_id} | {
        v.destino_lugar_id for v in viajes if v.destino_lugar_id
    }
    lugares = {l.id: l for l in session.exec(select(Lugar).where(Lugar.id.in_(lugares_ids)))} if lugares_ids else {}
    mercancias = [
        {
            "bienes_transp": m.bienes_transp,
            "descripcion": m.descripcion,
            "cantidad": m.cantidad,
            "clave_unidad": m.clave_unidad,
            "unidad_desc": m.unidad_desc,
            "peso_kg": m.peso_kg,
        }
        for v in viajes
        for m in session.exec(select(ViajeMercancia).where(ViajeMercancia.viaje_id == v.id)).all()
    ]
    descripcion = servicio.descripcion_concepto or _descripcion_autogenerada(
        unidad, viajes, lugares, cliente, folios_por_viaje(session, servicio, viajes)
    )
    total_dist_rec = sum((v.distancia_km or 0) for v in viajes if v.destino_lugar_id)

    try:
        client = FacturamaClient()
    except FacturamaError as exc:
        raise AppError("facturama_no_configurado", str(exc), 503) from exc

    try:
        ubicaciones = _ubicaciones_payload(client, session, viajes, lugares)
        payload = construir_payload_cfdi(
            serie=settings.facturama_serie,
            expedition_place=settings.emisor_lugar_expedicion,
            receptor={
                "razon_social": cliente.razon_social,
                "rfc": cliente.rfc,
                "cp_fiscal": cliente.cp_fiscal,
                "regimen_fiscal": cliente.regimen_fiscal,
                "regimen_receptor": cliente.regimen_receptor.value,
                "uso_cfdi": servicio.uso_cfdi or cliente.uso_cfdi,
                "metodo_pago": servicio.metodo_pago or cliente.metodo_pago_default.value,
                "forma_pago": "99",
            },
            concepto={"descripcion": descripcion},
            montos={
                "subtotal": montos.subtotal,
                "iva_trasladado": montos.iva_trasladado,
                "iva_retenido": montos.iva_retenido,
                "total": montos.total,
            },
            ubicaciones=ubicaciones,
            mercancias=mercancias,
            autotransporte={
                "placa": unidad.placa,
                "config_vehicular": unidad.config_vehicular,
                "peso_bruto_vehicular": unidad.peso_bruto_vehicular,
                "anio_modelo": unidad.anio_modelo,
                "perm_sct": unidad.perm_sct,
                "num_permiso_sct": unidad.num_permiso_sct,
                "aseguradora": unidad.aseguradora_resp_civil,
                "poliza": unidad.poliza_resp_civil,
            },
            figura={"nombre": operador.nombre, "rfc": operador.rfc, "num_licencia": operador.num_licencia},
            total_dist_rec=total_dist_rec,
        )

        factura = session.exec(
            select(Factura).where(Factura.servicio_id == servicio.id, Factura.estado == EstadoFactura.error)
        ).first()
        if factura is None:
            factura = Factura(
                servicio_id=servicio.id,
                estado=EstadoFactura.error,
                metodo_pago=payload["PaymentMethod"],
                forma_pago=payload["PaymentForm"],
                uso_cfdi=payload["Receiver"]["CfdiUse"],
                subtotal=montos.subtotal,
                iva_trasladado=montos.iva_trasladado,
                iva_retenido=montos.iva_retenido,
                total=montos.total,
                saldo_insoluto=montos.total,
            )
        factura.payload = payload
        session.add(factura)
        session.commit()

        try:
            resultado = client.create_cfdi(payload)
        except FacturamaError as exc:
            factura.estado = EstadoFactura.error
            factura.error_detalle = str(exc)
            session.add(factura)
            session.commit()
            raise AppError("facturama_error", str(exc), 502) from exc
    except FacturamaError as exc:  # p. ej. credenciales inválidas al resolver un CP
        raise AppError("facturama_error", str(exc), 502) from exc
    finally:
        client.close()

    # NOTA: no se ha podido verificar esta forma de la respuesta contra un timbrado
    # real todavía (el CSD de la cuenta sigue vacío, ver `.misc/PENDIENTES-VLAD.md`).
    # `Id` y `Complement.TaxStamp.Uuid` sí están confirmados (`backend/NOTES.md`);
    # `Serie`/`Folio` son el eco razonable del payload de entrada -- revisar en
    # cuanto exista un timbrado real de prueba.
    complemento = resultado.get("Complement", {})
    uuid_fiscal = complemento.get("TaxStamp", {}).get("Uuid")
    factura.estado = EstadoFactura.timbrada
    factura.uuid_fiscal = uuid_fiscal
    factura.serie = resultado.get("Serie", payload["Serie"])
    factura.folio = str(resultado.get("Folio", ""))
    factura.facturama_id = resultado.get("Id")
    factura.fecha_emision = utcnow()
    factura.timbrado_at = utcnow()
    factura.error_detalle = None
    servicio.estado_facturacion = EstadoFacturacion.facturado
    session.add(factura)
    session.add(servicio)
    session.commit()
    session.refresh(factura)

    # R2 después del commit: si falla, la factura sigue timbrada (`reintentar-archivos`).
    from app.modules.facturacion.facturas import guardar_archivos

    archivos_guardados = guardar_archivos(session, factura)
    session.refresh(factura)

    # Timbrado anticipado "sin precio": con los archivos ya guardados se cancela solo
    # (motivo 02). Si la cancelación falla, la factura queda vigente y se avisa para
    # cancelarla a mano desde la factura; el servicio sigue en modo `cero`.
    cancelada_automaticamente = False
    cancelacion_error: str | None = None
    if modo_timbrado(servicio) == "cero":
        from app.modules.facturacion.facturas import cancelar

        try:
            cancelar(session, factura, "02")
        except AppError as exc:
            session.rollback()
            cancelacion_error = exc.message
        else:
            session.refresh(servicio)
            if factura.estado == EstadoFactura.cancelada:
                cancelada_automaticamente = True
                servicio.timbrado_modo = "precio"  # consumido: el siguiente timbrado es con precio
                session.add(servicio)
                session.commit()
        session.refresh(factura)

    return {
        "factura": {
            "id": str(factura.id),
            "uuid_fiscal": factura.uuid_fiscal,
            "estado": factura.estado.value,
            "total": str(factura.total),
            "pdf_url": _url_o_none(factura.pdf_key),
            "xml_url": _url_o_none(factura.xml_key),
        },
        "cancelada_automaticamente": cancelada_automaticamente,
        "cancelacion_error": cancelacion_error,
        "archivos_guardados": archivos_guardados,
    }
