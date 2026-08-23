# Sparkle Car Wash — AI Booking Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Baileys-25D366?logo=whatsapp&logoColor=white)](https://github.com/WhiskeySockets/Baileys)
[![Gemini](https://img.shields.io/badge/LLM-Gemini-8E75B2?logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![VAPI](https://img.shields.io/badge/Voice-VAPI-0F172A)](https://vapi.ai/)
[![Phase](https://img.shields.io/badge/Phase-10A%20Admin%20Auth-2dd4bf)](#whats-built)
[![Status](https://img.shields.io/badge/Status-Active-success)](https://github.com/MTahaFarrukh/Car-Wash-Booking-Voice-Agent)
[![GitHub](https://img.shields.io/badge/GitHub-Car--Wash--Booking--Voice--Agent-181717?logo=github)](https://github.com/MTahaFarrukh/Car-Wash-Booking-Voice-Agent)

Monorepo for **Sparkle Car Wash**: book, reschedule, and cancel washes through a shared booking engine, with WhatsApp (Gemini) and voice (VAPI / Uplift) on top.

> Day-to-day startup commands live in [`run.txt`](run.txt). This README is the project overview — a fuller write-up can wait until the final pass.

---

## What’s built

| Area | Status |
|------|--------|
| Booking domain (services, availability, create / reschedule / cancel) | Done |
| REST API + Next.js web app (public + admin) | Done — Phase 9 |
| WhatsApp bridge (Baileys) + Gemini tool-calling agent | Done |
| Voice channel (Phase 8) + VAPI / Uplift adapters (8.1) | Done — live VAPI booking verified |
| Browser VAPI voice booking (`/voice`) | Done — uses `@vapi-ai/web` + public key |
| Shared Phase 5 tool layer (no second booking engine) | Done |
| Admin auth (Supabase) + Render/Baileys deploy prep | Done — Phase 10A (not deployed yet) |

Voice, WhatsApp, and website bookings all use the same booking engine. Manual web bookings use `BookingSource.dashboard`; voice uses `voice`; WhatsApp uses `whatsapp`.

Production prep notes: [`DEPLOYMENT.md`](DEPLOYMENT.md). Admin login: `/admin/login` (public site stays open).

---

## Repo layout

```
carwash-booking/
├── backend/                 # FastAPI, Alembic, domain + agents
│   ├── app/
│   │   ├── agent/           # Phase 5 booking tools
│   │   ├── whatsapp/        # WhatsApp conversation + LLM agent
│   │   ├── voice/           # Voice agent + VAPI / Uplift providers
│   │   ├── llm/             # Gemini / OpenAI / fake providers
│   │   └── routers/         # HTTP API
│   ├── alembic/
│   ├── scripts/             # Seed data
│   └── tests/
├── frontend/                # Next.js dashboard / UI
├── whatsapp-bridge/         # Baileys → backend message bridge
├── .env.example             # Env template (copy to `.env`)
├── run.txt                  # How to start everything (Windows)
└── README.md
```

Deeper notes:

- [`backend/app/voice/README.md`](backend/app/voice/README.md) — voice providers & webhooks  
- [`backend/app/whatsapp/README.md`](backend/app/whatsapp/README.md) — WhatsApp agent  
- [`whatsapp-bridge/README.md`](whatsapp-bridge/README.md) — Baileys bridge  

---

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** (local or Supabase `DATABASE_URL`)
- Optional: **ngrok** (VAPI webhooks), Gemini API key (WhatsApp LLM), VAPI / Uplift credentials (voice)

---

## Quick start

### 1. Environment

```powershell
copy .env.example .env
copy frontend\.env.local.example frontend\.env.local
```

Fill in at least `DATABASE_URL`. For WhatsApp / voice, set the keys listed under [Environment](#environment).

### 2. Backend (one-time)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
```

### 3. Run day-to-day

Use [`run.txt`](run.txt) — typically:

1. **Backend** — `uvicorn` on port `8000`  
2. **Frontend** — `npm run dev` in `frontend/` (copy `frontend/.env.local.example` → `.env.local`)  
3. **WhatsApp bridge** — `npm start` in `whatsapp-bridge/` (optional)  
4. **ngrok** — `ngrok http 8000` for VAPI tool webhooks (optional)

Public site: `http://localhost:3000` — Book Online · Talk to AI · WhatsApp  
Admin: `http://localhost:3000/admin`

For browser voice: set `NEXT_PUBLIC_VAPI_PUBLIC_KEY` (VAPI **public** key) and `NEXT_PUBLIC_VAPI_ASSISTANT_ID` in `frontend/.env.local`. Never put `VAPI_API_KEY` or webhook secrets in `NEXT_PUBLIC_*`.

### 4. Tests

```powershell
cd backend
.\venv\Scripts\activate
pytest tests/ -q
```

---

## Channels

### WhatsApp

1. Start backend + `whatsapp-bridge`  
2. Scan QR once  
3. Needs `WHATSAPP_BRIDGE_SECRET`, `GEMINI_API_KEY`, `WHATSAPP_AGENT_MODE=auto`  

### Voice (VAPI)

1. Start backend + ngrok  
2. Set `VOICE_PROVIDER=vapi` and VAPI keys in root `.env`  
3. In VAPI, tool / assistant **Server URL**:

   `https://<ngrok-host>/api/voice/vapi/webhook`

4. Auth: **Bearer** = `VAPI_WEBHOOK_SECRET` (not `VAPI_API_KEY`)  
5. Free ngrok URLs change on restart — update VAPI when they do  

Uplift: set `VOICE_PROVIDER=uplift` and see the voice README.

---

## Environment

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres / Supabase |
| `CORS_ORIGINS` | Allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | Frontend → API base URL |
| `SUPABASE_*` | Supabase project keys |
| `WHATSAPP_BRIDGE_SECRET` | Bridge ↔ backend auth |
| `WHATSAPP_AGENT_MODE` | `auto` / `llm` / `rule` |
| `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` | WhatsApp LLM |
| `VOICE_PROVIDER` | `vapi` \| `uplift` \| `fake` \| `auto` |
| `VAPI_API_KEY`, `VAPI_ASSISTANT_ID`, `VAPI_WEBHOOK_SECRET` | VAPI |
| `UPLIFT_API_KEY`, `UPLIFT_AGENT_ID`, `VOICE_WEBHOOK_SECRET` | Uplift / shared voice secret |

Full template: [`.env.example`](.env.example). **Never commit** `.env`.

---

## License

[![License](https://img.shields.io/badge/License-Private-lightgrey)](#license)

Private course project — not for public distribution.
