from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

from config import ADMIN_ID
from database.db import db
from keyboards.main import admin_menu_kb
from states.admin_states import AdminStates
from services.reminders import cancel_reminder_if_exists

admin_router = Router()


def is_admin(message: Message | CallbackQuery) -> bool:
    return message.from_user.id == ADMIN_ID


def parse_admin_date(text: str) -> str | None:
    """
    Принимает несколько форматов и возвращает дату в виде 'YYYY-MM-DD',
    либо None, если распарсить не удалось.
    Поддерживаемые примеры:
      - 2026-03-10
      - 10.03.2026
      - 10-03-2026
      - 10/03/2026
    """
    text = text.strip()
    formats = ["%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_admin_time(text: str) -> str | None:
    """
    Принимает 'H:M', 'HH:M', 'H:MM', 'HH:MM' и приводит к 'HH:MM'.
    """
    text = text.strip()
    # Пытаемся сначала в формате HH:MM
    for fmt in ["%H:%M"]:
        try:
            tm = datetime.strptime(text, fmt)
            return tm.strftime("%H:%M")
        except ValueError:
            continue
    # Попробуем аккуратно дополнить нули, если введено, например, '9:0'
    try:
        parts = text.split(":")
        if len(parts) != 2:
            return None
        h = int(parts[0])
        m = int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return f"{h:02d}:{m:02d}"
    except Exception:
        return None


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        "<b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(F.data == "menu:admin")
async def menu_admin(call: CallbackQuery):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.message.answer(
        "<b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb()
    )
    await call.answer()


@admin_router.callback_query(F.data == "admin:add_day")
async def admin_add_day_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.add_day)
    await call.message.answer(
        "Введите дату рабочего дня в формате <b>ДД.ММ.ГГГГ</b> (например, 15.03.2025):"
    )
    await call.answer()


@admin_router.message(AdminStates.add_day)
async def admin_add_day_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Попробуйте ещё раз, например: <code>10.03.2026</code> или <code>10-03-2026</code>."
        )
        return
    await db.add_work_day(date_str)
    await state.clear()
    await message.answer(f"Рабочий день <b>{date_str}</b> добавлен/активирован.")


@admin_router.callback_query(F.data == "admin:add_slot")
async def admin_add_slot_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.add_slot_date)
    await call.message.answer(
        "Введите дату для добавления слота в формате <b>ДД.ММ.ГГГГ</b> (например, 10.03.2026):"
    )
    await call.answer()


@admin_router.message(AdminStates.add_slot_date)
async def admin_add_slot_date(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>10.03.2026</code>, <code>10-03-2026</code>, <code>10/03/2026</code>."
        )
        return
    await state.update_data(date=date_str)
    await state.set_state(AdminStates.add_slot_time)
    await message.answer("Введите время в формате <b>ЧЧ:ММ</b> (например, 10:30):")


@admin_router.message(AdminStates.add_slot_time)
async def admin_add_slot_time(message: Message, state: FSMContext):
    raw_time = message.text.strip()
    time_str = parse_admin_time(raw_time)
    if not time_str:
        await message.answer(
            "Не удалось распознать время.\n"
            "Примеры корректного ввода: <code>9:00</code>, <code>09:00</code>, <code>14:30</code>."
        )
        return
    data = await state.get_data()
    date_str = data.get("date")
    await db.add_time_slot(date_str, time_str)
    await state.clear()
    await message.answer(
        f"Слот <b>{date_str}</b> {time_str} добавлен и доступен для записи."
    )


@admin_router.callback_query(F.data == "admin:del_slot")
async def admin_del_slot_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.del_slot_date)
    await call.message.answer(
        "Введите дату слота для удаления в формате <b>ДД.ММ.ГГГГ</b> (например, 10.03.2026):"
    )
    await call.answer()


