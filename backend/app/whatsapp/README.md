# WhatsApp Conversational Agent

Phase 6 adds a WhatsApp booking experience on top of the existing Phase 5 agent integration layer.

## Architecture

```
Baileys Bridge (Node.js)
    ↓ POST /api/whatsapp/messages
WhatsAppService
    ↓
WhatsAppConversationAgent
    ↓ Phase 5 tools
AgentIntegrationService
    ↓
BookingService / AvailabilityService / CustomerVehicleService / ServiceCatalogService
    ↓
Supabase PostgreSQL
```

## Endpoint

`POST /api/whatsapp/messages`

Headers:

- `X-WhatsApp-Bridge-Secret`: must match `WHATSAPP_BRIDGE_SECRET`

Body: `WhatsAppIncomingMessage` (`backend/app/schemas/whatsapp.py`)

Response: `WhatsAppReply` with the text Baileys should send back.

## Phase 5 tools reused

All booking operations go through `AgentIntegrationService`:

- `find_or_create_customer`
- `get_customer`
- `create_vehicle`
- `get_customer_vehicles`
- `list_services`
- `check_availability`
- `create_booking`
- `get_booking`
- `reschedule_booking`
- `cancel_booking`

Read-only active booking lookup for cancel/reschedule uses `BookingService.get_customer_bookings` (no duplicated booking mutations).

## Customer identity

WhatsApp `sender_id` and normalized `phone_number` identify the customer. On first contact, `find_or_create_customer` creates a profile keyed by phone. No JWT or Supabase Auth in Phase 6.

## Conversation state

Short-term state is kept in memory per `sender_id` (`ConversationStateStore`):

- selected service / vehicle / date / time
- pending intent (book, cancel, reschedule)
- confirmation flag
- cached services, vehicles, and active bookings

State survives multiple messages in the same process but is not persisted across backend restarts.

## Idempotency

Processed WhatsApp `message_id` values are stored in `whatsapp_processed_messages`. Duplicate deliveries return the original response without re-running booking actions.

## Error handling

- Non-text messages receive a friendly unsupported-media reply
- Tool failures are converted to user-safe messages
- Invalid bridge secret returns HTTP 401

## Parser

`backend/app/whatsapp/parser.py` extracts services, vehicles, dates, and times from natural language so customers can say things like:

> Book my Honda Civic for premium wash tomorrow at 3pm.

## Tests

See `backend/tests/test_whatsapp_agent.py`.
