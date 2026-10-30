import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip() or f"sqlite+aiosqlite:///{BASE_DIR / 'dragonlife.db'}"
    # Render / Heroku give "postgres://..." — SQLAlchemy async needs the asyncpg driver
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = _db_url()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-please")

    # First admin account (created on first start if no admin exists)
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = _int("PORT", _int("WEB_PORT", 8000))  # Render sets PORT

    # Webhook mode: set on hosts that sleep (Render free). Render fills RENDER_EXTERNAL_URL itself.
    # Empty → the bot uses long polling.
    WEBHOOK_BASE: str = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")

    # Google Sheets backup (optional)
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
    GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")  # whole JSON key as text
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
    SHEETS_SYNC_INTERVAL: int = _int("SHEETS_SYNC_INTERVAL", 60)

    # Contacts shown in the bot
    CONTACT_USERNAME: str = os.getenv("CONTACT_USERNAME", "@dragonlife02")
    CONTACT_PHONE: str = os.getenv("CONTACT_PHONE", "+998 97 661 16 66")


settings = Settings()

# Warehouse in China — must stay exactly as given (clients copy it into Chinese shops)
WAREHOUSE_PHONE = "136 9058 9717"
WAREHOUSE_ADDRESS_CN = "广东省佛山市南海区里水镇胜利工业区29号 龙命物流"
WAREHOUSE_ZIP = "528244"

LINK_TRACK_HELP = "https://telegra.ph/Pinduoduo-taobaolardan-track-kod-topish-07-01"
LINK_VOLUME_HELP = "https://telegra.ph/Gabaritlik-vesni-olchas-usuli-07-01"
LINK_FORBIDDEN = "https://telegra.ph/Mumkin-bolmagan-Zapret-yuklar-07-01"
