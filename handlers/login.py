from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import BotStates
from utils.helpers import build_cancel_keyboard, build_account_keyboard, safe_edit_menu
from services.pyrogram_manager import pyrogram_manager
from database.db import db
from utils.logger import logger

router = Router()

@router.callback_query(F.data == "btn_login")
async def cb_login_start(callback: CallbackQuery, state: FSMContext):
    """Prompt user to paste Pyrogram String Session."""
    await state.set_state(BotStates.waiting_for_session)
    prompt_text = (
        "🔐 <b><u>LOGIN PYROGRAM ACCOUNT</u></b>\n\n"
        "Please paste your <b>Pyrogram String Session</b> in the chat below.\n\n"
        "❖ <i>Your session string is stored encrypted & locally in SQLite database.</i>"
    )
    await safe_edit_menu(callback.message, prompt_text, build_cancel_keyboard())
    await callback.answer()

@router.message(BotStates.waiting_for_session)
async def process_session_string(message: Message, state: FSMContext):
    """Validates and saves Pyrogram String Session."""
    session_str = message.text.strip() if message.text else ""

    if not session_str or len(session_str) < 20:
        await message.answer(
            text="❌ <b>Invalid Input!</b> Please paste a valid Pyrogram String Session string.",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer("🔄 <b>Validating String Session...</b>", parse_mode="HTML")

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
                "✅ <b><u>LOGIN SUCCESSFUL!</u></b>\n\n"
                f"👤 <b>Account:</b> <code>{acc_info['account_name']}</code>\n"
                f"📞 <b>Phone / ID:</b> <code>{acc_info['phone_number']}</code>\n\n"
                "❖ Your account session is active and saved securely."
            ),
            reply_markup=build_account_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Session validation failed for user {message.from_user.id}: {e}")
        await status_msg.edit_text(
            text=(
                "❌ <b><u>LOGIN FAILED!</u></b>\n\n"
                f"<b>Error:</b> <code>{str(e)}</code>\n\n"
                "Please verify your Pyrogram String Session and try again."
            ),
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )

