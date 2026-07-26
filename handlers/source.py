from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import BotStates
from utils.helpers import build_cancel_keyboard, build_main_keyboard, clean_chat_input
from database.db import db

router = Router()

@router.callback_query(F.data == "btn_set_source")
async def cb_set_source_start(callback: CallbackQuery, state: FSMContext):
    """Prompt user to set source chat."""
    await state.set_state(BotStates.waiting_for_source)
    await callback.message.edit_text(
        text=(
            "📥 <b>Set Source Chat</b>\n\n"
            "Please send the source chat details where messages will be forwarded from.\n\n"
            "Supported formats:\n"
            "• <b>Chat ID:</b> <code>-1001234567890</code>\n"
            "• <b>Username:</b> <code>@source_chat</code>\n"
            "• <b>Invite Link:</b> <code>https://t.me/+AbCdEfGhIjKl</code>"
        ),
        reply_markup=build_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BotStates.waiting_for_source)
async def process_source_chat(message: Message, state: FSMContext):
    """Saves source chat input."""
    raw_input = message.text.strip() if message.text else ""

    if not raw_input:
        await message.answer("❌ Invalid input. Please send a Chat ID, @username, or Invite Link.")
        return

    cleaned_source = clean_chat_input(raw_input)
    user_id = message.from_user.id

    await db.save_source(user_id=user_id, source_chat=cleaned_source)
    await state.clear()

    await message.answer(
        text=(
            "✅ <b>Source Chat Configured!</b>\n\n"
            f"📥 <b>Source Chat:</b> <code>{cleaned_source}</code>"
        ),
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )
