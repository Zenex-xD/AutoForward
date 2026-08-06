import re
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

START_VIDEO_URL = "https://telegra.ph/file/4c14cbb141189eeea0c9c.mp4"

MEDIA_TYPE_LABELS = {
    "text": "💬 Text Messages",
    "photo": "📸 Photos",
    "video": "🎥 Videos",
    "document": "📁 Documents",
    "audio": "🎵 Audio / Music",
    "voice": "🎙 Voice Notes",
    "sticker": "🎨 Stickers",
    "animation": "🎆 GIFs / Animations",
    "poll": "📊 Polls"
}

def clean_chat_input(input_str: str) -> str:
    """Cleans and standardizes user input for source/destination chats."""
    input_str = input_str.strip()

    if re.match(r"^100\d{10,}$", input_str):
        return f"-{input_str}"

    if re.match(r"^-?\d+$", input_str):
        return input_str

    if "t.me/+" in input_str or "t.me/joinchat/" in input_str:
        return input_str

    m = re.search(r"(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]{5,})", input_str)
    if m:
        return f"@{m.group(1)}"

    if input_str.startswith("@"):
        return input_str

    if re.match(r"^[a-zA-Z0-9_]{5,}$", input_str):
        return f"@{input_str}"

    return input_str

def build_main_keyboard() -> InlineKeyboardMarkup:
    """Constructs the primary bot UI inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 𝐀ᴄᴄᴏᴜɴᴛѕ", callback_data="btn_accounts_list"),
                InlineKeyboardButton(text="🔀 𝐅ᴏʀᴡᴀʀᴅ 𝐑ᴏᴜᴛᴇѕ", callback_data="btn_routes_list")
            ],
            [
                InlineKeyboardButton(text="⚡ 𝐐ᴜɪᴄᴋ 𝐒ᴛᴀʀᴛ", callback_data="btn_toggle_forward"),
                InlineKeyboardButton(text="📊 𝐒ᴛᴀᴛѕ & 𝐋ᴏɢѕ", callback_data="btn_status")
            ]
        ]
    )

def build_accounts_keyboard(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Constructs the Accounts List menu keyboard."""
    buttons = []
    for acc in accounts:
        acc_id = acc.get("account_id", "acc_1")
        acc_name = acc.get("account_name", "Account")
        phone = acc.get("phone_number", "N/A")
        buttons.append([
            InlineKeyboardButton(text=f"👤 {acc_name} ({phone})", callback_data=f"acc_view_{acc_id}")
        ])

    buttons.append([InlineKeyboardButton(text="➕ 𝐀ᴅᴅ 𝐍ᴇᴡ 𝐀ᴄᴄᴏᴜɴᴛ", callback_data="btn_add_account")])
    buttons.append([InlineKeyboardButton(text="⚡ 𝐆ᴇɴᴇʀᴀᴛᴇ 𝐒ᴇѕѕɪᴏɴ (/string)", callback_data="btn_gen_string")])
    buttons.append([InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_account_details_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Constructs action keyboard for a single account."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 𝐑ᴇᴍᴏᴠᴇ 𝐀ᴄᴄᴏᴜɴᴛ", callback_data=f"acc_del_{account_id}")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ to 𝐀ᴄᴄᴏᴜɴᴛѕ", callback_data="btn_accounts_list")]
        ]
    )

