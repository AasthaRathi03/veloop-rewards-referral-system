"""Milestone engine + idempotency."""
import uuid

from tests.conftest import auth_header, device_headers, register, watch_ads


def _pair(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]
    b = register(client, "bob@example.com", referral_code=code, device="dev-b")
    return a, b


def test_15_ads_credits_5000_sve_once(client):
    a, b = _pair(client)
    watch_ads(client, auth_header(b), 15)

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalSvesEarned"] == 5000
    assert dash["totalTokensEarned"] == 0
    assert dash["referralProgress"]["adsWatched"] == 15

    # more ads below the next milestone -> no extra SVE
    watch_ads(client, auth_header(b), 2)
    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalSvesEarned"] == 5000


def test_duplicate_ad_event_cannot_duplicate_reward(client):
    a, b = _pair(client)
    watch_ads(client, auth_header(b), 14)

    event_id = f"evt-{uuid.uuid4()}"
    payload = {"provider": "veloop-sdk", "providerEventId": event_id, "watchedSeconds": 30}
    headers = {**auth_header(b), **device_headers("dev-b")}

    first = client.post("/api/ads/complete", json=payload, headers=headers).json()["data"]
    second = client.post("/api/ads/complete", json=payload, headers=headers).json()["data"]

    assert first["eligibleAds"] == 15
    assert second["duplicate"] is True
    assert second["eligibleAds"] == 15
    assert client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]["totalSvesEarned"] == 5000


def test_idempotency_key_replay_returns_same_result(client):
    a, b = _pair(client)
    headers = {**auth_header(b), **device_headers("dev-b"), "Idempotency-Key": "key-123"}
    payload = {"provider": "veloop-sdk", "providerEventId": f"evt-{uuid.uuid4()}", "watchedSeconds": 30}

    r1 = client.post("/api/ads/complete", json=payload, headers=headers).json()
    r2 = client.post("/api/ads/complete", json=payload, headers=headers).json()
    assert r1 == r2


def test_all_milestones_credit_exactly_once(client):
    a, b = _pair(client)
    watch_ads(client, auth_header(b), 35)

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalSvesEarned"] == 5000
    assert dash["totalSpinsEarned"] == 2
    assert dash["totalTokensEarned"] == 5000
    assert dash["totalGemsEarned"] == 10
    assert dash["totalXpEarned"] == 20
    assert dash["successfulReferrals"] == 1
    assert dash["pendingReferrals"] == 0

    # re-open the page / extra ads -> nothing new is credited
    client.get("/api/referrals/me", headers=auth_header(a))
    watch_ads(client, auth_header(b), 5)
    dash2 = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash2["totalSvesEarned"] == 5000
    assert dash2["totalGemsEarned"] == 10
    assert dash2["totalXpEarned"] == 20

    history = client.get("/api/referrals/rewards/history", headers=auth_header(a)).json()["data"]["items"]
    assert len(history) == 5  # XP + 4 milestones


def test_balances_match_ledger(client):
    a, b = _pair(client)
    watch_ads(client, auth_header(b), 35)
    me = client.get("/api/auth/me", headers=auth_header(a)).json()["data"]
    assert me["balances"]["sve"] == 5000
    assert me["balances"]["gems"] == 10
    assert me["balances"]["spins"] == 2
    assert me["balances"]["xp"] == 20


def test_short_ad_watch_is_rejected(client):
    a, b = _pair(client)
    res = client.post(
        "/api/ads/complete",
        json={"provider": "veloop-sdk", "providerEventId": "evt-tooshort-1", "watchedSeconds": 2},
        headers={**auth_header(b), **device_headers("dev-b")},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "AD_EVENT_REJECTED"
    assert client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]["referralProgress"]["adsWatched"] == 0
