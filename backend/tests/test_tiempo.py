# ruff: noqa: DTZ001 — las horas locales de México se manejan sin zona a propósito
"""Hora de México para la Carta Porte: `terminado_at` se guarda en UTC."""
from datetime import UTC, date, datetime, time

from app.core.tiempo import a_hora_mx
from app.modules.facturacion.service import _llegada_viaje, _salida_viaje
from app.modules.servicios.models import TipoViaje, Viaje


def test_a_hora_mx_convierte_utc_con_y_sin_zona():
    # 02:30 UTC del 12 oct = 20:30 del 11 oct en México (UTC-6, sin horario de verano desde 2022)
    assert a_hora_mx(datetime(2026, 10, 12, 2, 30, tzinfo=UTC)) == datetime(2026, 10, 11, 20, 30)
    assert a_hora_mx(datetime(2026, 10, 12, 2, 30)) == datetime(2026, 10, 11, 20, 30)


def test_salida_y_llegada_reales_en_hora_local():
    v = Viaje(servicio_id=None, orden=1, tipo=TipoViaje.recoleccion, fecha=date(2026, 10, 11),
              terminado_at=datetime(2026, 10, 12, 1, 0, tzinfo=UTC))
    assert _salida_viaje(v) == (datetime(2026, 10, 11, 19, 0), "real")
    v.hora_llegada = time(18, 45)
    assert _llegada_viaje(v) == (datetime(2026, 10, 11, 18, 45), "real")


def test_mensaje_error_pac_agrega_donde_corregir():
    from app.modules.facturacion.service import mensaje_error_pac

    m = mensaje_error_pac("El campo Nombre del receptor, debe pertenecer al nombre asociado al RFC")
    assert "Catálogos → Clientes" in m
    assert mensaje_error_pac("Otro error") == "Otro error"
