"""Voice booking agent API routes (Phase 8 / 8.1)."""

from __future__ import annotations

import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.voice.provider import UpliftVoiceProvider, VapiVoiceProvider, create_voice_provider
from app.voice.schemas import (
    VoiceCallEndRequest,
    VoiceCallEndResponse,
    VoiceCallStartRequest,
    VoiceCallStartResponse,
    VoiceToolExecuteRequest,
    VoiceToolExecuteResponse,
    VoiceTurnRequest,
    VoiceTurnResponse,
    VoiceWebhookEvent,
)
from app.voice.service import VoiceConversationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])
settings = get_settings()


def verify_voice_secret(x_voice_webhook_secret: str = Header(...)) -> None:
    expected = (settings.voice_webhook_secret or settings.uplift_webhook_secret or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice webhook secret is not configured",
        )
    if not hmac.compare_digest(x_voice_webhook_secret, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid voice webhook secret")


@router.post("/calls/start", response_model=VoiceCallStartResponse)
def start_voice_call(
    payload: VoiceCallStartRequest,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> VoiceCallStartResponse:
    return VoiceConversationService(db).start_call(payload)


@router.post("/turns", response_model=VoiceTurnResponse)
def voice_turn(
    payload: VoiceTurnRequest,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> VoiceTurnResponse:
    return VoiceConversationService(db).process_turn(payload)


@router.post("/tools/execute", response_model=VoiceToolExecuteResponse)
def voice_tool_execute(
    payload: VoiceToolExecuteRequest,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> VoiceToolExecuteResponse:
    return VoiceConversationService(db).execute_tool(payload)


@router.post("/calls/end", response_model=VoiceCallEndResponse)
def end_voice_call(
    payload: VoiceCallEndRequest,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> VoiceCallEndResponse:
    return VoiceConversationService(db).end_call(payload)


@router.post("/webhook")
def voice_webhook(
    event: VoiceWebhookEvent,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> dict:
    """Sparkle-canonical voice event ingress (provider-agnostic)."""
    if not event.call_id or not event.event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook event")
    return VoiceConversationService(db).handle_webhook(event)


@router.post("/events")
def voice_events(
    event: VoiceWebhookEvent,
    _: None = Depends(verify_voice_secret),
    db: Session = Depends(get_db),
) -> dict:
    """Alias for /webhook (same Sparkle event contract)."""
    if not event.call_id or not event.event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook event")
    return VoiceConversationService(db).handle_webhook(event)


@router.post("/vapi/webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    VAPI Server URL webhook.

    Parses VAPI-native payloads inside VapiVoiceProvider, then routes through
    the shared VoiceConversationService + Phase 5 tools.
    """
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    provider = VapiVoiceProvider(get_settings())
    if not provider.verify_webhook(headers=headers, body=body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid VAPI webhook auth")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    if str(message.get("type") or "") == "assistant-request":
        return provider.assistant_request_response()

    events = provider.parse_webhook(payload)
    if not events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unrecognized VAPI event")

    service = VoiceConversationService(db, voice_provider=provider)
    summary = service.handle_normalized_events(events)

    # tool-calls require a VAPI-shaped response
    if any(e.event_type == "tool.execute" for e in events):
        return provider.format_tool_results(summary.get("tool_results") or [])

    return {"ok": True, "handled": summary.get("handled", [])}


@router.post("/uplift/webhook")
async def uplift_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Uplift ingress for Sparkle-canonical events / tool proxies.

    Uplift's documented tool path is client-side RPC; this endpoint authenticates
    our adapter traffic — it does not invent an undocumented Uplift PSTN schema.
    """
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    provider = UpliftVoiceProvider(get_settings())
    if not provider.verify_webhook(headers=headers, body=body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Uplift webhook auth")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    events = provider.parse_webhook(payload)
    if not events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unrecognized Uplift event")

    service = VoiceConversationService(db, voice_provider=provider)
    summary = service.handle_normalized_events(events)

    if any(e.event_type == "tool.execute" for e in events):
        return provider.format_tool_results(summary.get("tool_results") or [])

    return {"ok": True, "handled": summary.get("handled", [])}


@router.get("/provider")
def voice_provider_status() -> dict:
    """Configuration readiness for the selected voice provider (no secrets)."""
    cfg = get_settings()
    selected = create_voice_provider(cfg)
    vapi = VapiVoiceProvider(cfg)
    uplift = UpliftVoiceProvider(cfg)
    return {
        "voice_provider_setting": (cfg.voice_provider or "auto").strip().lower(),
        "active_provider": selected.name,
        "active_configured": selected.is_configured(),
        "supports_barge_in": selected.supports_barge_in(),
        "providers": {
            "vapi": {"configured": vapi.is_configured()},
            "uplift": {"configured": uplift.is_configured()},
            "fake": {"configured": True},
        },
    }
