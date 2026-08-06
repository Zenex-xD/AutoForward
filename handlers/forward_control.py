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
    """Enables auto-forwarding for all user routes."""
    user_id = callback.from_user.id
    accounts = await db.get_user_accounts(user_id)
    routes = await db.get_user_routes(user_id)

    # Prerequisites check
    missing = []
    if not accounts:
        missing.append("🔐 Pyrogram String Session Account")

    valid_routes = [r for r in routes if r.get("source_chat") and r.get("destination_chat")]
    if not valid_routes:
        missing.append("📥 Source & 📤 Destination Chat Configuration")

    if missing:
        missing_text = (
            "⚠️ <b><u>CANNOT ENABLE AUTO FORWARD!</u></b>\n\n"
            "The following required settings are missing:\n"
            + "\n".join([f"  • {m}" for m in missing]) + "\n\n"
            "<i>Please add an account or configure a forwarding route first.</i>"
        )
        await safe_edit_menu(callback.message, missing_text, build_main_keyboard())
        await callback.answer("Missing configuration settings.")
        return

    await safe_edit_menu(callback.message, "🔄 <b>Connecting account & starting auto-forwarder...</b>", None)

    started_count = 0
    errors = []

    for r in valid_routes:
        acc_id = r.get("account_id") or accounts[0]["account_id"]
        acc = next((a for a in accounts if a["account_id"] == acc_id), accounts[0])

        try:
            await pyrogram_manager.start_route_forwarder(
                user_id=user_id,
                route_id=r["route_id"],
                session_string=acc["session_string"],
                source_chat=r["source_chat"],
                destination_chat=r["destination_chat"],
                account_id=acc["account_id"],
                media_filters=r.get("media_filters")
            )
            started_count += 1
        except Exception as e:
            logger.error(f"Error starting route '{r['route_id']}' for user {user_id}: {e}")
            errors.append(f"{r.get('route_name', r['route_id'])}: {e}")

    if started_count > 0:
        active_text = (
            "▶️ <b><u>AUTO FORWARD ENABLED & ACTIVE!</u></b>\n\n"
            f"❖ Successfully started <b>{started_count}/{len(valid_routes)}</b> forwarding route(s).\n\n"
            "❖ <i>The bot is listening for incoming messages in real-time.</i>"
        )
        await safe_edit_menu(callback.message, active_text, build_main_keyboard())
        await callback.answer("Auto forward enabled!")
    else:
        err_msg = "\n".join(errors) if errors else "Unknown error"
        error_text = (
            "❌ <b><u>FAILED TO ENABLE AUTO FORWARD!</u></b>\n\n"
            f"<b>Error details:</b>\n<code>{err_msg}</code>\n\n"
            "Please verify chat permissions, IDs, or string session and try again."
        )
        await safe_edit_menu(callback.message, error_text, build_main_keyboard())
        await callback.answer("Failed to enable auto forward.")

@router.callback_query(F.data == "btn_disable_forward")
async def cb_disable_forward(callback: CallbackQuery):
    """Disables auto-forwarding for all routes."""
    user_id = callback.from_user.id
    await pyrogram_manager.stop_forwarder(user_id)

    disabled_text = (
        "⏸ <b><u>AUTO FORWARD DISABLED!</u></b>\n\n"
        "❖ All real-time message forwarding routes have been stopped."
    )
    await safe_edit_menu(callback.message, disabled_text, build_main_keyboard())
    await callback.answer("Auto forward disabled.")
