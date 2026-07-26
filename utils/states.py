from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_session = State()
    waiting_for_source = State()
    waiting_for_destination = State()
    
    # String Session Generator States
    waiting_for_phone = State()
    waiting_for_otp = State()
    waiting_for_2fa = State()
