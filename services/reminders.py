from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from database.db import db

scheduler = AsyncIOScheduler()


async def send_reminder(bot: Bot, user_id: int, booking_id: int):
    booking = await db.get_booking_by_id(booking_id)
    if not booking:
        return
    (
        _bid,
        tg_id,
        _name,
        _phone,
        date_str,
        time_str,
        appointment_dt_str,
        _reminder_scheduled,
        _job_id,
    ) = booking

    text = (
        f"Напоминаем, что вы записаны на наращивание ресниц завтра в {time_str}.\n"
        f"Ждём вас ️"
    )
    try:
        await bot.send_message(chat_id=tg_id, text=text)
    except Exception:
        pass


async def schedule_reminder_if_needed(
    bot: Bot,
    booking_id: int,
    tg_id: int,
    appointment_dt_str: str,
):
    appointment_dt = datetime.fromisoformat(appointment_dt_str)
    now = datetime.now()
    reminder_time = appointment_dt - timedelta(hours=24)

    if reminder_time <= now:
        await db.set_booking_reminder(booking_id, None)
        return

    job_id = f"reminder_{booking_id}"
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=reminder_time,
        args=[bot, tg_id, booking_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    await db.set_booking_reminder(booking_id, job_id)


async def cancel_reminder_if_exists(booking_id: int):
    booking = await db.get_booking_by_id(booking_id)
    if not booking:
        return
    job_id = booking[8]
    if job_id:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        await db.set_booking_reminder(booking_id, None)


async def restore_all_reminders(bot: Bot):
    rows = await db.get_future_bookings_with_reminders()
    now = datetime.now()
    for booking_id, tg_id, appointment_dt_str, job_id in rows:
        appointment_dt = datetime.fromisoformat(appointment_dt_str)
        reminder_time = appointment_dt - timedelta(hours=24)
        if reminder_time <= now:
            await db.set_booking_reminder(booking_id, None)
            continue
        new_job_id = f"reminder_{booking_id}"
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=reminder_time,
            args=[bot, tg_id, booking_id],
            id=new_job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        await db.set_booking_reminder(booking_id, new_job_id)

