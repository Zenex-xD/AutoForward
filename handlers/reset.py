from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_main_keyboard

router = Router()

@router.callback_query(F.data == "btn_reset")
async def cb_reset_config(callback: CallbackQuery):
    """Resets user configuration and stops active clients."""
    user_id = callback.from_user.id

    # Stop active Pyrogram client if running
    await pyrogram_manager.stop_forwarder(user_id)

    # Delete configuration from database
    await db.reset_user_config(user_id)

    await callback.message.edit_text(
        text=(
            "🗑 <b>Configuration Reset Successful!</b>\n\n"
            "All saved session data, source/destination settings, and metrics have been cleared."
        ),
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Configuration reset.")
