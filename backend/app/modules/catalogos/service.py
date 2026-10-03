"""Lógica de negocio de catálogos y accesos — `fase-1-catalogos`, `02 §3.2-3.6/§5`.

Funciones puras que reciben `session`. Cada catálogo tiene su propio
`contar_uso_*`: es "el único lugar" (H1.6) donde se cuentan referencias para
decidir si `DELETE` borra físico o archiva — las Fases 2+ amplían estas
funciones (agregan sus tablas) sin tocar el router ni el contrato de `/uso`.
"""
import uuid

from sqlmodel import Session, SQLModel, func, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.core.security import hash_password
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.catalogos.models import Cliente, Lugar, MercanciaFrecuente, Operador, Unidad
from app.modules.catalogos.schemas import (
    AccesoOperadorCreate,
    AccesoOperadorOut,
    AccesoOperadorUpdate,
    ClienteCreate,
    ClienteUpdate,
    DeleteResultOut,
    LugarCreate,
    LugarUpdate,
    MercanciaCreate,
    MercanciaUpdate,
    OperadorCreate,
    OperadorUpdate,
    UnidadCreate,
    UnidadUpdate,
    UsoOut,
    UsuarioAdminCreate,
    UsuarioAdminUpdate,
)

# --- helpers genéricos -------------------------------------------------------


def _get_or_404[ModelT: SQLModel](
    session: Session, model: type[ModelT], obj_id: uuid.UUID, nombre: str
) -> ModelT:
    obj = session.get(model, obj_id)
    if obj is None:
        raise AppError("not_found", f"{nombre} no encontrado", 404)
    return obj


def _check_unique(
    session: Session,
    model: type[SQLModel],
    field_name: str,
    value: object,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(model).where(getattr(model, field_name) == value)
    existing = session.exec(stmt).first()
    if existing is not None and getattr(existing, "id", None) != exclude_id:
        raise AppError(
            "validation_error",
            f"Ya existe un registro con ese {field_name}",
            422,
            details=[{"field": field_name, "issue": "duplicado"}],
        )


def _apply_patch(obj: SQLModel, payload: dict) -> None:
    for field, value in payload.items():
        setattr(obj, field, value)
    obj.updated_at = utcnow()


def _count(session: Session, model: type[SQLModel], **filters: object) -> int:
    stmt = select(func.count()).select_from(model)
    for field_name, value in filters.items():
        stmt = stmt.where(getattr(model, field_name) == value)
    return session.exec(stmt).one()


def _finalizar_eliminar(session: Session, obj: SQLModel, uso: UsoOut) -> DeleteResultOut:
    if uso.bloqueos:
        raise AppError(
            "conflict",
            "Hay servicios activos que usan este registro; reasígnalos antes de continuar.",
            409,
            details=[b.model_dump(mode="json") for b in uso.bloqueos],
        )
    if uso.accion_al_eliminar == "archivar":
        obj.activo = False
        obj.updated_at = utcnow()
        session.add(obj)
        session.commit()
        return DeleteResultOut(resultado="archivado")
    session.delete(obj)
    session.commit()
    return DeleteResultOut(resultado="eliminado")


# --- Unidad -------------------------------------------------------------


def list_unidades(
    session: Session, activo: str | None, q: str | None, page: int, size: int
) -> tuple[list[Unidad], int]:
    stmt = select(Unidad)
    if activo == "true":
        stmt = stmt.where(Unidad.activo == True)
    elif activo == "false":
        stmt = stmt.where(Unidad.activo == False)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Unidad.apodo.ilike(like)) | (Unidad.placa.ilike(like)))  # type: ignore[attr-defined]
    total = len(session.exec(stmt).all())
    items = session.exec(stmt.order_by(Unidad.apodo).offset((page - 1) * size).limit(size)).all()
    return items, total


def get_unidad(session: Session, unidad_id: uuid.UUID) -> Unidad:
    return _get_or_404(session, Unidad, unidad_id, "Unidad")


def create_unidad(session: Session, data: UnidadCreate) -> Unidad:
    _check_unique(session, Unidad, "apodo", data.apodo)
    _check_unique(session, Unidad, "placa", data.placa)
    unidad = Unidad(**data.model_dump())
    session.add(unidad)
    session.commit()
    session.refresh(unidad)
    return unidad


def update_unidad(session: Session, unidad_id: uuid.UUID, data: UnidadUpdate) -> Unidad:
    unidad = get_unidad(session, unidad_id)
    payload = data.model_dump(exclude_unset=True)
    if "apodo" in payload:
        _check_unique(session, Unidad, "apodo", payload["apodo"], exclude_id=unidad_id)
    if "placa" in payload:
        _check_unique(session, Unidad, "placa", payload["placa"], exclude_id=unidad_id)
    tipo_medidor = payload.get("tipo_medidor", unidad.tipo_medidor)
    num_barras = payload.get("num_barras", unidad.num_barras)
    if str(tipo_medidor) == "barras" and not (num_barras is not None and 2 <= num_barras <= 20):
        raise AppError(
            "validation_error",
            "num_barras es obligatorio (entre 2 y 20) si tipo_medidor=barras",
            422,
            details=[{"field": "num_barras", "issue": "requerido"}],
        )
    _apply_patch(unidad, payload)
    session.add(unidad)
    session.commit()
    session.refresh(unidad)
    return unidad


def contar_uso_unidad(session: Session, unidad_id: uuid.UUID) -> UsoOut:
    get_unidad(session, unidad_id)
    # Fase 1: ninguna tabla referencia todavía a `unidad` (servicio/inspeccion_salida/
    # carga_combustible llegan en Fases 2-3). Referencias = {} hasta entonces.
    referencias: dict[str, int] = {}
    return UsoOut(
        referencias=referencias,
        accion_al_eliminar="archivar" if sum(referencias.values()) else "eliminar",
        bloqueos=[],
    )


def eliminar_unidad(session: Session, unidad_id: uuid.UUID) -> DeleteResultOut:
    unidad = get_unidad(session, unidad_id)
    return _finalizar_eliminar(session, unidad, contar_uso_unidad(session, unidad_id))


def restaurar_unidad(session: Session, unidad_id: uuid.UUID) -> Unidad:
    unidad = get_unidad(session, unidad_id)
    unidad.activo = True
    unidad.updated_at = utcnow()
    session.add(unidad)
    session.commit()
    session.refresh(unidad)
    return unidad


# --- Operador -------------------------------------------------------------


def list_operadores(
    session: Session, activo: str | None, q: str | None, page: int, size: int
) -> tuple[list[Operador], int]:
    stmt = select(Operador)
    if activo == "true":
        stmt = stmt.where(Operador.activo == True)
    elif activo == "false":
        stmt = stmt.where(Operador.activo == False)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Operador.nombre.ilike(like)) | (Operador.rfc.ilike(like)))  # type: ignore[attr-defined]
    total = len(session.exec(stmt).all())
    items = session.exec(
        stmt.order_by(Operador.nombre).offset((page - 1) * size).limit(size)
    ).all()
    return items, total


def get_operador(session: Session, operador_id: uuid.UUID) -> Operador:
    return _get_or_404(session, Operador, operador_id, "Operador")


def create_operador(session: Session, data: OperadorCreate) -> Operador:
    operador = Operador(**data.model_dump())
    session.add(operador)
    session.commit()
    session.refresh(operador)
    return operador


def update_operador(session: Session, operador_id: uuid.UUID, data: OperadorUpdate) -> Operador:
    operador = get_operador(session, operador_id)
    _apply_patch(operador, data.model_dump(exclude_unset=True))
    session.add(operador)
    session.commit()
    session.refresh(operador)
    return operador


def contar_uso_operador(session: Session, operador_id: uuid.UUID) -> UsoOut:
    get_operador(session, operador_id)
    referencias = {"usuarios": _count(session, Usuario, operador_id=operador_id)}
    # Fase 2 agregará aquí: referencias["servicios"] = ...
    return UsoOut(
        referencias=referencias,
        accion_al_eliminar="archivar" if sum(referencias.values()) else "eliminar",
        bloqueos=[],
    )


def eliminar_operador(session: Session, operador_id: uuid.UUID) -> DeleteResultOut:
    operador = get_operador(session, operador_id)
    return _finalizar_eliminar(session, operador, contar_uso_operador(session, operador_id))


