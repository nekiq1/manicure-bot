from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    add_day = State()
    add_slot_date = State()
    add_slot_time = State()
    del_slot_date = State()
    del_slot_time = State()
    close_day = State()
    view_schedule = State()
    cancel_booking_id = State()