@admin_router.message(AdminStates.del_slot_date)
async def admin_del_slot_date(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>10.03.2026</code>, <code>10-03-2026</code>, <code>10/03/2026</code>."
        )
        return
    await state.update_data(date=date_str)
    await state.set_state(AdminStates.del_slot_time)
    await message.answer("Введите время слота в формате <b>ЧЧ:ММ</b> для удаления:")


@admin_router.message(AdminStates.del_slot_time)
async def admin_del_slot_time(message: Message, state: FSMContext):
    raw_time = message.text.strip()
    time_str = parse_admin_time(raw_time)
    if not time_str:
        await message.answer(
            "Не удалось распознать время.\n"
            "Примеры корректного ввода: <code>9:00</code>, <code>09:00</code>, <code>14:30</code>."
        )
        return
    data = await state.get_data()
    date_str = data.get("date")
    deleted = await db.delete_time_slot(date_str, time_str)
    await state.clear()
    if deleted:
        await message.answer(
            f"Слот <b>{date_str}</b> {time_str} удалён (если не было активных записей)."
        )
    else:
        await message.answer("Слот не найден или не удалось удалить.")


@admin_router.callback_query(F.data == "admin:close_day")
async def admin_close_day_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.close_day)
    await call.message.answer(
        "Введите дату, которую нужно полностью закрыть (формат <b>ДД.ММ.ГГГГ</b>, например 10.03.2026):"
    )
    await call.answer()


@admin_router.message(AdminStates.close_day)
async def admin_close_day_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>10.03.2026</code>, <code>10-03-2026</code>, <code>10/03/2026</code>."
        )
        return
    await db.close_work_day(date_str)
    await state.clear()
    await message.answer(
        f"День <b>{date_str}</b> закрыт. Новые записи недоступны."
    )


@admin_router.callback_query(F.data == "admin:view_schedule")
async def admin_view_schedule_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.view_schedule)
    await call.message.answer(
        "Введите дату для просмотра расписания (формат <b>ДД.ММ.ГГГГ</b>, например 10.03.2026):"
    )
    await call.answer()


@admin_router.message(AdminStates.view_schedule)
async def admin_view_schedule_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>10.03.2026</code>, <code>10-03-2026</code>, <code>10/03/2026</code>."
        )
        return
    schedule = await db.get_schedule_for_date(date_str)
    await state.clear()

    if not schedule:
        await message.answer(f"На дату <b>{date_str}</b> нет созданных слотов.")
        return

    lines = [f"<b>Расписание на {date_str}</b>:"]
    for time_slot, name, status in schedule:
        if name:
            lines.append(f"{time_slot} — {name} ({status})")
        else:
            lines.append(f"{time_slot} — свободно")
    await message.answer("\n".join(lines))


@admin_router.callback_query(F.data == "admin:cancel_booking")
async def admin_cancel_booking_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.cancel_booking_id)
    await call.message.answer("Введите <b>ID записи</b>, которую нужно отменить:")
    await call.answer()


