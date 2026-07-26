from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_session = State()
    waiting_for_source = State()
    waiting_for_destination = State()
