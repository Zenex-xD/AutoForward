import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

START_VIDEO_URL = "https://telegra.ph/file/4c14cbb141189eeea0c9c.mp4"

def clean_chat_input(input_str: str) -> str:
    """Cleans and standardizes user input for source/destination chats.
    Supports Chat ID, @username, t.me link, or join link.
    """
    input_str = input_str.strip()

    # Check if pure integer Chat ID (e.g. -100123456789 or 123456789)
    if re.match(r"^-?\d+$", input_str):
        return input_str

    # Telegram invite link: https://t.me/+abcdef or https://t.me/joinchat/abcdef
    if "t.me/+" in input_str or "t.me/joinchat/" in input_str:
        return input_str

    # Telegram public chat link: https://t.me/username or t.me/username
    m = re.search(r"(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]{5,})", input_str)
    if m:
        return f"@{m.group(1)}"

    # Handles with @
    if input_str.startswith("@"):
        return input_str

    # Plain username without @
    if re.match(r"^[a-zA-Z0-9_]{5,}$", input_str):
        return f"@{input_str}"

    return input_str

def build_main_keyboard() -> InlineKeyboardMarkup:
    """Constructs the primary 4-button bot UI inline keyboard with stylish font."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 𝐀ᴄᴄᴏᴜɴᴛ", callback_data="btn_account"),
                InlineKeyboardButton(text="📥 𝐅ᴏʀᴡᴀʀᴅ", callback_data="btn_forward_menu")
            ],
            [
                InlineKeyboardButton(text="▶️ 𝐒ᴛᴀʀᴛ 𝐅ᴡᴅ", callback_data="btn_toggle_forward"),
                InlineKeyboardButton(text="📊 𝐒ᴛᴀᴛᴜѕ", callback_data="btn_status")
            ]
        ]
    )

def build_account_keyboard() -> InlineKeyboardMarkup:
    """Constructs the Account management menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ 𝐆ᴇɴᴇʀᴀᴛᴇ 𝐒ᴇѕѕɪᴏɴ (/string)", callback_data="btn_gen_string")],
            [InlineKeyboardButton(text="🔐 𝐋ᴏɢɪɴ / 𝐏ᴀѕᴛᴇ 𝐒ᴛʀɪɴɢ 𝐒ᴇѕѕɪᴏɴ", callback_data="btn_login")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")]
        ]
    )

def build_forward_keyboard() -> InlineKeyboardMarkup:
    """Constructs the Forward Settings menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 𝐒ᴇᴛ 𝐒ᴏᴜʀᴄᴇ 𝐂ʜᴀᴛ", callback_data="btn_set_source")],
            [InlineKeyboardButton(text="📤 𝐒ᴇᴛ 𝐃ᴇѕᴛɪɴᴀᴛɪᴏɴ 𝐂ʜᴀᴛ", callback_data="btn_set_destination")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")]
        ]
    )

def build_status_keyboard(is_active: bool = False) -> InlineKeyboardMarkup:
    """Constructs status action inline keyboard with toggle and reset options."""
    toggle_btn = (
        InlineKeyboardButton(text="⏸ 𝐃ɪѕᴀʙʟᴇ 𝐀ᴜᴛᴏ 𝐅ᴏʀᴡᴀʀᴅ", callback_data="btn_disable_forward")
        if is_active
        else InlineKeyboardButton(text="▶️ 𝐄ɴᴀʙʟᴇ 𝐀ᴜᴛᴏ 𝐅ᴏʀᴡᴀʀᴅ", callback_data="btn_enable_forward")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle_btn],
            [InlineKeyboardButton(text="🗑 𝐑ᴇѕᴇᴛ 𝐂ᴏɴғɪɢᴜʀᴀᴛɪᴏɴ", callback_data="btn_reset")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")]
        ]
    )

def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Constructs a simple cancel/back button keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ 𝐂ᴀɴᴄᴇʟ", callback_data="btn_cancel")]
        ]
    )

async def safe_edit_menu(message: Message, text: str, reply_markup=None):
    """Edits message caption or text depending on whether message contains media."""
    try:
        if message.video or message.photo or message.animation:
            await message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await message.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await message.answer(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            pass

