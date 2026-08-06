from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_accounts_keyboard, build_account_details_keyboard, build_cancel_keyboard, safe_edit_menu
from utils.states import BotStates

router = Router()

@router.callback_query(F.data == "btn_accounts_list")
async def cb_accounts_list(callback: CallbackQuery, state: FSMContext):
    """Displays list of connected Telegram Pyrogram accounts."""
    await state.clear()
    user_id = callback.from_user.id
    accounts = await db.get_user_accounts(user_id)

    if accounts:
        acc_text = (
            "👤 <b><u>CONNECTED TELEGRAM ACCOUNTS</u></b>\n\n"
            f"You have <b>{len(accounts)}</b> active account(s) saved.\n\n"
            "❖ Select an account below to view details or remove, or tap <b>➕ Add New Account</b> to log in another Pyrogram session:"
        )
    else:
        acc_text = (
            "👤 <b><u>CONNECTED TELEGRAM ACCOUNTS</u></b>\n\n"
            "❌ <b>No Accounts Logged In!</b>\n\n"
            "<i>Please tap '➕ Add New Account' or '⚡ Generate Session' to add your Telegram account string session.</i>"
        )

    await safe_edit_menu(callback.message, acc_text, build_accounts_keyboard(accounts))
    await callback.answer()

@router.callback_query(F.data.startswith("acc_view_"))
async def cb_account_view(callback: CallbackQuery, state: FSMContext):
    """Displays details for a specific account."""
    await state.clear()
    user_id = callback.from_user.id
    account_id = callback.data.replace("acc_view_", "")
    accounts = await db.get_user_accounts(user_id)

    account = next((a for a in accounts if a.get("account_id") == account_id), None)
    if not account:
        await callback.answer("Account not found!", show_alert=True)
        return

    acc_name = account.get("account_name", "Account")
    phone = account.get("phone_number", "N/A")

    text = (
        f"👤 <b><u>ACCOUNT DETAILS</u></b>\n\n"
        f"👤 <b>Name:</b> <code>{acc_name}</code>\n"
        f"📞 <b>Phone / ID:</b> <code>{phone}</code>\n"
        f"🔑 <b>Account ID:</b> <code>{account_id}</code>\n\n"
        "❖ <i>This Pyrogram string session is active and stored securely.</i>"
    )

    await safe_edit_menu(callback.message, text, build_account_details_keyboard(account_id))
    await callback.answer()

@router.callback_query(F.data == "btn_add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    """Prompts user to send a new string session."""
    await state.set_state(BotStates.waiting_for_session)
    prompt_text = (
        "🔐 <b><u>ADD TELEGRAM ACCOUNT SESSION</u></b>\n\n"
        "Please paste your <b>Pyrogram String Session</b> in the chat below.\n\n"
        "❖ <i>You can generate a session using the ⚡ Generate Session command or external tools.</i>"
    )
    await safe_edit_menu(callback.message, prompt_text, build_cancel_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("acc_del_"))
async def cb_account_delete(callback: CallbackQuery):
    """Deletes a specific account."""
    user_id = callback.from_user.id
    account_id = callback.data.replace("acc_del_", "")

    await db.delete_account(user_id, account_id)
    accounts = await db.get_user_accounts(user_id)

    text = f"✅ Account <code>{account_id}</code> removed successfully."
    await safe_edit_menu(callback.message, text, build_accounts_keyboard(accounts))
    await callback.answer("Account removed.")
