from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.core.deps import require_role
from app.main import app
from app.modules.auth.models import RolUsuario, Usuario


def test_login_success(client: TestClient, admin_user: Usuario):
    response = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "secret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == admin_user.email
    assert body["user"]["rol"] == "admin"


def test_login_invalid_password(client: TestClient, admin_user: Usuario):
    response = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_unknown_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login", json={"email": "nope@test.mx", "password": "whatever"}
    )
    assert response.status_code == 401


def test_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_token(client: TestClient, admin_user: Usuario):
    login = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "secret123"}
    )
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


def test_refresh_returns_new_access_token(client: TestClient, admin_user: Usuario):
    login = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "secret123"}
    )
    refresh_token = login.json()["refresh_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_with_access_token_rejected(client: TestClient, admin_user: Usuario):
    login = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "secret123"}
    )
    access_token = login.json()["access_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


# --- require_role("admin") protege endpoints administrativos ---
_test_router = APIRouter()


@_test_router.get("/api/v1/_test/admin-only")
def _admin_only_route(user: Usuario = Depends(require_role(RolUsuario.admin))):
    return {"ok": True}


app.include_router(_test_router)


def test_require_role_rejects_operador(client: TestClient, operador_user: Usuario):
    login = client.post(
        "/api/v1/auth/login", json={"email": operador_user.email, "password": "secret123"}
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/_test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_require_role_allows_admin(client: TestClient, admin_user: Usuario):
    login = client.post(
        "/api/v1/auth/login", json={"email": admin_user.email, "password": "secret123"}
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/_test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
