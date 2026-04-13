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
    # Debug: show all env vars with TOKEN or BOT in the name
    print("[DEBUG] Environment variables found:")
    for key, val in os.environ.items():
        if any(word in key.upper() for word in ["TOKEN", "BOT"]):
            masked = val[:6] + "***" if len(val) > 6 else "***"
            print(f"  {key} = {masked} (length: {len(val)})")

    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        print(f"[ERROR] BOT_TOKEN is empty or invalid (length: {len(BOT_TOKEN)})", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Token OK, length: {len(BOT_TOKEN)}, starts with: {BOT_TOKEN[:8]}...")

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

    print("[INFO] Bot started polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
