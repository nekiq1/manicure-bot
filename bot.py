import asyncio
import dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # <-- добавили

from config import BOT_TOKEN
from database.db import db
from handlers.user import user_router
from handlers.admin import admin_router
from services.reminders import scheduler, restore_all_reminders


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),  # <-- вместо parse_mode=...
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