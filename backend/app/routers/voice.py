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
# Catch common VAPI misconfigurations (tool Server URL truncated).
vapi_alias_router = APIRouter(tags=["voice"])


def verify_voice_secret(x_voice_webhook_secret: str = Header(...)) -> None:
    cfg = get_settings()
    expected = (cfg.voice_webhook_secret or cfg.uplift_webhook_secret or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice webhook secret is not configured",
        )
    if not hmac.compare_digest(x_voice_webhook_secret, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid voice webhook secret")


async def _handle_vapi_request(request: Request, db: Session) -> dict:
    """Shared VAPI webhook handler used by canonical + alias paths."""
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
    msg_type = str(message.get("type") or "")
    logger.info("vapi_webhook path=%s type=%s", request.url.path, msg_type or "unknown")

    if msg_type == "assistant-request":
        return provider.assistant_request_response()

    if msg_type == "tool-calls":
        preview_calls = provider.normalize_tool_calls(payload)
        logger.info(
            "vapi_tool_calls names=%s ids=%s",
            [c.name for c in preview_calls],
            [c.id for c in preview_calls],
        )

    events = provider.parse_webhook(payload)
    if not events:
        # Never 400 on tool-calls — VAPI treats non-results bodies as "No result returned".
        if msg_type == "tool-calls":
            fallback_ids = provider.extract_tool_call_ids(payload) or ["unknown"]
            logger.warning("vapi_tool_calls unrecognized payload; returning fallback results ids=%s", fallback_ids)
            return provider.format_tool_results(
                [
                    {
                        "id": cid,
                        "name": "unknown",
                        "result": {"success": False, "error": {"message": "Unrecognized tool payload"}},
                        "presentation": "Sorry, I could not process that booking request.",
                    }
                    for cid in fallback_ids
                ]
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unrecognized VAPI event")

    service = VoiceConversationService(db, voice_provider=provider)
    summary = service.handle_normalized_events(events)

    if any(e.event_type == "tool.execute" for e in events):
        tool_results = summary.get("tool_results") or []
        if not tool_results:
            fallback_ids = provider.extract_tool_call_ids(payload)
            logger.warning(
                "vapi_tool_calls empty results after handle; fallback ids=%s",
                fallback_ids,
            )
            tool_results = [
                {
                    "id": cid,
                    "name": "unknown",
                    "result": {"success": False, "error": {"message": "No tool calls parsed"}},
                    "presentation": "Sorry, I could not save the booking just now.",
                }
                for cid in fallback_ids
            ] or [
                {
                    "id": "unknown",
                    "name": "unknown",
                    "result": {"success": False, "error": {"message": "No tool calls parsed"}},
                    "presentation": "Sorry, I could not save the booking just now.",
                }
            ]
        response = provider.format_tool_results(tool_results)
        logger.info(
            "vapi_tool_results ids=%s",
            [r.get("toolCallId") for r in response.get("results") or []],
        )
        return response

    return {"ok": True, "handled": summary.get("handled", [])}


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
    """Canonical VAPI Server URL webhook."""
    return await _handle_vapi_request(request, db)


@router.api_route("", methods=["POST"])
@router.api_route("/", methods=["POST"])
async def vapi_webhook_root_alias(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Alias for tools whose Server URL was set to .../api/voice (missing /vapi/webhook).
    """
    return await _handle_vapi_request(request, db)


@vapi_alias_router.post("/vapi/webhook")
async def vapi_webhook_legacy_alias(request: Request, db: Session = Depends(get_db)) -> dict:
    """Alias for .../vapi/webhook without the /api/voice prefix."""
    return await _handle_vapi_request(request, db)


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
