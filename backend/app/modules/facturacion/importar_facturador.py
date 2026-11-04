"""Importa el reporte de emisión del Facturador Electrónico (la app anterior) como facturas.

El reporte (`Emision_<RFC>_<desde>_<hasta>.xlsx`, hoja "Reporte") trae una fila por CFDI emitido:
Fecha, UUID, Serie, Folio, RFC, Razón social, Tipo (Ingreso/Pago), Estatus Comprobante, Uso CFDI,
Forma Pago, Subtotal, Traslado, Retención, Total y "Estatus pago (MXN)", que es **lo ya cobrado**
de esa factura con sus REP (en 3,064 de 3,139 vigentes coincide exacto con el total).

- Solo se importan las de tipo Ingreso; los REP del Facturador no traen montos útiles.
- Idempotente por UUID: volver a subir un reporte más nuevo actualiza estatus y lo cobrado.
- Una factura que ya existe en la app (timbrada aquí) no se toca.
- El saldo = total − lo cobrado en el Facturador − lo aplicado en la app.
- Un RFC que no está en Clientes se da de alta con la razón social del reporte; su CP y régimen
  fiscal quedan vacíos y hay que completarlos en Catálogos antes de emitirle un REP.
"""
from __future__ import annotations

import io
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import openpyxl
from sqlmodel import Session, func, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.core.tiempo import MX
from app.modules.catalogos.models import Cliente, MetodoPago, ModoAcuse, RegimenReceptor
from app.modules.cobranza.models import PagoAplicacion
from app.modules.facturacion.models import EstadoCobro, EstadoFactura, Factura

ORIGEN = "facturador"
_CENTAVO = Decimal("0.01")
_FORMAS = {
    "POR DEFINIR": "99",
    "TRANSFERENCIA ELECTRONICA DE FONDOS": "03",
    "EFECTIVO": "01",
    "CHEQUE NOMINATIVO": "02",
    "TARJETA DE CREDITO": "04",
    "TARJETA DE DEBITO": "28",
}
_COLUMNAS = {
    "FECHA": "fecha",
    "UUID": "uuid",
    "SERIE": "serie",
    "FOLIO": "folio",
    "RFC": "rfc",
    "RAZON SOCIAL": "nombre",
    "TIPO": "tipo",
    "ESTATUS COMPROBANTE": "estatus",
    "USO CFDI": "uso_cfdi",
    "FORMA PAGO": "forma_pago",
    "SUBTOTAL (MXN)": "subtotal",
    "TRASLADO": "traslado",
    "RETENCION": "retencion",
    "TOTAL (MXN)": "total",
    "ESTATUS PAGO (MXN)": "pagado",
}


