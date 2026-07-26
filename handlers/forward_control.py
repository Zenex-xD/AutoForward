from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_main_keyboard
from utils.logger import logger

router = Router()

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
        await callback.message.edit_text(
            text=(
                "⚠️ <b>Cannot Enable Auto Forward!</b>\n\n"
                "The following required settings are missing:\n"
                + "\n".join([f"• {m}" for m in missing]) + "\n\n"
                "Please configure them first using the menu buttons below."
            ),
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("Missing configuration settings.")
        return

    status_msg = await callback.message.edit_text("⏳ Connecting Pyrogram account & starting auto-forwarder...")

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

        await status_msg.edit_text(
            text=(
                "▶️ <b>Auto Forward Enabled & Active!</b>\n\n"
                f"📥 <b>Source:</b> <code>{source}</code>\n"
                f"📤 <b>Destination:</b> <code>{dest}</code>\n\n"
                "The bot is now listening for incoming messages in real-time."
            ),
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("Auto forward enabled!")

    except Exception as e:
        logger.error(f"Error starting auto-forwarder for user {user_id}: {e}")
        await status_msg.edit_text(
            text=(
                "❌ <b>Failed to Enable Auto Forward!</b>\n\n"
                f"Error details: <code>{str(e)}</code>\n\n"
                "Please verify your chat permissions, chat IDs, or session string and try again."
            ),
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("Failed to enable auto forward.")

@router.callback_query(F.data == "btn_disable_forward")
async def cb_disable_forward(callback: CallbackQuery):
    """Disables auto-forwarding for the user."""
    user_id = callback.from_user.id
    await pyrogram_manager.stop_forwarder(user_id)

    await callback.message.edit_text(
        text=(
            "⏸ <b>Auto Forward Disabled!</b>\n\n"
            "Real-time message forwarding has been stopped for your account."
        ),
        reply_markup=build_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Auto forward disabled.")
