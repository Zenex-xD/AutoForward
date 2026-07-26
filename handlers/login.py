from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import BotStates
from utils.helpers import build_cancel_keyboard, build_main_keyboard
from services.pyrogram_manager import pyrogram_manager
from database.db import db
from utils.logger import logger

router = Router()

@router.callback_query(F.data == "btn_login")
async def cb_login_start(callback: CallbackQuery, state: FSMContext):
    """Prompt user to paste Pyrogram String Session."""
    await state.set_state(BotStates.waiting_for_session)
    await callback.message.edit_text(
        text=(
            "🔐 <b>Login Pyrogram Account</b>\n\n"
            "Please paste your <b>Pyrogram String Session</b> below.\n\n"
            "<i>Note: Your session string will be stored securely in your private SQLite configuration database.</i>"
        ),
        reply_markup=build_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BotStates.waiting_for_session)
async def process_session_string(message: Message, state: FSMContext):
    """Validates and saves Pyrogram String Session."""
    session_str = message.text.strip() if message.text else ""

    if not session_str or len(session_str) < 20:
        await message.answer(
            text="❌ Invalid input. Please paste a valid Pyrogram String Session.",
            reply_markup=build_cancel_keyboard()
        )
        return

    status_msg = await message.answer("🔄 Validating String Session, please wait...")

    try:
        acc_info = await pyrogram_manager.validate_session(session_str)
        user_id = message.from_user.id

        await db.save_session(
            user_id=user_id,
            session_string=session_str,
            account_name=acc_info["account_name"],
            phone_number=acc_info["phone_number"]
        )

        await state.clear()
        await status_msg.edit_text(
            text=(
                "✅ <b>Login Successful!</b>\n\n"
                f"👤 <b>Account Name:</b> {acc_info['account_name']}\n"
                f"📞 <b>Phone / ID:</b> {acc_info['phone_number']}\n\n"
                "Your account session is saved successfully."
            ),
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Session validation failed for user {message.from_user.id}: {e}")
        await status_msg.edit_text(
            text=(
                "❌ <b>Login Failed!</b>\n\n"
                f"Error: {str(e)}\n\n"
                "Please make sure your string session is valid and try again."
            ),
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
