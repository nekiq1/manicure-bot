from datetime import date, datetime

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, CHANNEL_ID, CHANNEL_LINK, SCHEDULE_CHANNEL_ID
from database.db import db
from keyboards.main import (
    main_menu_kb,
    build_calendar,
    subscription_check_kb,
    build_time_slots_kb,
    confirm_booking_kb,
    my_booking_kb,
)
from states.user_states import BookingStates
from services.reminders import schedule_reminder_if_needed, cancel_reminder_if_exists

user_router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        status = member.status
        return status in ("member", "administrator", "creator")
    except Exception:
        return False


async def ensure_subscription(call_or_msg, bot: Bot) -> bool:
    user_id = call_or_msg.from_user.id
    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        text = (
            "Для записи необходимо подписаться на канал.\n\n"
            "После подписки нажмите кнопку <b>«Проверить подписку»</b>."
        )
        if isinstance(call_or_msg, CallbackQuery):
            await call_or_msg.message.answer(
                text, reply_markup=subscription_check_kb(CHANNEL_LINK)
            )
        else:
            await call_or_msg.answer(
                text, reply_markup=subscription_check_kb(CHANNEL_LINK)
            )
        return False
    return True


@user_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    is_admin = message.from_user.id == ADMIN_ID
    await db.connect()
    await db.get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = (
        "✨ <b>Добро пожаловать к мастеру по маникюру!</b>\n\n"
        "Через этого бота вы можете записаться на удобное время, "
        "посмотреть свою запись, узнать прайс и посмотреть портфолио."
    )
    await message.answer(text, reply_markup=main_menu_kb(is_admin=is_admin))


@user_router.callback_query(F.data == "sub:check")
async def callback_check_subscription(call: CallbackQuery, bot: Bot):
    subscribed = await check_subscription(bot, call.from_user.id)
    if not subscribed:
        await call.answer(
            "Подписка не найдена. Проверьте, что вы подписаны на канал.",
            show_alert=True,
        )
    else:
        await call.answer("Подписка подтверждена!", show_alert=True)
        await call.message.answer(
            "Спасибо за подписку! Теперь вам доступна запись.",
            reply_markup=main_menu_kb(is_admin=(call.from_user.id == ADMIN_ID)),
        )


@user_router.callback_query(F.data == "menu:book")
async def menu_book(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await ensure_subscription(call, bot):
        await call.answer()
        return

    today = date.today()
    await state.set_state(BookingStates.selecting_date)
    await call.message.answer(
        "Выберите, пожалуйста, <b>дату для записи</b>:",
        reply_markup=build_calendar(today.year, today.month),
    )
    await call.answer()


@user_router.callback_query(F.data == "menu:my_booking")
async def menu_my_booking(call: CallbackQuery):
    await db.connect()
    booking = await db.get_active_booking_by_tg(call.from_user.id)
    if not booking:
        await call.message.answer("У вас нет активной записи.")
        await call.answer()
        return

    booking_id, date_str, time_str, appointment_dt_str = booking
    text = (
        "<b>Ваша текущая запись:</b>\n\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"⏰ Время: <b>{time_str}</b>\n\n"
        "Вы можете отменить запись, если это необходимо."
    )
    await call.message.answer(text, reply_markup=my_booking_kb(booking_id))
    await call.answer()


@user_router.callback_query(F.data == "menu:prices")
async def menu_prices(call: CallbackQuery):
    text = "<b>Прайс-лист</b>\n\nФренч — <b>1000₽</b>\nКвадрат — <b>500₽</b>"
    await call.message.answer(text)
    await call.answer()


@user_router.callback_query(F.data == "menu:portfolio")
async def menu_portfolio(call: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Смотреть портфолио",
                    url="https://ru.pinterest.com/pin/in-2025--24066179252596108/",
                )
            ]
        ]
    )
    await call.message.answer(
        "<b>Портфолио работ</b>\n\nНажмите кнопку ниже, чтобы посмотреть примеры.",
        reply_markup=kb,
    )
    await call.answer()


