# Phase 10B+ — Deployment

Last touched: 2026-08-29

## Live URLs

| | |
|--|--|
| Frontend | https://car-wash-booking-voice-agent.vercel.app |
| Backend | https://car-wash-booking-voice-agent.onrender.com |
| Health | `GET /health` → ok |

## VAPI Server URL (critical)

Tool calls must hit Render, **not** a local ngrok tunnel.

Expected assistant + `save_booking` tool server URL:

`https://car-wash-booking-voice-agent.onrender.com/api/voice/vapi/webhook`

If voice says there was a “technical” problem and no booking appears, check VAPI Dashboard → Assistant / Tools → Server URL.

## Vercel

- Root Directory: `frontend`
- Framework Preset: **Next.js** (not Other)
- `NEXT_PUBLIC_API_URL=https://car-wash-booking-voice-agent.onrender.com`

## Render CORS

```text
FRONTEND_URL=https://car-wash-booking-voice-agent.vercel.app
CORS_ORIGINS=https://car-wash-booking-voice-agent.vercel.app
```

Render runs `alembic upgrade head` before each deploy (`preDeployCommand` in `render.yaml`).

---

## Live demo / video checklist

Do this **before** recording on the live URL.

### 1. Deploy latest `main`

Push to GitHub — Vercel (frontend) and Render (backend) auto-deploy.

### 2. Warm up Render (free tier)

Open the live site and hit **Book** once ~30–60s before recording so cold start is not on camera.

### 3. Clean demo data (production DB)

Wipes bookings/customers so your new booking is obvious in admin. **Keeps** services, availability, and admin users.

From your machine (with production `DATABASE_URL` in `backend/.env`):

```powershell
cd backend
.\venv\Scripts\activate
python -m scripts.reset_demo_data --confirm
```

Or set `DATABASE_URL` once for the command:

```powershell
$env:DATABASE_URL = "<your-supabase-postgres-url>"
python -m scripts.reset_demo_data --confirm
```

### 4. Record the flow

1. **Book** on live `/book` (or voice on `/voice`)
2. Open **Admin** → bell shows **New appointment through Web/Voice/WhatsApp**
3. Click **Accept** → red dot clears, booking shows as **confirmed** in Bookings

### 5. WhatsApp on live (optional)

Baileys runs on your PC; point it at Render so WhatsApp bookings land in the same DB as the live site.

In `whatsapp-bridge/.env`:

```text
BACKEND_URL=https://car-wash-booking-voice-agent.onrender.com
WHATSAPP_BRIDGE_SECRET=<same value as on Render>
```

Then `cd whatsapp-bridge` → `npm start` (scan QR if needed).

### 6. Browser voice

Enter a real mobile number on `/voice` before starting the VAPI call.

---

## Admin notifications

New bookings set `admin_acknowledged_at = NULL` until an admin clicks **Accept** in the bell dropdown or Bookings table. Accept also moves `pending` → `confirmed`.

Existing rows were backfilled on migration — only **new** bookings after deploy trigger notifications.

## Notes

- Admin bookings list orders by `created_at` (newest first)
- Never put `SUPABASE_SERVICE_ROLE_KEY` on Vercel