def restaurar_operador(session: Session, operador_id: uuid.UUID) -> Operador:
    operador = get_operador(session, operador_id)
    operador.activo = True
    operador.updated_at = utcnow()
    session.add(operador)
    session.commit()
    session.refresh(operador)
    return operador


# --- Acceso del operador a la app -------------------------------------------


def get_acceso_operador(session: Session, operador_id: uuid.UUID) -> AccesoOperadorOut | None:
    get_operador(session, operador_id)
    usuario = session.exec(select(Usuario).where(Usuario.operador_id == operador_id)).first()
    if usuario is None:
        return None
    return AccesoOperadorOut(usuario_id=usuario.id, email=usuario.email, activo=usuario.activo)


def crear_acceso_operador(
    session: Session, operador_id: uuid.UUID, data: AccesoOperadorCreate
) -> AccesoOperadorOut:
    operador = get_operador(session, operador_id)
    existente = session.exec(select(Usuario).where(Usuario.operador_id == operador_id)).first()
    if existente is not None:
        raise AppError("conflict", "Este operador ya tiene acceso a la app", 409)
    _check_unique(session, Usuario, "email", data.email)
    usuario = Usuario(
        nombre=operador.nombre,
        email=data.email,
        password_hash=hash_password(data.password_temporal),
        rol=RolUsuario.operador,
        operador_id=operador_id,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return AccesoOperadorOut(usuario_id=usuario.id, email=usuario.email, activo=usuario.activo)


def actualizar_acceso_operador(
    session: Session, operador_id: uuid.UUID, data: AccesoOperadorUpdate
) -> AccesoOperadorOut:
    get_operador(session, operador_id)
    usuario = session.exec(select(Usuario).where(Usuario.operador_id == operador_id)).first()
    if usuario is None:
        raise AppError("not_found", "Este operador no tiene acceso a la app", 404)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("email") and payload["email"] != usuario.email:
        _check_unique(session, Usuario, "email", payload["email"], exclude_id=usuario.id)
        usuario.email = payload["email"]
    if payload.get("password_temporal"):
        usuario.password_hash = hash_password(payload["password_temporal"])
    if "activo" in payload and payload["activo"] is not None:
        usuario.activo = payload["activo"]
    usuario.updated_at = utcnow()
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return AccesoOperadorOut(usuario_id=usuario.id, email=usuario.email, activo=usuario.activo)


# --- Cliente -------------------------------------------------------------


def list_clientes(
    session: Session, activo: str | None, q: str | None, page: int, size: int
) -> tuple[list[Cliente], int]:
    stmt = select(Cliente)
    if activo == "true":
        stmt = stmt.where(Cliente.activo == True)
    elif activo == "false":
        stmt = stmt.where(Cliente.activo == False)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Cliente.nombre_comercial.ilike(like))  # type: ignore[attr-defined]
            | (Cliente.razon_social.ilike(like))  # type: ignore[attr-defined]
            | (Cliente.rfc.ilike(like))  # type: ignore[attr-defined]
        )
    total = len(session.exec(stmt).all())
    items = session.exec(
        stmt.order_by(Cliente.nombre_comercial).offset((page - 1) * size).limit(size)
    ).all()
    return items, total


def get_cliente(session: Session, cliente_id: uuid.UUID) -> Cliente:
    return _get_or_404(session, Cliente, cliente_id, "Cliente")


def create_cliente(session: Session, data: ClienteCreate) -> Cliente:
    cliente = Cliente(**data.model_dump())
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


def update_cliente(session: Session, cliente_id: uuid.UUID, data: ClienteUpdate) -> Cliente:
    cliente = get_cliente(session, cliente_id)
    _apply_patch(cliente, data.model_dump(exclude_unset=True))
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


def contar_uso_cliente(session: Session, cliente_id: uuid.UUID) -> UsoOut:
    get_cliente(session, cliente_id)
    referencias = {
        "mercancias": _count(session, MercanciaFrecuente, cliente_id=cliente_id),
        "lugares": _count(session, Lugar, cliente_id=cliente_id),
    }
    # Fase 2+ agregará aquí: referencias["servicios"] = ...
    return UsoOut(
        referencias=referencias,
        accion_al_eliminar="archivar" if sum(referencias.values()) else "eliminar",
        bloqueos=[],
    )


