# VELOOP Rewards — Submission Guide

Two projects are included:

```
veloop-referral-backend/    Python (FastAPI) backend — the main deliverable
veloop-referral-frontend/   the existing referral UI, now connected to that backend
```

## 1. Run it locally (5 minutes)

```bash
# terminal 1 — backend
cd veloop-referral-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000     # docs: http://localhost:8000/docs

# terminal 2 — frontend
cd veloop-referral-frontend
npm install
cp .env.example .env
npm run dev                                   # http://localhost:5173
```

Demo flow: create account A → copy its referral code → open an incognito window (or another
browser) → create account B with that code → sign in as B and call `POST /api/ads/complete` from
`/docs` 15 times → refresh A's page: 5,000 SVE appears. Try registering a third account **in the
same browser profile as A** using A's code: the "Account Already Exists" modal appears with the
masked email.

## 2. Push to GitHub

```bash
cd veloop-referral-backend
git init && git add . && git commit -m "VELOOP referral backend (FastAPI)"
git remote add origin git@github.com:<you>/veloop-referral-backend.git && git push -u origin main

cd ../veloop-referral-frontend
git init && git add . && git commit -m "Connect referral page to VELOOP backend"
git remote add origin git@github.com:<you>/veloop-referral-frontend.git && git push -u origin main
```

`.env` is git-ignored in both; only `.env.example` is committed.

## 3. Deploy

**Backend → Render:** New → Blueprint → pick the backend repo (`render.yaml` provisions PostgreSQL,
generates secrets, runs migrations). Then set:
* `CORS_ORIGINS` = your Vercel frontend URL
* `REFERRAL_LINK_BASE` = `https://www.velooprewards.in/register`

**Frontend → Vercel:** import the frontend repo, set `VITE_API_BASE_URL=https://<render-host>/api`,
deploy.

Verify: `curl https://<render-host>/api/health`.

## 4. What to submit

| # | Deliverable | Where |
|---|---|---|
| 1 | Backend GitHub repository | `veloop-referral-backend/` |
| 2 | Database schema + migrations | `alembic/versions/0001_initial_referral_schema.py`, `sql/schema.sql` |
| 3 | API documentation | `/docs` (Swagger), `docs/API.md`, `docs/openapi.json` |
| 4 | Frontend integration | `veloop-referral-frontend/` |
| 5 | Live backend | Render URL |
| 6 | Live frontend | Vercel URL |
| 7 | README.md | both repos |
| 8 | Testing evidence | `docs/TEST_EVIDENCE.md` (`pytest -v`, `python -m scripts.e2e_evidence`) |

## 5. Talking points for the review

* The frontend is never the source of truth — code, link, counts, balances, milestones and ad
  progress all come from the backend; `dummyData.js` keeps only rules and FAQ text.
* Rewards are idempotent at the database level: `UNIQUE(referral_id, milestone, reward_type)` plus a
  unique ledger idempotency key, inside one transaction with the balance update.
* Ad progress is a projection of a verified ad-event ledger with unique provider event ids — a
  client cannot post "35 ads watched".
* Fraud uses layered signals with configurable thresholds; a shared IP alone never means fraud,
  ambiguous cases go to `FRAUD_REVIEW`.
* Device identity ignores the browser, so Chrome → Firefox → incognito is still the same device;
  only an HMAC is stored, never a raw fingerprint.
* Self-referral returns `SELF_REFERRAL_DETECTED` + masked email, and nothing else about the account.
