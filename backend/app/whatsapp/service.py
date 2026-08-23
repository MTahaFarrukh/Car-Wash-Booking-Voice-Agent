"""WhatsApp inbound message orchestration."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.service import AgentIntegrationService
from app.llm.base import LLMProvider
from app.models.whatsapp_message import WhatsAppProcessedMessage
from app.schemas.agent import CustomerLookupInput, CustomerToolInput
from app.schemas.whatsapp import WhatsAppIncomingMessage, WhatsAppReply
from app.services.booking_service import BookingService
from app.whatsapp.conversation import WhatsAppConversationAgent
from app.whatsapp.parser import uuid_from_string
from app.whatsapp.state import ConversationState, conversation_state_store

_PLACEHOLDER_NAME_RE = re.compile(r"^whatsapp customer\b", re.IGNORECASE)


class WhatsAppService:
    """Coordinates idempotency, customer identity, and conversation handling."""

    def __init__(
        self,
        db: Session,
        *,
        llm: LLMProvider | None = None,
        conversation: WhatsAppConversationAgent | None = None,
    ) -> None:
        self.db = db
        self.agent = AgentIntegrationService(db)
        self.booking_service = BookingService(db)
        self.conversation = conversation or WhatsAppConversationAgent(
            self.agent,
            self.booking_service,
            llm=llm,
        )

    def process_message(self, payload: WhatsAppIncomingMessage) -> WhatsAppReply:
        existing = self.db.scalar(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == payload.message_id
            )
        )
        if existing is not None:
            return WhatsAppReply(
                success=True,
                message=existing.response_message,
                recipient=payload.sender_id,
            )

        if payload.message_type != "text" or not payload.text.strip():
            reply_text = (
                "Sorry, I can currently process text messages. "
                "Please send me your request as text."
            )
            return self._persist_and_reply(payload, reply_text)

        state = conversation_state_store.get(payload.sender_id)
        self._ensure_customer(state, payload)
        reply_text = self.conversation.handle_message(state, payload.text)
        return self._persist_and_reply(payload, reply_text)

    def _ensure_customer(self, state: ConversationState, payload: WhatsAppIncomingMessage) -> None:
        phone = self._resolved_phone(payload)
        push_name = (payload.push_name or "").strip() or None

        if not phone:
            state.needs_phone = True
            # Keep any previously resolved phone on this sender session.
            if not state.phone:
                state.phone = None
            if state.customer_id and state.customer_name:
                state.needs_name = self.is_placeholder_name(state.customer_name)
            else:
                state.needs_name = True
            return

        state.phone = phone
        state.needs_phone = False

        lookup = self.agent.get_customer(CustomerLookupInput(phone=phone))
        if lookup.success and lookup.data:
            state.customer_id = uuid_from_string(lookup.data["customer_id"])
            state.customer_name = lookup.data.get("name")
            if self.is_placeholder_name(state.customer_name) and push_name:
                updated = self.agent.find_or_create_customer(
                    CustomerToolInput(name=push_name, phone=phone)
                )
                if updated.success and updated.data:
                    state.customer_name = updated.data.get("name") or push_name
            state.needs_name = self.is_placeholder_name(state.customer_name)
            return

        # Prefer WhatsApp profile name; otherwise create a placeholder and ask later.
        display_name = push_name if push_name else self._default_customer_name(phone)
        created = self.agent.find_or_create_customer(
            CustomerToolInput(name=display_name, phone=phone)
        )
        if created.success and created.data:
            state.customer_id = uuid_from_string(created.data["customer_id"])
            state.customer_name = created.data.get("name")
            state.needs_name = self.is_placeholder_name(state.customer_name)

    @classmethod
    def is_placeholder_name(cls, name: str | None) -> bool:
        if not name or not str(name).strip():
            return True
        return bool(_PLACEHOLDER_NAME_RE.match(str(name).strip()))

    @staticmethod
    def _resolved_phone(payload: WhatsAppIncomingMessage) -> str | None:
        """Return a real mobile phone, never a WhatsApp LID disguised as digits."""
        raw = (payload.phone_number or "").strip()
        sender = payload.sender_id or ""
        digits = re.sub(r"\D", "", raw)

        if sender.endswith("@lid"):
            lid_digits = re.sub(r"\D", "", sender.split("@", 1)[0].split(":", 1)[0])
            # Bridge mistakenly used LID digits as the phone.
            if not digits or digits == lid_digits:
                return None

        if 10 <= len(digits) <= 15:
            return f"+{digits}"

        # Fallback: phone-number JID (never @lid).
        if sender.endswith("@s.whatsapp.net") or sender.endswith("@c.us"):
            jid_digits = re.sub(r"\D", "", sender.split("@", 1)[0].split(":", 1)[0])
            if 10 <= len(jid_digits) <= 15:
                return f"+{jid_digits}"

        return None

    @staticmethod
    def _default_customer_name(phone_number: str) -> str:
        suffix = phone_number[-4:] if len(phone_number) >= 4 else phone_number
        return f"WhatsApp Customer {suffix}"

    def _persist_and_reply(self, payload: WhatsAppIncomingMessage, reply_text: str) -> WhatsAppReply:
        record = WhatsAppProcessedMessage(
            message_id=payload.message_id,
            sender_id=payload.sender_id,
            response_message=reply_text,
        )
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.scalar(
                select(WhatsAppProcessedMessage).where(
                    WhatsAppProcessedMessage.message_id == payload.message_id
                )
            )
            if existing is not None:
                reply_text = existing.response_message

        return WhatsAppReply(success=True, message=reply_text, recipient=payload.sender_id)
