from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.helpers import build_status_keyboard, safe_edit_menu

router = Router()

async def generate_stats_text(user_id: int) -> str:
    """Generates detailed statistics and activity logs report for a user."""
    stats = await db.get_user_stats(user_id)
    routes = await db.get_user_routes(user_id)
    accounts = await db.get_user_accounts(user_id)

    total_fwd = stats.get("total_forwarded", 0)
    total_failed = stats.get("total_failed", 0)
    logs = stats.get("logs", [])

    active_routes_count = len([r for r in routes if pyrogram_manager.is_route_active(user_id, r["route_id"])])
    total_routes_count = len(routes)
    total_accounts_count = len(accounts)

    system_status = "🟢 Active & Online" if active_routes_count > 0 else "⏸ Offline / Paused"

    # Format Recent Activity Logs
    log_lines = []
    if logs:
        for entry in logs[:7]:
            status = entry.get("status", "").upper()
            icon = "✅" if status == "SUCCESS" else ("⚠️" if status == "SKIPPED" else "❌")
            ts = entry.get("timestamp", "").split(" ")[-1]
            details = entry.get("details", "")
            log_lines.append(f"  • {icon} <code>[{ts}]</code> {details}")
        logs_formatted = "\n".join(log_lines)
    else:
        logs_formatted = "  • <i>No recent forward activity logged yet.</i>"

    # Format Routes Summary
    routes_summary = []
    if routes:
        for r in routes:
            r_id = r["route_id"]
            r_name = r.get("route_name", r_id)
            is_active = pyrogram_manager.is_route_active(user_id, r_id)
            st = "🟢" if is_active else "🔴"
            src = r.get("source_chat", "Not set")
            dst = r.get("destination_chat", "Not set")
            routes_summary.append(f"  • {st} <b>{r_name}:</b> <code>{src}</code> ➔ <code>{dst}</code>")
        routes_formatted = "\n".join(routes_summary)
    else:
        routes_formatted = "  • <i>No forwarding routes created.</i>"

    text = (
        "📊 <b><u>TELEGRAM AUTO-FORWARDER DASHBOARD</u></b>\n\n"
        f"⚡ <b>System Engine:</b> {system_status}\n"
        f"📈 <b>Total Messages Forwarded:</b> <code>{total_fwd:,}</code>\n"
        f"❌ <b>Total Failed Attempts:</b> <code>{total_failed:,}</code>\n\n"
        f"👥 <b>Connected Accounts:</b> <code>{total_accounts_count}</code>\n"
        f"🔀 <b>Active Routes:</b> <code>{active_routes_count} / {total_routes_count}</code>\n\n"
        "🔀 <b><u>CONFIGURED ROUTES:</u></b>\n"
        f"{routes_formatted}\n\n"
        "📜 <b><u>RECENT ACTIVITY LOGS:</u></b>\n"
        f"{logs_formatted}"
    )
    return text

@router.message(Command("status"))
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handles /stats or /status command."""
    text = await generate_stats_text(message.from_user.id)
    await message.answer(text=text, reply_markup=build_status_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "btn_status")
async def cb_stats(callback: CallbackQuery):
    """Handles status / stats button callback."""
    text = await generate_stats_text(callback.from_user.id)
    await safe_edit_menu(callback.message, text, build_status_keyboard())
    await callback.answer("Dashboard updated.")
