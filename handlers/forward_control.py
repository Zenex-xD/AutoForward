from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_main_keyboard, build_status_keyboard, safe_edit_menu
from utils.logger import logger

router = Router()

@router.callback_query(F.data == "btn_toggle_forward")
async def cb_toggle_forward(callback: CallbackQuery):
    """Toggles auto-forwarding state (Enable if stopped, Disable if running)."""
    user_id = callback.from_user.id
    if pyrogram_manager.is_active(user_id):
        await cb_disable_forward(callback)
    else:
        await cb_enable_forward(callback)

@router.callback_query(F.data == "btn_enable_forward")
async def cb_enable_forward(callback: CallbackQuery):
    """Enables auto-forwarding for the user."""
    user_id = callback.from_user.id
    config = await db.get_user_config(user_id)

    # Check prerequisites
    missing = []
    if not config or not config.get("session_string"):
        missing.append("🔐 Pyrogram String Session")
    if not config or not config.get("source_chat"):
        missing.append("📥 Source Chat")
    if not config or not config.get("destination_chat"):
        missing.append("📤 Destination Chat")

    if missing:
        missing_text = (
            "⚠️ <b><u>CANNOT ENABLE AUTO FORWARD!</u></b>\n\n"
            "The following required settings are missing:\n"
            + "\n".join([f"  • {m}" for m in missing]) + "\n\n"
            "<i>Please configure them using the Account and Forward buttons in the main menu.</i>"
        )
        await safe_edit_menu(callback.message, missing_text, build_main_keyboard())
        await callback.answer("Missing configuration settings.")
        return

    await safe_edit_menu(callback.message, "🔄 <b>Connecting account & starting auto-forwarder...</b>", None)

    try:
        session_str = config["session_string"]
        source = config["source_chat"]
        dest = config["destination_chat"]

        await pyrogram_manager.start_forwarder(
            user_id=user_id,
            session_string=session_str,
            source_chat=source,
            destination_chat=dest
        )

        active_text = (
            "▶️ <b><u>AUTO FORWARD ENABLED & ACTIVE!</u></b>\n\n"
            f"📥 <b>Source:</b> <code>{source}</code>\n"
            f"📤 <b>Destination:</b> <code>{dest}</code>\n\n"
            "❖ <i>The bot is listening for new incoming messages in real-time.</i>"
        )
        await safe_edit_menu(callback.message, active_text, build_main_keyboard())
        await callback.answer("Auto forward enabled!")

    except Exception as e:
        logger.error(f"Error starting auto-forwarder for user {user_id}: {e}")
        error_text = (
            "❌ <b><u>FAILED TO ENABLE AUTO FORWARD!</u></b>\n\n"
            f"<b>Error details:</b> <code>{str(e)}</code>\n\n"
            "Please verify chat permissions, IDs, or session string and try again."
        )
        await safe_edit_menu(callback.message, error_text, build_main_keyboard())
        await callback.answer("Failed to enable auto forward.")

@router.callback_query(F.data == "btn_disable_forward")
async def cb_disable_forward(callback: CallbackQuery):
    """Disables auto-forwarding for the user."""
    user_id = callback.from_user.id
    await pyrogram_manager.stop_forwarder(user_id)

    disabled_text = (
        "⏸ <b><u>AUTO FORWARD DISABLED!</u></b>\n\n"
        "❖ Real-time message forwarding has been stopped."
    )
    await safe_edit_menu(callback.message, disabled_text, build_main_keyboard())
    await callback.answer("Auto forward disabled.")

