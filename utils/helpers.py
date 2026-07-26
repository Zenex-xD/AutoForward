import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    """Constructs the primary bot UI inline keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔐 Login Account", callback_data="btn_login")
            ],
            [
                InlineKeyboardButton(text="📥 Set Source Chat", callback_data="btn_set_source"),
                InlineKeyboardButton(text="📤 Set Destination Chat", callback_data="btn_set_destination")
            ],
            [
                InlineKeyboardButton(text="▶️ Enable Auto Forward", callback_data="btn_enable_forward"),
                InlineKeyboardButton(text="⏸ Disable Auto Forward", callback_data="btn_disable_forward")
            ],
            [
                InlineKeyboardButton(text="📊 Status", callback_data="btn_status"),
                InlineKeyboardButton(text="🗑 Reset Configuration", callback_data="btn_reset")
            ]
        ]
    )
    return keyboard

def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Constructs a simple cancel/back button keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="btn_cancel")]
        ]
    )
