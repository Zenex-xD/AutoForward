from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import db
from utils.helpers import (
    build_main_keyboard,
    build_account_keyboard,
    build_forward_keyboard,
    safe_edit_menu,
    START_VIDEO_URL
)

router = Router()

START_TEXT = (
    "✨ <b><u>TELEGRAM AUTO-FORWARDER BOT</u></b> ✨\n\n"
    "🚀 <i>Ultra-fast, high-performance real-time message forwarder.</i>\n\n"
    "❖ <b>Core Capabilities:</b>\n"
    "  • 💬 Text Messages & Captions\n"
    "  • 📸 Photos, 🎥 Videos & 🎬 Video Notes\n"
    "  • 📁 Documents, 🎵 Audio & 🎙 Voice\n"
    "  • 🎨 Stickers, 🎆 GIFs & 👾 Animations\n\n"
    "👇 <b>Select an option below to get started:</b>"
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handles /start command with video header."""
    await state.clear()
    try:
        await message.answer_video(
            video=START_VIDEO_URL,
            caption=START_TEXT,
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        # Fallback to text message if video load fails
        await message.answer(
            text=START_TEXT,
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )

@router.callback_query(F.data.in_({"btn_back", "btn_cancel"}))
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Handles back / cancel button to return to main menu."""
    await state.clear()
    await safe_edit_menu(callback.message, START_TEXT, build_main_keyboard())
    await callback.answer("Main Menu")

@router.callback_query(F.data == "btn_account")
async def cb_account_menu(callback: CallbackQuery, state: FSMContext):
    """Displays account information and login options."""
    await state.clear()
    user_id = callback.from_user.id
    config = await db.get_user_config(user_id)

    if config and config.get("session_string"):
        acc_name = config.get("account_name", "Logged In")
        phone = config.get("phone_number", "N/A")
        account_text = (
            "👤 <b><u>ACCOUNT SETTINGS</u></b>\n\n"
            "✅ <b>Status:</b> <code>Logged In</code>\n"
            f"👤 <b>Name:</b> <code>{acc_name}</code>\n"
            f"📞 <b>Phone / ID:</b> <code>{phone}</code>\n\n"
            "<i>To change or update your session string, tap the button below:</i>"
        )
    else:
        account_text = (
            "👤 <b><u>ACCOUNT SETTINGS</u></b>\n\n"
            "❌ <b>Status:</b> <code>Not Logged In</code>\n\n"
            "<i>Please paste your Pyrogram String Session to authorize auto-forwarding.</i>"
        )

    await safe_edit_menu(callback.message, account_text, build_account_keyboard())
    await callback.answer()

@router.callback_query(F.data == "btn_forward_menu")
async def cb_forward_menu(callback: CallbackQuery, state: FSMContext):
    """Displays source and destination chat settings."""
    await state.clear()
    user_id = callback.from_user.id
    config = await db.get_user_config(user_id)

    src = config.get("source_chat", "Not Set") if config else "Not Set"
    dest = config.get("destination_chat", "Not Set") if config else "Not Set"

    forward_text = (
        "📥 <b><u>FORWARD SETTINGS</u></b>\n\n"
        f"📥 <b>Source Chat:</b> <code>{src}</code>\n"
        f"📤 <b>Destination Chat:</b> <code>{dest}</code>\n\n"
        "<i>Configure your Source and Destination channels/groups/chats using the options below:</i>"
    )

    await safe_edit_menu(callback.message, forward_text, build_forward_keyboard())
    await callback.answer()

