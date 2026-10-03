"""Lectura/escritura de `configuracion` — `02-data-model §3.19`.

Los valores por defecto de aquí son los que ya trae el spec (ej. `precio.redondeo`
= 50), no datos de negocio reales de Vlad — esos (tarifas, costo por km) nunca se
siembran, solo se leen si existe la fila (`07-precio-sugerido §5`).
"""
import uuid
from typing import Any

from sqlmodel import Session, select

from app.modules.configuracion.models import Configuracion

DEFAULTS: dict[str, Any] = {
    "precio.tarifa_base": None,
    "precio.tarifa_km": None,
    "precio.cargo_parada_extra": None,
    "precio.redondeo": 50,
    "precio.ventana_historial_dias": 365,
    "precio.recordatorio_descartado": False,
    "facturacion.permisos_revisar": ["TPAF14"],
    "conciliacion.tolerancia": "1.00",
    "conciliacion.max_facturas_busqueda": 60,
    "conciliacion.tiempo_max_ms": 1500,
}


def get_valor(session: Session, clave: str) -> Any:
    fila = session.get(Configuracion, clave)
    if fila is not None:
        return fila.valor
    return DEFAULTS.get(clave)


def get_todas(session: Session) -> dict[str, Any]:
    filas = {f.clave: f.valor for f in session.exec(select(Configuracion)).all()}
    return {clave: filas.get(clave, default) for clave, default in DEFAULTS.items()}


def set_valor(session: Session, clave: str, valor: Any, usuario_id: uuid.UUID | None) -> Configuracion:
    fila = session.get(Configuracion, clave)
    if fila is None:
        fila = Configuracion(clave=clave, valor=valor, updated_by=usuario_id)
        session.add(fila)
    else:
        fila.valor = valor
        fila.updated_by = usuario_id
    session.commit()
    session.refresh(fila)
    return fila
