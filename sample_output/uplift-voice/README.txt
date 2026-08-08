UPLIFT VOICE TEST CLIENT
========================

Why this exists:
- Testing on platform.upliftai.org can confirm bookings in voice
  but will NOT save to your local bookings.csv.
- Uplift tools run in the browser. This client registers save_booking
  and sends confirmed bookings to POST http://localhost:8000/booking.

SETUP
-----
1. Start backend (project root):
   python app.py

2. Install and run this client:
   cd sample_output/uplift-voice
   npm install
   npm run dev

3. Open:
   http://localhost:5173

4. Paste your Uplift Assistant ID
5. Click Start Voice Call
6. Complete booking and confirm
7. Check bookings.csv or http://localhost:8000/bookings

You should see in Terminal 1:
   [Uplift/booking] saved: {...}
