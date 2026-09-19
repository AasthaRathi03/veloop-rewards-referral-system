# VELOOP Rewards — Referral Backend (Python / FastAPI)

Secure backend for the VELOOP Rewards referral program: referral attribution, a configurable
milestone reward engine, an immutable reward ledger, verified ad-watch tracking, and layered
anti-fraud / self-referral protection.

> **Stack note:** the task suggested Node/Express, this implementation uses **Python + FastAPI +
> SQLAlchemy + PostgreSQL + Alembic**. Every requirement (schema, endpoints, rules, security) is
> implemented 1:1; only the language differs.

**Core principle:** the frontend is never the source of truth. Referral counts, balances,
eligibility, milestones and ad progress are computed and stored server-side. A user cannot
manipulate React state, localStorage or an API request to create a reward.

---

## Contents

1. [Project overview](#1-project-overview)
2. [Referral architecture](#2-referral-architecture)
3. [Backend architecture](#3-backend-architecture)
4. [Database schema](#4-database-schema)
5. [Referral lifecycle](#5-referral-lifecycle)
6. [Reward milestones](#6-reward-milestones)
7. [Reward ledger & idempotency](#7-reward-ledger--idempotency)
8. [Ad-watch verification](#8-ad-watch-verification)
9. [Anti-fraud system](#9-anti-fraud-system)
10. [Device detection](#10-device-detection)
11. [Self-referral detection & masked email](#11-self-referral-detection--masked-email)
12. [Spam referral handling](#12-spam-referral-handling)
13. [Authentication & authorization](#13-authentication--authorization)
14. [Security](#14-security)
15. [API documentation](#15-api-documentation)
16. [Environment variables](#16-environment-variables)
17. [Local setup](#17-local-setup)
18. [Database setup & migrations](#18-database-setup--migrations)
19. [Testing](#19-testing)
20. [Deployment](#20-deployment)
21. [Frontend integration](#21-frontend-integration)
22. [Acceptance criteria mapping](#22-acceptance-criteria-mapping)

---

## 1. Project overview

| | |
|---|---|
| Runtime | Python 3.12, FastAPI, Uvicorn |
| ORM / DB | SQLAlchemy 2.0, PostgreSQL 16 (SQLite for tests) |
| Migrations | Alembic |
| Auth | JWT access tokens (bcrypt password hashing) + signed device tokens |
| Cache / limits | Redis (optional; in-process fallback) |
| Docs | Swagger UI at `/docs`, OpenAPI at `/openapi.json`, `docs/API.md` |
| Tests | pytest — 25 tests + a 21-check end-to-end evidence run |

---

## 2. Referral architecture

```
React frontend
      │  fetch (+ Authorization, X-Device-Signals, Idempotency-Key)
      ▼
FastAPI routers  ──►  middleware: CORS · security headers · rate limit · validation · error handler
      │
      ▼
Services   referral · milestone · reward · fraud · device · ad · audit
      │
      ▼
PostgreSQL   referrals · referral_progress · referral_rewards · reward_transactions
             ad_events · devices · user_devices · spam_referrals · audit_logs · milestone_configs
```

The frontend never talks to the database and never computes a reward.

---

## 3. Backend architecture

```
app/
├── main.py                  FastAPI app, CORS, security headers, request logging
├── core/
│   ├── config.py            env-driven settings (no hardcoded secrets)
│   ├── security.py          bcrypt, JWT, device tokens, HMAC hashing
│   ├── errors.py            AppError + error codes + structured handlers
│   └── rate_limit.py        fixed-window limiter (Redis or in-process)
├── db/
│   ├── base.py              engine, session, Base, get_db
│   └── seed.py              milestone configuration seeding
├── models/                  User, Device, UserDevice, Referral, ReferralClick,
│                            ReferralProgress, MilestoneConfig, ReferralReward,
│                            RewardTransaction, IdempotencyRecord, AdEvent,
│                            SpamReferral, AuditLog
├── schemas/                 pydantic request/response validation
├── services/
│   ├── referral_service.py  attribution, dashboard, listings, spam summary
│   ├── milestone_service.py configurable milestone engine
│   ├── reward_service.py    ledger + balance updates + reconciliation
│   ├── fraud_service.py     layered risk scoring, self-referral detection
│   ├── device_service.py    device identity, hashing, signed device tokens
│   ├── ad_service.py        verified ad events → referral progress
│   └── audit_service.py     append-only audit trail
├── api/
│   ├── deps.py              auth, admin guard, device resolution
│   └── routes/              auth · referrals · ads · admin · health
└── utils/                   email masking, referral codes, idempotency
alembic/                     migrations (0001_initial)
sql/schema.sql               generated PostgreSQL DDL
scripts/                     seed_demo.py, e2e_evidence.py
tests/                       referral, fraud, rewards, security, masking
docs/                        API.md, openapi.json, TEST_EVIDENCE.md
```

---

## 4. Database schema

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | account + balances (`sve`, `tokens`, `gems`, `spins`, `xp`) | `email` UNIQUE, `referral_code` UNIQUE |
| `devices` | device identity (HMAC hash only) | `device_hash` UNIQUE |
| `user_devices` | account ↔ device association | UNIQUE(`user_id`,`device_id`) |
| `referrals` | the referral relationship | **UNIQUE(`referred_user_id`)** → one referrer per user |
| `referral_clicks` | link clicks (never a referral) | index(`referral_code`,`created_at`) |
| `referral_progress` | projection of verified ad events | UNIQUE(`referral_id`) |
| `milestone_configs` | reward rules (DB-driven, not in code) | UNIQUE(`milestone`,`reward_type`) |
| `referral_rewards` | per-milestone reward state | **UNIQUE(`referral_id`,`milestone`,`reward_type`)** |
| `reward_transactions` | immutable ledger | **UNIQUE(`idempotency_key`)** |
| `idempotency_records` | request replay protection | UNIQUE(`scope`,`user_id`,`key`) |
| `ad_events` | verified ad ledger | **UNIQUE(`provider`,`provider_event_id`)** |
| `spam_referrals` | fraud evidence (internal) | index(`referrer_user_id`) |
| `audit_logs` | append-only audit trail | index(action, created_at), (entity_type, entity_id) |

Indexes also cover `referrer_user_id`, `status`, `created_at`, `reward_type`, `milestone` and the
device lookups used by fraud checks. Full DDL: [`sql/schema.sql`](sql/schema.sql).

---

## 5. Referral lifecycle

```
LINK_CLICKED ──► REGISTERED ──► PENDING ──► QUALIFYING ──► SUCCESSFUL
                      │
                      └─► SPAM / FRAUD_REVIEW / REJECTED   (no rewards)
```

* A click is stored in `referral_clicks` and is **not** a referral.
* On registration with a valid code the referral is created `PENDING` and `+20 XP` is credited.
* Each verified ad event moves progress; the referral becomes `QUALIFYING`, then `SUCCESSFUL`
  with `completed_at` once the final milestone (35 ads) is reached.
* Attribution is immutable: a second referral code returns `REFERRAL_ALREADY_ASSIGNED`. Only an
  admin endpoint can change an attributed referral, and the change is audited.

---

## 6. Reward milestones

Stored in `milestone_configs` — changing an amount is a row update, not a deploy:

| Referred user activity | Referrer reward | Type |
|---|---|---|
| Successful referral (registration) | +20 XP | `XP` |
| 15 eligible ad watches | 5,000 SVE | `SVE` |
| 20 eligible ad watches | 2 Spins | `SPINS` |
| 30 eligible ad watches | 5,000 Tokens | `TOKENS` |
| 35 eligible ad watches | 10 Gems | `GEMS` |

Each milestone is credited **once per referral**, guaranteed by
`UNIQUE(referral_id, milestone, reward_type)` plus a unique ledger idempotency key.

---

## 7. Reward ledger & idempotency

Balances are never touched outside `reward_service.credit()`. Every credit:

```
BEGIN
  lock referral row (SELECT … FOR UPDATE)
  check milestone config + existing referral_rewards row
  insert reward_transactions (idempotency_key = referral:{id}:m{milestone}:{type})
  update user balance (balance_after recorded on the transaction)
  mark referral_rewards.status = CREDITED
  write audit log (REWARD_CREDITED)
COMMIT            -- any failure → ROLLBACK, no partial credit
```

`GET /api/admin/reconciliation/{userId}` compares ledger sums against stored balances, so a drift
is always detectable. Totals shown on the dashboard (`totalSvesEarned` etc.) are ledger sums, never
client values.

---

## 8. Ad-watch verification

The client cannot post a counter. It posts a single completion event which is validated:

* authenticated user (identity from the JWT, never from the body)
* minimum watch duration (`AD_MIN_WATCH_SECONDS`)
* timestamp freshness (`AD_EVENT_MAX_AGE_SECONDS`)
* unique `provider_event_id` (DB constraint) → duplicates credit nothing
* optional `Idempotency-Key` header → replays return the stored response
* rate limiting per user
* `POST /api/ads/postback` for server-to-server provider callbacks, HMAC-signed

Referral progress is a **projection of `ad_events`**, recomputed from the ledger, so the counter can
never be edited independently.

---

## 9. Anti-fraud system

`fraud_service.assess_referral_risk()` combines layered signals into an internal score:

| Signal | Weight |
|---|---|
| Device already linked to the referrer's own account | 70 |
| Device already hosts other accounts | 25 |
| Blocked device | 80 |
| Device-token / fingerprint drift | 10 |
| Shared network (IP hash match) | 12 — *never decisive alone* |
| Similar email root (dots/+tags normalised) | 20 |
| Same phone number | 35 |
| Referral burst from one device in 24h | 18 |
| Referrer's spam history | 12 |
| Referrer account created minutes ago | 10 |

Bands (configurable via env): `0–30 LOW → PENDING`, `31–60 REVIEW → FRAUD_REVIEW`,
`61–100 HIGH → SPAM`. Blocked statuses earn **zero** rewards. A single weak signal such as a shared
IP can never reach the HIGH band on its own.

---

## 10. Device detection

* The frontend sends coarse signals (platform, screen, timezone, language, hardware, canvas hint).
  **No user agent / browser name is included**, so Chrome → Firefox → Incognito on the same machine
  resolves to the same device.
* The server normalises them and stores only `HMAC-SHA256(DEVICE_HASH_SECRET, signals)`; raw
  fingerprints are never persisted. IPs are stored only as `HMAC(IP_HASH_SECRET, ip)`.
* A **signed device token** (`payload.HMAC`) is issued and stored in an httpOnly cookie plus
  localStorage. It is tamper-resistant, server-verifiable, expiring, rotatable and revocable
  (`token_version`), so clearing cookies alone does not create a "new" device.

---

## 11. Self-referral detection & masked email

If the device used at signup already belongs to the referrer's account, registration is blocked
before the account is created:

```json
{
  "success": false,
  "code": "SELF_REFERRAL_DETECTED",
  "message": "This device has already been associated with a VELOOP Rewards account. Please use that account to log in.",
  "maskedEmail": "ayan***lam@gmail.com"
}
```

Masking rules (`app/utils/email_mask.py`): long local part → first 4 + `***` + last 3
(`ayanalam@example.com` → `ayan***lam@example.com`); short local part → `ab***@gmail.com`. The full
local part is never returned, and the masked email is returned **only** in this security response.
The frontend renders it in the "Account Already Exists" modal.

Never exposed to the frontend: full email, phone, internal user ids of other accounts, device
hashes, IP hashes, risk scores, fraud reasons.

---

## 12. Spam referral handling

Flagged referrals are written to `spam_referrals` with reason, category, risk score and hashed
device/IP. Users see only a count and a neutral message via `GET /api/referrals/spam`
(`spamCount`, `recentSpam[].message`) — no detection logic leaks. Spam/rejected/review referrals
receive no XP and no milestone rewards.

---

## 13. Authentication & authorization

* `Authorization: Bearer <JWT>`; the user id always comes from the verified token. A `userId` in a
  request body is ignored.
* Ownership checks on every referral resource — requesting another user's referral returns `403
  FORBIDDEN` (IDOR protected).
* `role=admin` required for `/api/admin/*`.
* Designed to slot into VELOOP's existing auth: replace `decode_access_token` in
  `app/core/security.py` (or `get_current_user` in `app/api/deps.py`) with the platform's verifier —
  no other module changes.

---

## 14. Security

* Validation on every input (pydantic): email, password length, phone pattern, referral code regex,
  UUIDs, pagination bounds, event ids, device token.
* Rate limits on auth, attribution, click, ad events and read endpoints.
* CORS restricted to an explicit origin allowlist (never `*` with credentials).
* Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, `Cache-Control: no-store`, HSTS outside development.
* Structured errors with stable codes; internals (stack traces, SQL, risk data) never returned.
* Secrets only via environment variables; `.env` is git-ignored, `.env.example` documents each one.
* Audit log for `REFERRAL_CREATED`, `REFERRAL_REJECTED`, `SELF_REFERRAL_DETECTED`,
  `REFERRAL_MARKED_SPAM`, `MILESTONE_REACHED`, `REWARD_CREDITED`, `AD_EVENT_VERIFIED`,
  `AD_EVENT_REJECTED`, `DEVICE_REGISTERED`, `ADMIN_STATUS_CHANGE`, and more.

---

## 15. API documentation

Full reference: [`docs/API.md`](docs/API.md) · OpenAPI: [`docs/openapi.json`](docs/openapi.json) ·
Live Swagger UI: `/docs`.

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | – | signup + device registration + referral attribution |
| POST | `/api/auth/login` | – | login |
| GET | `/api/auth/me` | ✔ | profile + balances |
| GET | `/api/referrals/me` | ✔ | full referral dashboard |
| POST | `/api/referrals/attribute` | ✔ | attach referrer (immutable) |
| POST | `/api/referrals/click` | – | track link click |
| GET | `/api/referrals` | ✔ | paginated, filterable referral list |
| GET | `/api/referrals/{id}/progress` | ✔ | per-referral ad progress + milestones |
| GET | `/api/referrals/spam` | ✔ | spam count + neutral summaries |
| GET | `/api/referrals/rewards/history` | ✔ | reward ledger history |
| GET | `/api/referrals/config/milestones` | – | reward structure from the DB |
| POST | `/api/ads/complete` | ✔ | verified ad completion (idempotent) |
| POST | `/api/ads/postback` | HMAC | provider server-to-server callback |
| GET/PATCH | `/api/admin/*` | admin | referral inspection, status change, reconciliation, audit |
| GET | `/api/health` | – | health check |

---

## 16. Environment variables

See [`.env.example`](.env.example). Summary:

| Group | Variables |
|---|---|
| App | `ENV`, `DEBUG`, `API_PREFIX` |
| Database | `DATABASE_URL` (`postgres://` is auto-upgraded to `postgresql+psycopg://`), `SQL_ECHO` |
| Auth | `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Device/fraud | `DEVICE_TOKEN_SECRET`, `DEVICE_HASH_SECRET`, `IP_HASH_SECRET`, `DEVICE_TOKEN_EXPIRE_DAYS`, `RISK_REVIEW_THRESHOLD`, `RISK_HIGH_THRESHOLD` |
| Ads | `AD_PROVIDER_SECRET`, `AD_MIN_WATCH_SECONDS`, `AD_EVENT_MAX_AGE_SECONDS` |
| Infra | `REDIS_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, `REFERRAL_LINK_BASE` |
| Limits | `RATE_LIMIT_AUTH`, `RATE_LIMIT_ATTRIBUTE`, `RATE_LIMIT_AD_EVENT`, `RATE_LIMIT_READ` |

Never commit real credentials.

---

## 17. Local setup

```bash
git clone <your-backend-repo> && cd veloop-referral-backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then fill in real secrets

uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs
```

Generate strong secrets: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.

Docker alternative: `docker compose up --build` (API + PostgreSQL + Redis).

---

## 18. Database setup & migrations

```bash
createdb veloop                                  # or use a managed Postgres
export DATABASE_URL=postgresql+psycopg://veloop:veloop@localhost:5432/veloop

alembic upgrade head                             # apply migrations
python -m scripts.seed_demo                      # seed milestone configuration
python -m scripts.seed_demo --demo               # + demo users, referrals, ad events
```

New migration after a model change: `alembic revision --autogenerate -m "describe change"`.

---

## 19. Testing

```bash
pytest -v                       # 25 tests
pytest --cov=app                # with coverage
python -m scripts.e2e_evidence  # 21-check end-to-end evidence report
```

Covered: valid/invalid/duplicate referrals, existing referrer, self-referral, first device,
same device + second account, browser change, cookie reset, suspicious device, 15/20/30/35 ad
milestones, duplicate events, duplicate reward processing, unauthorised requests, another user's
data, rate limiting, invalid payloads, replay requests, email masking.
Results: [`docs/TEST_EVIDENCE.md`](docs/TEST_EVIDENCE.md).

---

## 20. Deployment

**Render** (`render.yaml` included): create a Blueprint from the repo — it provisions PostgreSQL,
generates secrets, runs `alembic upgrade head` and starts Uvicorn. Set `CORS_ORIGINS` to the
deployed frontend origin and `REFERRAL_LINK_BASE` to the production register URL.

**Railway / Fly.io / any Docker host:** use the included `Dockerfile` (`Procfile` also provided).
Requirements: managed PostgreSQL with TLS, all secrets as environment variables, HTTPS only.

Frontend (Vercel): set `VITE_API_BASE_URL=https://<backend-host>/api` and redeploy.

---

## 21. Frontend integration

The existing referral UI was kept; only its data source changed. See the frontend repo README —
in short: `src/api/client.js` + `src/api/referrals.js` + `src/api/device.js` (device signals),
`src/context/ReferralContext.jsx` (fetch, loading, error, refresh), `SelfReferralModal`, and every
component now reads backend values. `src/utils/dummyData.js` retains only static page copy
(rules + FAQ); no user-specific values remain in the frontend.

---

## 22. Acceptance criteria mapping

| Criterion | Where |
|---|---|
| Referral code / link from backend | `utils/codes.py`, `referral_service.referral_link`, `GET /referrals/me` |
| Total / successful / pending / spam referrals from backend | `referral_service.statistics` |
| SVE / XP / Gems / Tokens totals from backend | `reward_service.totals_by_type` (ledger sums) |
| Referred-user ad progress from backend | `ad_service`, `referral_progress` table |
| Milestones backend-controlled | `milestone_configs` + `milestone_service` |
| 15/20/30/35 + 20 XP milestones work | `tests/test_rewards.py`, evidence run |
| Rewards credited only once | `UNIQUE(referral_id, milestone, reward_type)` + ledger idempotency key |
| Duplicate events cannot duplicate rewards | `UNIQUE(provider, provider_event_id)`, `Idempotency-Key` |
| Attribution immutable / one referrer | `UNIQUE(referred_user_id)`, `REFERRAL_ALREADY_ASSIGNED` |
| Same-device abuse via layered signals | `fraud_service`, `device_service` |
| Self-referral detected + required error + masked email | `guard_pre_registration`, `utils/email_mask.py` |
| Spam referrals: no rewards, count visible | `spam_referrals`, `GET /referrals/spam` |
| Auth / authorization / validation / rate limiting / CORS / secrets | `api/deps.py`, `schemas/`, `core/rate_limit.py`, `main.py`, `.env.example` |
| Audit logs / DB constraints / ledger / transactional processing | `audit_service`, models, `reward_service` |
| API docs / tests / README / deployment / frontend connected | `docs/`, `tests/`, this file, `render.yaml`, frontend repo |
| No sensitive information exposed | privacy tests in `tests/test_security.py` |
