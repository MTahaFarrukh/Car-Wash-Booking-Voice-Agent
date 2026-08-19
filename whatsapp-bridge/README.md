# Sparkle WhatsApp Bridge (Baileys)

The WhatsApp bridge is a **transport-only** Node.js service. It connects to WhatsApp using [Baileys](https://github.com/WhiskeySockets/Baileys), forwards normalized inbound messages to the FastAPI backend, and sends the backend reply back to the customer.

It does **not** contain booking logic, database access, or duplicated agent tools.

## What Baileys does here

- Maintains the WhatsApp Web session
- Receives inbound customer messages
- Sends outbound replies
- Handles reconnect and QR pairing

## Install

```powershell
cd whatsapp-bridge
npm install
copy .env.example .env
```

Set `WHATSAPP_BRIDGE_SECRET` in `whatsapp-bridge/.env` to the same value as `WHATSAPP_BRIDGE_SECRET` in the monorepo root `.env`.

## Start the bridge

```powershell
cd whatsapp-bridge
npm start
```

On first run, a QR code is printed in the terminal. Scan it with the WhatsApp account used for the business/test line.

Session files are stored in `whatsapp-bridge/auth_info/` (gitignored).

## Connect to FastAPI

| Variable | Purpose |
|---|---|
| `BACKEND_URL` | FastAPI base URL, e.g. `http://127.0.0.1:8000` |
| `WHATSAPP_BRIDGE_SECRET` | Shared secret sent as `X-WhatsApp-Bridge-Secret` |
| `WHATSAPP_SESSION_PATH` | Directory for Baileys auth state |
| `BACKEND_TIMEOUT_MS` | HTTP timeout when calling FastAPI (default 30000) |

## Message flow

### Inbound

1. Customer sends WhatsApp text
2. Baileys emits a message event
3. Bridge normalizes payload (`message_id`, `sender_id`, `phone_number`, `text`, `timestamp`)
4. Bridge `POST`s to `/api/whatsapp/messages`
5. FastAPI returns `{ success, message, recipient }`
6. Bridge sends `message` back through WhatsApp

### Outbound

Phase 6 uses synchronous request/response: FastAPI returns the reply in the same HTTP call. Baileys sends it immediately.

## Reconnect / logout

- Temporary disconnects: bridge reconnects automatically
- Logged out: delete `auth_info/` and restart to scan a new QR code

## Tests

```powershell
cd whatsapp-bridge
npm test
```

Tests cover message normalization only — no real WhatsApp account required.

## Local development (full stack)

Terminal 1 — backend:

```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — bridge:

```powershell
cd whatsapp-bridge
npm start
```

Scan the QR code, then send `Hi` from a customer phone to the paired WhatsApp number.
