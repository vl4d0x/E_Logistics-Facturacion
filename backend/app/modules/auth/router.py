from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.core.deps import get_current_user
from app.modules.auth import service
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    return service.login(session, body.email, body.password)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)) -> RefreshResponse:
    return service.refresh(session, body.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: Usuario = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        nombre=user.nombre,
        email=user.email,
        rol=user.rol,
        operador_id=user.operador_id,
    )
