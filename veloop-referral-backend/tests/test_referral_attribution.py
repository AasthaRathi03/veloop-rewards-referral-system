"""Referral creation, immutability and self-referral rules."""
from tests.conftest import auth_header, device_headers, register


def test_valid_referral_creates_pending_relationship(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]

    b = register(client, "bob@example.com", referral_code=code, device="dev-b")
    assert b.status_code == 200
    assert b.json()["data"]["referral"]["status"] == "PENDING"

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalReferrals"] == 1
    assert dash["pendingReferrals"] == 1
    assert dash["successfulReferrals"] == 0
    assert dash["referralCode"] == code
    assert dash["referralLink"].endswith(f"?ref={code}")


def test_registration_grants_20_xp_to_referrer(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]
    register(client, "bob@example.com", referral_code=code, device="dev-b")

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalXpEarned"] == 20


def test_invalid_referral_code_rejected(client):
    res = register(client, "bob@example.com", referral_code="VELOOPZZZZZ", device="dev-b")
    assert res.status_code == 400
    assert res.json()["code"] == "INVALID_REFERRAL_CODE"


def test_referral_attribution_is_immutable(client):
    a = register(client, "alice@example.com", device="dev-a")
    c = register(client, "carol@example.com", device="dev-c")
    code_a = a.json()["data"]["user"]["referralCode"]
    code_c = c.json()["data"]["user"]["referralCode"]

    b = register(client, "bob@example.com", referral_code=code_a, device="dev-b")

    retry = client.post(
        "/api/referrals/attribute",
        json={"referralCode": code_c},
        headers={**auth_header(b), **device_headers("dev-b")},
    )
    assert retry.status_code == 409
    assert retry.json()["code"] == "REFERRAL_ALREADY_ASSIGNED"

    assert client.get("/api/referrals/me", headers=auth_header(c)).json()["data"]["totalReferrals"] == 0
    assert client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]["totalReferrals"] == 1


def test_user_cannot_refer_themselves_with_own_code(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]
    res = client.post(
        "/api/referrals/attribute",
        json={"referralCode": code},
        headers={**auth_header(a), **device_headers("dev-a")},
    )
    assert res.status_code in (400, 409)
    assert res.json()["code"] == "SELF_REFERRAL_DETECTED"


def test_click_is_not_a_referral(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]
    res = client.post("/api/referrals/click", json={"referralCode": code}, headers=device_headers("dev-x"))
    assert res.status_code == 200
    assert client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]["totalReferrals"] == 0
