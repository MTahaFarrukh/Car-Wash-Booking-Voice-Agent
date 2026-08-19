# Agent Integration Layer (Phase 5)

This package provides a provider-independent integration layer for conversational agents.

## Purpose

- Offer safe, typed operations for AI assistants.
- Reuse existing domain services (`BookingService`, `AvailabilityService`) instead of duplicating business logic.
- Return structured success/error payloads that can be mapped into natural language responses.

## Architecture

AI Agent -> Agent Tools -> `AgentIntegrationService` -> Domain Services -> SQLAlchemy -> Supabase PostgreSQL

## Available tools

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

Tool metadata lives in `app/agent/tools.py` and includes:
- name
- description
- input schema
- output schema
- handler name

## Inputs and outputs

- Input schemas: `app/schemas/agent.py`
- Output envelope:
  - `success: bool`
  - `data: object | null`
  - `error: { error_code, message, retryable, suggested_action } | null`

This format is intentionally generic so future VAPI/WhatsApp/Uplift/OpenAI integrations can map it to their own tool-call payloads.

## Error handling

Domain/service exceptions are converted to stable agent error codes, such as:
- `CUSTOMER_NOT_FOUND`
- `VEHICLE_NOT_FOUND`
- `SERVICE_NOT_FOUND`
- `SLOT_UNAVAILABLE`
- `BOOKING_NOT_FOUND`
- `INVALID_BOOKING_TIME`
- `BOOKING_ALREADY_CANCELLED`
- `VALIDATION_ERROR`
- `DUPLICATE_REQUEST`

Raw SQL errors and stack traces are not exposed to the agent.

## Safety notes

- Booking creation validates customer, vehicle ownership, service, and slot availability.
- Availability comes from `AvailabilityService`; conflict detection is not duplicated.
- Duplicate/retry protection is implemented as an exact active-booking lookup before create.

## Future integrations (Phase 6+)

Future provider adapters should:
1. Parse provider tool payload into `app/schemas/agent.py` models.
2. Call the matching `AgentIntegrationService` method.
3. Convert `AgentResult` into provider-specific response format.
4. Preserve error codes for consistent conversational behavior.
