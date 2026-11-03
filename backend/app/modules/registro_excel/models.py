"""Facturar desde el Excel de registros (3 nov 2026).

Vlad sube su Excel una vez (se guarda hasta que suba uno nuevo), escribe el número de
fila y la app arma el servicio con lo que encuentra en los catálogos.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, LargeBinary, UniqueConstraint
from sqlmodel import Field

from app.core.models import TimestampMixin


class RegistroExcel(TimestampMixin, table=True):
    """El Excel vigente. Solo hay uno: al subir otro, el anterior se borra."""

    __tablename__ = "registro_excel"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nombre_archivo: str = Field(nullable=False)
    hoja: str = Field(nullable=False)
    # {campo: letra de columna}, p. ej. {"factura": "K"} — para escribir de vuelta.
    columnas: dict = Field(sa_column=Column(JSON, nullable=False))
    # El archivo original tal cual (≈1.5 MB): de aquí sale la copia con las facturas escritas.
    contenido: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    total_filas: int = Field(nullable=False)
    ultima_fila: int = Field(nullable=False)
    subido_at: datetime = Field(nullable=False)
    subido_por: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")


class RegistroExcelFila(TimestampMixin, table=True):
    __tablename__ = "registro_excel_fila"
    __table_args__ = (UniqueConstraint("registro_id", "fila", name="uq_registro_excel_fila"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    registro_id: uuid.UUID = Field(foreign_key="registro_excel.id", nullable=False, index=True)
    fila: int = Field(nullable=False, index=True)
    datos: dict = Field(sa_column=Column(JSON, nullable=False))


class RegistroExcelServicio(TimestampMixin, table=True):
    """Qué servicio salió de qué fila. Sobrevive a subir un Excel nuevo: la fila se vuelve a
    ubicar por su huella (fecha + cliente + destino) por si se insertaron filas antes."""

    __tablename__ = "registro_excel_servicio"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    servicio_id: uuid.UUID = Field(foreign_key="servicio.id", nullable=False, unique=True)
    fila: int = Field(nullable=False, index=True)
    huella: str = Field(nullable=False)


class RegistroExcelAlias(TimestampMixin, table=True):
    """Lo que el admin eligió para un texto del Excel ("VASSA DIVASA" → lugar X): la próxima
    vez que aparezca ese texto ya sale elegido."""

    __tablename__ = "registro_excel_alias"
    __table_args__ = (
        UniqueConstraint("tipo", "cliente_id", "texto", name="uq_registro_excel_alias"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tipo: str = Field(nullable=False)  # lugar | cliente | operador | unidad
    # Para lugares: el cliente del catálogo (un mismo texto puede ser otro lugar en otro cliente).
    cliente_id: uuid.UUID | None = Field(default=None, foreign_key="cliente.id")
    texto: str = Field(nullable=False)  # normalizado
    objetivo_id: uuid.UUID = Field(nullable=False)
