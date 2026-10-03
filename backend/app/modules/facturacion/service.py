"""Orquesta impuestos, validación y la pantalla "Facturar" — `04 §3,§5,§6`."""
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, Lugar, Operador, Unidad
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.facturacion.schemas import (
    AcuseFacturarOut,
    AutotransporteOut,
    ConceptoOut,
    DesgloseLineaOut,
    FacturacionDetalleOut,
    FacturacionUpdateIn,
    FacturarIn,
    FiguraOut,
    ImpuestosPreviewIn,
    MercanciaFacturarOut,
    MontosOut,
    PrecioSugeridoOut,
    ReceptorOut,
    UbicacionOut,
    ValidacionOut,
)
from app.modules.facturacion.taxes import calcular_impuestos, subtotal_desde_total
from app.modules.facturacion.validar import validar_servicio
from app.modules.precios.service import sugerir_para_servicio
from app.modules.servicios.models import Acuse, EstadoServicio, TipoViaje, Viaje, ViajeMercancia
from app.modules.servicios.service import datos_fiscales_bloqueados, get_servicio


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
    if servicio.subtotal and servicio.subtotal > Decimal(0):
        montos = calcular_impuestos(servicio.subtotal, cliente.regimen_receptor)
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


def _lugar_dict(lugar: Lugar | None) -> dict:
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
        "codigo_postal": lugar.codigo_postal,
    }


def _descripcion_autogenerada(
    unidad: Unidad, viajes: list[Viaje], lugares: dict[uuid.UUID, Lugar]
) -> str:
    """`04-facturacion-cfdi §2`."""
    origenes = [lugares[v.origen_lugar_id].nombre for v in viajes if v.origen_lugar_id in lugares]
    destinos = [lugares[v.destino_lugar_id].nombre for v in viajes if v.destino_lugar_id in lugares]
    fechas = sorted({v.fecha for v in viajes})
    if len(fechas) <= 1:
        fecha_txt = (fechas[0] if fechas else datetime.now(UTC).date()).strftime("%d/%m/%Y")
    else:
        fecha_txt = f"{fechas[0].strftime('%d/%m/%Y')} – {fechas[-1].strftime('%d/%m/%Y')}"
    return (
        f"FLETE UNIDAD {unidad.apodo}\n"
        f"ORIGEN: {' / '.join(origenes) or '—'}\n"
        f"DESTINO: {' / '.join(destinos) or '—'}\n"
        f"FECHA: {fecha_txt}"
    )


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
                    lugar=_lugar_dict(lugares.get(v.origen_lugar_id)),
                    fecha_hora=fecha_hora,
                    fecha_hora_fuente=fuente,
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
                    lugar=_lugar_dict(lugares.get(v.destino_lugar_id)),
                    fecha_hora=fecha_hora,
                    fecha_hora_fuente=fuente,
                    distancia_km=v.distancia_km,
                    km_reportado=v.km_reportado,
                )
            )
    return ubicaciones


def construir_detalle_facturacion(session: Session, servicio_id: uuid.UUID) -> FacturacionDetalleOut:
    servicio = get_servicio(session, servicio_id)
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
    descripcion = servicio.descripcion_concepto or _descripcion_autogenerada(unidad, viajes, lugares)

    montos = None
    if servicio.subtotal and servicio.subtotal > Decimal(0):
        montos = MontosOut(**calcular_impuestos(servicio.subtotal, cliente.regimen_receptor)._asdict())

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
        modo="anticipado" if anticipado else "normal",
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
        concepto=ConceptoOut(descripcion=descripcion, descripcion_autogenerada=descripcion_autogenerada),
        ubicaciones=_ubicaciones(viajes, lugares),
        mercancias=mercancias,
        autotransporte=AutotransporteOut(
            apodo=unidad.apodo,
            placa=unidad.placa,
            config_vehicular=unidad.config_vehicular,
            peso_bruto_vehicular=unidad.peso_bruto_vehicular,
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


def facturar(session: Session, servicio_id: uuid.UUID, body: FacturarIn, current_user: Usuario) -> None:
    """`04-facturacion-cfdi §6`. El mapeo del payload CFDI (H4.2) y la llamada real a
    Facturama (H4.7) todavía no existen -- dependen del CFDI real de referencia y de
    las credenciales del sandbox (`.misc/PENDIENTES-VLAD.md`). Mientras tanto corre
    toda la validación y falla con un error claro antes de intentar timbrar nada.
    """
    servicio = get_servicio(session, servicio_id)

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
    montos = calcular_impuestos(servicio.subtotal, cliente.regimen_receptor)
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

    # El mapeo del payload CFDI + Carta Porte y la llamada al PAC llegan en H4.2/H4.7.
    raise AppError(
        "no_implementado",
        "El timbrado real todavía no está implementado (falta el mapeo del payload "
        "CFDI, H4.2, y la integración con Facturama, H4.7)",
        501,
    )
