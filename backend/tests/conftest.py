"""Fixtures compartidos. Usa SQLite en memoria para tests (Postgres en dev/prod real)."""
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.core.security import hash_password
from app.main import app
from app.modules.auth.models import RolUsuario, Usuario


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(session: Session) -> Usuario:
    user = Usuario(
        nombre="Admin Test",
        email="admin@test.mx",
        password_hash=hash_password("secret123"),
        rol=RolUsuario.admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def operador_user(session: Session) -> Usuario:
    user = Usuario(
        nombre="Operador Test",
        email="operador@test.mx",
        password_hash=hash_password("secret123"),
        rol=RolUsuario.operador,
        operador_id=uuid.uuid4(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
