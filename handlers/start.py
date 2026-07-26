from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.helpers import build_main_keyboard

router = Router()

START_TEXT = (
    "🤖 <b>Telegram Auto-Forwarder Bot</b>\n\n"
    "Automatically forward messages, photos, videos, media, documents, stickers, and animations "
    "from any source chat to your destination chat in real-time.\n\n"
    "Choose an option below to manage your settings:"
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handles /start command."""
    await state.clear()
    await message.answer(
        text=START_TEXT,
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "btn_cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    """Handles cancellation back to main menu."""
    await state.clear()
    await callback.message.edit_text(
        text=START_TEXT,
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Operation cancelled.")
