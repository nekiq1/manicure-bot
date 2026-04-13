import os

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")).strip().strip('"').strip("'")

ADMIN_ID = int(os.getenv("ADMIN_ID", "7642780807"))

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003751381022"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/manikqure")

SCHEDULE_CHANNEL_ID = int(os.getenv("SCHEDULE_CHANNEL_ID", str(CHANNEL_ID)))

DB_PATH = os.getenv("DB_PATH", "database.sqlite3")
