from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import db
from utils.helpers import (
    build_main_keyboard,
    build_accounts_keyboard,
    build_routes_keyboard,
    safe_edit_menu,
    START_VIDEO_URL
)

router = Router()

START_TEXT = (
    "✨ <b><u>TELEGRAM AUTO-FORWARDER BOT</u></b> ✨\n\n"
    "🚀 <i>Ultra-fast, high-performance real-time message forwarder.</i>\n\n"
    "❖ <b>Core Features:</b>\n"
    "  • 🔀 <b>Multi-Route Routing:</b> Multiple source ➔ destination pairs\n"
    "  • 👤 <b>Multi-Account Support:</b> Multiple Pyrogram string sessions\n"
    "  • 🎯 <b>Media Type Filters:</b> Toggle Text, Photos, Videos, Docs, Voice, Stickers\n"
    "  • 📊 <b>Live Stats & Logs:</b> Detailed message counts & instant failure alerts\n\n"
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
async def cb_account_redirect(callback: CallbackQuery, state: FSMContext):
    """Redirects legacy account button to Accounts List."""
    await state.clear()
    user_id = callback.from_user.id
    accounts = await db.get_user_accounts(user_id)
    text = (
        "👤 <b><u>CONNECTED TELEGRAM ACCOUNTS</u></b>\n\n"
        f"You have <b>{len(accounts)}</b> account(s) saved.\n\n"
        "❖ Select an account or add a new Pyrogram session below:"
    )
    await safe_edit_menu(callback.message, text, build_accounts_keyboard(accounts))
    await callback.answer()

@router.callback_query(F.data == "btn_forward_menu")
async def cb_forward_redirect(callback: CallbackQuery, state: FSMContext):
    """Redirects legacy forward menu button to Routes List."""
    await state.clear()
    user_id = callback.from_user.id
    routes = await db.get_user_routes(user_id)
    text = (
        "🔀 <b><u>FORWARDING ROUTES MANAGEMENT</u></b>\n\n"
        f"You have <b>{len(routes)}</b> forwarding route(s) configured.\n\n"
        "❖ Select a route below to configure source/destination, media filters, or toggle status:"
    )
    await safe_edit_menu(callback.message, text, build_routes_keyboard(routes))
    await callback.answer()
