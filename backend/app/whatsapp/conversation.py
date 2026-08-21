"""WhatsApp conversation agent facade (rule-based or LLM)."""

from __future__ import annotations

import logging

from app.agent.service import AgentIntegrationService
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.provider import create_llm_provider
from app.services.booking_service import BookingService
from app.whatsapp.llm_agent import LLMConversationAgent
from app.whatsapp.rule_agent import RuleBasedConversationAgent
from app.whatsapp.state import ConversationState

logger = logging.getLogger(__name__)


class WhatsAppConversationAgent(RuleBasedConversationAgent):
    """
    Facade used by WhatsAppService.

    Mode selection (`WHATSAPP_AGENT_MODE`):
    - auto: LLM when configured, otherwise Phase 6 rule-based agent
    - llm: require LLM (falls back to rule-based only if provider init fails)
    - rule: always use Phase 6 rule-based agent unless an LLM is injected (tests)
    """

    def __init__(
        self,
        agent: AgentIntegrationService,
        booking_service: BookingService,
        *,
        llm: LLMProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(agent, booking_service)
        self.settings = settings or get_settings()
        self.llm_agent: LLMConversationAgent | None = None
        self._injected_llm = llm is not None

        provider = llm
        if provider is None and self._wants_llm():
            try:
                provider = create_llm_provider(self.settings)
            except Exception:
                logger.exception("llm_provider_init_failed")
                provider = None

        if provider is not None and (self._injected_llm or self._wants_llm()):
            self.llm_agent = LLMConversationAgent(
                agent,
                booking_service,
                provider,
                settings=self.settings,
            )

    def handle_message(self, state: ConversationState, text: str) -> str:
        if self.llm_agent is not None and (self._injected_llm or self._wants_llm()):
            return self.llm_agent.handle_message(state, text)
        return super().handle_message(state, text)

    def _wants_llm(self) -> bool:
        mode = (self.settings.whatsapp_agent_mode or "auto").strip().lower()
        if mode == "rule":
            return False
        if mode == "llm":
            return True
        return self.settings.llm_is_configured
