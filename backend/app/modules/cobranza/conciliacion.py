"""Conciliación de pagos — `06-cobranza-rep §3`. Función pura: sin DB ni red, en centavos enteros.

Dado el saldo abierto de un cliente y el monto de un depósito, propone qué facturas pagó.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from itertools import pairwise

MAX_EXACTAS = 5
MAX_APROXIMADAS = 3
_TOPE_SOLUCIONES = 200


@dataclass(frozen=True)
class FacturaAbierta:
    id: str
    folio: str
    fecha: date
    saldo_cents: int


@dataclass
class Candidato:
    factura_ids: list[str]
    aplicaciones: list[tuple[str, int]]  # (factura_id, cents)
    suma_cents: int
    etiquetas: list[str] = field(default_factory=list)
    explicacion: str = ""
    diferencia_cents: int = 0
    factura_parcial_id: str | None = None


@dataclass
class Resultado:
    objetivo_cents: int
    saldo_total_cents: int
    exactas: list[Candidato]
    ambigua: bool
    nota_montos_iguales: bool
    aproximadas: list[Candidato]
    fifo_parcial: Candidato | None
    excede_saldo_cents: int | None
    busqueda_completa: bool
    facturas_consideradas: int


class _Timeout(Exception):
    pass


def _candidato_completo(facturas: list[FacturaAbierta]) -> Candidato:
    return Candidato(
        factura_ids=[f.id for f in facturas],
        aplicaciones=[(f.id, f.saldo_cents) for f in facturas],
        suma_cents=sum(f.saldo_cents for f in facturas),
    )


def _fifo_parcial(facturas: list[FacturaAbierta], objetivo: int) -> Candidato:
    """Las más antiguas completas mientras quepan; el remanente queda como pago parcial."""
    aplicaciones: list[tuple[str, int]] = []
    restante = objetivo
    parcial_id = None
    for f in facturas:
        if restante <= 0:
            break
        monto = min(f.saldo_cents, restante)
        aplicaciones.append((f.id, monto))
        if monto < f.saldo_cents:
            parcial_id = f.id
        restante -= monto
    return Candidato(
        factura_ids=[a for a, _ in aplicaciones],
        aplicaciones=aplicaciones,
        suma_cents=objetivo - restante,
        etiquetas=["fifo"],
        explicacion="Las facturas más antiguas, con la última como pago parcial"
        if parcial_id
        else "Las facturas más antiguas",
        factura_parcial_id=parcial_id,
    )


def _clave_ranking(indices: list[int], facturas: list[FacturaAbierta]) -> tuple:
    """Menor es mejor (§3.5): saltadas, huecos, fecha de la más reciente, número de facturas."""
    elegidas = sorted(indices)
    seleccion = set(elegidas)
    saltadas = sum(1 for i in range(elegidas[-1]) if i not in seleccion)
    huecos = sum(1 for a, b in pairwise(elegidas) if b != a + 1)
    return (saltadas, huecos, facturas[elegidas[-1]].fecha, len(elegidas))


def _etiquetas(indices: list[int], facturas: list[FacturaAbierta]) -> list[str]:
    saltadas, huecos, _fecha, n = _clave_ranking(indices, facturas)
    etiquetas = []
    if n == 1:
        etiquetas.append("unica_factura")
    if saltadas == 0:
        etiquetas.append("fifo")
    if huecos == 0 and n > 1:
        etiquetas.append("consecutivas")
    if len({(facturas[i].fecha.year, facturas[i].fecha.month) for i in indices}) == 1:
        etiquetas.append("mismo_mes")
    return etiquetas


def _explicacion(indices: list[int], facturas: list[FacturaAbierta], etiquetas: list[str]) -> str:
    n = len(indices)
    if n == 1:
        return f"Una sola factura ({facturas[indices[0]].folio})"
    if "fifo" in etiquetas:
        return f"Las {n} facturas más antiguas"
    if "consecutivas" in etiquetas:
        return f"{n} facturas consecutivas ({facturas[min(indices)].folio} a {facturas[max(indices)].folio})"
    return f"{n} facturas que suman exacto"


def _soluciones_quick(facturas: list[FacturaAbierta], objetivo: int) -> list[list[int]]:
    """Factura única, prefijo FIFO y ventanas consecutivas (§3.3)."""
    encontradas = []
    for i in range(len(facturas)):
        suma = 0
        for j in range(i, len(facturas)):
            suma += facturas[j].saldo_cents
            if suma == objetivo:
                encontradas.append(list(range(i, j + 1)))
            if suma >= objetivo:
                break
    return encontradas


def _buscar_general(
    facturas: list[FacturaAbierta], objetivo: int, tolerancia: int, deadline: float
) -> tuple[list[list[int]], list[tuple[list[int], int]], bool]:
    """Subset-sum exacto con facturas agrupadas por saldo (§3.4). Devuelve (exactas, aproximadas, completa)."""
    por_saldo: dict[int, list[int]] = defaultdict(list)
    for idx, f in enumerate(facturas):
        por_saldo[f.saldo_cents].append(idx)
    grupos = sorted(por_saldo.items(), key=lambda kv: kv[0], reverse=True)  # saldo desc; índices ya por fecha asc
    sufijo = [0] * (len(grupos) + 1)
    for i in range(len(grupos) - 1, -1, -1):
        sufijo[i] = sufijo[i + 1] + grupos[i][0] * len(grupos[i][1])

    exactas: list[list[int]] = []
    aproximadas: list[tuple[list[int], int]] = []
    completa = True

    def expandir(eleccion: list[tuple[int, int]]) -> list[int]:
        return [idx for g, k in eleccion for idx in grupos[g][1][:k]]

    def dfs(i: int, restante: int, eleccion: list[tuple[int, int]]) -> None:
        if time.monotonic() > deadline or len(exactas) >= _TOPE_SOLUCIONES:
            raise _Timeout
        if restante == 0:
            exactas.append(expandir(eleccion))
            return
        if -tolerancia <= restante < 0:
            aproximadas.append((expandir(eleccion), -restante))
            return
        if restante < -tolerancia or i == len(grupos) or sufijo[i] < restante:
            return
        saldo, indices = grupos[i]
        k_max = min(len(indices), (restante + tolerancia) // saldo)
        for k in range(k_max, -1, -1):
            dfs(i + 1, restante - k * saldo, eleccion + ([(i, k)] if k else []))

    try:
        dfs(0, objetivo, [])
    except _Timeout:
        completa = False
    return exactas, aproximadas, completa


def conciliar(
    facturas: list[FacturaAbierta],
    objetivo_cents: int,
    tolerancia_cents: int = 100,
    max_facturas: int = 60,
    tiempo_max_ms: int = 1500,
) -> Resultado:
    facturas = sorted((f for f in facturas if f.saldo_cents > 0), key=lambda f: (f.fecha, f.folio))
    saldo_total = sum(f.saldo_cents for f in facturas)
    base = Resultado(
        objetivo_cents=objetivo_cents,
        saldo_total_cents=saldo_total,
        exactas=[],
        ambigua=False,
        nota_montos_iguales=False,
        aproximadas=[],
        fifo_parcial=None,
        excede_saldo_cents=None,
        busqueda_completa=True,
        facturas_consideradas=len(facturas),
    )
    if objetivo_cents > saldo_total:
        base.excede_saldo_cents = objetivo_cents - saldo_total
        base.fifo_parcial = _candidato_completo(facturas) if facturas else None
        return base

    deadline = time.monotonic() + tiempo_max_ms / 1000
    consideradas = facturas[:max_facturas]
    base.busqueda_completa = len(consideradas) == len(facturas)

    soluciones = _soluciones_quick(facturas, objetivo_cents)
    exactas_g, aproximadas_g, completa = _buscar_general(consideradas, objetivo_cents, tolerancia_cents, deadline)
    base.busqueda_completa = base.busqueda_completa and completa
    soluciones += exactas_g

    # Dos soluciones con el mismo multiconjunto de saldos son equivalentes: gana la mejor rankeada.
    mejores: dict[tuple, list[int]] = {}
    for sol in soluciones:
        clave_saldos = tuple(sorted(facturas[i].saldo_cents for i in sol))
        actual = mejores.get(clave_saldos)
        if actual is None or _clave_ranking(sol, facturas) < _clave_ranking(actual, facturas):
            mejores[clave_saldos] = sol
    ranking = sorted(mejores.values(), key=lambda s: _clave_ranking(s, facturas))

    for sol in ranking[:MAX_EXACTAS]:
        etiquetas = _etiquetas(sol, facturas)
        base.exactas.append(
            Candidato(
                factura_ids=[facturas[i].id for i in sorted(sol)],
                aplicaciones=[(facturas[i].id, facturas[i].saldo_cents) for i in sorted(sol)],
                suma_cents=objetivo_cents,
                etiquetas=etiquetas,
                explicacion=_explicacion(sol, facturas, etiquetas),
            )
        )
    base.ambigua = len(ranking) > 1
    if ranking:
        elegida = ranking[0]
        conteo = defaultdict(int)
        for f in facturas:
            conteo[f.saldo_cents] += 1
        usados = defaultdict(int)
        for i in elegida:
            usados[facturas[i].saldo_cents] += 1
        base.nota_montos_iguales = any(conteo[s] > k for s, k in usados.items())

    if not base.exactas:
        vistos: set[frozenset[int]] = set()
        aprox = []
        for sol, diferencia in aproximadas_g:
            clave = frozenset(sol)
            if clave in vistos or not sol:
                continue
            vistos.add(clave)
            aprox.append((sol, diferencia))
        aprox.sort(key=lambda sd: (sd[1], _clave_ranking(sd[0], facturas)))
        for sol, diferencia in aprox[:MAX_APROXIMADAS]:
            orden = sorted(sol)
            parcial = facturas[orden[-1]]  # la más reciente de la combinación absorbe la diferencia
            aplicaciones = [
                (facturas[i].id, facturas[i].saldo_cents - (diferencia if i == orden[-1] else 0)) for i in orden
            ]
            base.aproximadas.append(
                Candidato(
                    factura_ids=[facturas[i].id for i in orden],
                    aplicaciones=aplicaciones,
                    suma_cents=objetivo_cents,
                    etiquetas=_etiquetas(sol, facturas),
                    explicacion=f"La combinación más cercana difiere ${diferencia / 100:,.2f}",
                    diferencia_cents=diferencia,
                    factura_parcial_id=parcial.id,
                )
            )

    base.fifo_parcial = _fifo_parcial(facturas, objetivo_cents)
    return base
