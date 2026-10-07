"""`06-cobranza-rep §3` y §8 — algoritmo de conciliación (puro, sin DB)."""
import random
import time
from datetime import date, timedelta

from app.modules.cobranza.conciliacion import FacturaAbierta, conciliar


def _facturas(*saldos_pesos, inicio=date(2026, 8, 1)):
    return [
        FacturaAbierta(id=f"f{i}", folio=f"A-{100 + i}", fecha=inicio + timedelta(days=i), saldo_cents=round(s * 100))
        for i, s in enumerate(saldos_pesos)
    ]


def test_factura_unica_exacta():
    r = conciliar(_facturas(1000, 2500, 700), 250000)
    assert [c.factura_ids for c in r.exactas] == [["f1"]]
    assert "unica_factura" in r.exactas[0].etiquetas
    assert not r.ambigua


def test_prefijo_fifo():
    r = conciliar(_facturas(1000, 2000, 3000, 4000), 600000)
    assert r.exactas[0].factura_ids == ["f0", "f1", "f2"]
    assert "fifo" in r.exactas[0].etiquetas and "consecutivas" in r.exactas[0].etiquetas


def test_ventana_consecutiva():
    r = conciliar(_facturas(1111, 2000, 3000, 7777), 500000)
    assert r.exactas[0].factura_ids == ["f1", "f2"]
    assert "consecutivas" in r.exactas[0].etiquetas and "fifo" not in r.exactas[0].etiquetas


def test_combinacion_no_consecutiva_unica():
    r = conciliar(_facturas(1500, 999, 2500, 333), 400000)  # 1500 + 2500
    assert r.exactas[0].factura_ids == ["f0", "f2"]
    assert not r.ambigua


def test_dos_combinaciones_exactas_es_ambigua_y_gana_la_que_salta_menos():
    # 1000+3000 y 2000+2000(no hay)… usamos 1000+4000 (f0,f3) vs 2500+2500 (f1,f2)
    r = conciliar(_facturas(1000, 2500, 2500, 4000), 500000)
    assert r.ambigua
    assert len(r.exactas) == 2
    assert r.exactas[0].factura_ids == ["f1", "f2"]  # 0 huecos, 1 saltada (f0) vs. f0+f3 salta 2


def test_montos_iguales_toma_las_mas_antiguas_y_avisa():
    r = conciliar(_facturas(1848, 1848, 1848, 1848, 1848), 369600)
    assert r.exactas[0].factura_ids == ["f0", "f1"]
    assert r.nota_montos_iguales


def test_diferencia_de_centavos_es_aproximada():
    r = conciliar(_facturas(1000.03, 2000), 300000)  # las facturas suman 3 centavos más que el pago
    assert not r.exactas
    assert r.aproximadas[0].diferencia_cents == 3
    assert r.aproximadas[0].factura_parcial_id == "f1"
    assert sum(m for _, m in r.aproximadas[0].aplicaciones) == 300000


def test_sin_coincidencia_ofrece_fifo_parcial():
    r = conciliar(_facturas(1000, 2000, 3000), 150000)
    assert not r.exactas and not r.aproximadas
    assert r.fifo_parcial.aplicaciones == [("f0", 100000), ("f1", 50000)]
    assert r.fifo_parcial.factura_parcial_id == "f1"


def test_objetivo_mayor_al_saldo_total_excede():
    r = conciliar(_facturas(1000, 2000), 400000)
    assert r.excede_saldo_cents == 100000
    assert not r.exactas


def test_ignora_facturas_sin_saldo():
    r = conciliar(_facturas(0, 1000), 100000)
    assert r.exactas[0].factura_ids == ["f1"]


def test_rendimiento_60_facturas_aleatorias():
    random.seed(7)
    facturas = _facturas(*[random.choice([1848, 2320, 3480, 1160, 5800, 927.5]) + random.randint(0, 40) for _ in range(60)])
    objetivo = sum(f.saldo_cents for f in random.sample(facturas, 9)) // 1  # alcanzable
    t0 = time.monotonic()
    r = conciliar(facturas, objetivo, tiempo_max_ms=1500)
    assert time.monotonic() - t0 < 2.0
    assert r.exactas or r.aproximadas or r.fifo_parcial
    assert r.busqueda_completa in (True, False)


def test_mas_de_max_facturas_marca_busqueda_incompleta():
    r = conciliar(_facturas(*[100 + i for i in range(70)]), 30000, max_facturas=60)
    assert r.busqueda_completa is False
    assert r.facturas_consideradas == 70