def _norm(v: object) -> str:
    s = unicodedata.normalize("NFD", str(v or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _dinero(v: object) -> Decimal:
    try:
        return abs(Decimal(str(v).replace(",", "").replace("$", "").strip() or "0")).quantize(_CENTAVO)
    except InvalidOperation:
        return Decimal("0.00")


def _fecha(v: object) -> datetime | None:
    if isinstance(v, datetime):
        local = v
    else:
        texto = str(v or "").strip()
        local = None
        for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                local = datetime.strptime(texto, fmt)  # noqa: DTZ007 — hora de México, se le pone abajo
                break
            except ValueError:
                continue
        if local is None:
            return None
    return local.replace(tzinfo=MX).astimezone(UTC)


def leer_reporte(contenido: bytes) -> list[dict[str, Any]]:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:
        raise AppError("validation_error", "El archivo no es un Excel (.xlsx) válido", 422) from exc
    try:
        for ws in wb.worksheets:
            filas = ws.iter_rows(values_only=True)
            for encabezado in filas:
                columnas = {_COLUMNAS[_norm(h)]: i for i, h in enumerate(encabezado) if _norm(h) in _COLUMNAS}
                if {"uuid", "tipo", "total", "pagado"} <= columnas.keys():
                    return [
                        {campo: (fila[i] if i < len(fila) else None) for campo, i in columnas.items()}
                        for fila in filas
                        if any(v is not None for v in fila)
                    ]
                if encabezado and any(v is not None for v in encabezado):
                    break  # la primera fila con datos no es el encabezado: siguiente hoja
    finally:
        wb.close()
    raise AppError(
        "validation_error",
        "No es el reporte de emisión del Facturador Electrónico (faltan UUID, Tipo, Total o Estatus pago)",
        422,
    )


def _cliente(session: Session, rfc: str, nombre: str, creados: list[str]) -> Cliente:
    cliente = session.exec(
        select(Cliente).where(func.upper(Cliente.rfc) == rfc).order_by(Cliente.activo.desc())
    ).first()
    if cliente is None:
        cliente = Cliente(
            razon_social=nombre or rfc,
            nombre_comercial=nombre or rfc,
            rfc=rfc,
            cp_fiscal="",  # no viene en el reporte: se completa en Catálogos antes de un REP
            regimen_fiscal="",
            regimen_receptor=RegimenReceptor.moral if len(rfc) == 12 else RegimenReceptor.fisica,
            metodo_pago_default=MetodoPago.PPD,
            modo_acuse=ModoAcuse.ninguno,
        )
        session.add(cliente)
        session.flush()
        creados.append(cliente.nombre_comercial)
    return cliente


def _estado(estatus: str) -> EstadoFactura:
    e = _norm(estatus)
    # "Emitido (Cancelación Rechazada)" sigue vigente.
    return EstadoFactura.cancelada if e.startswith("CANCELADO") else EstadoFactura.timbrada


def _aplicado_en_app(session: Session, factura_id) -> Decimal:
    return session.exec(
        select(func.coalesce(func.sum(PagoAplicacion.monto), 0)).where(PagoAplicacion.factura_id == factura_id)
    ).one() or Decimal(0)


def importar(session: Session, contenido: bytes) -> dict[str, Any]:
    filas = leer_reporte(contenido)
    resumen = {
        "creadas": 0,
        "actualizadas": 0,
        "de_la_app": 0,
        "ignoradas": 0,
        "clientes_creados": [],
        "vigentes": 0,
        "canceladas": 0,
        "pagadas": 0,
        "con_saldo": 0,
        "saldo_total": Decimal(0),
    }
    existentes = {
        (f.uuid_fiscal or "").upper(): f
        for f in session.exec(select(Factura).where(Factura.uuid_fiscal.is_not(None))).all()
    }
    for fila in filas:
        uuid_fiscal = str(fila.get("uuid") or "").strip()
        if len(uuid_fiscal) != 36:
            continue  # filas vacías o de totales
        if _norm(fila.get("tipo")) != "INGRESO":
            resumen["ignoradas"] += 1  # REP emitidos en el Facturador
            continue
        existente = existentes.get(uuid_fiscal.upper())
        if existente is not None and existente.origen != ORIGEN:
            resumen["de_la_app"] += 1  # timbrada en esta app: manda la app
            continue

        rfc = _norm(fila.get("rfc")).replace(" ", "")
        nombre = " ".join(str(fila.get("nombre") or "").split())
        cliente = _cliente(session, rfc, nombre, resumen["clientes_creados"])
        estado = _estado(str(fila.get("estatus") or ""))
        forma = _FORMAS.get(_norm(fila.get("forma_pago")), "99")
        total = _dinero(fila.get("total"))
        pagado = min(_dinero(fila.get("pagado")), total)

        f = existente or Factura(uuid_fiscal=uuid_fiscal, origen=ORIGEN)
        f.cliente_id = cliente.id
        f.receptor_nombre = nombre or None
        f.estado = estado
        serie = str(fila.get("serie") or "").strip()
        f.serie = None if not serie or _norm(serie) == "SIN SERIE" else serie
        f.folio = str(fila.get("folio") or "").strip() or None
        f.fecha_emision = _fecha(fila.get("fecha"))
        f.timbrado_at = f.fecha_emision
        f.forma_pago = forma
        f.metodo_pago = "PPD" if forma == "99" else "PUE"
        f.uso_cfdi = str(fila.get("uso_cfdi") or "").split(" - ")[0].strip() or "G03"
        f.subtotal = _dinero(fila.get("subtotal"))
        f.iva_trasladado = _dinero(fila.get("traslado"))
        f.iva_retenido = _dinero(fila.get("retencion"))
        f.total = total
        f.pagado_externo = pagado
        # Si ya había cobros parciales, el siguiente REP no es la parcialidad 1.
        f.parcialidades_externas = 1 if pagado > 0 else 0
        if estado == EstadoFactura.cancelada:
            f.saldo_insoluto = Decimal("0.00")
            f.cancelada_at = f.cancelada_at or f.fecha_emision
        else:
            aplicado = _aplicado_en_app(session, f.id) if existente is not None else Decimal(0)
            f.saldo_insoluto = max(total - pagado - Decimal(aplicado), Decimal("0.00"))
        if f.saldo_insoluto <= 0:
            f.estado_cobro = EstadoCobro.pagada
        else:
            f.estado_cobro = EstadoCobro.pendiente if f.saldo_insoluto == total else EstadoCobro.parcial
        f.updated_at = utcnow()
        session.add(f)
        existentes[uuid_fiscal.upper()] = f

        resumen["actualizadas" if existente is not None else "creadas"] += 1
        if estado == EstadoFactura.cancelada:
            resumen["canceladas"] += 1
        else:
            resumen["vigentes"] += 1
            if f.saldo_insoluto > 0:
                resumen["con_saldo"] += 1
                resumen["saldo_total"] += f.saldo_insoluto
            else:
                resumen["pagadas"] += 1
    session.commit()
    resumen["saldo_total"] = f"{resumen['saldo_total']:.2f}"
    return resumen
