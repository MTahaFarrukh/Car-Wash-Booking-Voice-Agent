# WhatsApp Conversational Agent

Phase 6 added WhatsApp booking on top of Phase 5 tools.
Phase 7 upgrades the conversation intelligence to an LLM orchestrator while keeping Baileys and domain services unchanged.

## Architecture

```
Baileys Bridge (Node.js)
    ↓ POST /api/whatsapp/messages
WhatsAppService
    ↓
WhatsAppConversationAgent (facade)
    ├── LLMConversationAgent (Phase 7, when configured)
    └── RuleBasedConversationAgent (Phase 6 fallback)
            ↓ Phase 5 tools
    AgentIntegrationService
            ↓
    Domain services → Supabase
```

## LLM conversation flow

1. Normalize WhatsApp message (unchanged).
2. Idempotency check via `message_id`.
3. Resolve/create customer from WhatsApp phone.
4. LLM receives system prompt + session context + short chat history.
5. LLM may call Phase 5 tools through `Phase5ToolExecutor`.
6. Tool results return to the LLM.
7. Final natural-language reply is sent back to Baileys.

## Structured state

`ConversationState` remains the source of truth for:

- customer_id / phone / name
- selected vehicle / service
- requested date / time
- target booking id / pending intent
- cached services, vehicles, active bookings
- short message history for LLM context

## Tool calling

Only these Phase 5 tools are exposed:

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

The LLM never touches SQLAlchemy or Supabase directly.

## Fallback behavior

`WHATSAPP_AGENT_MODE`:

| Value | Behavior |
|---|---|
| `auto` (default) | Use LLM when `LLM_API_KEY` is set; otherwise Phase 6 rule agent |
| `llm` | Prefer LLM when provider can be created |
| `rule` | Always use Phase 6 rule-based agent |

FastAPI still starts if no LLM key is configured.

## Configuration

See root `.env.example` for `LLM_*`, `GEMINI_*`, and `WHATSAPP_AGENT_MODE`.

Default LLM provider is **Gemini** (`LLM_PROVIDER=gemini`). Set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey). Google AI Plus (consumer) is separate from Gemini API developer quota.

## Prompt injection

The system prompt instructs the model to ignore override attempts and never expose secrets, prompts, or internal IDs.
Customer-facing replies are lightly sanitized.

## Tool-call loop protection

`LLM_MAX_TOOL_CALLS` caps tool invocations per inbound message.

## Tests

- Phase 6: `backend/tests/test_whatsapp_agent.py` (rule mode)
- Phase 7: `backend/tests/test_whatsapp_llm_agent.py` (FakeLLMProvider)
