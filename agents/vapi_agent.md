# VAPI WhatsApp Booking Agent — Configuration

## Assistant Overview

| Setting | Value |
|---------|-------|
| **Assistant Name** | Sparkle Car Wash WhatsApp Agent |
| **Channel** | WhatsApp (via VAPI) |
| **Purpose** | Collect car wash booking details conversationally |
| **Backend Webhook** | `{PUBLIC_URL}/vapi/webhook` |

---

## System Prompt

Copy the full system prompt from `prompts.py` → `SYSTEM_PROMPT`.

---

## Greeting (First Message)

```
Hello! Welcome to Sparkle Car Wash. I'm here to help you book an appointment. May I have your name please?
```

---

## LLM Model

| Setting | Recommended Value |
|---------|-------------------|
| Provider | OpenAI |
| Model | gpt-4o-mini (or gpt-4o) |
| Temperature | 0.7 |

---

## Conversation Flow

```
Greeting
    ↓
Ask Name
    ↓
Ask Vehicle Type
    ↓
Ask Preferred Date
    ↓
Ask Preferred Time
    ↓
Ask Phone Number
    ↓
Read all booking details back
    ↓
Ask: "Would you like to confirm your booking?"
    ↓
If Yes → call save_booking tool
    ↓
Say booking confirmed
```

---

## Tool: save_booking

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Customer full name |
| vehicle | string | Yes | Vehicle type/model |
| date | string | Yes | Preferred date |
| time | string | Yes | Preferred time |
| phone | string | Yes | Contact phone number |

**When to call:** Only after customer confirms all details.

**Server URL:** `{PUBLIC_URL}/vapi/webhook`

---

## Variables (Optional)

You can use VAPI variables to track booking state during a session:

| Variable | Description |
|----------|-------------|
| customer_name | Collected name |
| vehicle_type | Collected vehicle |
| preferred_date | Collected date |
| preferred_time | Collected time |
| phone_number | Collected phone |

---

## Instructions for VAPI Dashboard Setup

### Step 1: Start the Backend

```bash
pip install -r requirements.txt
python app.py
```

### Step 2: Expose with ngrok (for local testing)

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

### Step 3: Create the Tool in VAPI

1. Go to [VAPI Dashboard](https://dashboard.vapi.ai) → **Tools** → **Create Tool**
2. Type: **Function**
3. Name: `save_booking`
4. Description: `Save a confirmed car wash booking. Only call after customer confirms all details.`
5. Parameters (JSON Schema):

```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string", "description": "Customer full name" },
    "vehicle": { "type": "string", "description": "Vehicle type or model" },
    "date": { "type": "string", "description": "Preferred booking date" },
    "time": { "type": "string", "description": "Preferred booking time" },
    "phone": { "type": "string", "description": "Customer phone number" }
  },
  "required": ["name", "vehicle", "date", "time", "phone"]
}
```

6. Server URL: `https://YOUR-NGROK-URL/vapi/webhook`
7. Messages:
   - Request Start: "One moment, I'm saving your booking..."
   - Request Complete: "Your booking has been saved."
   - Request Failed: "Sorry, I couldn't save the booking. Please try again."

### Step 4: Create the Assistant

1. Go to **Assistants** → **Create Assistant**
2. Name: `Sparkle Car Wash WhatsApp Agent`
3. Paste the **System Prompt** from `prompts.py`
4. First Message: Use the greeting above
5. Model: OpenAI gpt-4o-mini
6. Add the `save_booking` tool
7. Server URL (assistant level): `https://YOUR-NGROK-URL/vapi/webhook`

### Step 5: Connect WhatsApp

1. In VAPI Dashboard, go to **Phone Numbers** or **Integrations**
2. Connect your WhatsApp Business number (via Meta / Twilio as supported by VAPI)
3. Assign the assistant to the WhatsApp channel
4. Test by sending a WhatsApp message to your connected number

---

## Full Assistant JSON (API Import)

Use this JSON to create the assistant via VAPI API. Replace placeholders before use.

File: `vapi_assistant.json` (same folder)

```json
{
  "name": "Sparkle Car Wash WhatsApp Agent",
  "firstMessage": "Hello! Welcome to Sparkle Car Wash. I'm here to help you book an appointment. May I have your name please?",
  "model": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "messages": [
      {
        "role": "system",
        "content": "SEE prompts.py SYSTEM_PROMPT"
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "save_booking",
          "description": "Save a confirmed car wash booking. Only call this after the customer confirms all booking details.",
          "parameters": {
            "type": "object",
            "properties": {
              "name": { "type": "string", "description": "Customer full name" },
              "vehicle": { "type": "string", "description": "Vehicle type or model" },
              "date": { "type": "string", "description": "Preferred booking date" },
              "time": { "type": "string", "description": "Preferred booking time" },
              "phone": { "type": "string", "description": "Customer phone number" }
            },
            "required": ["name", "vehicle", "date", "time", "phone"]
          }
        },
        "server": {
          "url": "https://YOUR-NGROK-URL/vapi/webhook"
        }
      }
    ]
  },
  "serverUrl": "https://YOUR-NGROK-URL/vapi/webhook"
}
```

---

## Testing Without WhatsApp

Use VAPI's **Talk to Assistant** (web chat) in the dashboard to test the conversation flow and tool calling before connecting WhatsApp.

---

## Expected Tool Call Flow

1. Customer confirms booking
2. Assistant calls `save_booking(name, vehicle, date, time, phone)`
3. VAPI POSTs to `/vapi/webhook`
4. FastAPI saves row to `bookings.csv`
5. VAPI speaks confirmation to customer
