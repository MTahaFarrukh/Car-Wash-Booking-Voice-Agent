# Phase 8 / 8.1 — AI Voice Booking Agent (multi-provider)

Provider-independent voice channel that reuses **Phase 5** booking tools.

## Architecture

```
Caller
  ├─ VAPI  ──POST /api/voice/vapi/webhook──┐
  └─ Uplift─POST /api/voice/uplift/webhook─┤
                                           ▼
                              VoiceProvider adapter
                                           ▼
                              NormalizedVoiceEvent / ToolCall
                                           ▼
                              VoiceConversationService / Agent
                                           ▼
                              Phase5ToolExecutor (source=VOICE)
                                           ▼
                              AgentIntegrationService → Supabase
```

WhatsApp remains unchanged on Baileys → Gemini → Phase 5.

## Provider selection

```
VOICE_PROVIDER=vapi
VOICE_PROVIDER=uplift
VOICE_PROVIDER=fake
VOICE_PROVIDER=auto   # first configured among uplift, then vapi; else fake
```

Inactive providers may omit credentials; the app still starts.
There is **no silent mid-call failover** between VAPI and Uplift.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/voice/calls/start\|end`, `/turns`, `/tools/execute` | `X-Voice-Webhook-Secret` |
| POST | `/api/voice/webhook`, `/events` | Sparkle-canonical events |
| POST | `/api/voice/vapi/webhook` | VAPI Bearer / `X-Vapi-Secret` / HMAC |
| POST | `/api/voice/uplift/webhook` | Voice/Uplift shared secret |
| GET | `/api/voice/provider` | none (no secrets returned) |

## Env

```
VOICE_PROVIDER=auto
VOICE_WEBHOOK_SECRET=
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_WEBHOOK_SECRET=
UPLIFT_API_KEY=
UPLIFT_AGENT_ID=
UPLIFT_WEBHOOK_SECRET=
```

## CallLog

`call_logs.provider` stores `vapi`, `uplift`, or `fake`.

## Live readiness

Do not claim VAPI or Uplift is operational until a real call has completed end-to-end.
Use `VOICE_PROVIDER=fake` + `/api/voice/turns` for local smoke tests without telephony.
