from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_status_keyboard, safe_edit_menu

router = Router()

async def generate_status_data(user_id: int):
    """Generates formatted status message and active state for a user."""
    config = await db.get_user_config(user_id)

    if not config:
        text = (
            "📊 <b><u>BOT STATUS</u></b>\n\n"
            "❌ <b>No Configuration Found!</b>\n"
            "<i>Please log in and configure source and destination chats first.</i>"
        )
        return text, False

    is_connected = pyrogram_manager.is_active(user_id)
    is_forwarding_db = bool(config.get("is_forwarding", 0))
    is_active = is_connected and is_forwarding_db

    conn_status = "🟢 Connected" if is_connected else "🔴 Disconnected"
    fwd_status = "▶️ Active & Running" if is_active else "⏸ Inactive"

    acc_name = config.get("account_name") or "Not Logged In"
    phone_id = config.get("phone_number") or "N/A"
    source = config.get("source_chat") or "Not Set"
    destination = config.get("destination_chat") or "Not Set"
    count = config.get("forwarded_count", 0)

    text = (
        "📊 <b><u>TELEGRAM AUTO-FORWARDER STATUS</u></b>\n\n"
        f"❖ <b>Connection Status:</b> {conn_status}\n"
        f"❖ <b>Forwarding Engine:</b> {fwd_status}\n\n"
        f"👤 <b>Account:</b> <code>{acc_name}</code> (<code>{phone_id}</code>)\n"
        f"📥 <b>Source Chat:</b> <code>{source}</code>\n"
        f"📤 <b>Destination Chat:</b> <code>{destination}</code>\n"
        f"📈 <b>Messages Forwarded:</b> <code>{count}</code>"
    )
    return text, is_active

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handles /status command."""
    text, is_active = await generate_status_data(message.from_user.id)
    await message.answer(text=text, reply_markup=build_status_keyboard(is_active), parse_mode="HTML")

@router.callback_query(F.data == "btn_status")
async def cb_status(callback: CallbackQuery):
    """Handles status button callback."""
    text, is_active = await generate_status_data(callback.from_user.id)
    await safe_edit_menu(callback.message, text, build_status_keyboard(is_active))
    await callback.answer()

