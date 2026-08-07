"""Simple configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root directory
BASE_DIR = Path(__file__).resolve().parent

# CSV file for storing bookings
BOOKINGS_CSV = BASE_DIR / "bookings.csv"

# FastAPI settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Public URL for webhooks (set when using ngrok for VAPI)
PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://localhost:{PORT}")
