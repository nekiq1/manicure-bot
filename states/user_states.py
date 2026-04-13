from aiogram.fsm.state import StatesGroup, State


class BookingStates(StatesGroup):
    selecting_date = State()
    selecting_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

