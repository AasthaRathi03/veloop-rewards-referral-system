import base64
import json
import os
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_veloop.db")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("DEVICE_HASH_SECRET", "test-device-secret")
os.environ.setdefault("DEVICE_TOKEN_SECRET", "test-device-token")
os.environ.setdefault("IP_HASH_SECRET", "test-ip-secret")
os.environ.setdefault("AD_PROVIDER_SECRET", "test-ad-secret")
os.environ.setdefault("RATE_LIMIT_AUTH", "1000/60")
os.environ.setdefault("RATE_LIMIT_ATTRIBUTE", "1000/60")
os.environ.setdefault("RATE_LIMIT_AD_EVENT", "10000/60")
os.environ.setdefault("RATE_LIMIT_READ", "10000/60")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.seed import seed_milestones  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_milestones()
    reset_rate_limits()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def device_headers(device_id: str = "device-a", browser: str = "Chrome", token: str | None = None):
    """Same device_id => same hardware signals, different browser => different UA."""
    signals = {
        "platform": f"Linux-{device_id}",
        "screen": "1920x1080x24",
        "timezone": "Asia/Kolkata",
        "language": "en-IN",
        "hardware": f"8-cores-{device_id}",
        "canvasHint": f"hint-{device_id}",
    }
    raw = base64.urlsafe_b64encode(json.dumps(signals).encode()).decode().rstrip("=")
    headers = {
        "X-Device-Signals": raw,
        "User-Agent": f"Mozilla/5.0 ({browser}) {browser}/120.0",
    }
    if token:
        headers["X-Device-Token"] = token
    return headers


def register(client, email, password="Password123!", referral_code=None, device="device-a",
             browser="Chrome", phone=None, token=None):
    body = {"email": email, "password": password}
    if referral_code:
        body["referralCode"] = referral_code
    if phone:
        body["phone"] = phone
    return client.post("/api/auth/register", json=body, headers=device_headers(device, browser, token))


def auth_header(res):
    return {"Authorization": f"Bearer {res.json()['data']['accessToken']}"}


def watch_ads(client, token_header, count, device="device-b", start=0):
    """Simulate `count` verified ad completions."""
    results = []
    for i in range(count):
        res = client.post(
            "/api/ads/complete",
            json={
                "provider": "veloop-sdk",
                "providerEventId": f"evt-{uuid.uuid4()}",
                "watchedSeconds": 30,
            },
            headers={**token_header, **device_headers(device)},
        )
        results.append(res)
    return results
