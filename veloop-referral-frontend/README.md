# VELOOP Rewards — Referral Frontend (backend-connected)

The original redesigned referral page, now driven entirely by the VELOOP referral backend
(FastAPI). `dummyData.js` no longer contains a single user-specific value.

## What changed

| Area | Before | Now |
|---|---|---|
| Referral code & link | `dummyData.referralInfo` | `GET /api/referrals/me` |
| Stats (total / successful / pending / **spam**) | hardcoded | backend statistics |
| SVE / XP / Gems / Tokens earned | hardcoded | reward-ledger sums from backend |
| Referral progress bar | counted referrals | referred friend's **verified ad watches** |
| Reward cards & timeline | `rewards` array in JS | `milestone_configs` table via API |
| Referral list | did not exist | `GET /api/referrals` with filters + pagination |
| Reward history | did not exist | `GET /api/referrals/rewards/history` |
| Self-referral | did not exist | `SELF_REFERRAL_DETECTED` → "Account Already Exists" modal |
| Loading / error / empty | demo toggle | real skeletons, retry and empty states |

## New / updated files

```
src/api/client.js               fetch wrapper: base URL, auth header, device headers, ApiError
src/api/device.js               device signal collection + signed device token storage
src/api/referrals.js            every referral endpoint in one module
src/context/ReferralContext.jsx dashboard fetch, loading/error state, refresh, ?ref= click tracking
src/hooks/useMilestones.js      milestone config (personalised when signed in, public otherwise)
src/components/AuthPanel/       minimal login/register surface (replace with VELOOP auth)
src/components/SelfReferralModal/  "Account Already Exists" modal with masked email
src/components/ReferralList/    filterable + paginated referral list and reward history
src/components/common/Skeleton.jsx  skeletons + error state
src/components/{ReferralCard,ShareButtons,StatsSection,ReferralProgress,RewardsSection,RewardTimeline}
                                rewritten to consume backend data
src/utils/dummyData.js          static page copy only (rules + FAQ)
```

## Device signals

`src/api/device.js` sends coarse signals (platform, screen, timezone, language, hardware, canvas
hint) as a base64 `X-Device-Signals` header. The browser name/user agent is deliberately excluded
so switching browsers or using incognito does not look like a new device. Hashing happens on the
server; the client never sees a device hash or a risk score.

## Setup

```bash
npm install
cp .env.example .env            # VITE_API_BASE_URL=http://localhost:8000/api
npm run dev                     # http://localhost:5173
npm run build
```

Backend must be running with this origin in `CORS_ORIGINS`.

## Production (Vercel)

Set `VITE_API_BASE_URL=https://<backend-host>/api` in the project's environment variables and
redeploy. No dummy data ships to production.

## Auth note

`AuthPanel` exists so the page can be demonstrated end to end. When integrating with VELOOP's real
auth, delete it and make sure `localStorage['veloop_access_token']` holds the platform access token
— everything else keeps working.
