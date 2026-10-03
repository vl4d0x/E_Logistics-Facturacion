"""DTOs de entrada/salida — ver `03-api-contract §5`."""
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.modules.catalogos.models import MetodoPago, ModoAcuse, RegimenReceptor, TipoMedidor
from app.modules.catalogos.validators import validate_rfc


# --- Unidad ---------------------------------------------------------------
class UnidadBase(BaseModel):
    apodo: str
    placa: str
    anio_modelo: int | None = None
    config_vehicular: str
    peso_bruto_vehicular: float
    capacidad_carga_kg: float | None = None
    perm_sct: str
    num_permiso_sct: str
    aseguradora_resp_civil: str | None = None
    poliza_resp_civil: str | None = None
    tipo_medidor: TipoMedidor = TipoMedidor.aguja
    num_barras: int | None = None
    capacidad_tanque_l: float | None = None
    tipo_combustible: str | None = None

    @model_validator(mode="after")
    def _check_num_barras(self) -> "UnidadBase":
        if self.tipo_medidor == TipoMedidor.barras and not (
            self.num_barras is not None and 2 <= self.num_barras <= 20
        ):
            raise ValueError("num_barras es obligatorio (entre 2 y 20) si tipo_medidor=barras")
        return self


class UnidadCreate(UnidadBase):
    pass


class UnidadUpdate(BaseModel):
    apodo: str | None = None
    placa: str | None = None
    anio_modelo: int | None = None
    config_vehicular: str | None = None
    peso_bruto_vehicular: float | None = None
    capacidad_carga_kg: float | None = None
    perm_sct: str | None = None
    num_permiso_sct: str | None = None
    aseguradora_resp_civil: str | None = None
    poliza_resp_civil: str | None = None
    tipo_medidor: TipoMedidor | None = None
    num_barras: int | None = None
    capacidad_tanque_l: float | None = None
    tipo_combustible: str | None = None


class UnidadOut(UnidadBase):
    id: uuid.UUID
    activo: bool


# --- Operador ---------------------------------------------------------------
class OperadorBase(BaseModel):
    nombre: str
    rfc: str
    num_licencia: str
    telefono: str | None = None

    @field_validator("rfc")
    @classmethod
    def _validate_rfc(cls, v: str) -> str:
        return validate_rfc(v)


class OperadorCreate(OperadorBase):
    pass


class OperadorUpdate(BaseModel):
    nombre: str | None = None
    rfc: str | None = None
    num_licencia: str | None = None
    telefono: str | None = None

    @field_validator("rfc")
    @classmethod
    def _validate_rfc(cls, v: str | None) -> str | None:
        return validate_rfc(v) if v is not None else v


class OperadorOut(OperadorBase):
    id: uuid.UUID
    activo: bool


# --- Cliente ---------------------------------------------------------------
class ClienteBase(BaseModel):
    razon_social: str
    nombre_comercial: str
    rfc: str
    cp_fiscal: str
    regimen_fiscal: str
    regimen_receptor: RegimenReceptor
    uso_cfdi: str = "G03"
    metodo_pago_default: MetodoPago = MetodoPago.PPD
    modo_acuse: ModoAcuse
    emails_facturacion: list[EmailStr] = []
    dias_credito: int = 30

    @field_validator("rfc")
    @classmethod
    def _validate_rfc(cls, v: str) -> str:
        return validate_rfc(v)


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    razon_social: str | None = None
    nombre_comercial: str | None = None
    rfc: str | None = None
    cp_fiscal: str | None = None
    regimen_fiscal: str | None = None
    regimen_receptor: RegimenReceptor | None = None
    uso_cfdi: str | None = None
    metodo_pago_default: MetodoPago | None = None
    modo_acuse: ModoAcuse | None = None
    emails_facturacion: list[EmailStr] | None = None
    dias_credito: int | None = None

    @field_validator("rfc")
    @classmethod
    def _validate_rfc(cls, v: str | None) -> str | None:
        return validate_rfc(v) if v is not None else v


class ClienteOut(ClienteBase):
    id: uuid.UUID
    activo: bool


# --- Mercancía frecuente -----------------------------------------------------
class MercanciaBase(BaseModel):
    nombre_humano: str
    bienes_transp: str
    clave_unidad: str
    unidad_desc: str | None = None
    peso_kg_sugerido: float | None = None


class MercanciaCreate(MercanciaBase):
    pass


class MercanciaUpdate(BaseModel):
    nombre_humano: str | None = None
    bienes_transp: str | None = None
    clave_unidad: str | None = None
    unidad_desc: str | None = None
    peso_kg_sugerido: float | None = None


class MercanciaOut(MercanciaBase):
    id: uuid.UUID
    cliente_id: uuid.UUID
    activo: bool


# --- Lugar -------------------------------------------------------------------
class LugarBase(BaseModel):
    cliente_id: uuid.UUID | None = None
    nombre: str
    rfc_remitente_destinatario: str = "XAXX010101000"
    nombre_remitente_destinatario: str | None = None
    calle: str | None = None
    num_exterior: str | None = None
    colonia: str | None = None
    localidad: str | None = None
    municipio: str | None = None
    estado: str
    pais: str = "MEX"
    codigo_postal: str
    referencia: str | None = None
    es_origen_predeterminado: bool = False


class LugarCreate(LugarBase):
    pass


class LugarUpdate(BaseModel):
    cliente_id: uuid.UUID | None = None
    nombre: str | None = None
    rfc_remitente_destinatario: str | None = None
    nombre_remitente_destinatario: str | None = None
    calle: str | None = None
    num_exterior: str | None = None
    colonia: str | None = None
    localidad: str | None = None
    municipio: str | None = None
    estado: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    referencia: str | None = None
    es_origen_predeterminado: bool | None = None


class LugarOut(LugarBase):
    id: uuid.UUID
    activo: bool


# --- Eliminar / archivar / restaurar (SmartDeleteDialog, `05 §5`) ------------
class BloqueoServicio(BaseModel):
    servicio_id: uuid.UUID
    numero: int
    estado: str


class UsoOut(BaseModel):
    referencias: dict[str, int]
    accion_al_eliminar: Literal["archivar", "eliminar"]
    bloqueos: list[BloqueoServicio] = []


class DeleteResultOut(BaseModel):
    resultado: Literal["eliminado", "archivado"]


# --- Acceso del operador a la app (`03 §5`) ----------------------------------
class AccesoOperadorOut(BaseModel):
    usuario_id: uuid.UUID
    email: str
    activo: bool


class AccesoOperadorCreate(BaseModel):
    email: str
    password_temporal: str


class AccesoOperadorUpdate(BaseModel):
    email: str | None = None
    password_temporal: str | None = None
    activo: bool | None = None


# --- Usuarios administradores (`03 §5`, H1.7) --------------------------------
class UsuarioAdminCreate(BaseModel):
    nombre: str
    email: EmailStr
    password_temporal: str


class UsuarioAdminUpdate(BaseModel):
    nombre: str | None = None
    email: EmailStr | None = None
    password_temporal: str | None = None
    activo: bool | None = None


class UsuarioAdminOut(BaseModel):
    id: uuid.UUID
    nombre: str
    email: str
    activo: bool


# --- Envelope de paginación (`03 §1`) ----------------------------------------
class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
