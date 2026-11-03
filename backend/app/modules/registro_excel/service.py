"""Facturar con el Excel de registros: subir el archivo, proponer los datos de una fila,
crear el servicio terminado y devolver el Excel con el número de factura escrito."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlmodel import Session, delete, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.core.tiempo import MX, ahora_mx, hoy_mx
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, Lugar, MercanciaFrecuente, Operador, Unidad
from app.modules.catalogos.service import clientes_del_catalogo
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.registro_excel import excel
from app.modules.registro_excel.matching import (
    UMBRAL_ALTA,
    UMBRAL_MEDIA,
    UNIDAD_ALIAS_FIJOS,
    Candidato,
    Indice,
    confianza,
    kg_en_texto,
    normalizar,
    partir_destinos,
    tokens,
    varios,
)
from app.modules.registro_excel.models import (
    RegistroExcel,
    RegistroExcelAlias,
    RegistroExcelFila,
    RegistroExcelServicio,
)
from app.modules.registro_excel.schemas import CrearDesdeFilaIn, LugarElegidoIn
from app.modules.servicios import service as servicios_service
from app.modules.servicios.models import (
    Acuse,
    EstadoServicio,
    EstadoViaje,
    Servicio,
    TipoAcuse,
    TipoViaje,
    Viaje,
    ViajeMercancia,
)
from app.modules.servicios.schemas import ServicioCreate, ViajeCreate, ViajeMercanciaIn

RFC_GENERICO = "XAXX010101000"
KM_GENERICO = 70.0
ESTADO_GENERICO = "MEX"
_VIGENTES = (EstadoFactura.timbrada, EstadoFactura.cancelacion_pendiente)


def _no_encontrado(msg: str) -> AppError:
    return AppError("not_found", msg, 404)


def huella(datos: dict) -> str:
    return "|".join(normalizar(datos.get(k)) for k in ("fecha", "cliente", "destino"))


# --- Archivo vigente ----------------------------------------------------------------

def registro_vigente(session: Session) -> RegistroExcel | None:
    return session.exec(select(RegistroExcel).order_by(RegistroExcel.subido_at.desc())).first()


def _registro_o_404(session: Session) -> RegistroExcel:
    registro = registro_vigente(session)
    if registro is None:
        raise _no_encontrado("Todavía no has subido el Excel de registros")
    return registro


def resumen(session: Session, registro: RegistroExcel | None) -> dict | None:
    if registro is None:
        return None
    return {
        "nombre_archivo": registro.nombre_archivo,
        "hoja": registro.hoja,
        "total_filas": registro.total_filas,
        "ultima_fila": registro.ultima_fila,
        "subido_at": registro.subido_at,
    }


def subir(session: Session, nombre_archivo: str, contenido: bytes, usuario: Usuario) -> dict:
    hoja, columnas, filas = excel.leer_registros(contenido)
    if not filas:
        raise AppError("validation_error", "La hoja de registros no tiene filas", 422)

    for viejo in session.exec(select(RegistroExcel)).all():
        session.exec(delete(RegistroExcelFila).where(RegistroExcelFila.registro_id == viejo.id))
        session.delete(viejo)
    session.flush()

    registro = RegistroExcel(
        nombre_archivo=nombre_archivo or "registros.xlsx",
        hoja=hoja,
        columnas=columnas,
        contenido=contenido,
        total_filas=len(filas),
        ultima_fila=max(f for f, _ in filas),
        subido_at=utcnow(),
        subido_por=usuario.id,
    )
    session.add(registro)
    session.flush()
    session.add_all(RegistroExcelFila(registro_id=registro.id, fila=f, datos=d) for f, d in filas)

    # Los servicios ya creados siguen ligados a su fila aunque se hayan insertado filas antes.
    por_huella: dict[str, list[int]] = {}
    por_fila = {}
    for f, d in filas:
        h = huella(d)
        por_huella.setdefault(h, []).append(f)
        por_fila[f] = h
    reubicados = 0
    for enlace in session.exec(select(RegistroExcelServicio)).all():
        if por_fila.get(enlace.fila) == enlace.huella:
            continue
        candidatas = por_huella.get(enlace.huella, [])
        if len(candidatas) == 1:
            enlace.fila = candidatas[0]
            session.add(enlace)
            reubicados += 1
    session.commit()
    session.refresh(registro)
    return {**resumen(session, registro), "enlaces_reubicados": reubicados}


# --- Estado de cada fila (¿ya se facturó?) ----------------------------------------------

def _enlaces(session: Session) -> dict[int, RegistroExcelServicio]:
    return {e.fila: e for e in session.exec(select(RegistroExcelServicio)).all()}


def _estado_servicio(session: Session, enlace: RegistroExcelServicio | None, datos: dict) -> dict | None:
    if enlace is None or enlace.huella != huella(datos):
        return None
    servicio = session.get(Servicio, enlace.servicio_id)
    if servicio is None or servicio.estado == EstadoServicio.cancelado:
        return None
    factura = session.exec(
        select(Factura).where(Factura.servicio_id == servicio.id, Factura.estado.in_(_VIGENTES))
    ).first()
    return {
        "servicio_id": servicio.id,
        "numero": servicio.numero,
        "estado": servicio.estado.value,
        "factura_folio": factura.folio if factura else None,
        "factura_id": factura.id if factura else None,
    }


def _fila_out(session: Session, fila: RegistroExcelFila, enlace: RegistroExcelServicio | None) -> dict:
    return {
        "fila": fila.fila,
        "datos": fila.datos,
        "servicio": _estado_servicio(session, enlace, fila.datos),
    }


def listar_filas(session: Session, solo_pendientes: bool, limite: int) -> list[dict]:
    registro = _registro_o_404(session)
    enlaces = _enlaces(session)
    filas = session.exec(
        select(RegistroExcelFila)
        .where(RegistroExcelFila.registro_id == registro.id)
        .order_by(RegistroExcelFila.fila.desc())
        .limit(max(limite * 6, 200))
    ).all()
    res = []
    for f in filas:
        item = _fila_out(session, f, enlaces.get(f.fila))
        if solo_pendientes and (f.datos.get("factura") is not None or (item["servicio"] or {}).get("factura_folio")):
            continue
        res.append(item)
        if len(res) >= limite:
            break
    return res


# --- Propuesta: lo que la app encontró para una fila -----------------------------------

def _alias(session: Session, tipo: str, texto: str, cliente_id: uuid.UUID | None = None) -> uuid.UUID | None:
    t = normalizar(texto)
    if not t:
        return None
    a = session.exec(
        select(RegistroExcelAlias).where(
            RegistroExcelAlias.tipo == tipo,
            RegistroExcelAlias.texto == t,
            RegistroExcelAlias.cliente_id == cliente_id if cliente_id else RegistroExcelAlias.cliente_id.is_(None),
        )
    ).first()
    return a.objetivo_id if a else None


def _recordar(session: Session, tipo: str, texto: str | None, objetivo_id: uuid.UUID, cliente_id: uuid.UUID | None = None) -> None:
    t = normalizar(texto)
    if not t:
        return
    a = session.exec(
        select(RegistroExcelAlias).where(
            RegistroExcelAlias.tipo == tipo,
            RegistroExcelAlias.texto == t,
            RegistroExcelAlias.cliente_id == cliente_id if cliente_id else RegistroExcelAlias.cliente_id.is_(None),
        )
    ).first()
    if a is None:
        a = RegistroExcelAlias(tipo=tipo, texto=t, cliente_id=cliente_id, objetivo_id=objetivo_id)
    else:
        a.objetivo_id = objetivo_id
        a.updated_at = utcnow()
    session.add(a)


def _elegido(objetivo_id, nombre, score: float, fuente: str) -> dict:
    return {"id": objetivo_id, "nombre": nombre, "score": round(score, 2), "confianza": confianza(score), "fuente": fuente}


def _buscar_cliente(session: Session, texto: str) -> dict | None:
    clientes = session.exec(select(Cliente).where(Cliente.activo == True)).all()
    alias = _alias(session, "cliente", texto)
    if alias and (c := next((c for c in clientes if c.id == alias), None)):
        return _elegido(c.id, c.nombre_comercial, 1.0, "recordado")
    indice = Indice([Candidato(c.id, c.nombre_comercial, alias=[c.razon_social]) for c in clientes])
    res = indice.buscar(texto or "", 1)
    if res and res[0][1] >= UMBRAL_MEDIA:
        return _elegido(res[0][0].id, res[0][0].nombre, res[0][1], "parecido")
    return None


def _buscar_operador(session: Session, texto: str) -> tuple[dict | None, list[str]]:
    operadores = session.exec(select(Operador).where(Operador.activo == True)).all()
    nombres = varios(texto)
    alias = _alias(session, "operador", texto)
    if alias and (o := next((o for o in operadores if o.id == alias), None)):
        return _elegido(o.id, o.nombre, 1.0, "recordado"), nombres
    indice = Indice([Candidato(o.id, o.nombre) for o in operadores])
    for nombre in nombres:
        res = indice.buscar(nombre, 1)
        if res and res[0][1] >= UMBRAL_ALTA:
            return _elegido(res[0][0].id, res[0][0].nombre, res[0][1], "parecido"), nombres
    return None, nombres


def _buscar_unidad(session: Session, texto: str) -> dict | None:
    unidades = session.exec(select(Unidad).where(Unidad.activo == True)).all()
    alias = _alias(session, "unidad", texto)
    if alias and (u := next((u for u in unidades if u.id == alias), None)):
        return _elegido(u.id, u.apodo, 1.0, "recordado")
    placas = {normalizar(u.placa).replace(" ", ""): u for u in unidades}
    t = tokens(texto)
    for tok in t:  # "KR9417A SAVEIRO BLANCA": la placa manda
        if tok in placas:
            return _elegido(placas[tok].id, placas[tok].apodo, 1.0, "placa")
    n = normalizar(texto)
    for apodo_excel, placa in UNIDAD_ALIAS_FIJOS.items():
        if n == apodo_excel or set(apodo_excel.split()) <= set(n.split()):
            u = placas.get(placa)
            if u is not None:
                return _elegido(u.id, u.apodo, 1.0, "regla")
    indice = Indice([Candidato(u.id, u.apodo) for u in unidades])
    res = indice.buscar(texto or "", 1)
    if res and res[0][1] >= UMBRAL_ALTA:
        return _elegido(res[0][0].id, res[0][0].nombre, res[0][1], "parecido")
    return None


def _dueno_catalogo(cliente: Cliente) -> uuid.UUID:
    return cliente.hereda_de_id or cliente.id


def _lugares(session: Session, cliente: Cliente) -> list[Lugar]:
    ids = clientes_del_catalogo(session, cliente.id)
    return session.exec(
        select(Lugar).where(Lugar.activo == True, Lugar.cliente_id.in_(ids) | (Lugar.cliente_id == None))
    ).all()


def _indice_lugares(lugares: list[Lugar]) -> Indice:
    return Indice([
        Candidato(
            l.id,
            l.nombre,
            alias=[l.nombre_remitente_destinatario] if l.nombre_remitente_destinatario else [],
            ubicacion=[x for x in (l.municipio, l.localidad, l.referencia) if x],
            preferido=l.es_origen_predeterminado,
        )
        for l in lugares
    ])


def _lugar_out(l: Lugar) -> dict:
    return {"id": l.id, "nombre": l.nombre, "codigo_postal": l.codigo_postal}


def _km(l: Lugar | None) -> tuple[float, bool]:
    if l is not None and l.km_confirmado and l.distancia_km:
        return l.distancia_km, True
    return KM_GENERICO, False


def _propuesta_lugar(
    session: Session, texto: str, indice: Indice, lugares: dict[uuid.UUID, Lugar], dueno: uuid.UUID,
    resultados=None,
) -> dict:
    resultados = resultados if resultados is not None else indice.buscar(texto)
    candidatos = [{**_lugar_out(lugares[c.id]), "score": round(s, 2)} for c, s in resultados if c.id in lugares]
    elegido, score, fuente = None, 0.0, None
    alias = _alias(session, "lugar", texto, dueno)
    if alias and alias in lugares:
        elegido, score, fuente = lugares[alias], 1.0, "recordado"
    elif resultados and resultados[0][1] >= UMBRAL_MEDIA:
        elegido, score, fuente = lugares[resultados[0][0].id], resultados[0][1], "parecido"
    km, km_confirmado = _km(elegido)
    return {
        "texto": texto,
        "lugar": _lugar_out(elegido) if elegido else None,
        "score": round(score, 2),
        "confianza": confianza(score) if elegido else "ninguna",
        "fuente": fuente,
        "candidatos": candidatos,
        "distancia_km": km,
        "km_confirmado": km_confirmado,
    }


def _mercancia_sugerida(session: Session, cliente: Cliente) -> uuid.UUID | None:
    ids = clientes_del_catalogo(session, cliente.id)
    ultima = session.exec(
        select(ViajeMercancia.mercancia_frecuente_id)
        .join(Viaje, ViajeMercancia.viaje_id == Viaje.id)
        .join(Servicio, Viaje.servicio_id == Servicio.id)
        .join(MercanciaFrecuente, MercanciaFrecuente.id == ViajeMercancia.mercancia_frecuente_id)
        .where(Servicio.cliente_id == cliente.id, MercanciaFrecuente.activo == True)
        .order_by(ViajeMercancia.created_at.desc())
    ).first()
    if ultima:
        return ultima
    primera = session.exec(
        select(MercanciaFrecuente)
        .where(MercanciaFrecuente.cliente_id.in_(ids), MercanciaFrecuente.activo == True)
        .order_by(MercanciaFrecuente.nombre_humano)
    ).first()
    return primera.id if primera else None


def _decimal(v: object) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        d = Decimal(str(v).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        return None
    return d.quantize(Decimal("0.01")) if d > 0 else None


def _fecha(v: object) -> date | None:
    try:
        return date.fromisoformat(str(v)) if v else None
    except ValueError:
        return None


def propuesta(session: Session, numero_fila: int, cliente_id: uuid.UUID | None = None) -> dict:
    registro = _registro_o_404(session)
    fila = session.exec(
        select(RegistroExcelFila).where(
            RegistroExcelFila.registro_id == registro.id, RegistroExcelFila.fila == numero_fila
        )
    ).first()
    if fila is None:
        raise _no_encontrado(f"La fila {numero_fila} está vacía o no existe en {registro.nombre_archivo}")
    d = fila.datos
    avisos: list[str] = []
    out = _fila_out(session, fila, _enlaces(session).get(numero_fila))

    if d.get("factura") is not None:
        avisos.append(f"En el Excel esta fila ya tiene factura: {d['factura']}")
    if out["servicio"]:
        s = out["servicio"]
        avisos.append(
            f"De esta fila ya se creó el servicio #{s['numero']}"
            + (f" (factura {s['factura_folio']})" if s["factura_folio"] else " (sin facturar)")
        )

    cliente_p = _buscar_cliente(session, d.get("cliente") or "")
    if cliente_id is not None:  # el admin eligió otro cliente: se buscan sus lugares
        elegido = session.get(Cliente, cliente_id)
        if elegido is None:
            raise _no_encontrado("Cliente no encontrado")
        cliente_p = _elegido(elegido.id, elegido.nombre_comercial, 1.0, "elegido")
    operador_p, operadores_excel = _buscar_operador(session, d.get("operador") or "")
    unidad_p = _buscar_unidad(session, d.get("unidad") or "")
    if cliente_p is None:
        avisos.append(f"El cliente “{d.get('cliente') or '—'}” no está en el catálogo: elígelo o dalo de alta")
    if operador_p is None:
        avisos.append(f"El operador “{d.get('operador') or '—'}” no está en el catálogo")
    elif len(operadores_excel) > 1:
        avisos.append(f"El Excel trae {len(operadores_excel)} operadores ({d.get('operador')}): la Carta Porte lleva uno, revisa cuál")
    if unidad_p is None:
        avisos.append(f"La unidad “{d.get('unidad') or '—'}” no está en el catálogo")
    subtotal = _decimal(d.get("subtotal"))
    if subtotal is None:
        avisos.append("La fila no trae subtotal: captúralo")

    origen = destinos = None
    mercancia_id = None
    modo_acuse = requiere_folio = None
    if cliente_p is not None:
        cliente = session.get(Cliente, cliente_p["id"])
        modo_acuse = cliente.modo_acuse.value
        requiere_folio = cliente.requiere_folio_concepto
        dueno = _dueno_catalogo(cliente)
        lugares_l = _lugares(session, cliente)
        lugares = {l.id: l for l in lugares_l}
        indice = _indice_lugares(lugares_l)

        # Origen: casi siempre el cliente mismo ("CHEMITAL") → su origen predeterminado.
        texto_origen = d.get("origen") or ""
        predeterminado = next(
            (l for l in lugares_l if l.es_origen_predeterminado and l.cliente_id == cliente.id), None
        ) or next((l for l in lugares_l if l.es_origen_predeterminado and l.cliente_id == dueno), None)
        origen = _propuesta_lugar(session, texto_origen, indice, lugares, dueno)
        if predeterminado is not None and origen["fuente"] != "recordado":
            nombre_cliente = Indice([Candidato(cliente.id, cliente.nombre_comercial, alias=[cliente.razon_social])])
            if not texto_origen or nombre_cliente.puntaje(texto_origen, nombre_cliente.candidatos[0]) >= UMBRAL_ALTA:
                origen.update(lugar=_lugar_out(predeterminado), score=1.0, confianza="alta", fuente="predeterminado")

        destinos = []
        for g in partir_destinos(d.get("destino") or "", indice):
            destinos.append(_propuesta_lugar(session, g.texto, indice, lugares, dueno, g.resultados))
        if not destinos:
            avisos.append("La fila no trae destino")
        mercancia_id = _mercancia_sugerida(session, cliente)

    return {
        **out,
        "registro": resumen(session, registro),
        "cliente": cliente_p,
        "modo_acuse": modo_acuse,
        "requiere_folio": requiere_folio,
        "operador": operador_p,
        "unidad": unidad_p,
        "fecha": d.get("fecha"),
        "subtotal": subtotal,
        "origen": origen,
        "destinos": destinos,
        "kg_sugerido": kg_en_texto(d.get("notas")) or kg_en_texto(d.get("ref")),
        "mercancia_sugerida_id": mercancia_id,
        "avisos": avisos,
        "lugar_generico": {"rfc": RFC_GENERICO, "estado": ESTADO_GENERICO, "distancia_km": KM_GENERICO},
    }


# --- Crear el servicio de la fila ---------------------------------------------------

def _resolver_lugar(session: Session, elegido: LugarElegidoIn, cliente: Cliente) -> tuple[Lugar, bool]:
    if elegido.lugar_id is not None:
        lugar = session.get(Lugar, elegido.lugar_id)
        if lugar is None:
            raise _no_encontrado("Lugar no encontrado")
        return lugar, False
    nuevo = elegido.nuevo
    dueno = _dueno_catalogo(cliente)
    existente = session.exec(
        select(Lugar).where(Lugar.cliente_id == dueno, Lugar.nombre == nuevo.nombre, Lugar.activo == True)
    ).first()
    if existente is not None:
        return existente, False
    lugar = Lugar(
        cliente_id=dueno,
        nombre=nuevo.nombre,
        rfc_remitente_destinatario=RFC_GENERICO,
        estado=ESTADO_GENERICO,
        codigo_postal=nuevo.codigo_postal,
        distancia_km=KM_GENERICO,
        km_confirmado=True,
        referencia="Dado de alta desde el Excel de registros (RFC genérico)",
    )
    session.add(lugar)
    session.flush()
    return lugar, True


def _utc(momento_mx: datetime) -> datetime:
    return momento_mx.replace(tzinfo=MX).astimezone(UTC)


def _horarios(fecha: date, destinos: int) -> list[datetime]:
    """Hora (México) de salida del origen y de llegada a cada destino. El Excel no trae horas:
    salida 9:00 y una hora por destino; si el servicio es de hoy, termina antes de ahora."""
    paso = timedelta(hours=1)
    base = datetime.combine(fecha, time(9, 0))
    if fecha >= hoy_mx():
        paso = timedelta(minutes=15)
        base = max(datetime.combine(fecha, time(0, 5)), ahora_mx() - paso * (destinos + 1))
    return [base + paso * i for i in range(destinos + 1)]


def crear_servicio(session: Session, numero_fila: int, data: CrearDesdeFilaIn, usuario: Usuario) -> Servicio:
    registro = _registro_o_404(session)
    fila = session.exec(
        select(RegistroExcelFila).where(
            RegistroExcelFila.registro_id == registro.id, RegistroExcelFila.fila == numero_fila
        )
    ).first()
    if fila is None:
        raise _no_encontrado(f"La fila {numero_fila} no existe en el Excel")
    enlace = _enlaces(session).get(numero_fila)
    previo = _estado_servicio(session, enlace, fila.datos)
    if previo is not None:
        raise AppError(
            "conflict",
            f"De esta fila ya se creó el servicio #{previo['numero']}",
            409,
            details=[{"field": "fila", "issue": str(previo["servicio_id"])}],
        )
    cliente = session.get(Cliente, data.cliente_id)
    if cliente is None:
        raise _no_encontrado("Cliente no encontrado")

    origen, _ = _resolver_lugar(session, data.origen, cliente)
    destinos = [_resolver_lugar(session, d, cliente)[0] for d in data.destinos]
    session.commit()  # los lugares nuevos quedan aunque algo de abajo falle

    viajes_in = [ViajeCreate(tipo=TipoViaje.recoleccion, fecha=data.fecha, origen_lugar_id=origen.id)]
    for d, lugar in zip(data.destinos, destinos):
        km = d.distancia_km or _km(lugar)[0]
        viajes_in.append(
            ViajeCreate(
                tipo=TipoViaje.entrega,
                fecha=data.fecha,
                destino_lugar_id=lugar.id,
                distancia_km=km,
                mercancias=[
                    ViajeMercanciaIn(mercancia_frecuente_id=m.mercancia_frecuente_id, cantidad=m.cantidad, peso_kg=m.peso_kg)
                    for m in d.mercancias
                ] or None,
            )
        )
    servicio = servicios_service.create_servicio(
        session,
        ServicioCreate(
            cliente_id=data.cliente_id,
            unidad_id=data.unidad_id,
            operador_id=data.operador_id,
            fecha=data.fecha,
            subtotal=data.subtotal,
            notas=f"Creado desde el Excel de registros (fila {numero_fila})",
            viajes=viajes_in,
        ),
        usuario,
    )

    # Terminado: el servicio ya se hizo, solo falta facturarlo.
    viajes = session.exec(select(Viaje).where(Viaje.servicio_id == servicio.id).order_by(Viaje.orden)).all()
    horas = _horarios(data.fecha, len(data.destinos))
    for i, v in enumerate(viajes):
        momento = horas[min(i, len(horas) - 1)]
        v.estado = EstadoViaje.terminado
        v.terminado_at = _utc(momento)
        v.terminado_por = usuario.id
        if v.tipo == TipoViaje.entrega:
            d = data.destinos[i - 1]
            v.hora_llegada = momento.time()
            v.sin_acuse = d.sin_acuse
            folio = (d.folio or "").strip()
            if folio and not d.sin_acuse:
                session.add(
                    Acuse(viaje_id=v.id, tipo=TipoAcuse.referencia, referencia=folio, subido_por=usuario.id, subido_at=utcnow())
                )
        session.add(v)
    servicio.estado = EstadoServicio.terminado
    servicio.iniciado_at = _utc(horas[0])
    servicio.terminado_at = _utc(horas[-1])
    servicio.terminado_por_admin = True
    servicio.updated_at = utcnow()
    session.add(servicio)

    if enlace is not None:
        session.delete(enlace)
        session.flush()
    session.add(RegistroExcelServicio(servicio_id=servicio.id, fila=numero_fila, huella=huella(fila.datos)))

    # Recordar lo elegido para la próxima vez.
    d = fila.datos
    _recordar(session, "cliente", d.get("cliente"), data.cliente_id)
    _recordar(session, "operador", d.get("operador"), data.operador_id)
    _recordar(session, "unidad", d.get("unidad"), data.unidad_id)
    dueno = _dueno_catalogo(cliente)
    _recordar(session, "lugar", data.origen.texto_excel, origen.id, dueno)
    for dest, lugar in zip(data.destinos, destinos):
        _recordar(session, "lugar", dest.texto_excel, lugar.id, dueno)
    session.commit()
    session.refresh(servicio)
    return servicio


# --- Excel con las facturas ------------------------------------------------------------

def descargar(session: Session) -> tuple[bytes, str, list[int]]:
    registro = _registro_o_404(session)
    filas = {
        f.fila: f.datos
        for f in session.exec(select(RegistroExcelFila).where(RegistroExcelFila.registro_id == registro.id)).all()
    }
    valores: dict[int, str] = {}
    for enlace in session.exec(select(RegistroExcelServicio)).all():
        datos = filas.get(enlace.fila)
        if datos is None or enlace.huella != huella(datos) or datos.get("factura") is not None:
            continue
        factura = session.exec(
            select(Factura).where(Factura.servicio_id == enlace.servicio_id, Factura.estado.in_(_VIGENTES))
        ).first()
        if factura is not None and factura.folio:
            valores[enlace.fila] = factura.folio
    letra = registro.columnas.get("factura", "K")
    contenido, escritas = excel.escribir_columna(registro.contenido, registro.hoja, letra, valores)
    return contenido, registro.nombre_archivo, escritas
