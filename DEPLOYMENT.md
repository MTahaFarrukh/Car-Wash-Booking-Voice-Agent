# Phase 10B+ — Deployment

Last touched: 2026-08-27

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

## Notes

- Admin bookings list orders by `created_at` (local fix may need deploy)
- Browser voice: enter a real mobile number before starting the call
- Never put `SUPABASE_SERVICE_ROLE_KEY` on Vercel
