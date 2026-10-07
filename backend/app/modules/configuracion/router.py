"""`GET/PATCH /configuracion` — `03-api-contract §9`. Solo admin."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.configuracion import service
from app.modules.precios.tarifario import TIERS

router = APIRouter(prefix="/configuracion", dependencies=[Depends(require_role(RolUsuario.admin))])


class _Tarifa(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cdmx: float
    extra: float

    @field_validator("cdmx", "extra")
    @classmethod
    def _no_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("no puede ser negativo")
        return v


class _Tarifario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cliente: str
    tarifas: dict[str, _Tarifa]

    @field_validator("tarifas")
    @classmethod
    def _tiers(cls, v: dict) -> dict:
        if set(v) != set(TIERS):
            raise ValueError(f"debe traer exactamente {', '.join(TIERS)}")
        return v


def _validar(clave: str, valor: Any) -> Any:
    if clave == "precio.tarifario_cliente":
        try:
            return _Tarifario.model_validate(valor).model_dump()
        except ValidationError as exc:
            raise HTTPException(422, detail=str(exc.errors()[0]["msg"])) from exc
    return valor


@router.get("")
def obtener(session: Session = Depends(get_session)) -> dict[str, Any]:
    return service.get_todas(session)


@router.patch("")
def actualizar(
    body: dict[str, Any],
    session: Session = Depends(get_session),
    user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> dict[str, Any]:
    desconocidas = set(body) - set(service.DEFAULTS)
    if desconocidas:
        raise HTTPException(422, detail=f"Claves desconocidas: {', '.join(sorted(desconocidas))}")
    for clave, valor in body.items():
        service.set_valor(session, clave, _validar(clave, valor), user.id)
    return service.get_todas(session)
