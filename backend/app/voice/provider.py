"""Voice provider factory (Phase 8.1)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.voice.base import VoiceProvider
from app.voice.fake import FakeVoiceProvider
from app.voice.uplift_provider import UpliftVoiceProvider
from app.voice.vapi_provider import VapiVoiceProvider

# Backwards-compatible re-export
__all__ = [
    "FakeVoiceProvider",
    "UpliftVoiceProvider",
    "VapiVoiceProvider",
    "create_voice_provider",
]


def create_voice_provider(settings: Settings | None = None) -> VoiceProvider:
    """
    Instantiate the selected voice provider.

    VOICE_PROVIDER:
      - vapi | uplift | fake — explicit selection (preferred)
      - auto — first configured among uplift, vapi; else fake

    Inactive providers may lack credentials; the app still starts.
    There is no silent mid-call failover between providers.
    """
    settings = settings or get_settings()
    requested = (settings.voice_provider or "auto").strip().lower()

    if requested == "fake":
        return FakeVoiceProvider()
    if requested == "vapi":
        return VapiVoiceProvider(settings)
    if requested == "uplift":
        return UpliftVoiceProvider(settings)

    # auto: prefer explicitly configured providers without failing startup
    uplift = UpliftVoiceProvider(settings)
    if uplift.is_configured():
        return uplift
    vapi = VapiVoiceProvider(settings)
    if vapi.is_configured():
        return vapi
    return FakeVoiceProvider()
