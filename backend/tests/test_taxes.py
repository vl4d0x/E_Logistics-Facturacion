"""`04-facturacion-cfdi §3-3.1` — casos de prueba literales del spec."""
from decimal import Decimal

import pytest

from app.modules.catalogos.models import RegimenReceptor
from app.modules.facturacion.taxes import calcular_impuestos, subtotal_desde_total


def test_calcular_impuestos_moral_retiene_4_porciento():
    montos = calcular_impuestos(Decimal("1650.00"), RegimenReceptor.moral)
    assert montos.subtotal == Decimal("1650.00")
    assert montos.iva_trasladado == Decimal("264.00")
    assert montos.iva_retenido == Decimal("66.00")
    assert montos.total == Decimal("1848.00")


def test_calcular_impuestos_fisica_sin_retencion():
    montos = calcular_impuestos(Decimal("1650.00"), RegimenReceptor.fisica)
    assert montos.iva_retenido == Decimal("0.00")
    assert montos.total == Decimal("1914.00")  # 1650 + 264


def test_subtotal_desde_total_moral():
    assert subtotal_desde_total(Decimal("1848.00"), RegimenReceptor.moral) == Decimal("1650.00")


def test_subtotal_desde_total_fisica():
    assert subtotal_desde_total(Decimal("1914.00"), RegimenReceptor.fisica) == Decimal("1650.00")


@pytest.mark.parametrize("subtotal", [Decimal("0.01"), Decimal("999999.99"), Decimal(100)])
def test_calcular_impuestos_redondea_a_dos_decimales(subtotal):
    montos = calcular_impuestos(subtotal, RegimenReceptor.moral)
    for campo in montos:
        assert campo == campo.quantize(Decimal("0.01"))


def test_round_half_up_no_banker_rounding():
    # 0.125 redondeado a 2 decimales: ROUND_HALF_UP da 0.13; banker's rounding daría 0.12.
    montos = calcular_impuestos(Decimal("0.125"), RegimenReceptor.fisica)
    assert montos.subtotal == Decimal("0.13")


def test_subtotal_simbolico_del_timbrado_en_cero():
    from app.modules.facturacion.taxes import SUBTOTAL_SIMBOLICO, subtotal_a_timbrar

    assert SUBTOTAL_SIMBOLICO == Decimal("0.10")
    assert subtotal_a_timbrar(Decimal("1650.00"), "cero") == Decimal("0.10")
    assert subtotal_a_timbrar(Decimal("1650.00"), "precio") == Decimal("1650.00")
    assert subtotal_a_timbrar(None, "precio") is None
    # persona moral: IVA 0.016 -> 0.02, retención 0.004 -> 0.00
    assert calcular_impuestos(SUBTOTAL_SIMBOLICO, RegimenReceptor.moral).total == Decimal("0.12")
