# VELOOP Rewards – Referral API Reference

Base URL: `{API_BASE}/api`  ·  Interactive docs: `/docs` (Swagger UI), `/redoc`, `/openapi.json`

All responses share one envelope:

```json
{ "success": true, "data": { } }
```

Errors:

```json
{ "success": false, "code": "SELF_REFERRAL_DETECTED", "message": "…", "maskedEmail": "ayan***lam@gmail.com" }
```

**Common headers**

| Header | Required | Purpose |
|---|---|---|
| `Authorization: Bearer <accessToken>` | private endpoints | the user identity is taken **only** from this token |
| `X-Device-Signals` | register / login / attribute / ads | base64url JSON of coarse device signals |
| `X-Device-Token` | optional | signed device token returned by register/login |
| `Idempotency-Key` | optional, reward-triggering calls | replay protection |

---

## Auth

### `POST /auth/register`
Creates an account, registers the device and (optionally) attributes a referral in the same transaction.

Request:
```json
{ "email": "rahul@example.com", "password": "Password123!", "phone": "+919876543210", "referralCode": "VELOOPDM4BX" }
```

Success `200`:
```json
{ "success": true, "data": {
    "accessToken": "eyJhbGciOi…", "tokenType": "Bearer", "deviceToken": "eyJ…​.sig",
    "user": { "id": "…", "email": "rahul@example.com", "referralCode": "VELOOPK3P9Z", "level": 1,
              "balances": { "sve": 0, "tokens": 0, "gems": 0, "spins": 0, "xp": 0 } },
    "referral": { "status": "PENDING", "referralId": "…" } } }
```

Errors: `EMAIL_ALREADY_REGISTERED` (409), `INVALID_REFERRAL_CODE` (400), `SELF_REFERRAL_DETECTED` (409, with `maskedEmail`), `RATE_LIMITED` (429), `VALIDATION_ERROR` (422).

### `POST /auth/login`
`{ "email": …, "password": … }` → same shape as register (without `referral`). Errors: `INVALID_CREDENTIALS` (401).

### `GET /auth/me`
Returns the authenticated user + balances.

---

## Referrals

### `GET /referrals/me` — dashboard (powers the whole page)

```json
{ "success": true, "data": {
  "referralCode": "VELOOPDM4BX",
  "referralLink": "https://www.velooprewards.in/register?ref=VELOOPDM4BX",
  "totalReferrals": 3, "successfulReferrals": 1, "pendingReferrals": 2, "spamReferrals": 1,
  "totalSvesEarned": 5000, "totalXpEarned": 60, "totalGemsEarned": 10,
  "totalTokensEarned": 5000, "totalSpinsEarned": 2,
  "referralProgress": { "referralId": "…", "referredUser": "rahu***rma@example.com",
                        "adsWatched": 18, "adsRequired": 20, "percent": 90, "adsRemaining": 2,
                        "nextReward": { "label": "2 Lucky Spins", "rewardType": "SPINS",
                                        "rewardAmount": 2, "milestone": 20 } },
  "rewardMilestones": [ { "id": "…", "milestone": 15, "rewardType": "SVE", "rewardAmount": 5000,
                          "label": "5,000 SVE", "subtitle": "≈ ₹10",
                          "condition": "Friend completes 15 Ad Watch tasks",
                          "unlocked": true, "credited": true } ],
  "recentReferrals": [ { "id": "…", "status": "PENDING", "referredUser": "rahu***rma@example.com",
                         "adsWatched": 18, "adsRequired": 35, "createdAt": "…", "completedAt": null } ],
  "balances": { "sve": 5000, "tokens": 5000, "gems": 10, "spins": 2, "xp": 60, "level": 1 } } }
```

### `POST /referrals/attribute`
Attach a referrer to the **authenticated** user (for flows where the code arrives after signup).
`{ "referralCode": "VELOOPDM4BX", "source": "LINK" }` → `{ "referralId": …, "status": "PENDING" }`.
Errors: `REFERRAL_ALREADY_ASSIGNED` (409), `SELF_REFERRAL_DETECTED`, `INVALID_REFERRAL_CODE`, `RATE_LIMITED`.

