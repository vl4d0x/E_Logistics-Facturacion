"""Endpoints de catálogos y accesos — `03-api-contract §5`. Todo solo-admin."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import require_role
from app.core.errors import AppError
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.catalogos import service
from app.modules.catalogos.schemas import (
    AccesoOperadorCreate,
    AccesoOperadorOut,
    AccesoOperadorUpdate,
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    DeleteResultOut,
    LugarCreate,
    LugarOut,
    LugarUpdate,
    MercanciaCreate,
    MercanciaOut,
    MercanciaUpdate,
    OperadorCreate,
    OperadorOut,
    OperadorUpdate,
    Page,
    UnidadCreate,
    UnidadOut,
    UnidadUpdate,
    UsoOut,
    UsuarioAdminCreate,
    UsuarioAdminOut,
    UsuarioAdminUpdate,
)

router = APIRouter(dependencies=[Depends(require_role(RolUsuario.admin))])


# --- Unidades ----------------------------------------------------------------
@router.get("/catalogos/unidades", response_model=Page[UnidadOut])
def listar_unidades(
    activo: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Page[UnidadOut]:
    items, total = service.list_unidades(session, activo, q, page, size)
    return Page(items=items, total=total, page=page, size=size)


@router.post("/catalogos/unidades", response_model=UnidadOut, status_code=201)
def crear_unidad(body: UnidadCreate, session: Session = Depends(get_session)) -> UnidadOut:
    return service.create_unidad(session, body)


@router.get("/catalogos/unidades/{unidad_id}", response_model=UnidadOut)
def obtener_unidad(unidad_id: uuid.UUID, session: Session = Depends(get_session)) -> UnidadOut:
    return service.get_unidad(session, unidad_id)


@router.patch("/catalogos/unidades/{unidad_id}", response_model=UnidadOut)
def editar_unidad(
    unidad_id: uuid.UUID, body: UnidadUpdate, session: Session = Depends(get_session)
) -> UnidadOut:
    return service.update_unidad(session, unidad_id, body)


@router.get("/catalogos/unidades/{unidad_id}/uso", response_model=UsoOut)
def uso_unidad(unidad_id: uuid.UUID, session: Session = Depends(get_session)) -> UsoOut:
    return service.contar_uso_unidad(session, unidad_id)


@router.delete("/catalogos/unidades/{unidad_id}", response_model=DeleteResultOut)
def eliminar_unidad(
    unidad_id: uuid.UUID, session: Session = Depends(get_session)
) -> DeleteResultOut:
    return service.eliminar_unidad(session, unidad_id)


@router.post("/catalogos/unidades/{unidad_id}/restaurar", response_model=UnidadOut)
def restaurar_unidad(unidad_id: uuid.UUID, session: Session = Depends(get_session)) -> UnidadOut:
    return service.restaurar_unidad(session, unidad_id)


# --- Operadores ----------------------------------------------------------------
@router.get("/catalogos/operadores", response_model=Page[OperadorOut])
def listar_operadores(
    activo: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Page[OperadorOut]:
    items, total = service.list_operadores(session, activo, q, page, size)
    return Page(items=items, total=total, page=page, size=size)


@router.post("/catalogos/operadores", response_model=OperadorOut, status_code=201)
def crear_operador(body: OperadorCreate, session: Session = Depends(get_session)) -> OperadorOut:
    return service.create_operador(session, body)


@router.get("/catalogos/operadores/{operador_id}", response_model=OperadorOut)
def obtener_operador(
    operador_id: uuid.UUID, session: Session = Depends(get_session)
) -> OperadorOut:
    return service.get_operador(session, operador_id)


@router.patch("/catalogos/operadores/{operador_id}", response_model=OperadorOut)
def editar_operador(
    operador_id: uuid.UUID, body: OperadorUpdate, session: Session = Depends(get_session)
) -> OperadorOut:
    return service.update_operador(session, operador_id, body)


@router.get("/catalogos/operadores/{operador_id}/uso", response_model=UsoOut)
def uso_operador(operador_id: uuid.UUID, session: Session = Depends(get_session)) -> UsoOut:
    return service.contar_uso_operador(session, operador_id)


@router.delete("/catalogos/operadores/{operador_id}", response_model=DeleteResultOut)
def eliminar_operador(
    operador_id: uuid.UUID, session: Session = Depends(get_session)
) -> DeleteResultOut:
    return service.eliminar_operador(session, operador_id)


@router.post("/catalogos/operadores/{operador_id}/restaurar", response_model=OperadorOut)
def restaurar_operador(
    operador_id: uuid.UUID, session: Session = Depends(get_session)
) -> OperadorOut:
    return service.restaurar_operador(session, operador_id)


@router.get("/catalogos/operadores/{operador_id}/acceso", response_model=AccesoOperadorOut)
def obtener_acceso_operador(
    operador_id: uuid.UUID, session: Session = Depends(get_session)
) -> AccesoOperadorOut:
    acceso = service.get_acceso_operador(session, operador_id)
    if acceso is None:
        raise AppError("not_found", "Este operador no tiene acceso a la app", 404)
    return acceso


@router.post(
    "/catalogos/operadores/{operador_id}/acceso", response_model=AccesoOperadorOut, status_code=201
)
def crear_acceso_operador(
    operador_id: uuid.UUID, body: AccesoOperadorCreate, session: Session = Depends(get_session)
) -> AccesoOperadorOut:
    return service.crear_acceso_operador(session, operador_id, body)


@router.patch("/catalogos/operadores/{operador_id}/acceso", response_model=AccesoOperadorOut)
def editar_acceso_operador(
    operador_id: uuid.UUID, body: AccesoOperadorUpdate, session: Session = Depends(get_session)
) -> AccesoOperadorOut:
    return service.actualizar_acceso_operador(session, operador_id, body)


# --- Clientes ----------------------------------------------------------------
@router.get("/catalogos/clientes", response_model=Page[ClienteOut])
def listar_clientes(
    activo: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Page[ClienteOut]:
    items, total = service.list_clientes(session, activo, q, page, size)
    return Page(items=items, total=total, page=page, size=size)


@router.post("/catalogos/clientes", response_model=ClienteOut, status_code=201)
def crear_cliente(body: ClienteCreate, session: Session = Depends(get_session)) -> ClienteOut:
    return service.create_cliente(session, body)


@router.get("/catalogos/clientes/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(cliente_id: uuid.UUID, session: Session = Depends(get_session)) -> ClienteOut:
    return service.get_cliente(session, cliente_id)


@router.patch("/catalogos/clientes/{cliente_id}", response_model=ClienteOut)
def editar_cliente(
    cliente_id: uuid.UUID, body: ClienteUpdate, session: Session = Depends(get_session)
) -> ClienteOut:
    return service.update_cliente(session, cliente_id, body)


@router.get("/catalogos/clientes/{cliente_id}/uso", response_model=UsoOut)
def uso_cliente(cliente_id: uuid.UUID, session: Session = Depends(get_session)) -> UsoOut:
    return service.contar_uso_cliente(session, cliente_id)


@router.delete("/catalogos/clientes/{cliente_id}", response_model=DeleteResultOut)
def eliminar_cliente(
    cliente_id: uuid.UUID, session: Session = Depends(get_session)
) -> DeleteResultOut:
    return service.eliminar_cliente(session, cliente_id)


@router.post("/catalogos/clientes/{cliente_id}/restaurar", response_model=ClienteOut)
def restaurar_cliente(cliente_id: uuid.UUID, session: Session = Depends(get_session)) -> ClienteOut:
    return service.restaurar_cliente(session, cliente_id)


# --- Mercancías (anidadas en cliente) ----------------------------------------
@router.get("/catalogos/clientes/{cliente_id}/mercancias", response_model=list[MercanciaOut])
def listar_mercancias(
    cliente_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[MercanciaOut]:
    return service.list_mercancias(session, cliente_id)


@router.post(
    "/catalogos/clientes/{cliente_id}/mercancias", response_model=MercanciaOut, status_code=201
)
def crear_mercancia(
    cliente_id: uuid.UUID, body: MercanciaCreate, session: Session = Depends(get_session)
) -> MercanciaOut:
    return service.create_mercancia(session, cliente_id, body)


@router.patch("/catalogos/mercancias/{mercancia_id}", response_model=MercanciaOut)
def editar_mercancia(
    mercancia_id: uuid.UUID, body: MercanciaUpdate, session: Session = Depends(get_session)
) -> MercanciaOut:
    return service.update_mercancia(session, mercancia_id, body)


@router.get("/catalogos/mercancias/{mercancia_id}/uso", response_model=UsoOut)
def uso_mercancia(mercancia_id: uuid.UUID, session: Session = Depends(get_session)) -> UsoOut:
    return service.contar_uso_mercancia(session, mercancia_id)


@router.delete("/catalogos/mercancias/{mercancia_id}", response_model=DeleteResultOut)
def eliminar_mercancia(
    mercancia_id: uuid.UUID, session: Session = Depends(get_session)
) -> DeleteResultOut:
    return service.eliminar_mercancia(session, mercancia_id)


@router.post("/catalogos/mercancias/{mercancia_id}/restaurar", response_model=MercanciaOut)
def restaurar_mercancia(
    mercancia_id: uuid.UUID, session: Session = Depends(get_session)
) -> MercanciaOut:
    return service.restaurar_mercancia(session, mercancia_id)


# --- Lugares ----------------------------------------------------------------
@router.get("/catalogos/lugares", response_model=list[LugarOut])
def listar_lugares(
    cliente_id: uuid.UUID | None = Query(default=None),
    incluir_globales: bool = Query(default=True),
    q: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[LugarOut]:
    return service.list_lugares(session, cliente_id, incluir_globales, q)


@router.post("/catalogos/lugares", response_model=LugarOut, status_code=201)
def crear_lugar(body: LugarCreate, session: Session = Depends(get_session)) -> LugarOut:
    return service.create_lugar(session, body)


@router.get("/catalogos/lugares/{lugar_id}", response_model=LugarOut)
def obtener_lugar(lugar_id: uuid.UUID, session: Session = Depends(get_session)) -> LugarOut:
    return service.get_lugar(session, lugar_id)


@router.patch("/catalogos/lugares/{lugar_id}", response_model=LugarOut)
def editar_lugar(
    lugar_id: uuid.UUID, body: LugarUpdate, session: Session = Depends(get_session)
) -> LugarOut:
    return service.update_lugar(session, lugar_id, body)


@router.get("/catalogos/lugares/{lugar_id}/uso", response_model=UsoOut)
def uso_lugar(lugar_id: uuid.UUID, session: Session = Depends(get_session)) -> UsoOut:
    return service.contar_uso_lugar(session, lugar_id)


@router.delete("/catalogos/lugares/{lugar_id}", response_model=DeleteResultOut)
def eliminar_lugar(lugar_id: uuid.UUID, session: Session = Depends(get_session)) -> DeleteResultOut:
    return service.eliminar_lugar(session, lugar_id)


@router.post("/catalogos/lugares/{lugar_id}/restaurar", response_model=LugarOut)
def restaurar_lugar(lugar_id: uuid.UUID, session: Session = Depends(get_session)) -> LugarOut:
    return service.restaurar_lugar(session, lugar_id)


# --- Usuarios administradores (H1.7) -----------------------------------------
@router.get("/usuarios", response_model=list[UsuarioAdminOut])
def listar_admins(session: Session = Depends(get_session)) -> list[UsuarioAdminOut]:
    return service.list_admins(session)


@router.post("/usuarios", response_model=UsuarioAdminOut, status_code=201)
def crear_admin(body: UsuarioAdminCreate, session: Session = Depends(get_session)) -> UsuarioAdminOut:
    return service.crear_admin(session, body)


@router.patch("/usuarios/{admin_id}", response_model=UsuarioAdminOut)
def editar_admin(
    admin_id: uuid.UUID,
    body: UsuarioAdminUpdate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(require_role(RolUsuario.admin)),
) -> UsuarioAdminOut:
    return service.actualizar_admin(session, admin_id, body, current_user)
