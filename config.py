import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", " ")

ADMIN_ID = int(os.getenv("ADMIN_ID", "7642780807"))

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003751381022"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/manikqure")

SCHEDULE_CHANNEL_ID = int(os.getenv("SCHEDULE_CHANNEL_ID", "-1003751381022"))

DB_PATH = os.getenv("DB_PATH", "database.sqlite3")
