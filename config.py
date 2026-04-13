import os

# ОБЯЗАТЕЛЬНО заполните перед запуском
BOT_TOKEN = os.getenv("BOT_TOKEN", "8703924448:AAFKBxj4czXmcBjVYJ2EXu1pARPL9yT6lgc")

# ID администратора (число, а не строка)
ADMIN_ID = int(os.getenv("ADMIN_ID", "7642780807"))

# Канал для проверки подписки и расписания
# Пример: CHANNEL_ID = -1001234567890
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003751381022"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/manikqure")

# Канал для расписания (можно использовать тот же, что и для подписки)
SCHEDULE_CHANNEL_ID = int(os.getenv("SCHEDULE_CHANNEL_ID", CHANNEL_ID))

# Путь к БД
DB_PATH = os.getenv("DB_PATH", "database.sqlite3")

