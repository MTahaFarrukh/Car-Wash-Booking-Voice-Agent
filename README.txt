================================================================================
SPARKLE CAR WASH - AI BOOKING AGENTS
Minimum Viable Submission for AI Season Assignment
================================================================================

PROJECT OVERVIEW
----------------
This project implements TWO AI-powered booking agents for a Car Wash Service:

1. WhatsApp Booking Agent (VAPI)
2. Voice Calling Booking Agent (Uplift AI Voice)

Both agents collect booking information conversationally and save bookings
to a CSV file via a simple FastAPI backend.

Technologies: Python, FastAPI, CSV storage, VAPI, Uplift AI Voice


TECHNOLOGIES USED
-----------------
- Python 3.10+
- FastAPI (REST API backend)
- Uvicorn (ASGI server)
- CSV file storage (bookings.csv)
- VAPI (WhatsApp conversational agent + tool calling)
- Uplift AI Voice (realtime voice assistant)
- ngrok (optional, for exposing local webhook to VAPI)


FOLDER STRUCTURE
----------------
carwash-booking/
|
|-- app.py                  # FastAPI app (endpoints + VAPI webhook)
|-- booking.py              # save_booking() and get_all_bookings()
|-- prompts.py              # System prompts and greetings
|-- config.py               # Environment configuration
|-- bookings.csv            # Saved bookings (CSV)
|-- requirements.txt        # Python dependencies
|-- README.txt              # This file
|-- .env.example            # Environment variable template
|
|-- agents/
|   |-- vapi_agent.md       # VAPI WhatsApp agent setup guide
|   |-- vapi_assistant.json # VAPI assistant JSON config
|   |-- uplift_agent.md     # Uplift voice agent setup guide
|   |-- uplift_assistant.json # Uplift assistant JSON config
|
|-- sample_output/
    |-- voice_client.html           # Minimal Uplift voice test page
    |-- generate_sample_bookings.py # Script to create sample bookings
    |-- sample_api_response.txt    # Example API/CSV output


HOW TO RUN
----------
1. Create virtual environment (recommended):
   python -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (Mac/Linux)

2. Install dependencies:
   pip install -r requirements.txt

3. Copy environment file:
   copy .env.example .env       (Windows)
   cp .env.example .env         (Mac/Linux)

4. Start the backend:
   python app.py

   Server runs at: http://localhost:8000

5. Test API manually:
   POST http://localhost:8000/booking
   Body (JSON):
   {
     "name": "Ali",
     "vehicle": "Civic",
     "date": "12 Aug",
     "time": "4 PM",
     "phone": "03001234567"
   }

   GET http://localhost:8000/bookings

6. Generate sample bookings:
   python sample_output/generate_sample_bookings.py
   (Make sure the server is running first)


HOW VAPI WORKS (WhatsApp Agent)
-------------------------------
1. Customer sends a WhatsApp message to your VAPI-connected number.
2. VAPI assistant uses the system prompt from prompts.py to guide conversation.
3. Assistant asks ONE question at a time: name, vehicle, date, time, phone.
4. After collecting all fields, assistant reads back the summary.
5. Customer confirms → assistant calls save_booking tool.
6. VAPI sends a POST request to /vapi/webhook on your FastAPI server.
7. Backend saves the booking to bookings.csv.
8. VAPI tells the customer the booking is confirmed.

Setup: See agents/vapi_agent.md for full dashboard and JSON configuration.


HOW UPLIFT AI WORKS (Voice Agent)
---------------------------------
1. Customer starts a voice session (phone call or web voice client).
2. Uplift AI agent greets the caller and follows the same booking flow.
3. Speech is converted to text (STT), processed by LLM, replied via TTS.
4. When customer confirms, agent calls save_booking tool via RPC.
5. Client-side tool handler POSTs to /booking on FastAPI backend.
6. Booking is saved to bookings.csv.
7. Agent confirms booking verbally.

Setup: See agents/uplift_agent.md for API config and voice client instructions.


HOW BOOKINGS ARE SAVED
----------------------
Function: save_booking(name, vehicle, date, time, phone)
Location: booking.py

Each confirmed booking is appended as one row in bookings.csv:

Name,Vehicle,Date,Time,Phone
Ali,Civic,12 Aug,4 PM,03001234567

Endpoints:
- POST /booking     → save a booking directly
- GET /bookings     → list all bookings
- POST /vapi/webhook → VAPI tool-call handler


FUTURE IMPROVEMENTS
-------------------
- PostgreSQL database instead of CSV
- Admin dashboard to view bookings
- SMS/email confirmation notifications
- Authentication and user accounts
- Payment integration
- Docker deployment
- Booking availability checking
- Calendar integration


================================================================================
ASSIGNMENT VERIFICATION
================================================================================

Requirement                                          Status
---------------------------------------------------  ------
WhatsApp booking agent using VAPI                    ✅
Collect booking details (5 fields)                   ✅
Voice booking agent using Uplift AI Voice            ✅
Voice conversation flow                              ✅
Save bookings to CSV                                 ✅
Source code (Python/FastAPI)                         ✅
Agent configurations (agents/)                       ✅
Prompts (prompts.py)                                 ✅
README documentation                                 ✅
Tool calling (save_booking)                          ✅
POST /booking and GET /bookings endpoints            ✅
Conversation flow (greeting → confirm → save)        ✅


================================================================================
TESTING GUIDE
================================================================================

A. TEST BACKEND LOCALLY
-----------------------
1. python app.py
2. Open http://localhost:8000 in browser (health check)
3. Use curl or Postman:

   curl -X POST http://localhost:8000/booking ^
     -H "Content-Type: application/json" ^
     -d "{\"name\":\"Ali\",\"vehicle\":\"Civic\",\"date\":\"12 Aug\",\"time\":\"4 PM\",\"phone\":\"03001234567\"}"

   curl http://localhost:8000/bookings

4. Check bookings.csv for the new row.


B. CONFIGURE & TEST VAPI (WhatsApp)
-----------------------------------
1. Sign up at https://dashboard.vapi.ai
2. Start backend: python app.py
3. Expose webhook: ngrok http 8000
4. Create save_booking tool (see agents/vapi_agent.md)
5. Create assistant with system prompt from prompts.py
6. Set server URL to: https://YOUR-NGROK-URL/vapi/webhook
7. Test with "Talk to Assistant" in VAPI dashboard first
8. Connect WhatsApp number and test end-to-end
9. Verify booking appears in GET /bookings


C. CONFIGURE & TEST UPLIFT AI VOICE
-----------------------------------
1. Sign up at https://platform.upliftai.org
2. Create assistant:
   curl -X POST https://api.upliftai.org/v1/realtime-assistants ^
     -H "Authorization: Bearer YOUR_API_KEY" ^
     -H "Content-Type: application/json" ^
     -d @agents/uplift_assistant.json
3. Set assistant to public in dashboard
4. Start backend: python app.py
5. Open sample_output/voice_client.html in browser
6. Enter Assistant ID and click Start Voice Assistant
7. Speak through microphone to complete a booking
8. For full tool support, use React SDK pattern in agents/uplift_agent.md
9. Verify booking in bookings.csv


D. GENERATE SAMPLE BOOKINGS
---------------------------
1. Ensure server is running
2. python sample_output/generate_sample_bookings.py
3. View results in sample_output/sample_api_response.txt format

================================================================================