def eliminar_cliente(session: Session, cliente_id: uuid.UUID) -> DeleteResultOut:
    cliente = get_cliente(session, cliente_id)
    return _finalizar_eliminar(session, cliente, contar_uso_cliente(session, cliente_id))


def restaurar_cliente(session: Session, cliente_id: uuid.UUID) -> Cliente:
    cliente = get_cliente(session, cliente_id)
    cliente.activo = True
    cliente.updated_at = utcnow()
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


# --- Mercancía frecuente (anidada en cliente) --------------------------------


def list_mercancias(session: Session, cliente_id: uuid.UUID) -> list[MercanciaFrecuente]:
    get_cliente(session, cliente_id)
    stmt = select(MercanciaFrecuente).where(MercanciaFrecuente.cliente_id == cliente_id)
    return session.exec(stmt.order_by(MercanciaFrecuente.nombre_humano)).all()


def get_mercancia(session: Session, mercancia_id: uuid.UUID) -> MercanciaFrecuente:
    return _get_or_404(session, MercanciaFrecuente, mercancia_id, "Mercancía")


def create_mercancia(
    session: Session, cliente_id: uuid.UUID, data: MercanciaCreate
) -> MercanciaFrecuente:
    get_cliente(session, cliente_id)
    mercancia = MercanciaFrecuente(cliente_id=cliente_id, **data.model_dump())
    session.add(mercancia)
    session.commit()
    session.refresh(mercancia)
    return mercancia


def update_mercancia(
    session: Session, mercancia_id: uuid.UUID, data: MercanciaUpdate
) -> MercanciaFrecuente:
    mercancia = get_mercancia(session, mercancia_id)
    _apply_patch(mercancia, data.model_dump(exclude_unset=True))
    session.add(mercancia)
    session.commit()
    session.refresh(mercancia)
    return mercancia


def contar_uso_mercancia(session: Session, mercancia_id: uuid.UUID) -> UsoOut:
    get_mercancia(session, mercancia_id)
    # Fase 2 agregará aquí: referencias["viajes"] = ... (viaje_mercancia.mercancia_frecuente_id)
    referencias: dict[str, int] = {}
    return UsoOut(
        referencias=referencias,
        accion_al_eliminar="archivar" if sum(referencias.values()) else "eliminar",
        bloqueos=[],
    )


def eliminar_mercancia(session: Session, mercancia_id: uuid.UUID) -> DeleteResultOut:
    mercancia = get_mercancia(session, mercancia_id)
    return _finalizar_eliminar(session, mercancia, contar_uso_mercancia(session, mercancia_id))


def restaurar_mercancia(session: Session, mercancia_id: uuid.UUID) -> MercanciaFrecuente:
    mercancia = get_mercancia(session, mercancia_id)
    mercancia.activo = True
    mercancia.updated_at = utcnow()
    session.add(mercancia)
    session.commit()
    session.refresh(mercancia)
    return mercancia


# --- Lugar -------------------------------------------------------------


def list_lugares(
    session: Session, cliente_id: uuid.UUID | None, incluir_globales: bool, q: str | None
) -> list[Lugar]:
    stmt = select(Lugar)
    if cliente_id is not None and incluir_globales:
        stmt = stmt.where((Lugar.cliente_id == cliente_id) | (Lugar.cliente_id == None))
    elif cliente_id is not None:
        stmt = stmt.where(Lugar.cliente_id == cliente_id)
    if q:
        stmt = stmt.where(Lugar.nombre.ilike(f"%{q}%"))  # type: ignore[attr-defined]
    return session.exec(stmt.order_by(Lugar.nombre)).all()


def get_lugar(session: Session, lugar_id: uuid.UUID) -> Lugar:
    return _get_or_404(session, Lugar, lugar_id, "Lugar")


