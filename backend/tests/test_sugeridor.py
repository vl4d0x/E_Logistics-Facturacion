"""`07-precio-sugerido §2-4` — cascada del sugeridor, sin DB."""
from datetime import date
from decimal import Decimal

from app.modules.precios.sugeridor import PuntoHistorial, PuntoKm, sugerir_precio


def test_sin_historial_ni_formula_sin_referencia():
    s = sugerir_precio(
        n_destinos=1, km=None, historial_ruta=[], historial_km_cliente=[], tarifa_base=None, tarifa_km=None
    )
    assert s.monto is None
    assert s.fuente is None
    assert s.explicacion == "Sin referencias para esta ruta"
    assert s.configuracion_pendiente is True


def test_formula_base_cuando_no_hay_historial():
    s = sugerir_precio(
        n_destinos=1,
        km=80,
        historial_ruta=[],
        historial_km_cliente=[],
        tarifa_base=Decimal("600.00"),
        tarifa_km=Decimal("12.50"),
        redondeo=Decimal(50),
    )
    assert s.fuente == "formula"
    assert s.confianza == "baja"
    # 600 + 80*12.5 = 1600 -> redondeado a 50 ya es múltiplo, sin línea de redondeo
    assert s.monto == Decimal("1600.00")
    assert sum((l.monto for l in s.desglose), Decimal(0)) == s.monto


def test_formula_con_redondeo():
    s = sugerir_precio(
        n_destinos=1,
        km=83,
        historial_ruta=[],
        historial_km_cliente=[],
        tarifa_base=Decimal("600.00"),
        tarifa_km=Decimal("12.50"),
        redondeo=Decimal(50),
    )
    # 600 + 83*12.5 = 1637.50 -> redondeado a 1650
    assert s.monto == Decimal("1650.00")
    assert any("Redondeo" in l.concepto for l in s.desglose)
    assert sum((l.monto for l in s.desglose), Decimal(0)) == s.monto


def test_dollar_por_km_cliente_sin_formula():
    historial_km = [PuntoKm(Decimal("1000.00"), 80), PuntoKm(Decimal("1100.00"), 88)]
    s = sugerir_precio(
        n_destinos=1,
        km=80,
        historial_ruta=[],
        historial_km_cliente=historial_km,
        tarifa_base=None,
        tarifa_km=None,
    )
    assert s.fuente == "historial_km"
    assert s.monto is not None


def test_misma_ruta_un_solo_precio_confianza_media():
    historial = [PuntoHistorial(servicio_numero=10, fecha=date(2026, 9, 1), subtotal=Decimal("1650.00"))]
    s = sugerir_precio(
        n_destinos=1, km=80, historial_ruta=historial, historial_km_cliente=[], tarifa_base=None, tarifa_km=None
    )
    assert s.fuente == "historial_ruta"
    assert s.confianza == "media"
    assert s.monto == Decimal("1650.00")
    assert s.referencias == [10]


def test_misma_ruta_consistente_usa_el_mas_reciente():
    historial = [
        PuntoHistorial(servicio_numero=30, fecha=date(2026, 9, 20), subtotal=Decimal("1700.00")),
        PuntoHistorial(servicio_numero=20, fecha=date(2026, 9, 10), subtotal=Decimal("1650.00")),
        PuntoHistorial(servicio_numero=10, fecha=date(2026, 9, 1), subtotal=Decimal("1680.00")),
    ]
    s = sugerir_precio(
        n_destinos=1, km=80, historial_ruta=historial, historial_km_cliente=[], tarifa_base=None, tarifa_km=None
    )
    assert s.confianza == "alta"
    assert s.monto == Decimal("1700.00")  # el más reciente
    assert s.referencias == [30]


def test_misma_ruta_inconsistente_usa_mediana():
    historial = [
        PuntoHistorial(servicio_numero=30, fecha=date(2026, 9, 20), subtotal=Decimal("3000.00")),
        PuntoHistorial(servicio_numero=20, fecha=date(2026, 9, 10), subtotal=Decimal("1000.00")),
        PuntoHistorial(servicio_numero=10, fecha=date(2026, 9, 1), subtotal=Decimal("1500.00")),
    ]
    s = sugerir_precio(
        n_destinos=1, km=80, historial_ruta=historial, historial_km_cliente=[], tarifa_base=None, tarifa_km=None
    )
    assert s.fuente == "historial_ruta"
    assert s.monto == Decimal("1500.00")  # mediana de [3000, 1000, 1500]
    assert len(s.referencias) == 3


def test_ultimos_precios_ruta_y_rango_siempre_se_devuelven():
    historial = [
        PuntoHistorial(servicio_numero=30, fecha=date(2026, 9, 20), subtotal=Decimal("1700.00")),
        PuntoHistorial(servicio_numero=20, fecha=date(2026, 9, 10), subtotal=Decimal("1650.00")),
    ]
    s = sugerir_precio(
        n_destinos=1, km=80, historial_ruta=historial, historial_km_cliente=[], tarifa_base=None, tarifa_km=None
    )
    assert len(s.ultimos_precios_ruta) == 2
    assert s.rango == (Decimal("1650.00"), Decimal("1700.00"))
