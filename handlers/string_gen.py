import asyncio
from typing import Dict
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from config import API_ID, API_HASH
from database.db import db
from utils.states import BotStates
from utils.helpers import build_cancel_keyboard, build_account_keyboard, safe_edit_menu
from utils.logger import logger

router = Router()

# In-memory dictionary to hold active temporary Pyrogram clients during login flow
# Key: user_id, Value: Pyrogram Client instance
TEMP_CLIENTS: Dict[int, Client] = {}

async def cleanup_temp_client(user_id: int):
    """Disconnects and removes temporary Pyrogram client for user."""
    client = TEMP_CLIENTS.pop(user_id, None)
    if client:
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting temp client for user {user_id}: {e}")

@router.message(Command("string"))
@router.callback_query(F.data == "btn_gen_string")
async def start_string_generator(event: Message | CallbackQuery, state: FSMContext):
    """Initiates Pyrogram String Session generator flow."""
    user_id = event.from_user.id
    await cleanup_temp_client(user_id)
    await state.clear()

    await state.set_state(BotStates.waiting_for_phone)

    prompt_text = (
        "⚡ <b><u>𝐒ᴛʀɪɴɢ 𝐒ᴇѕѕɪᴏɴ 𝐆ᴇɴᴇʀᴀᴛᴏʀ</u></b>\n\n"
        "Please send your Telegram account <b>phone number</b> with country code.\n\n"
        "❖ <b>Example:</b> <code>+919876543210</code>\n"
        "❖ <b>Note:</b> You will receive an OTP code in Telegram chat."
    )

    if isinstance(event, CallbackQuery):
        await safe_edit_menu(event.message, prompt_text, build_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(prompt_text, reply_markup=build_cancel_keyboard(), parse_mode="HTML")

@router.message(BotStates.waiting_for_phone)
async def process_phone_number(message: Message, state: FSMContext):
    """Processes user phone number and sends login OTP code."""
    phone_number = message.text.strip().replace(" ", "") if message.text else ""
    user_id = message.from_user.id

    if not phone_number.startswith("+") and not phone_number.isdigit():
        await message.answer(
            "❌ <b>Invalid Phone Number!</b> Please include your country code (e.g. <code>+919876543210</code>).",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer("🔄 <b>Sending OTP code to your Telegram account...</b>", parse_mode="HTML")

    try:
        # Create temp client in-memory
        temp_client = Client(
            name=f"temp_gen_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )

        await temp_client.connect()
        sent_code = await temp_client.send_code(phone_number)

        TEMP_CLIENTS[user_id] = temp_client
        await state.update_data(
            phone_number=phone_number,
            phone_code_hash=sent_code.phone_code_hash
        )

        await state.set_state(BotStates.waiting_for_otp)

        await status_msg.edit_text(
            text=(
                "📩 <b><u>𝐄ɴᴛᴇʀ 𝐎𝐓𝐏 𝐂ᴏᴅᴇ</u></b>\n\n"
                f"An OTP code has been sent to <code>{phone_number}</code> via Telegram!\n\n"
                "Please reply with the code in this format:\n"
                "❖ <code>12345</code> or <code>1 2 3 4 5</code>"
            ),
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )

    except PhoneNumberInvalid:
        await cleanup_temp_client(user_id)
        await status_msg.edit_text(
            "❌ <b>Invalid Phone Number!</b> Please check your phone number and try again.",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
    except ApiIdInvalid:
        await cleanup_temp_client(user_id)
        await status_msg.edit_text(
            "❌ <b>API ID / API Hash invalid!</b> Please verify server configuration.",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await cleanup_temp_client(user_id)
        logger.error(f"Error sending OTP to {phone_number}: {e}")
        await status_msg.edit_text(
            f"❌ <b>Failed to send OTP code!</b>\n\n<b>Error:</b> <code>{str(e)}</code>",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )

@router.message(BotStates.waiting_for_otp)
async def process_otp_code(message: Message, state: FSMContext):
    """Processes OTP code sent by user."""
    user_id = message.from_user.id
    raw_code = message.text.strip().replace(" ", "") if message.text else ""
    data = await state.get_data()

    phone_number = data.get("phone_number")
    phone_code_hash = data.get("phone_code_hash")
    temp_client = TEMP_CLIENTS.get(user_id)

    if not temp_client or not phone_number or not phone_code_hash:
        await message.answer("❌ Session expired. Please start again with /string command.")
        await cleanup_temp_client(user_id)
        await state.clear()
        return

    status_msg = await message.answer("🔄 <b>Verifying OTP code...</b>", parse_mode="HTML")

    try:
        await temp_client.sign_in(
            phone_number=phone_number,
            phone_code_hash=phone_code_hash,
            phone_code=raw_code
        )

        # Logged in successfully without 2FA
        session_string = await temp_client.export_session_string()
        me = await temp_client.get_me()

        acc_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or f"User_{me.id}"
        phone = me.phone_number or phone_number

        # Auto-save string session to database for user
        await db.save_session(
            user_id=user_id,
            session_string=session_string,
            account_name=acc_name,
            phone_number=phone
        )

        await cleanup_temp_client(user_id)
        await state.clear()

        await status_msg.edit_text(
            text=(
                "✅ <b><u>𝐒ᴛʀɪɴɢ 𝐒ᴇѕѕɪᴏɴ 𝐆ᴇɴᴇʀᴀᴛᴇᴅ!</u></b>\n\n"
                f"👤 <b>Account:</b> <code>{acc_name}</code>\n"
                f"📞 <b>Phone:</b> <code>{phone}</code>\n\n"
                "❖ <b><u>Your Session String:</u></b>\n"
                f"<code>{session_string}</code>\n\n"
                "✅ <i>This session has been automatically saved to your account!</i>"
            ),
            reply_markup=build_account_keyboard(),
            parse_mode="HTML"
        )

    except SessionPasswordNeeded:
        # User has 2FA Password enabled
        await state.set_state(BotStates.waiting_for_2fa)
        await status_msg.edit_text(
            text=(
                "🔐 <b><u>𝐓ᴡᴏ-𝐒ᴛᴇᴘ 𝐕ᴇʀɪғɪᴄᴀᴛɪᴏɴ</u></b>\n\n"
                "Your account has 2FA password enabled.\n\n"
                "Please enter your <b>Two-Step Verification Password</b> below."
            ),
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )

    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        await status_msg.edit_text(
            f"❌ <b>Invalid or Expired OTP code!</b> Please check the code and try again.",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error signing in user {user_id}: {e}")
        await status_msg.edit_text(
            f"❌ <b>Sign-in error!</b>\n\n<b>Error:</b> <code>{str(e)}</code>",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )

@router.message(BotStates.waiting_for_2fa)
async def process_2fa_password(message: Message, state: FSMContext):
    """Processes 2FA password for accounts with Two-Step Verification."""
    user_id = message.from_user.id
    password = message.text.strip() if message.text else ""
    temp_client = TEMP_CLIENTS.get(user_id)

    if not temp_client:
        await message.answer("❌ Session expired. Please start again with /string command.")
        await state.clear()
        return

    status_msg = await message.answer("🔄 <b>Verifying 2FA password...</b>", parse_mode="HTML")

    try:
        await temp_client.check_password(password)

        # Logged in successfully
        session_string = await temp_client.export_session_string()
        me = await temp_client.get_me()

        acc_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or f"User_{me.id}"
        phone = me.phone_number or f"ID: {me.id}"

        # Auto-save string session to database for user
        await db.save_session(
            user_id=user_id,
            session_string=session_string,
            account_name=acc_name,
            phone_number=phone
        )

        await cleanup_temp_client(user_id)
        await state.clear()

        await status_msg.edit_text(
            text=(
                "✅ <b><u>𝐒ᴛʀɪɴɢ 𝐒ᴇѕѕɪᴏɴ 𝐆ᴇɴᴇʀᴀᴛᴇᴅ!</u></b>\n\n"
                f"👤 <b>Account:</b> <code>{acc_name}</code>\n"
                f"📞 <b>Phone:</b> <code>{phone}</code>\n\n"
                "❖ <b><u>Your Session String:</u></b>\n"
                f"<code>{session_string}</code>\n\n"
                "✅ <i>This session has been automatically saved to your account!</i>"
            ),
            reply_markup=build_account_keyboard(),
            parse_mode="HTML"
        )

    except PasswordHashInvalid:
        await status_msg.edit_text(
            "❌ <b>Incorrect Password!</b> Please check your 2FA password and try again.",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error checking 2FA password for user {user_id}: {e}")
        await status_msg.edit_text(
            f"❌ <b>2FA verification error!</b>\n\n<b>Error:</b> <code>{str(e)}</code>",
            reply_markup=build_cancel_keyboard(),
            parse_mode="HTML"
        )
