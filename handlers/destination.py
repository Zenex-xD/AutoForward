from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import BotStates
from utils.helpers import build_cancel_keyboard, build_main_keyboard, clean_chat_input
from database.db import db

router = Router()

@router.callback_query(F.data == "btn_set_destination")
async def cb_set_dest_start(callback: CallbackQuery, state: FSMContext):
    """Prompt user to set destination chat."""
    await state.set_state(BotStates.waiting_for_destination)
    await callback.message.edit_text(
        text=(
            "📤 <b>Set Destination Chat</b>\n\n"
            "Please send the destination chat details where messages will be forwarded to.\n\n"
            "Supported formats:\n"
            "• <b>Chat ID:</b> <code>-1009876543210</code>\n"
            "• <b>Username:</b> <code>@destination_chat</code>\n"
            "• <b>Invite Link:</b> <code>https://t.me/+AbCdEfGhIjKl</code>"
        ),
        reply_markup=build_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BotStates.waiting_for_destination)
async def process_destination_chat(message: Message, state: FSMContext):
    """Saves destination chat input."""
    raw_input = message.text.strip() if message.text else ""

    if not raw_input:
        await message.answer("❌ Invalid input. Please send a Chat ID, @username, or Invite Link.")
        return

    cleaned_dest = clean_chat_input(raw_input)
    user_id = message.from_user.id

    await db.save_destination(user_id=user_id, destination_chat=cleaned_dest)
    await state.clear()

    await message.answer(
        text=(
            "✅ <b>Destination Chat Configured!</b>\n\n"
            f"📤 <b>Destination Chat:</b> <code>{cleaned_dest}</code>"
        ),
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )
