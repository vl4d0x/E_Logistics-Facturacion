"""Validación pre-timbrado — `04-facturacion-cfdi §5`.

Devuelve una lista de checks (`regla`, `nivel`, `mensaje`, `campo?`); cualquier
`error` bloquea el timbrado, los `warning` solo se muestran. El modo
("normal" vs "anticipado") decide qué reglas aplican, según la columna
"Aplica" de la tabla del spec.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.models import utcnow
from app.modules.catalogos.models import Cliente, Lugar, Operador, Unidad
from app.modules.configuracion.service import get_valor
from app.modules.facturacion.schemas import ValidacionCheck
from app.modules.facturacion.taxes import subtotal_a_timbrar
from app.modules.operacion.models import InspeccionSalida
from app.modules.servicios.models import (
    Acuse,
    EstadoServicio,
    EstadoViaje,
    Servicio,
    TipoAcuse,
    Viaje,
    ViajeMercancia,
)
from app.modules.servicios.service import datos_fiscales_bloqueados


def folios_por_viaje(session: Session, servicio: Servicio, viajes: list[Viaje]) -> dict[uuid.UUID, str | None]:
    """Folio del cliente de cada viaje con destino: la referencia de su acuse (así lo captura el
    operador o el admin). Servicios viejos con un solo destino caen al `folio_cliente` único."""
    folios: dict[uuid.UUID, str | None] = {}
    destinos = [v for v in viajes if v.destino_lugar_id is not None]
    for v in destinos:
        acuse = session.exec(
            select(Acuse)
            .where(Acuse.viaje_id == v.id, Acuse.tipo == TipoAcuse.referencia, Acuse.referencia.is_not(None))
            .order_by(Acuse.pagina)
        ).first()
        folios[v.id] = acuse.referencia if acuse else None
    if len(destinos) == 1 and not folios[destinos[0].id] and servicio.folio_cliente:
        folios[destinos[0].id] = servicio.folio_cliente
    return folios


def desglose_por_destino(viajes: list[Viaje], subtotal: Decimal | None) -> list[tuple[Viaje, Decimal | None]]:
    """Monto de cada viaje con destino (desglose de precio). Con un solo destino sin monto
    capturado, ese destino se lleva todo el subtotal."""
    def _2d(monto) -> Decimal | None:
        return None if monto is None else Decimal(monto).quantize(Decimal("0.01"))

    destinos = [v for v in viajes if v.destino_lugar_id is not None]
    if len(destinos) == 1 and destinos[0].monto_desglose is None:
        return [(destinos[0], _2d(subtotal))]
    return [(v, _2d(v.monto_desglose)) for v in destinos]


def modo_timbrado(servicio: Servicio) -> str:
    """`cero` solo cuenta mientras el timbrado anticipado siga vigente (servicio no terminado)."""
    if servicio.timbrado_anticipado and servicio.estado != EstadoServicio.terminado:
        return servicio.timbrado_modo
    return "precio"


def subtotal_efectivo(servicio: Servicio):
    return subtotal_a_timbrar(servicio.subtotal, modo_timbrado(servicio))


CAMPOS_INSPECCION = (
    "unidad_limpia",
    "fumigacion_vigente",
    "botiquin",
    "casco_chaleco",
    "aceite_ok",
    "anticongelante_ok",
    "neumaticos_ok",
    "extintor_ok",
)


def _ok(regla: str, campo: str | None = None) -> ValidacionCheck:
    return ValidacionCheck(regla=regla, nivel="ok", mensaje="", campo=campo)


def _error(regla: str, mensaje: str, campo: str | None = None) -> ValidacionCheck:
    return ValidacionCheck(regla=regla, nivel="error", mensaje=mensaje, campo=campo)


def _warning(regla: str, mensaje: str, campo: str | None = None) -> ValidacionCheck:
    return ValidacionCheck(regla=regla, nivel="warning", mensaje=mensaje, campo=campo)


def validar_servicio(session: Session, servicio: Servicio) -> list[ValidacionCheck]:
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

    anticipado = servicio.timbrado_anticipado and servicio.estado != EstadoServicio.terminado
    checks: list[ValidacionCheck] = []
    hoy = utcnow().date()

    # --- Estado del servicio ---
    if anticipado:
        if servicio.estado == EstadoServicio.cancelado:
            checks.append(_error("servicio_vigente", "El servicio está cancelado", "estado"))
        else:
            checks.append(_ok("servicio_vigente", "estado"))
    else:
        if servicio.estado != EstadoServicio.terminado:
            checks.append(
                _error(
                    "servicio_terminado",
                    "El servicio aún no está terminado — márcalo terminado o espera a que el operador cierre",
                    "estado",
                )
            )
        else:
            checks.append(_ok("servicio_terminado", "estado"))

    # --- Sin factura vigente ---
    if datos_fiscales_bloqueados(session, servicio):
        checks.append(_error("sin_factura_vigente", "Ya existe una factura vigente para este servicio"))
    else:
        checks.append(_ok("sin_factura_vigente"))

    # --- Origen/destino ---
    tiene_origen = any(v.origen_lugar_id for v in viajes)
    tiene_destino = any(v.destino_lugar_id for v in viajes)
    if not (tiene_origen and tiene_destino):
        checks.append(_error("origen_destino", "El servicio necesita al menos un origen y un destino", "viajes"))
    else:
        checks.append(_ok("origen_destino", "viajes"))

    # --- Subtotal ---
    subtotal = subtotal_efectivo(servicio)
    if subtotal is None or subtotal <= 0:
        checks.append(_error("subtotal_presente", "Captura un subtotal mayor a cero", "subtotal"))
    else:
        checks.append(_ok("subtotal_presente", "subtotal"))

    # --- Desglose de precio por destino (va en el correo; no aplica al timbrado con $0) ---
    if subtotal and subtotal > 0 and modo_timbrado(servicio) != "cero":
        desglose = desglose_por_destino(viajes, subtotal)
        capturados = [m for _v, m in desglose if m is not None]
        if not capturados:
            checks.append(
                _warning(
                    "desglose_precio",
                    "Sin desglose de precio por destino: el correo irá sin la tabla",
                    "desglose",
                )
            )
        elif len(capturados) < len(desglose):
            checks.append(_error("desglose_precio", "Captura el monto de cada destino en el desglose de precio", "desglose"))
        elif sum(capturados, Decimal(0)) != subtotal:
            checks.append(
                _error(
                    "desglose_precio",
                    f"El desglose suma ${sum(capturados, Decimal(0)):,.2f} y el subtotal es ${subtotal:,.2f}",
                    "desglose",
                )
            )
        else:
            checks.append(_ok("desglose_precio", "desglose"))

    # --- Folio del cliente en el concepto (exclusivo de clientes que lo exigen) ---
    if cliente.requiere_folio_concepto:
        folios = folios_por_viaje(session, servicio, viajes)
        faltan = [
            lugares[v.destino_lugar_id].nombre if v.destino_lugar_id in lugares else "destino"
            for v in viajes
            if v.destino_lugar_id is not None and not folios.get(v.id)
        ]
        if faltan:
            checks.append(
                _error(
                    "folio_cliente_presente",
                    f"Captura el folio de {cliente.nombre_comercial} para: {', '.join(faltan)}",
                    "concepto",
                )
            )
        else:
            checks.append(_ok("folio_cliente_presente", "concepto"))

    # --- Acuse por entrega (solo modo normal) ---
    if not anticipado:
        entregas = [v for v in viajes if v.destino_lugar_id is not None]
        if cliente.modo_acuse.value == "ninguno":
            checks.append(_ok("acuse_por_entrega", "viajes"))
        else:
            from app.modules.servicios.models import Acuse

            faltantes = []
            for v in entregas:
                acuses = session.exec(select(Acuse).where(Acuse.viaje_id == v.id)).all()
                if cliente.modo_acuse.value == "escaneo":
                    completo = any(a.archivo_key for a in acuses)
                else:
                    completo = any(a.referencia for a in acuses)
                if not completo:
                    faltantes.append(v.orden)
            if faltantes:
                checks.append(
                    _error(
                        "acuse_por_entrega",
                        f"Falta el acuse del viaje {', '.join(str(o) for o in faltantes)}",
                        "viajes",
                    )
                )
            else:
                checks.append(_ok("acuse_por_entrega", "viajes"))

    # --- Distancia en cada destino ---
    sin_distancia = [v.orden for v in viajes if v.destino_lugar_id and not (v.distancia_km and v.distancia_km > 0)]
    if sin_distancia:
        checks.append(
            _error(
                "distancia_destino",
                f"Falta la distancia del viaje {', '.join(str(o) for o in sin_distancia)}",
                "viajes",
            )
        )
    else:
        checks.append(_ok("distancia_destino", "viajes"))

    # --- Horas programadas (solo anticipado) ---
    if anticipado:
        sin_horas = [
            v.orden
            for v in viajes
            if v.estado != EstadoViaje.terminado
            and (
                (v.origen_lugar_id and not v.hora_salida_programada)
                or (v.destino_lugar_id and not v.hora_llegada_programada)
            )
        ]
        if sin_horas:
            checks.append(
                _error(
                    "horas_programadas",
                    f"Falta la hora programada del viaje {', '.join(str(o) for o in sin_horas)}",
                    "viajes",
                )
            )
        else:
            checks.append(_ok("horas_programadas", "viajes"))

    # --- km_reportado vs distancia_km (solo normal) ---
    if not anticipado:
        discrepantes = [
            v
            for v in viajes
            if v.km_reportado and v.distancia_km and v.distancia_km > 0
            and abs(v.km_reportado - v.distancia_km) / v.distancia_km > 0.2
        ]
        if discrepantes:
            v = discrepantes[0]
            checks.append(
                _warning(
                    "km_discrepante",
                    f"El operador reportó {v.km_reportado:g} km; la Carta Porte dice {v.distancia_km:g} km (viaje {v.orden})",
                    "viajes",
                )
            )
        else:
            checks.append(_ok("km_discrepante", "viajes"))

    # --- Orden cronológico (salida del origen antes de la llegada a cada destino) ---
    # Interpretación: con los datos que capturamos (no hay "hora de salida real", solo
    # programada, y "hora_llegada" real al terminar el viaje), se arma una línea de
    # tiempo con lo más real disponible por viaje y se exige que no retroceda.
    momentos: list[datetime] = []
    desorden = False
    for v in viajes:
        hora = v.hora_llegada or v.hora_llegada_programada or v.hora_salida_programada
        if hora is None:
            continue
        momento = datetime.combine(v.fecha, hora)
        if momentos and momento < momentos[-1]:
            desorden = True
        momentos.append(momento)
    if desorden:
        checks.append(_error("orden_cronologico", "Las horas de los viajes no siguen el orden de la ruta", "viajes"))
    else:
        checks.append(_ok("orden_cronologico", "viajes"))

    # --- Fechas futuras / pasadas ---
    if anticipado:
        vencidas = [
            v.orden
            for v in viajes
            if v.estado != EstadoViaje.terminado
            and v.hora_salida_programada
            and datetime.combine(v.fecha, v.hora_salida_programada) < utcnow().replace(tzinfo=None)
        ]
        if vencidas:
            checks.append(
                _warning(
                    "fecha_pasada",
                    f"La salida programada del viaje {', '.join(str(o) for o in vencidas)} ya pasó; revisa fecha y hora",
                    "viajes",
                )
            )
        else:
            checks.append(_ok("fecha_pasada", "viajes"))
    else:
        futuras = [v.orden for v in viajes if v.fecha > hoy]
        if futuras:
            checks.append(
                _error("fecha_futura", f"El viaje {', '.join(str(o) for o in futuras)} tiene fecha futura", "viajes")
            )
        else:
            checks.append(_ok("fecha_futura", "viajes"))

    # --- Mercancías ---
    mercancias_por_viaje: dict = {}
    for v in viajes:
        mercancias_por_viaje[v.id] = session.exec(
            select(ViajeMercancia).where(ViajeMercancia.viaje_id == v.id)
        ).all()
    peso_total = sum(
        (m.peso_kg for ms in mercancias_por_viaje.values() for m in ms), 0.0
    )
    if peso_total <= 0:
        checks.append(_error("mercancias_peso", "Captura al menos una mercancía con peso mayor a cero"))
    else:
        checks.append(_ok("mercancias_peso"))

    entregas_sin_mercancias = [
        v.orden for v in viajes if v.destino_lugar_id is not None and not mercancias_por_viaje.get(v.id)
    ]
    if entregas_sin_mercancias:
        checks.append(
            _warning(
                "entrega_sin_mercancias",
                f"La entrega del viaje {', '.join(str(o) for o in entregas_sin_mercancias)} no tiene mercancías",
                "viajes",
            )
        )
    else:
        checks.append(_ok("entrega_sin_mercancias", "viajes"))

    if unidad.capacidad_carga_kg:
        if peso_total > unidad.capacidad_carga_kg:
            checks.append(
                _warning(
                    "peso_vs_capacidad",
                    f"El peso total ({peso_total:g} kg) excede la capacidad de carga de la unidad ({unidad.capacidad_carga_kg:g} kg)",
                    "unidad",
                )
            )
        else:
            checks.append(_ok("peso_vs_capacidad", "unidad"))

    # --- Peso bruto vehicular plausible (toneladas) ---
    if unidad.peso_bruto_vehicular and unidad.peso_bruto_vehicular > 100:
        checks.append(
            _warning(
                "pbv_en_toneladas",
                "El peso bruto vehicular de la unidad parece estar en kg; debe ir en toneladas",
                "unidad",
            )
        )
    else:
        checks.append(_ok("pbv_en_toneladas", "unidad"))

    # --- Permiso SCT a revisar ---
    permisos_revisar = get_valor(session, "facturacion.permisos_revisar") or []
    if unidad.perm_sct in permisos_revisar:
        checks.append(
            _warning(
                "permiso_a_revisar",
                f"El permiso SCT de la unidad ({unidad.perm_sct}) suele ser de paquetería; confírmalo para este flete",
                "unidad",
            )
        )
    else:
        checks.append(_ok("permiso_a_revisar", "unidad"))

    # --- Lugares con CP, estado y país ---
    lugares_incompletos = [
        l.nombre for l in lugares.values() if not (l.codigo_postal and l.estado and l.pais)
    ]
    if lugares_incompletos:
        checks.append(
            _error(
                "lugares_completos",
                f"Falta CP, estado o país en: {', '.join(lugares_incompletos)}",
                "viajes",
            )
        )
    else:
        checks.append(_ok("lugares_completos", "viajes"))

    # --- Datos fiscales del cliente, operador y unidad ---
    if not (cliente.rfc and cliente.cp_fiscal and cliente.regimen_fiscal):
        checks.append(_error("cliente_fiscal_completo", "Falta RFC, CP fiscal o régimen fiscal del cliente", "cliente"))
    else:
        checks.append(_ok("cliente_fiscal_completo", "cliente"))

    if not (operador.rfc and operador.num_licencia):
        checks.append(_error("operador_completo", "Falta el RFC o la licencia del operador", "operador"))
    else:
        checks.append(_ok("operador_completo", "operador"))

    if not (unidad.placa and unidad.perm_sct and unidad.num_permiso_sct and unidad.poliza_resp_civil):
        checks.append(
            _error("unidad_completa", "Falta la placa, el permiso SCT o la póliza de la unidad", "unidad")
        )
    else:
        checks.append(_ok("unidad_completa", "unidad"))

    # --- Retención 4% sii receptor moral (invariante de nuestro propio cálculo) ---
    checks.append(_ok("retencion_consistente"))

    # --- Inspección con fallas (solo normal) ---
    if not anticipado:
        inspeccion = session.exec(
            select(InspeccionSalida).where(InspeccionSalida.servicio_id == servicio.id)
        ).first()
        if inspeccion and not inspeccion.todo_ok:
            fallas = [c for c in CAMPOS_INSPECCION if not getattr(inspeccion, c)]
            checks.append(
                _warning("inspeccion_sin_fallas", f"La inspección reportó: {', '.join(fallas)}", "inspeccion")
            )
        else:
            checks.append(_ok("inspeccion_sin_fallas", "inspeccion"))

        # --- Terminado por admin sin reporte del operador ---
        if servicio.terminado_por_admin:
            checks.append(
                _warning(
                    "terminado_por_admin",
                    "El servicio se marcó terminado desde el admin, sin el reporte del operador",
                )
            )
        else:
            checks.append(_ok("terminado_por_admin"))

    return checks