def _desmarcar_origen_predeterminado(
    session: Session, cliente_id: uuid.UUID | None, excluir_id: uuid.UUID | None = None
) -> None:
    if cliente_id is None:
        return
    stmt = select(Lugar).where(
        Lugar.cliente_id == cliente_id, Lugar.es_origen_predeterminado == True
    )
    for otro in session.exec(stmt).all():
        if otro.id != excluir_id:
            otro.es_origen_predeterminado = False
            otro.updated_at = utcnow()
            session.add(otro)


def create_lugar(session: Session, data: LugarCreate) -> Lugar:
    if data.cliente_id is not None:
        get_cliente(session, data.cliente_id)
    if data.es_origen_predeterminado:
        _desmarcar_origen_predeterminado(session, data.cliente_id)
    lugar = Lugar(**data.model_dump())
    session.add(lugar)
    session.commit()
    session.refresh(lugar)
    return lugar


def update_lugar(session: Session, lugar_id: uuid.UUID, data: LugarUpdate) -> Lugar:
    lugar = get_lugar(session, lugar_id)
    payload = data.model_dump(exclude_unset=True)
    cliente_id = payload.get("cliente_id", lugar.cliente_id)
    if payload.get("es_origen_predeterminado"):
        _desmarcar_origen_predeterminado(session, cliente_id, excluir_id=lugar_id)
    _apply_patch(lugar, payload)
    session.add(lugar)
    session.commit()
    session.refresh(lugar)
    return lugar


def contar_uso_lugar(session: Session, lugar_id: uuid.UUID) -> UsoOut:
    get_lugar(session, lugar_id)
    # Fase 2 agregará aquí: referencias["viajes"] = ... (viaje.origen/destino_lugar_id)
    referencias: dict[str, int] = {}
    return UsoOut(
        referencias=referencias,
        accion_al_eliminar="archivar" if sum(referencias.values()) else "eliminar",
        bloqueos=[],
    )


def eliminar_lugar(session: Session, lugar_id: uuid.UUID) -> DeleteResultOut:
    lugar = get_lugar(session, lugar_id)
    return _finalizar_eliminar(session, lugar, contar_uso_lugar(session, lugar_id))


def restaurar_lugar(session: Session, lugar_id: uuid.UUID) -> Lugar:
    lugar = get_lugar(session, lugar_id)
    lugar.activo = True
    lugar.updated_at = utcnow()
    session.add(lugar)
    session.commit()
    session.refresh(lugar)
    return lugar


# --- Usuarios administradores (H1.7) -----------------------------------------


def list_admins(session: Session) -> list[Usuario]:
    stmt = select(Usuario).where(Usuario.rol == RolUsuario.admin)
    return session.exec(stmt.order_by(Usuario.nombre)).all()


def crear_admin(session: Session, data: UsuarioAdminCreate) -> Usuario:
    _check_unique(session, Usuario, "email", data.email)
    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password_temporal),
        rol=RolUsuario.admin,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def actualizar_admin(
    session: Session, admin_id: uuid.UUID, data: UsuarioAdminUpdate, current_user: Usuario
) -> Usuario:
    usuario = session.get(Usuario, admin_id)
    if usuario is None or usuario.rol != RolUsuario.admin:
        raise AppError("not_found", "Administrador no encontrado", 404)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("activo") is False:
        if usuario.id == current_user.id:
            raise AppError("conflict", "No puedes desactivarte a ti mismo", 409)
        otros_activos = session.exec(
            select(func.count())
            .select_from(Usuario)
            .where(
                Usuario.rol == RolUsuario.admin,
                Usuario.activo == True,
                Usuario.id != usuario.id,
            )
        ).one()
        if otros_activos == 0:
            raise AppError(
                "conflict", "No puede quedar el sistema sin administradores activos", 409
            )
    if payload.get("email") and payload["email"] != usuario.email:
        _check_unique(session, Usuario, "email", payload["email"], exclude_id=usuario.id)
        usuario.email = payload["email"]
    if payload.get("nombre"):
        usuario.nombre = payload["nombre"]
    if payload.get("password_temporal"):
        usuario.password_hash = hash_password(payload["password_temporal"])
    if "activo" in payload and payload["activo"] is not None:
        usuario.activo = payload["activo"]
    usuario.updated_at = utcnow()
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario
