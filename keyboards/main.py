from datetime import date, datetime
import calendar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📅 Записаться", callback_data="menu:book"),
        ],
        [
            InlineKeyboardButton(text="❌ Моя запись", callback_data="menu:my_booking"),
        ],
        [
            InlineKeyboardButton(text="💅 Прайсы", callback_data="menu:prices"),
        ],
        [
            InlineKeyboardButton(
                text="📸 Портфолио", callback_data="menu:portfolio"
            ),
        ],
    ]
    if is_admin:
        buttons.append(
            [InlineKeyboardButton(text="🛠 Админ-панель", callback_data="menu:admin")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    kb = []

    month_name = datetime(year, month, 1).strftime("%B %Y")
    kb.append([InlineKeyboardButton(text=month_name, callback_data="cal:ignore")])

    days_row = [
        InlineKeyboardButton(text=d, callback_data="cal:ignore")
        for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ]
    kb.append(days_row)

    month_cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)

    today = date.today()

    for week in month_cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore"))
                continue
            btn_date = date(year, month, day)
            text = str(day)
            if btn_date == today:
                text = f"[{day}]"
            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"date:{btn_date.isoformat()}",
                )
            )
        kb.append(row)

    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    kb.append(
        [
            InlineKeyboardButton(
                text="⬅️", callback_data=f"cal:prev:{prev_year}:{prev_month}"
            ),
            InlineKeyboardButton(text="Отмена", callback_data="cal:cancel"),
            InlineKeyboardButton(
                text="➡️", callback_data=f"cal:next:{next_year}:{next_month}"
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=kb)


def subscription_check_kb(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📲 Подписаться", url=channel_link
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку", callback_data="sub:check"
                )
            ],
        ]
    )


def build_time_slots_kb(slots: list) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for idx, (slot_id, time_str) in enumerate(slots, start=1):
        row.append(
            InlineKeyboardButton(
                text=time_str, callback_data=f"time:{slot_id}"
            )
        )
        if idx % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(text="🔙 Другая дата", callback_data="book:change_date"),
            InlineKeyboardButton(text="Отмена", callback_data="book:cancel_flow"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="book:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="book:cancel_flow"
                )
            ],
        ]
    )


def my_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись", callback_data=f"user_cancel:{booking_id}"
                )
            ]
        ]
    )


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить рабочий день", callback_data="admin:add_day"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить слот", callback_data="admin:add_slot"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ Удалить слот", callback_data="admin:del_slot"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Закрыть день", callback_data="admin:close_day"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Расписание на дату",
                    callback_data="admin:view_schedule",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись клиента",
                    callback_data="admin:cancel_booking",
                )
            ],
        ]
    )

