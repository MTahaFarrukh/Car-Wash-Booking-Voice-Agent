"""Pydantic schemas for WhatsApp bridge communication."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MessageType = Literal["text", "image", "audio", "video", "document", "sticker", "unknown"]


class WhatsAppIncomingMessage(BaseModel):
    """Normalized inbound message forwarded by the Baileys bridge."""

    message_id: str = Field(min_length=1, max_length=128)
    sender_id: str = Field(min_length=3, max_length=128)
    phone_number: str = Field(min_length=3, max_length=32)
    text: str = Field(default="", max_length=4000)
    timestamp: datetime | None = None
    message_type: MessageType = "text"


class WhatsAppReply(BaseModel):
    """Structured reply returned to the Baileys bridge."""

    success: bool = True
    message: str = Field(min_length=1, max_length=4000)
    recipient: str = Field(min_length=3, max_length=128)
