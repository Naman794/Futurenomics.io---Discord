import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _csv_set(value: str) -> Set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "e67731cbb43cf4c97")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "web3_teacher_bot.db"))
NEWSLETTER_HOUR = int(os.getenv("NEWSLETTER_HOUR", "9"))
NEWSLETTER_MINUTE = int(os.getenv("NEWSLETTER_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
ADMIN_USER_IDS = _csv_set(os.getenv("ADMIN_USER_IDS", "506472665519751179, 485489178583498764"))

LOG_PATH = str(BASE_DIR / "logs" / "bot.log")
DISCLAIMER = "Educational information only. Not financial advice."

COGS = [
    "cogs.general_commands",
    "cogs.education_commands",
    "cogs.market_commands",
    "cogs.chart_commands",
    "cogs.news_commands",
    "cogs.newsletter_commands",
    "cogs.alert_commands",
    "cogs.market_pulse_commands",
    "cogs.admin_commands",
]
