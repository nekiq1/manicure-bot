import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.db import db
from handlers.user import user_router
from handlers.admin import admin_router
from services.reminders import scheduler, restore_all_reminders


async def main():
    print("[DEBUG] All env var keys:", sorted(os.environ.keys()))

    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        print(f"[ERROR] BOT_TOKEN empty! Check Railway Variables.", file=sys.stderr)
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    await db.connect()
    dp.include_router(user_router)
    dp.include_router(admin_router)
    scheduler.start()
    await restore_all_reminders(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