@admin_router.message(AdminStates.cancel_booking_id)
async def admin_cancel_booking_message(message: Message, state: FSMContext, bot: Bot):
    try:
        booking_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID записи должен быть числом.")
        return

    booking = await db.get_booking_by_id(booking_id)
    if not booking:
        await state.clear()
        await message.answer("Запись не найдена.")
        return

    (
        _bid,
        tg_id,
        name,
        phone,
        date_str,
        time_str,
        appointment_dt_str,
        reminder_scheduled,
        job_id,
    ) = booking

    await cancel_reminder_if_exists(booking_id)

    cur = await db._conn.execute(
        "SELECT slot_id FROM bookings WHERE id = ?", (booking_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    if row:
        slot_id = row[0]
        await db.mark_slot_available(slot_id)

    await db.cancel_booking(booking_id)
    await state.clear()

    await message.answer(
        f"Запись ID <b>{booking_id}</b> на <b>{date_str}</b> {time_str} отменена."
    )

    text_client = (
        "❌ <b>Ваша запись была отменена администратором.</b>\n\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n\n"
        "При необходимости вы можете записаться снова."
    )
    try:
        await bot.send_message(tg_id, text_client)
    except Exception:
        pass


def parse_admin_date(text: str) -> str | None:
    """
    Принимает несколько форматов и возвращает дату в виде 'YYYY-MM-DD',
    либо None, если распарсить не удалось.
    Поддерживаемые примеры:
      - 2026-03-10
      - 10.03.2026
      - 10-03-2026
      - 10/03/2026
    """
    text = text.strip()
    formats = ["%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_admin_time(text: str) -> str | None:
    """
    Принимает 'H:M', 'HH:M', 'H:MM', 'HH:MM' и приводит к 'HH:MM'.
    """
    text = text.strip()
    # Пытаемся сначала в формате HH:MM
    for fmt in ["%H:%M"]:
        try:
            tm = datetime.strptime(text, fmt)
            return tm.strftime("%H:%M")
        except ValueError:
            continue
    # Попробуем аккуратно дополнить нули, если введено, например, '9:0'
    try:
        parts = text.split(":")
        if len(parts) != 2:
            return None
        h = int(parts[0])
        m = int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return f"{h:02d}:{m:02d}"
    except Exception:
        return None


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        "<b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(F.data == "menu:admin")
async def menu_admin(call: CallbackQuery):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.message.answer(
        "<b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb()
    )
    await call.answer()


@admin_router.callback_query(F.data == "admin:add_day")
async def admin_add_day_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.add_day)
    await call.message.answer(
        "Введите дату рабочего дня в формате <b>ГГГГ-ММ-ДД</b> (например, 2025-03-15):"
    )
    await call.answer()


@admin_router.message(AdminStates.add_day)
async def admin_add_day_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Попробуйте ещё раз, например: <code>2026-03-10</code> или <code>10.03.2026</code>."
        )
        return
    await db.add_work_day(date_str)
    await state.clear()
    await message.answer(f"Рабочий день <b>{date_str}</b> добавлен/активирован.")


@admin_router.callback_query(F.data == "admin:add_slot")
async def admin_add_slot_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.add_slot_date)
    await call.message.answer(
        "Введите дату для добавления слота в формате <b>ГГГГ-ММ-ДД</b>:"
    )
    await call.answer()


@admin_router.message(AdminStates.add_slot_date)
async def admin_add_slot_date(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>2026-03-10</code> или <code>10.03.2026</code>."
        )
        return
    await state.update_data(date=date_str)
    await state.set_state(AdminStates.add_slot_time)
    await message.answer("Введите время в формате <b>ЧЧ:ММ</b> (например, 10:30):")


@admin_router.message(AdminStates.add_slot_time)
async def admin_add_slot_time(message: Message, state: FSMContext):
    raw_time = message.text.strip()
    time_str = parse_admin_time(raw_time)
    if not time_str:
        await message.answer(
            "Не удалось распознать время.\n"
            "Примеры корректного ввода: <code>9:00</code>, <code>09:00</code>, <code>14:30</code>."
        )
        return
    data = await state.get_data()
    date_str = data.get("date")
    await db.add_time_slot(date_str, time_str)
    await state.clear()
    await message.answer(
        f"Слот <b>{date_str}</b> {time_str} добавлен и доступен для записи."
    )


@admin_router.callback_query(F.data == "admin:del_slot")
async def admin_del_slot_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.del_slot_date)
    await call.message.answer(
        "Введите дату слота для удаления в формате <b>ГГГГ-ММ-ДД</b>:"
    )
    await call.answer()


@admin_router.message(AdminStates.del_slot_date)
async def admin_del_slot_date(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>2026-03-10</code> или <code>10.03.2026</code>."
        )
        return
    await state.update_data(date=date_str)
    await state.set_state(AdminStates.del_slot_time)
    await message.answer("Введите время слота в формате <b>ЧЧ:ММ</b> для удаления:")


