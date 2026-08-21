"""WhatsApp inbound message orchestration."""

from __future__ import annotations

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
        state.phone = payload.phone_number
        lookup = self.agent.get_customer(CustomerLookupInput(phone=payload.phone_number))
        if lookup.success and lookup.data:
            state.customer_id = uuid_from_string(lookup.data["customer_id"])
            state.customer_name = lookup.data.get("name")
            return

        display_name = self._default_customer_name(payload.phone_number)
        created = self.agent.find_or_create_customer(
            CustomerToolInput(name=display_name, phone=payload.phone_number)
        )
        if created.success and created.data:
            state.customer_id = uuid_from_string(created.data["customer_id"])
            state.customer_name = created.data.get("name")

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
