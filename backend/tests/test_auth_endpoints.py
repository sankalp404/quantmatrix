import uuid
import pytest

try:
    from fastapi.testclient import TestClient
    from backend.api.main import app

    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False


@pytest.fixture(scope="module")
def client():
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI TestClient not available in this env")
    try:
        return TestClient(app, raise_server_exceptions=False)
    except TypeError:
        pytest.skip("Starlette TestClient incompatible in this runtime")


def test_auth_health(client):
    r = client.get("/api/v1/auth/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_register_and_login(client):
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "TestPassw0rd!"

    # Register
    r_reg = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    # Either created (200) or already exists (400) if test re-runs against same DB
    assert r_reg.status_code in (200, 400)

    # Login
    r_login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert r_login.status_code == 200
    data = r_login.json()
    assert isinstance(data.get("access_token"), str) and data.get("token_type") == "bearer"
    token = data["access_token"]

    # Verify /me with token
    r_me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r_me.status_code == 200
    me = r_me.json()
    assert me.get("username") == username