@admin_router.message(AdminStates.del_slot_time)
async def admin_del_slot_time(message: Message, state: FSMContext):
    raw_time = message.text.strip()
    time_str = parse_admin_time(raw_time)
    if not time_str:
        await message.answer(
            "Не удалось распознать время.\n"
            "Примеры корректного ввода: <code>9:00</code>, <code>09:00</code>, <code>14:30</code>."
        )
        return
    data = await state.get_data()
    date_str = data.get("date")
    deleted = await db.delete_time_slot(date_str, time_str)
    await state.clear()
    if deleted:
        await message.answer(
            f"Слот <b>{date_str}</b> {time_str} удалён (если не было активных записей)."
        )
    else:
        await message.answer("Слот не найден или не удалось удалить.")


@admin_router.callback_query(F.data == "admin:close_day")
async def admin_close_day_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.close_day)
    await call.message.answer(
        "Введите дату, которую нужно полностью закрыть (формат <b>ГГГГ-ММ-ДД</b>):"
    )
    await call.answer()


@admin_router.message(AdminStates.close_day)
async def admin_close_day_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>2026-03-10</code> или <code>10.03.2026</code>."
        )
        return
    await db.close_work_day(date_str)
    await state.clear()
    await message.answer(
        f"День <b>{date_str}</b> закрыт. Новые записи недоступны."
    )


@admin_router.callback_query(F.data == "admin:view_schedule")
async def admin_view_schedule_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.view_schedule)
    await call.message.answer(
        "Введите дату для просмотра расписания (формат <b>ГГГГ-ММ-ДД</b>):"
    )
    await call.answer()


@admin_router.message(AdminStates.view_schedule)
async def admin_view_schedule_message(message: Message, state: FSMContext):
    raw = message.text.strip()
    date_str = parse_admin_date(raw)
    if not date_str:
        await message.answer(
            "Не удалось распознать дату.\n"
            "Примеры корректного ввода: <code>2026-03-10</code> или <code>10.03.2026</code>."
        )
        return
    schedule = await db.get_schedule_for_date(date_str)
    await state.clear()

    if not schedule:
        await message.answer(f"На дату <b>{date_str}</b> нет созданных слотов.")
        return

    lines = [f"<b>Расписание на {date_str}</b>:"]
    for time_slot, name, status in schedule:
        if name:
            lines.append(f"{time_slot} — {name} ({status})")
        else:
            lines.append(f"{time_slot} — свободно")
    await message.answer("\n".join(lines))


@admin_router.callback_query(F.data == "admin:cancel_booking")
async def admin_cancel_booking_call(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminStates.cancel_booking_id)
    await call.message.answer("Введите <b>ID записи</b>, которую нужно отменить:")
    await call.answer()


@admin_router.message(AdminStates.cancel_booking_id)
async def admin_cancel_booking_message(message: Message, state: FSMContext, bot: Bot):
    try:
        booking_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID записи должен быть числом.")
        return

    booking = await db.get_booking_by_id(booking_id)
    if not booking:
        await state.clear()
        await message.answer("Запись не найдена.")
        return

    (
        _bid,
        tg_id,
        name,
        phone,
        date_str,
        time_str,
        appointment_dt_str,
        reminder_scheduled,
        job_id,
    ) = booking

    await cancel_reminder_if_exists(booking_id)

    cur = await db._conn.execute(
        "SELECT slot_id FROM bookings WHERE id = ?", (booking_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    if row:
        slot_id = row[0]
        await db.mark_slot_available(slot_id)

    await db.cancel_booking(booking_id)
    await state.clear()

    await message.answer(
        f"Запись ID <b>{booking_id}</b> на <b>{date_str}</b> {time_str} отменена."
    )

    text_client = (
        "❌ <b>Ваша запись была отменена администратором.</b>\n\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n\n"
        "При необходимости вы можете записаться снова."
    )
    try:
        await bot.send_message(tg_id, text_client)
    except Exception:
        pass


