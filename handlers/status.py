from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_main_keyboard

router = Router()

async def generate_status_text(user_id: int) -> str:
    """Generates formatted status message for a user."""
    config = await db.get_user_config(user_id)

    if not config:
        return (
            "📊 <b>Bot Status</b>\n\n"
            "❌ No configuration found for your account.\n"
            "Please log in and set up your source and destination chats."
        )

    is_connected = pyrogram_manager.is_active(user_id)
    is_forwarding_db = bool(config.get("is_forwarding", 0))

    conn_status = "🟢 Connected" if is_connected else "🔴 Disconnected"
    fwd_status = "▶️ Active" if (is_connected and is_forwarding_db) else "⏸ Inactive"

    acc_name = config.get("account_name") or "Not Logged In"
    phone_id = config.get("phone_number") or "N/A"
    source = config.get("source_chat") or "<i>Not Set</i>"
    destination = config.get("destination_chat") or "<i>Not Set</i>"
    count = config.get("forwarded_count", 0)

    text = (
        "📊 <b>Telegram Auto-Forwarder Status</b>\n\n"
        f"• <b>Connection Status:</b> {conn_status}\n"
        f"• <b>Forward Status:</b> {fwd_status}\n\n"
        f"👤 <b>Account:</b> {acc_name} ({phone_id})\n"
        f"📥 <b>Source Chat:</b> <code>{source}</code>\n"
        f"📤 <b>Destination Chat:</b> <code>{destination}</code>\n"
        f"📈 <b>Messages Forwarded:</b> <code>{count}</code>"
    )
    return text

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handles /status command."""
    text = await generate_status_text(message.from_user.id)
    await message.answer(text=text, reply_markup=build_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "btn_status")
async def cb_status(callback: CallbackQuery):
    """Handles status button callback."""
    text = await generate_status_text(callback.from_user.id)
    await callback.message.edit_text(text=text, reply_markup=build_main_keyboard(), parse_mode="HTML")
    await callback.answer()
