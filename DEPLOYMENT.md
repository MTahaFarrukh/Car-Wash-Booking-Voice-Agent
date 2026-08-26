# Phase 10B — FastAPI on Render

Last touched: 2026-08-26

Intended production shape:

- Frontend → Vercel (Next.js) — not this step
- Backend → Render (FastAPI) — **this step**
- Database / Auth → Supabase
- Voice → VAPI
- LLM → Gemini
- WhatsApp → always-on Baileys host (not this step)

## Deploy status (2026-08-26)

Prepared and attempted CLI deploy of service `sparkle-api` from
`https://github.com/MTahaFarrukh/Car-Wash-Booking-Voice-Agent.git` (`main`, `rootDir: backend`).

**Blocked by Render billing:** API returned `402 Payment information is required`.
Add a payment method at https://dashboard.render.com/billing , then re-run create/deploy
(or ask the agent to retry). Until `/health` succeeds on the live HTTPS URL, this is
**not** considered deployed.

Local pre-checks (passed):

- `pytest -q` → 164 passed, 1 skipped
- `/health` is public (no auth)
- Admin routes remain Bearer + `admin_users`
- `DATABASE_URL` points at Supabase pooler (`sslmode` set)
- No `.env` committed; service-role not used by frontend

## Render service settings

| Setting | Value |
|--------|--------|
| Service name | `sparkle-api` |
| Root directory | `backend` |
| Runtime | Python 3 (`PYTHON_VERSION=3.12.0` in blueprint) |
| Build | `pip install -r requirements.txt` |
| Pre-deploy / release | `alembic upgrade head` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Plan | free (when billing allows) |
| Blueprint | [`render.yaml`](render.yaml) |

## Environment variables (Render Dashboard — secrets never in git)

### Required for a healthy API

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | Supabase Postgres (prefer pooler + `sslmode=require`) |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | Anon key — used to verify admin JWTs |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | Comma-separated production frontend origins (**no `*`**) |
| `FRONTEND_URL` | Optional; merged into CORS (set to Vercel URL when ready) |

### LLM / WhatsApp / Voice (existing app config)

| Variable | Suggested production value |
|----------|----------------------------|
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | secret |
| `GEMINI_MODEL` | match local (currently `gemini-3.6-flash` in repo defaults) |
| `WHATSAPP_AGENT_MODE` | `auto` |
| `WHATSAPP_BRIDGE_SECRET` | shared with Baileys bridge |
| `VOICE_PROVIDER` | `vapi` |
| `VOICE_WEBHOOK_SECRET` | secret |
| `VAPI_API_KEY` | secret |
| `VAPI_ASSISTANT_ID` | assistant UUID |
| `VAPI_WEBHOOK_SECRET` | secret |

### Optional / not required for admin JWT verify

| Variable | Notes |
|----------|--------|
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only if ever needed; **never** put on Vercel / frontend |

Do **not** set `CORS_ORIGINS=*`.

Until Vercel exists, leave `CORS_ORIGINS` / `FRONTEND_URL` empty (or set only known HTTPS origins). Browser admin against the API will need the real frontend origin later.

## Post-deploy verification checklist

Once the service is live:

1. `GET https://<service>.onrender.com/health` → 200
2. `GET https://<service>.onrender.com/docs` → 200
3. `GET https://<service>.onrender.com/health/db` → `{"status":"ok","database":"connected"}`
4. `GET /api/admin/me` without token → 401
5. `GET /api/admin/me` with non-admin Bearer → 403
6. `GET /api/admin/me` with seeded admin Bearer → 200

Free instances spin down after ~15 minutes idle (cold start ~30–60s).

## Admin bootstrap (if not already done on Supabase)

1. Create email/password user in Supabase Auth.
2. From a machine with `DATABASE_URL`:  
   `python -m scripts.seed_admin --email … --auth-user-id …`

## Baileys (unchanged — not deploying now)

Prefer a separate always-on host with durable `auth_info`. Do not use Render free web sleep for Baileys.

## Security notes

- `/api/admin/*` requires Supabase Bearer + active `admin_users` row
- Public booking / services / availability remain open
- CORS is origin-list based
- Service role key stays server-only
