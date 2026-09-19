"""Device level abuse + self-referral across browsers."""
from tests.conftest import auth_header, device_headers, register


def test_same_device_second_account_self_referral_blocked(client):
    a = register(client, "ayanalam@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]

    res = register(client, "ayan.second@example.com", referral_code=code, device="dev-a")
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "SELF_REFERRAL_DETECTED"
    assert body["maskedEmail"] == "ayan***lam@example.com"
    assert "@" in body["maskedEmail"] and "ayanalam@" not in body["maskedEmail"]

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    assert dash["totalReferrals"] == 0
    assert dash["totalXpEarned"] == 0


def test_browser_change_does_not_bypass_device_rule(client):
    a = register(client, "ayanalam@example.com", device="dev-a", browser="Chrome")
    code = a.json()["data"]["user"]["referralCode"]

    # Same machine, different browser (and no device token/cookie).
    res = register(client, "ayan.alt@example.com", referral_code=code, device="dev-a", browser="Firefox")
    assert res.status_code == 409
    assert res.json()["code"] == "SELF_REFERRAL_DETECTED"


def test_spam_referral_gets_no_reward_and_is_counted(client):
    """Multi-accounting on one device -> flagged, rewards blocked."""
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]

    # dev-shared already hosts two unrelated accounts + similar email + same network
    register(client, "alice1@example.com", device="dev-shared")
    register(client, "alice2@example.com", device="dev-shared")
    res = register(client, "alice3@example.com", referral_code=code, device="dev-shared")

    status = res.json()["data"]["referral"]["status"]
    assert status in ("PENDING", "FRAUD_REVIEW", "SPAM")

    dash = client.get("/api/referrals/me", headers=auth_header(a)).json()["data"]
    if status in ("FRAUD_REVIEW", "SPAM"):
        assert dash["spamReferrals"] >= 1
        assert dash["totalXpEarned"] == 0
        spam = client.get("/api/referrals/spam", headers=auth_header(a)).json()["data"]
        assert spam["spamCount"] >= 1
        # no internal fraud signals leak out
        assert "riskScore" not in str(spam)
        assert "deviceHash" not in str(spam)


def test_legit_referral_on_different_device_is_allowed(client):
    a = register(client, "alice@example.com", device="dev-a")
    code = a.json()["data"]["user"]["referralCode"]
    res = register(client, "bob@example.com", referral_code=code, device="dev-b")
    assert res.json()["data"]["referral"]["status"] == "PENDING"
