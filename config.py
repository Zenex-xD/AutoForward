import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot_database.db").strip()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", "")).strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "telegram_forwarder").strip()

# Convert API_ID to int if provided
if API_ID.isdigit():
    API_ID = int(API_ID)
else:
    API_ID = 0

def validate_config():
    """Validates required environment configuration."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")

    if missing:
        print(f"[FATAL ERROR] Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Please configure them in your environment or .env file.", file=sys.stderr)
        return False
    return True
