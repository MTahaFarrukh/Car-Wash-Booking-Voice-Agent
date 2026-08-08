"""FastAPI backend for car wash booking agents."""

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from booking import get_all_bookings, save_booking
from config import HOST, PORT
app = FastAPI(
    title="Sparkle Car Wash Booking API",
    description="Simple API for VAPI and Uplift AI booking agents.",
    version="1.0.0",
)

# Allow browser-based Uplift voice client to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookingRequest(BaseModel):
    """Booking payload for POST /booking."""

    name: str = Field(..., min_length=1)
    vehicle: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    time: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)


@app.get("/")
def root() -> dict:
    """Health check."""
    return {"status": "ok", "service": "Sparkle Car Wash Booking API"}


@app.post("/booking")
def create_booking(booking: BookingRequest) -> dict:
    """Save a new booking (used by Uplift client and manual testing)."""
    print(f"[Uplift/booking] saving: {booking.model_dump()}")
    result = save_booking(
        name=booking.name,
        vehicle=booking.vehicle,
        date=booking.date,
        time=booking.time,
        phone=booking.phone,
    )
    print(f"[Uplift/booking] saved: {result['booking']}")
    return result


@app.get("/bookings")
def list_bookings() -> dict:
    """Return all saved bookings."""
    return {"count": len(get_all_bookings()), "bookings": get_all_bookings()}


def _parse_arguments(raw: Any) -> dict[str, Any]:
    """Normalize tool arguments to a dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Parse arguments from different VAPI tool-call payload shapes."""
    function_data = tool_call.get("function", {})

    for candidate in (
        tool_call.get("arguments"),
        tool_call.get("parameters"),
        function_data.get("arguments"),
        function_data.get("parameters"),
    ):
        parsed = _parse_arguments(candidate)
        if parsed:
            return parsed

    return {}


def _extract_tool_name(tool_call: dict[str, Any], fallback: str = "") -> str:
    """Get tool name from various VAPI payload shapes."""
    function_data = tool_call.get("function", {})
    return (
        tool_call.get("name")
        or function_data.get("name")
        or fallback
        or ""
    )


def _collect_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect tool calls from all known VAPI message fields."""
    collected: list[dict[str, Any]] = []

    for item in message.get("toolCallList", []):
        collected.append(
            {
                "id": item.get("id", ""),
                "name": _extract_tool_name(item),
                "arguments": _extract_tool_arguments(item),
            }
        )

    if collected:
        return collected

    for item in message.get("toolWithToolCallList", []):
        tool_call = item.get("toolCall", {})
        collected.append(
            {
                "id": tool_call.get("id", ""),
                "name": _extract_tool_name(tool_call, fallback=item.get("name", "")),
                "arguments": _extract_tool_arguments(tool_call),
            }
        )

    return collected


def _vapi_tool_response(tool_call_id: str, result: str | None = None, error: str | None = None) -> dict[str, str]:
    """Build one VAPI-compatible tool result object."""
    response: dict[str, str] = {"toolCallId": tool_call_id}
    if error:
        response["error"] = error.replace("\n", " ").strip()
    else:
        response["result"] = (result or "Done.").replace("\n", " ").strip()
    return response


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request) -> JSONResponse:
    """
    VAPI server URL webhook.
    Handles tool-calls for save_booking and returns VAPI-compatible results.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Some integrations wrap the message; others send it at the root.
    message = payload.get("message", payload)
    message_type = message.get("type", "")

    print(f"[VAPI webhook] type={message_type}")
    print(f"[VAPI webhook] payload={json.dumps(payload)[:2000]}")

    if message_type != "tool-calls":
        return JSONResponse(status_code=200, content={"status": "received"})

    tool_calls = _collect_tool_calls(message)
    results: list[dict[str, str]] = []

    if not tool_calls:
        print("[VAPI webhook] warning: tool-calls received but no tool call list found")
        return JSONResponse(
            status_code=200,
            content={
                "results": [
                    {
                        "toolCallId": "unknown",
                        "error": "No tool calls found in webhook payload.",
                    }
                ]
            },
        )

    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id", "")
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        print(f"[VAPI webhook] tool={tool_name} id={tool_call_id} args={arguments}")

        if not tool_call_id:
            print("[VAPI webhook] warning: missing toolCallId")
            continue

        if tool_name != "save_booking":
            results.append(_vapi_tool_response(tool_call_id, result=f"Tool {tool_name} acknowledged."))
            continue

        name = arguments.get("name", "").strip()
        vehicle = arguments.get("vehicle", "").strip()
        date = arguments.get("date", "").strip()
        time = arguments.get("time", "").strip()
        phone = arguments.get("phone", "").strip()

        if not all([name, vehicle, date, time, phone]):
            missing = [
                field
                for field, value in {
                    "name": name,
                    "vehicle": vehicle,
                    "date": date,
                    "time": time,
                    "phone": phone,
                }.items()
                if not value
            ]
            results.append(
                _vapi_tool_response(
                    tool_call_id,
                    error=f"Missing booking fields: {', '.join(missing)}",
                )
            )
            continue

        try:
            result = save_booking(
                name=name,
                vehicle=vehicle,
                date=date,
                time=time,
                phone=phone,
            )
            booking = result["booking"]
            print(f"[VAPI webhook] saved booking: {booking}")
            spoken_result = (
                f"Booking saved successfully for {booking['Name']} on {booking['Date']} at {booking['Time']}."
            )
            results.append(_vapi_tool_response(tool_call_id, result=spoken_result))
        except Exception as exc:
            print(f"[VAPI webhook] error: {exc}")
            results.append(
                _vapi_tool_response(
                    tool_call_id,
                    error=f"Failed to save booking: {exc}",
                )
            )

    if not results:
        return JSONResponse(
            status_code=200,
            content={
                "results": [
                    {
                        "toolCallId": "unknown",
                        "error": "Unable to process tool call. Missing toolCallId.",
                    }
                ]
            },
        )

    response_body = {"results": results}
    print(f"[VAPI webhook] response={response_body}")
    return JSONResponse(status_code=200, content=response_body)

if __name__ == "__main__":
    import uvicorn

    # Pass app directly (not "app:app") so uvicorn never starts a reload subprocess.
    uvicorn.run(app, host=HOST, port=PORT)