### `POST /referrals/click` (public)
`{ "referralCode": "VELOOPDM4BX" }` → `{ "clickId": "…" }`. A click is never a referral.

### `GET /referrals?page=1&limit=20&status=pending`
`status` ∈ `all | successful | pending | spam`. Returns `{ items, page, limit, total, totalPages }`; referred users appear as masked emails only.

### `GET /referrals/{id}/progress`
Ownership-checked. Returns ads watched/required, milestones reached and remaining. `FORBIDDEN` (403) for another user's referral.

### `GET /referrals/spam`
`{ "spamCount": 3, "recentSpam": [ { "id": "…", "createdAt": "…", "status": "NOT_ELIGIBLE", "message": "This referral attempt was not eligible for rewards." } ] }` — no device hashes, IPs or risk scores.

### `GET /referrals/rewards/history?page=1&limit=20`
Reward ledger entries: `rewardType`, `amount`, `reason`, `milestone`, `referralId`, `createdAt`, `status`.

### `GET /referrals/config/milestones` (public)
The reward structure as stored in the `milestone_configs` table.

---

## Ads

### `POST /ads/complete` (auth, `Idempotency-Key` supported)
```json
{ "provider": "veloop-sdk", "providerEventId": "b3f1…", "adUnit": "rewarded_home", "watchedSeconds": 30, "completedAt": "2026-09-16T09:00:00Z" }
```
→ `{ "duplicate": false, "eligibleAds": 15, "creditedRewards": [ { "milestone": 15, "rewardType": "SVE", "amount": 5000, "label": "5,000 SVE", "transactionId": "…" } ] }`

Rejections (`AD_EVENT_REJECTED`, 400): watch time below `AD_MIN_WATCH_SECONDS`, stale `completedAt`. Duplicate `providerEventId` returns `duplicate: true` and credits nothing.

### `POST /ads/postback` (server-to-server)
Requires `X-Veloop-Signature: HMAC-SHA256(AD_PROVIDER_SECRET, rawBody)`. Body adds `userId`.

---

## Admin (`role=admin`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/referrals?status=&page=&limit=` | all referrals with risk score/level |
| GET | `/admin/referrals/{id}` | referral + ad progress + rewards + fraud flags + audit trail |
| PATCH | `/admin/referrals/{id}/status` | the only authorised way to change an attributed referral |
| GET | `/admin/reconciliation/{userId}` | ledger totals vs stored balances |
| GET | `/admin/audit?action=&limit=` | audit log |

---

## Error codes

`INVALID_REFERRAL_CODE`, `REFERRAL_ALREADY_ASSIGNED`, `SELF_REFERRAL_DETECTED`, `DEVICE_ALREADY_ASSOCIATED`, `REFERRAL_NOT_ELIGIBLE`, `REWARD_ALREADY_CREDITED`, `RATE_LIMITED`, `UNAUTHORIZED`, `FORBIDDEN`, `FRAUD_REVIEW`, `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `INVALID_CREDENTIALS`, `EMAIL_ALREADY_REGISTERED`, `INVALID_DEVICE_TOKEN`, `AD_EVENT_REJECTED`, `DUPLICATE_EVENT`, `INTERNAL_ERROR`.

## cURL examples

```bash
# register with a referral code
curl -X POST "$API/api/auth/register" -H 'Content-Type: application/json' \
  -H "X-Device-Signals: $(printf '{"platform":"Linux","screen":"1920x1080x24","timezone":"Asia/Kolkata","language":"en-IN","hardware":"8c/8g","canvasHint":"42"}' | base64 -w0 | tr '+/' '-_' | tr -d '=')" \
  -d '{"email":"rahul@example.com","password":"Password123!","referralCode":"VELOOPDM4BX"}'

# dashboard
curl "$API/api/referrals/me" -H "Authorization: Bearer $TOKEN"

# verified ad completion
curl -X POST "$API/api/ads/complete" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -H "Idempotency-Key: $(uuidgen)" \
  -d '{"provider":"veloop-sdk","providerEventId":"'$(uuidgen)'","watchedSeconds":30}'
```
