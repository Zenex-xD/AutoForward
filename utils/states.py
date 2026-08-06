from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_session = State()
    waiting_for_source = State()
    waiting_for_destination = State()

    # Route specific states
    waiting_for_route_source = State()
    waiting_for_route_destination = State()
    waiting_for_route_name = State()

    # String Session Generator States
    waiting_for_phone = State()
    waiting_for_otp = State()
    waiting_for_2fa = State()
