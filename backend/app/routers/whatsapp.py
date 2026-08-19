"""WhatsApp bridge API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.whatsapp import WhatsAppIncomingMessage, WhatsAppReply
from app.whatsapp.service import WhatsAppService

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
settings = get_settings()


def verify_bridge_secret(x_whatsapp_bridge_secret: str = Header(...)) -> None:
    if not settings.whatsapp_bridge_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp bridge secret is not configured",
        )
    if x_whatsapp_bridge_secret != settings.whatsapp_bridge_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bridge secret")


@router.post("/messages", response_model=WhatsAppReply)
def receive_whatsapp_message(
    payload: WhatsAppIncomingMessage,
    _: None = Depends(verify_bridge_secret),
    db: Session = Depends(get_db),
) -> WhatsAppReply:
    service = WhatsAppService(db)
    return service.process_message(payload)