@user_router.callback_query(BookingStates.selecting_date, F.data.startswith("cal:"))
async def calendar_nav(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    action = parts[1]
    if action == "ignore":
        await call.answer()
        return
    if action == "cancel":
        await state.clear()
        await call.message.edit_text("Запись отменена.")
        await call.answer()
        return
    if action in ("prev", "next"):
        year = int(parts[2])
        month = int(parts[3])
        await call.message.edit_reply_markup(reply_markup=build_calendar(year, month))
        await call.answer()


@user_router.callback_query(BookingStates.selecting_date, F.data.startswith("date:"))
async def calendar_date_selected(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split(":", maxsplit=1)[1]
    await state.update_data(selected_date=date_str)

    slots = await db.get_available_slots_for_date(date_str)
    if not slots:
        await call.message.answer(
            f"На выбранную дату <b>{date_str}</b> нет доступных слотов.\n"
            "Попробуйте выбрать другую дату."
        )
        await call.answer()
        return

    await state.set_state(BookingStates.selecting_time)
    await call.message.answer(
        f"Вы выбрали дату: <b>{date_str}</b>\n\nВыберите, пожалуйста, <b>время</b>:",
        reply_markup=build_time_slots_kb(slots),
    )
    await call.answer()


@user_router.callback_query(BookingStates.selecting_time, F.data == "book:change_date")
async def change_date(call: CallbackQuery, state: FSMContext):
    today = date.today()
    await state.set_state(BookingStates.selecting_date)
    await call.message.answer(
        "Выберите другую дату:",
        reply_markup=build_calendar(today.year, today.month),
    )
    await call.answer()


@user_router.callback_query(BookingStates.selecting_time, F.data == "book:cancel_flow")
@user_router.callback_query(BookingStates.confirming, F.data == "book:cancel_flow")
async def cancel_flow(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Процесс записи отменён.")
    await call.answer()


@user_router.callback_query(BookingStates.selecting_time, F.data.startswith("time:"))
async def time_selected(call: CallbackQuery, state: FSMContext):
    slot_id = int(call.data.split(":")[1])

    slot_info = await db.get_slot_info(slot_id)
    if not slot_info:
        await call.message.answer("Этот слот больше недоступен. Попробуйте снова.")
        await call.answer()
        return

    _sid, date_str, time_str = slot_info
    await state.update_data(slot_id=slot_id, date=date_str, time=time_str)

    await state.set_state(BookingStates.entering_name)
    await call.message.answer(
        f"Вы выбрали:\n\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"⏰ Время: <b>{time_str}</b>\n\n"
        "Введите, пожалуйста, ваше <b>имя</b>:"
    )
    await call.answer()


@user_router.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer("Введите, пожалуйста, ваш <b>номер телефона</b>:")


@user_router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    data = await state.get_data()

    date_str = data.get("date")
    time_str = data.get("time")
    name = data.get("name")

    text = (
        "<b>Проверьте данные перед подтверждением:</b>\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n\n"
        "Нажмите <b>«Подтвердить»</b>, чтобы сохранить запись."
    )

    await state.set_state(BookingStates.confirming)
    await message.answer(text, reply_markup=confirm_booking_kb())


@user_router.callback_query(BookingStates.confirming, F.data == "book:confirm")
async def confirm_booking(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    slot_id = data.get("slot_id")
    date_str = data.get("date")
    time_str = data.get("time")
    name = data.get("name")
    phone = data.get("phone")

    if await db.has_active_booking(call.from_user.id):
        await call.message.answer(
            "У вас уже есть активная запись. "
            "Вы можете отменить её в разделе <b>«Моя запись»</b>."
        )
        await state.clear()
        await call.answer()
        return

    slots = await db.get_available_slots_for_date(date_str)
    if not any(s[0] == slot_id for s in slots):
        await call.message.answer(
            "К сожалению, выбранный слот уже недоступен. Попробуйте выбрать другое время."
        )
        await state.clear()
        await call.answer()
        return

    await db.mark_slot_unavailable(slot_id)

    appointment_dt = datetime.fromisoformat(f"{date_str} {time_str}")
    booking_id = await db.create_booking(
        tg_id=call.from_user.id,
        name=name,
        phone=phone,
        slot_id=slot_id,
        appointment_dt=appointment_dt,
    )

    await schedule_reminder_if_needed(
        bot, booking_id, call.from_user.id, appointment_dt.isoformat()
    )

    await state.clear()

    text_user = (
        "✅ <b>Вы успешно записаны!</b>\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n\n"
        "До встречи!"
    )
    await call.message.answer(text_user)

    text_admin = (
        "📥 <b>Новая запись</b>\n\n"
        f"ID клиента: <code>{call.from_user.id}</code>\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n"
        f"ID записи: <b>{booking_id}</b>"
    )
    try:
        await bot.send_message(ADMIN_ID, text_admin)
    except Exception:
        pass

    schedule = await db.get_schedule_for_date(date_str)
    lines = [f"<b>Расписание на {date_str}</b>:"]
    for time_slot, client_name, status in schedule:
        if client_name:
            lines.append(f"{time_slot} — {client_name}")
        else:
            lines.append(f"{time_slot} — свободно")
    text_channel = "\n".join(lines)
    try:
        await bot.send_message(SCHEDULE_CHANNEL_ID, text_channel)
    except Exception:
        pass

    await call.answer()


@user_router.callback_query(F.data.startswith("user_cancel:"))
async def user_cancel(call: CallbackQuery, bot: Bot):
    booking_id = int(call.data.split(":")[1])
    booking = await db.get_booking_by_id(booking_id)
    if not booking:
        await call.message.answer("Запись не найдена.")
        await call.answer()
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

    if tg_id != call.from_user.id:
        await call.answer("Вы не можете отменить чужую запись.", show_alert=True)
        return

    await cancel_reminder_if_exists(booking_id)

    slot_query = "SELECT slot_id FROM bookings WHERE id = ?"
    cur = await db._conn.execute(slot_query, (booking_id,))
    row = await cur.fetchone()
    await cur.close()
    if row:
        slot_id = row[0]
        await db.mark_slot_available(slot_id)

    await db.cancel_booking(booking_id)

    await call.message.answer(
        f"❌ Ваша запись на <b>{date_str}</b> в <b>{time_str}</b> отменена."
    )

    text_admin = (
        "❌ <b>Запись отменена клиентом</b>\n\n"
        f"ID клиента: <code>{tg_id}</code>\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"Дата: <b>{date_str}</b>\n"
        f"Время: <b>{time_str}</b>\n"
        f"ID записи: <b>{booking_id}</b>"
    )
    try:
        await bot.send_message(ADMIN_ID, text_admin)
    except Exception:
        pass

    await call.answer()