def build_routes_keyboard(routes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Constructs the Routes List menu keyboard."""
    buttons = []
    for r in routes:
        r_id = r.get("route_id", "route_1")
        r_name = r.get("route_name") or f"Route {r_id}"
        is_act = "🟢" if r.get("is_active") == 1 else "🔴"
        buttons.append([
            InlineKeyboardButton(text=f"{is_act} {r_name}", callback_data=f"route_view_{r_id}")
        ])

    buttons.append([InlineKeyboardButton(text="➕ 𝐂ʀᴇᴀᴛᴇ 𝐍ᴇᴡ 𝐑ᴏᴜᴛᴇ", callback_data="btn_create_route")])
    buttons.append([InlineKeyboardButton(text="▶️ 𝐒ᴛᴀʀᴛ 𝐀ʟʟ 𝐑ᴏᴜᴛᴇѕ", callback_data="btn_start_all_routes")])
    buttons.append([InlineKeyboardButton(text="⏸ 𝐒ᴛᴏᴘ 𝐀ʟʟ 𝐑ᴏᴜᴛᴇѕ", callback_data="btn_stop_all_routes")])
    buttons.append([InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_route_details_keyboard(route_id: str, is_active: bool) -> InlineKeyboardMarkup:
    """Constructs management keyboard for a specific route."""
    toggle_text = "⏸ 𝐒ᴛᴏᴘ 𝐑ᴏᴜᴛᴇ" if is_active else "▶️ 𝐒ᴛᴀʀᴛ 𝐑ᴏᴜᴛᴇ"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=f"route_toggle_{route_id}")],
            [
                InlineKeyboardButton(text="📥 𝐒ᴇᴛ 𝐒ᴏᴜʀᴄᴇ", callback_data=f"route_src_{route_id}"),
                InlineKeyboardButton(text="📤 𝐒ᴇᴛ 𝐃ᴇѕᴛɪɴᴀᴛɪᴏɴ", callback_data=f"route_dst_{route_id}")
            ],
            [
                InlineKeyboardButton(text="🎯 𝐌ᴇᴅɪᴀ 𝐅ɪʟᴛᴇʀѕ", callback_data=f"route_filters_{route_id}"),
                InlineKeyboardButton(text="👤 𝐒ᴇʟᴇᴄᴛ 𝐀ᴄᴄᴏᴜɴᴛ", callback_data=f"route_acc_{route_id}")
            ],
            [InlineKeyboardButton(text="🗑 𝐃ᴇʟᴇᴛᴇ 𝐑ᴏᴜᴛᴇ", callback_data=f"route_del_{route_id}")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ to 𝐑ᴏᴜᴛᴇѕ", callback_data="btn_routes_list")]
        ]
    )

def build_filter_toggle_keyboard(route_id: str, active_filters: List[str]) -> InlineKeyboardMarkup:
    """Constructs interactive toggle keyboard for media type filters."""
    buttons = []
    all_types = ["text", "photo", "video", "document", "audio", "voice", "sticker", "animation", "poll"]

    for i in range(0, len(all_types), 2):
        row = []
        t1 = all_types[i]
        icon1 = "✅" if t1 in active_filters else "❌"
        label1 = f"{icon1} {t1.capitalize()}"
        row.append(InlineKeyboardButton(text=label1, callback_data=f"filter_toggle_{route_id}_{t1}"))

        if i + 1 < len(all_types):
            t2 = all_types[i + 1]
            icon2 = "✅" if t2 in active_filters else "❌"
            label2 = f"{icon2} {t2.capitalize()}"
            row.append(InlineKeyboardButton(text=label2, callback_data=f"filter_toggle_{route_id}_{t2}"))

        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="✅ 𝐄ɴᴀʙʟᴇ 𝐀ʟʟ", callback_data=f"filter_all_{route_id}"),
        InlineKeyboardButton(text="❌ 𝐃ɪѕᴀʙʟᴇ 𝐀ʟʟ", callback_data=f"filter_none_{route_id}")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ to 𝐑ᴏᴜᴛᴇ", callback_data=f"route_view_{route_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_status_keyboard(is_active: bool = False) -> InlineKeyboardMarkup:
    """Constructs status menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 𝐑ᴇғʀᴇѕʜ 𝐒ᴛᴀᴛѕ", callback_data="btn_status")],
            [InlineKeyboardButton(text="🗑 𝐑ᴇѕᴇᴛ 𝐂ᴏɴғɪɢᴜʀᴀᴛɪᴏɴ", callback_data="btn_reset")],
            [InlineKeyboardButton(text="🔙 𝐁ᴀᴄᴋ", callback_data="btn_back")]
        ]
    )

def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Constructs cancel button keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ 𝐂ᴀɴᴄᴇʟ", callback_data="btn_cancel")]
        ]
    )

async def safe_edit_menu(message: Message, text: str, reply_markup=None):
    """Edits message caption or text smoothly."""
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
