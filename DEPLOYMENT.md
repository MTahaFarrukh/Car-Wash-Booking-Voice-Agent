# Phase 10A — deployment preparation (DO NOT treat as “deployed”)
#
# Last touched: 2026-08-25 (docs-only streak keep-alive)
#
# Intended production shape:
#   Frontend  → Vercel (Next.js)
#   Backend   → Render (FastAPI)
#   Database  → Supabase Postgres
#   Voice     → VAPI
#   LLM       → Gemini
#   WhatsApp  → Baileys bridge (hosting TBD — see below)

## FastAPI on Render (ready, not deployed)

Suggested service settings:

- Root directory: `backend`
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Release / pre-deploy: `alembic upgrade head`

Blueprint sketch: [`render.yaml`](render.yaml)

Required env on Render (private):

- `DATABASE_URL`
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` (token verification)
- `SUPABASE_SERVICE_ROLE_KEY` (optional; not required for admin JWT verify)
- `CORS_ORIGINS` and/or `FRONTEND_URL` (production Vercel URL)
- `ENVIRONMENT=production`
- WhatsApp / VAPI / Gemini secrets as today

Admin bootstrap after first deploy:

1. Create email/password user in Supabase Auth.
2. Run: `python -m scripts.seed_admin --email … --auth-user-id …`

## Frontend on Vercel

- Root: `frontend`
- Env: all `NEXT_PUBLIC_*` including Supabase URL + **anon** key
- Never set `SUPABASE_SERVICE_ROLE_KEY` on Vercel

## Baileys WhatsApp bridge — audit findings

Code reality (`whatsapp-bridge/`):

- Auth via `useMultiFileAuthState` → default dir `auth_info/` (or `WHATSAPP_SESSION_PATH`)
- Creds saved on `creds.update`
- Reconnects in-process unless `loggedOut` (then QR again)
- Long-lived Node process; **no HTTP server / no PORT**
- Session **survives process restart only if the auth directory survives**

### A. Render backend + Render Baileys web service

| Factor | Fit |
|--------|-----|
| Ephemeral disk (free) | Poor — `auth_info` lost → re-QR |
| Sleep when idle | Poor — WhatsApp disconnects; misses messages |
| Persistent disk (paid) | Possible if always-on + disk mounted at session path |
| Process model | Mismatch — bridge is not an HTTP app |

### B. Render backend + separate persistent Baileys host

Matches the code: always-on VM/VPS (or Render **Background Worker** + persistent disk) with durable `auth_info`.

### C. Other low-cost options

Small always-on VPS (Hetzner/DigitalOcean/Oracle free tier), or home/office machine with tunnel — only if you accept ops burden.

### Recommendation (not a final decision)

Prefer **B**: keep FastAPI on Render; run Baileys as a **single always-on process with durable disk**. Do not use Render free web sleep for Baileys. Revisit after you pick budget (worker+disk vs cheap VPS).

## Security notes (Phase 10A)

- `/api/admin/*` requires Supabase Bearer + `admin_users` row
- Public booking / services / availability remain open
- CORS is origin-list based (no `*` in production config)
- Service role key must stay server-only
