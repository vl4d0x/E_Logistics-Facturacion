"""Sugeridor de precio — `07-precio-sugerido §2-4`. Puro: recibe historial ya
consultado de la DB y parámetros, devuelve la sugerencia. Sin red, sin SQL aquí.

Nivel 1 (tarifa pactada) NO está implementado todavía — depende de la tabla
`tarifa_pactada` y de la pantalla Configuración → Precios y tarifas (H4.6),
que no se ha construido. Mientras tanto la cascada empieza en el nivel 2.
"""
import statistics
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class PuntoHistorial:
    servicio_numero: int
    fecha: date
    subtotal: Decimal


@dataclass
class PuntoKm:
    subtotal: Decimal
    km: float


@dataclass
class DesgloseLinea:
    concepto: str
    monto: Decimal


@dataclass
class Sugerencia:
    monto: Decimal | None
    desglose: list[DesgloseLinea]
    confianza: str | None  # "alta" | "media" | "baja" | None
    fuente: str | None  # "historial_ruta" | "historial_km" | "formula" | None
    explicacion: str
    referencias: list[int]  # números de servicio usados
    ultimos_precios_ruta: list[PuntoHistorial]
    rango: tuple[Decimal, Decimal] | None
    configuracion_pendiente: bool


def _redondear(valor: Decimal, redondeo: Decimal) -> Decimal:
    if redondeo <= 0:
        return valor
    multiplo = (valor / redondeo).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return multiplo * redondeo


def _sin_referencia(ultimos_precios_ruta: list[PuntoHistorial], configuracion_pendiente: bool) -> Sugerencia:
    return Sugerencia(
        monto=None,
        desglose=[],
        confianza=None,
        fuente=None,
        explicacion="Sin referencias para esta ruta",
        referencias=[],
        ultimos_precios_ruta=ultimos_precios_ruta,
        rango=None,
        configuracion_pendiente=configuracion_pendiente,
    )


def sugerir_precio(
    *,
    n_destinos: int,
    km: float | None,
    historial_ruta: list[PuntoHistorial],
    historial_km_cliente: list[PuntoKm],
    tarifa_base: Decimal | None,
    tarifa_km: Decimal | None,
    redondeo: Decimal = Decimal(50),
) -> Sugerencia:
    historial_ruta = sorted(historial_ruta, key=lambda p: p.fecha, reverse=True)
    ultimos_precios_ruta = historial_ruta[:3]
    rango = (
        (min(p.subtotal for p in ultimos_precios_ruta), max(p.subtotal for p in ultimos_precios_ruta))
        if ultimos_precios_ruta
        else None
    )
    configuracion_pendiente = tarifa_base is None or tarifa_km is None

    # --- Nivel 2: misma ruta, mismo cliente ---
    if historial_ruta:
        ultimos5 = historial_ruta[:5]
        if len(ultimos5) >= 2:
            ultimos3 = ultimos5[:3]
            if len(ultimos3) >= 2:
                base = ultimos3[0].subtotal
                consistentes = all(
                    base == 0 or abs(p.subtotal - base) / base <= Decimal("0.10") for p in ultimos3
                )
            else:
                consistentes = True
            if len(ultimos3) >= 3 and consistentes:
                elegido = ultimos5[0]
                monto = elegido.subtotal
                return Sugerencia(
                    monto=monto,
                    desglose=[
                        DesgloseLinea(
                            f"Último precio de esta ruta · {elegido.fecha.isoformat()} · servicio #{elegido.servicio_numero}",
                            monto,
                        )
                    ],
                    confianza="alta",
                    fuente="historial_ruta",
                    explicacion="Precio más reciente de esta misma ruta",
                    referencias=[elegido.servicio_numero],
                    ultimos_precios_ruta=ultimos_precios_ruta,
                    rango=rango,
                    configuracion_pendiente=configuracion_pendiente,
                )
            mediana = Decimal(str(statistics.median(float(p.subtotal) for p in ultimos5))).quantize(
                Decimal("0.01")
            )
            return Sugerencia(
                monto=mediana,
                desglose=[DesgloseLinea(f"Mediana de los últimos {len(ultimos5)} servicios de esta ruta", mediana)],
                confianza="alta",
                fuente="historial_ruta",
                explicacion="Los precios recientes de esta ruta no son consistentes; se usa la mediana",
                referencias=[p.servicio_numero for p in ultimos5],
                ultimos_precios_ruta=ultimos_precios_ruta,
                rango=rango,
                configuracion_pendiente=configuracion_pendiente,
            )
        unico = ultimos5[0]
        return Sugerencia(
            monto=unico.subtotal,
            desglose=[
                DesgloseLinea(
                    f"Último precio de esta ruta · {unico.fecha.isoformat()} · servicio #{unico.servicio_numero}",
                    unico.subtotal,
                )
            ],
            confianza="media",
            fuente="historial_ruta",
            explicacion="Solo hay un servicio previo de esta ruta",
            referencias=[unico.servicio_numero],
            ultimos_precios_ruta=ultimos_precios_ruta,
            rango=rango,
            configuracion_pendiente=configuracion_pendiente,
        )

    # --- Nivel 3: $/km del cliente ---
    if km and km > 0 and historial_km_cliente:
        ratios = [float(p.subtotal) / p.km for p in historial_km_cliente if p.km > 0]
        if ratios:
            mediana_ratio = statistics.median(ratios)
            monto = Decimal(str(mediana_ratio * km)).quantize(Decimal("0.01"))
            monto_redondeado = _redondear(monto, redondeo)
            desglose = [DesgloseLinea(f"{km:g} km × ${mediana_ratio:.2f}/km (mediana de {len(ratios)} servicios)", monto)]
            if monto_redondeado != monto:
                desglose.append(DesgloseLinea(f"Redondeo a ${redondeo:g}", monto_redondeado - monto))
            return Sugerencia(
                monto=monto_redondeado,
                desglose=desglose,
                confianza="media" if len(ratios) >= 5 else "baja",
                fuente="historial_km",
                explicacion="Calculado con el $/km histórico de este cliente",
                referencias=[],
                ultimos_precios_ruta=ultimos_precios_ruta,
                rango=rango,
                configuracion_pendiente=configuracion_pendiente,
            )

    # --- Nivel 4: fórmula base ---
    if km and km > 0 and tarifa_base is not None and tarifa_km is not None:
        monto = tarifa_base + tarifa_km * Decimal(str(km))
        monto_redondeado = _redondear(monto, redondeo)
        desglose = [
            DesgloseLinea("Tarifa base", tarifa_base),
            DesgloseLinea(f"{km:g} km × ${tarifa_km:g}", tarifa_km * Decimal(str(km))),
        ]
        if monto_redondeado != monto:
            desglose.append(DesgloseLinea(f"Redondeo a ${redondeo:g}", monto_redondeado - monto))
        return Sugerencia(
            monto=monto_redondeado,
            desglose=desglose,
            confianza="baja",
            fuente="formula",
            explicacion="Fórmula base: no hay servicios previos de esta ruta",
            referencias=[],
            ultimos_precios_ruta=ultimos_precios_ruta,
            rango=rango,
            configuracion_pendiente=configuracion_pendiente,
        )

    # --- Sin referencia ---
    return _sin_referencia(ultimos_precios_ruta, configuracion_pendiente)
