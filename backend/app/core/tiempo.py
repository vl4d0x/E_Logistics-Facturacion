"""Hora de México (`01-architecture §9`: UTC en la DB, hora local en lo fiscal y en la UI)."""
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

MX = ZoneInfo("America/Mexico_City")


def ahora_mx() -> datetime:
    """Ahora en México, sin zona (como se comparan las fechas/horas capturadas por el admin)."""
    return datetime.now(MX).replace(tzinfo=None)


def hoy_mx() -> date:
    return datetime.now(MX).date()


def a_hora_mx(momento: datetime) -> datetime:
    """Un instante guardado en UTC (con o sin tzinfo: SQLite lo devuelve sin) → hora local de México sin zona."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(MX).replace(tzinfo=None)
