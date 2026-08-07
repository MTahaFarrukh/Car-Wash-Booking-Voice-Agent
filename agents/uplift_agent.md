# Uplift AI Voice Booking Agent — Configuration

## Assistant Overview

| Setting | Value |
|---------|-------|
| **Assistant Name** | Sparkle Car Wash Voice Agent |
| **Channel** | Voice (Uplift AI Realtime Assistants) |
| **Purpose** | Collect car wash booking details via phone/voice conversation |
| **Backend API** | `{PUBLIC_URL}/booking` |

---

## System Prompt (Instructions)

Copy the full system prompt from `prompts.py` → `SYSTEM_PROMPT`.

---

## Greeting

```
Hello! Thank you for calling Sparkle Car Wash. I'd be happy to help you book a car wash. Can I start with your name?
```

---

## LLM / Voice Settings

| Component | Setting |
|-----------|---------|
| LLM Provider | groq |
| LLM Model | openai/gpt-oss-120b |
| STT Provider | groq |
| STT Model | whisper-large-v3 |
| TTS Provider | upliftai |
| Voice ID | v_meklc281 |
| Language | en |

---

## Conversation Flow

Same as VAPI agent — see `prompts.py` → `CONVERSATION_FLOW`.

---

## Tool: save_booking

Uplift AI tools run on the **client device** via RPC. The tool schema is defined in the assistant config; the handler calls our FastAPI backend.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Customer full name |
| vehicle | string | Yes | Vehicle type/model |
| date | string | Yes | Preferred date |
| time | string | Yes | Preferred time |
| phone | string | Yes | Contact phone number |

**When to call:** Only after customer verbally confirms all details.

---

## Variables (Session State)

| Variable | Description |
|----------|-------------|
| customer_name | Collected name |
| vehicle_type | Collected vehicle |
| preferred_date | Collected date |
| preferred_time | Collected time |
| phone_number | Collected phone |

---

## Full Assistant JSON (Create via API)

File: `uplift_assistant.json` (same folder)

```json
{
  "name": "Sparkle Car Wash Voice Agent",
  "description": "Voice booking agent for car wash appointments",
  "public": true,
  "config": {
    "session": {
      "ttl": 3600,
      "roomPrefix": "carwash"
    },
    "agent": {
      "instructions": "SEE prompts.py SYSTEM_PROMPT",
      "initialGreeting": true,
      "greetingInstructions": "Greet the caller warmly and ask for their name to start the booking.",
      "tools": [
        {
          "name": "save_booking",
          "description": "Save a confirmed car wash booking to the system. Only call after the customer confirms all details.",
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
          },
          "timeout": 10
        }
      ]
    },
    "stt": {
      "default": {
        "provider": "groq",
        "model": "whisper-large-v3",
        "language": "en"
      }
    },
    "tts": {
      "default": {
        "provider": "upliftai",
        "voiceId": "v_meklc281",
        "outputFormat": "MP3_22050_32"
      }
    },
    "llm": {
      "default": {
        "provider": "groq",
        "model": "openai/gpt-oss-120b"
      }
    }
  }
}
```

---

## Setup Instructions

### Step 1: Start the Backend

```bash
pip install -r requirements.txt
python app.py
```

### Step 2: Create Assistant via Uplift API

```bash
curl -X POST https://api.upliftai.org/v1/realtime-assistants \
  -H "Authorization: Bearer YOUR_UPLIFT_API_KEY" \
  -H "Content-Type: application/json" \
  -d @agents/uplift_assistant.json
```

Save the returned `id` as `UPLIFT_ASSISTANT_ID` in your `.env`.

### Step 3: Test with Voice Client

Open `sample_output/voice_client.html` in a browser:

1. Enter your Uplift Assistant ID
2. Enter backend URL (`http://localhost:8000`)
3. Click **Start Voice Call**
4. Speak through your microphone to complete a booking

The voice client registers the `save_booking` tool handler that POSTs to `/booking`.

### Step 4: Phone Integration (Optional)

Configure a phone number in the Uplift AI dashboard and assign this assistant for inbound voice calls.

---

## Tool Handler (Client-Side)

Uplift requires the tool handler in the browser/app. See `sample_output/voice_client.html`:

```javascript
{
  name: 'save_booking',
  description: 'Save a confirmed car wash booking.',
  parameters: { /* same schema as above */ },
  timeout: 10,
  handler: async (data) => {
    const args = JSON.parse(data.payload).arguments.raw_arguments;
    const response = await fetch(`${API_URL}/booking`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: args.name,
        vehicle: args.vehicle,
        date: args.date,
        time: args.time,
        phone: args.phone
      })
    });
    const result = await response.json();
    return JSON.stringify({
      result: result,
      presentationInstructions: 'Your booking is confirmed! We look forward to seeing you.'
    });
  }
}
```

---

## Testing Flow

1. Start FastAPI backend
2. Open voice client HTML
3. Start voice session
4. Say: "I'd like to book a car wash"
5. Provide: name, vehicle, date, time, phone when asked
6. Confirm when asked
7. Check `GET http://localhost:8000/bookings` or `bookings.csv`
