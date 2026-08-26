# Phase 10B+ — Deployment

Last touched: 2026-08-26

Intended production shape:

- Frontend → Vercel (Next.js)
- Backend → Render (FastAPI) — **live**
- Database / Auth → Supabase
- Voice → VAPI
- LLM → Gemini
- WhatsApp → always-on Baileys host (not yet)

## Backend (Render) — live

| | |
|--|--|
| Service | `Car-Wash-Booking-Voice-Agent` (`srv-da7hjom417fc73924v90`) |
| URL | https://car-wash-booking-voice-agent.onrender.com |
| Root directory | `backend` |
| Health | `GET /health` → ok |
| DB | `GET /health/db` → connected |
| Admin | `GET /api/admin/me` → 401 without Bearer (expected) |

Build / start (as configured on Render):

- Build: `pip install -r requirements.txt`
- Pre-deploy: `alembic upgrade head` (if configured)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

### CORS (required before the website can call the API)

Set on the Render service (Dashboard → Environment):

```text
FRONTEND_URL=https://car-wash-booking-voice-agent.vercel.app
CORS_ORIGINS=https://car-wash-booking-voice-agent.vercel.app
```

Do **not** use `CORS_ORIGINS=*`.

Redeploy / restart the Render service after changing env vars.

## Frontend (Vercel) — 404 fix

Symptom: `https://car-wash-booking-voice-agent.vercel.app/` → `404 NOT_FOUND`

Cause: this repo is a **monorepo**. There is **no** `package.json` at the repo root. The Next.js app lives in `frontend/`. If Vercel Root Directory is empty / `.`, the project has nothing to deploy → platform `NOT_FOUND`.

### Fix in Vercel Dashboard

1. Project → **Settings → General → Root Directory** → set to **`frontend`** → Save
2. **Settings → Environment Variables** (Production), add:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://car-wash-booking-voice-agent.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | (same as local / Supabase project URL) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (anon key only — never service role) |
| `NEXT_PUBLIC_WHATSAPP_NUMBER` | digits only |
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY` | VAPI **public** key |
| `NEXT_PUBLIC_VAPI_ASSISTANT_ID` | assistant id |

3. **Deployments → Redeploy** the latest commit (or push an empty commit / “Redeploy”)

Optional: `frontend/vercel.json` is present for framework hints; Root Directory is what actually matters.

### Verify after redeploy

- `https://car-wash-booking-voice-agent.vercel.app/` → landing page
- `/book`, `/voice`, `/admin/login` load
- Admin login talks to Render `/api/admin/me` (CORS must include the Vercel origin)

## Security notes

- Never put `SUPABASE_SERVICE_ROLE_KEY` on Vercel
- Never commit `.env`, `frontend/.env.local`, or `deployment.env`
- Free Render instances may cold-start after ~15 minutes idle
