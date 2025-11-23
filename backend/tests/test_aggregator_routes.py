import asyncio
import uuid
import jwt
import pytest

from backend.api.main import app
from backend.config import settings
from backend.models.broker_account import BrokerAccount, BrokerType, AccountType
from backend.database import SessionLocal


try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False


@pytest.fixture(scope="module")
def client():
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI TestClient not available in this env")
    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("Starlette TestClient incompatible in this runtime")


def _login_token(client) -> str:
    # Create a user and login (unique username)
    username = f"agg_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "Passw0rd!"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    r_login = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert r_login.status_code == 200
    return r_login.json()["access_token"], username


def _create_schwab_account_for_user(username: str) -> int:
    # Associate a BrokerAccount to this user by looking up user.id
    session = SessionLocal()
    try:
        from backend.models.user import User

        user = session.query(User).filter(User.username == username).first()
        acct = BrokerAccount(
            user_id=user.id,
            broker=BrokerType.SCHWAB,
            account_number=f"S{uuid.uuid4().hex[:6]}",
            account_name="Schwab Test",
            account_type=AccountType.TAXABLE,
        )
        session.add(acct)
        session.commit()
        session.refresh(acct)
        return acct.id
    finally:
        session.close()


def test_brokers_list(client):
    r = client.post("/api/v1/aggregator/brokers")
    assert r.status_code == 200 and "schwab" in r.json().get("brokers", [])


def test_link_and_callback_flow(client, monkeypatch):
    _login_tuple = _login_token(client)
    token, username = _login_tuple
    account_id = _create_schwab_account_for_user(username)

    # Stub httpx.AsyncClient used by /schwab/link (probe GET) and /schwab/callback (token POST)
    class DummyResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.headers = {}
        def json(self):
            return self._payload
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url, params=None, timeout=None):
            return DummyResponse(200)
        async def post(self, url, data=None):
            return DummyResponse(200, {\"access_token\": \"AT\", \"refresh_token\": \"RT\"})

    import httpx
    monkeypatch.setattr(httpx, \"AsyncClient\", DummyClient)

    # Link -> get URL (probe runs inside)
    r_link = client.post(
        \"/api/v1/aggregator/schwab/link\",
        json={\"account_id\": account_id, \"trading\": False},
        headers={\"Authorization\": f\"Bearer {token}\"},
    )
    assert r_link.status_code == 200
    url = r_link.json()[\"url\"]
    # Extract state query param from URL for callback
    import urllib.parse as _up
    qs = _up.urlparse(url).query
    params = dict(_up.parse_qsl(qs))
    assert \"state\" in params
    state = params[\"state\"]

    r_cb = client.get(
        \"/api/v1/aggregator/schwab/callback\", params={\"code\": \"abc\", \"state\": state}
    )
    assert r_cb.status_code == 200
    assert r_cb.json().get(\"status\") == \"linked\"


