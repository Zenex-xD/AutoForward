from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.states import BotStates
from utils.helpers import (
    build_routes_keyboard,
    build_route_details_keyboard,
    build_cancel_keyboard,
    clean_chat_input,
    safe_edit_menu
)
from utils.logger import logger

router = Router()

@router.callback_query(F.data == "btn_routes_list")
async def cb_routes_list(callback: CallbackQuery, state: FSMContext):
    """Displays the list of configured forwarding routes."""
    await state.clear()
    user_id = callback.from_user.id
    routes = await db.get_user_routes(user_id)

    text = (
        "🔀 <b><u>FORWARDING ROUTES MANAGEMENT</u></b>\n\n"
        f"You currently have <b>{len(routes)}</b> forwarding route(s) configured.\n\n"
        "❖ Select a route below to view details, configure source/destination, set media filters, or toggle forwarding:"
    )

    await safe_edit_menu(callback.message, text, build_routes_keyboard(routes))
    await callback.answer()

@router.callback_query(F.data.startswith("route_view_"))
async def cb_route_view(callback: CallbackQuery, state: FSMContext):
    """Displays details and settings for a specific route."""
    await state.clear()
    user_id = callback.from_user.id
    route_id = callback.data.replace("route_view_", "")
    route = await db.get_route(user_id, route_id)

    if not route:
        await callback.answer("Route not found!", show_alert=True)
        return

    is_act = pyrogram_manager.is_route_active(user_id, route_id)
    status_str = "🟢 Active & Forwarding" if is_act else "🔴 Stopped / Inactive"

    src = route.get("source_chat") or "Not Set"
    dst = route.get("destination_chat") or "Not Set"
    acc_id = route.get("account_id", "acc_1")
    filters_list = route.get("media_filters", [])

    filters_str = ", ".join([f.capitalize() for f in filters_list]) if filters_list else "None (All Disabled)"

    text = (
        f"🔀 <b><u>ROUTE DETAILS: {route.get('route_name', route_id)}</u></b>\n\n"
        f"⚡ <b>Status:</b> {status_str}\n"
        f"📥 <b>Source Chat:</b> <code>{src}</code>\n"
        f"📤 <b>Destination Chat:</b> <code>{dst}</code>\n"
        f"🎯 <b>Media Filters:</b> <code>{filters_str}</code>\n"
        f"👤 <b>Account ID:</b> <code>{acc_id}</code>\n\n"
        "<i>Use the controls below to configure or start/stop this route:</i>"
    )

    await safe_edit_menu(callback.message, text, build_route_details_keyboard(route_id, is_act))
    await callback.answer()

@router.callback_query(F.data == "btn_create_route")
async def cb_create_route(callback: CallbackQuery, state: FSMContext):
    """Creates a new route and prompts user for source chat."""
    user_id = callback.from_user.id
    routes = await db.get_user_routes(user_id)
    new_route_id = f"route_{len(routes) + 1}"
    new_route_name = f"Route {len(routes) + 1}"

    accounts = await db.get_user_accounts(user_id)
    acc_id = accounts[0]["account_id"] if accounts else "acc_1"

    await db.save_route(
        user_id=user_id,
        route_id=new_route_id,
        source_chat="",
        destination_chat="",
        account_id=acc_id,
        route_name=new_route_name
    )

    await state.update_data(editing_route_id=new_route_id)
    await state.set_state(BotStates.waiting_for_route_source)

    text = (
        f"➕ <b><u>CREATING {new_route_name.upper()}</u></b>\n\n"
        "Please send the <b>Source Chat</b> details below.\n\n"
        "❖ <b>Supported Formats:</b>\n"
        "  • Chat ID: <code>-1001234567890</code>\n"
        "  • Username: <code>@source_channel</code>\n"
        "  • Invite Link: <code>https://t.me/+AbCdEfGh</code>"
    )

    await safe_edit_menu(callback.message, text, build_cancel_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("route_src_"))
async def cb_route_set_source(callback: CallbackQuery, state: FSMContext):
    """Prompts for source chat for specific route."""
    route_id = callback.data.replace("route_src_", "")
    await state.update_data(editing_route_id=route_id)
    await state.set_state(BotStates.waiting_for_route_source)

    text = (
        "📥 <b><u>SET ROUTE SOURCE CHAT</u></b>\n\n"
        "Please send the source channel/group details below.\n\n"
        "❖ Chat ID (<code>-100...</code>), @username, or invite link."
    )
    await safe_edit_menu(callback.message, text, build_cancel_keyboard())
    await callback.answer()

@router.message(BotStates.waiting_for_route_source)
async def process_route_source(message: Message, state: FSMContext):
    """Processes source chat input for route."""
    raw_input = message.text.strip() if message.text else ""
    if not raw_input:
        await message.answer("❌ Invalid input. Please send a valid Chat ID, Username, or Invite Link.")
        return

    data = await state.get_data()
    route_id = data.get("editing_route_id", "route_1")
    cleaned_source = clean_chat_input(raw_input)
    user_id = message.from_user.id

    await db.save_source(user_id=user_id, source_chat=cleaned_source, route_id=route_id)
    await state.clear()

    route = await db.get_route(user_id, route_id)
    is_act = pyrogram_manager.is_route_active(user_id, route_id)

    text = (
        "✅ <b><u>SOURCE CHAT SAVED!</u></b>\n\n"
        f"📥 <b>Source:</b> <code>{cleaned_source}</code>\n"
    )
    await message.answer(text, reply_markup=build_route_details_keyboard(route_id, is_act), parse_mode="HTML")

@router.callback_query(F.data.startswith("route_dst_"))
async def cb_route_set_dest(callback: CallbackQuery, state: FSMContext):
    """Prompts for destination chat for specific route."""
    route_id = callback.data.replace("route_dst_", "")
    await state.update_data(editing_route_id=route_id)
    await state.set_state(BotStates.waiting_for_route_destination)

    text = (
        "📤 <b><u>SET ROUTE DESTINATION CHAT</u></b>\n\n"
        "Please send the destination channel/group details below.\n\n"
        "❖ Chat ID (<code>-100...</code>), @username, or invite link."
    )
    await safe_edit_menu(callback.message, text, build_cancel_keyboard())
    await callback.answer()

@router.message(BotStates.waiting_for_route_destination)
async def process_route_dest(message: Message, state: FSMContext):
    """Processes destination chat input for route."""
    raw_input = message.text.strip() if message.text else ""
    if not raw_input:
        await message.answer("❌ Invalid input. Please send a valid Chat ID, Username, or Invite Link.")
        return

    data = await state.get_data()
    route_id = data.get("editing_route_id", "route_1")
    cleaned_dest = clean_chat_input(raw_input)
    user_id = message.from_user.id

    await db.save_destination(user_id=user_id, destination_chat=cleaned_dest, route_id=route_id)
    await state.clear()

    route = await db.get_route(user_id, route_id)
    is_act = pyrogram_manager.is_route_active(user_id, route_id)

    text = (
        "✅ <b><u>DESTINATION CHAT SAVED!</u></b>\n\n"
        f"📤 <b>Destination:</b> <code>{cleaned_dest}</code>\n"
    )
    await message.answer(text, reply_markup=build_route_details_keyboard(route_id, is_act), parse_mode="HTML")

@router.callback_query(F.data.startswith("route_toggle_"))
async def cb_route_toggle(callback: CallbackQuery):
    """Starts or stops forwarding for a specific route."""
    user_id = callback.from_user.id
    route_id = callback.data.replace("route_toggle_", "")
    route = await db.get_route(user_id, route_id)

    if not route or not route.get("source_chat") or not route.get("destination_chat"):
        await callback.answer("Please configure both Source and Destination chats first!", show_alert=True)
        return

    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await callback.answer("Please log in with a Telegram session account first!", show_alert=True)
        return

    acc_id = route.get("account_id") or accounts[0]["account_id"]
    acc = next((a for a in accounts if a["account_id"] == acc_id), accounts[0])

    is_currently_active = pyrogram_manager.is_route_active(user_id, route_id)

    if is_currently_active:
        await pyrogram_manager.stop_route_forwarder(user_id, route_id)
        await callback.answer("Route forwarding stopped.")
    else:
        try:
            await pyrogram_manager.start_route_forwarder(
                user_id=user_id,
                route_id=route_id,
                session_string=acc["session_string"],
                source_chat=route["source_chat"],
                destination_chat=route["destination_chat"],
                account_id=acc["account_id"],
                media_filters=route.get("media_filters")
            )
            await callback.answer("Route forwarding started successfully!")
        except Exception as e:
            logger.error(f"Failed to toggle route {route_id}: {e}")
            await callback.answer(f"Failed to start route: {e}", show_alert=True)

    # Refresh details view
    is_act = pyrogram_manager.is_route_active(user_id, route_id)
    status_str = "🟢 Active & Forwarding" if is_act else "🔴 Stopped / Inactive"
    filters_list = route.get("media_filters", [])
    filters_str = ", ".join([f.capitalize() for f in filters_list]) if filters_list else "None"

    text = (
        f"🔀 <b><u>ROUTE DETAILS: {route.get('route_name', route_id)}</u></b>\n\n"
        f"⚡ <b>Status:</b> {status_str}\n"
        f"📥 <b>Source Chat:</b> <code>{route['source_chat']}</code>\n"
        f"📤 <b>Destination Chat:</b> <code>{route['destination_chat']}</code>\n"
        f"🎯 <b>Media Filters:</b> <code>{filters_str}</code>\n"
    )
    await safe_edit_menu(callback.message, text, build_route_details_keyboard(route_id, is_act))

@router.callback_query(F.data.startswith("route_del_"))
async def cb_route_delete(callback: CallbackQuery):
    """Deletes a specific route."""
    user_id = callback.from_user.id
    route_id = callback.data.replace("route_del_", "")

    await pyrogram_manager.stop_route_forwarder(user_id, route_id)
    await db.delete_route(user_id, route_id)

    routes = await db.get_user_routes(user_id)
    text = f"✅ Route <code>{route_id}</code> deleted successfully."
    await safe_edit_menu(callback.message, text, build_routes_keyboard(routes))
    await callback.answer("Route deleted.")

@router.callback_query(F.data == "btn_start_all_routes")
async def cb_start_all_routes(callback: CallbackQuery):
    """Starts all configured routes for user."""
    user_id = callback.from_user.id
    routes = await db.get_user_routes(user_id)
    accounts = await db.get_user_accounts(user_id)

    if not accounts:
        await callback.answer("No logged-in Telegram account found!", show_alert=True)
        return

    started = 0
    for r in routes:
        if r.get("source_chat") and r.get("destination_chat"):
            acc_id = r.get("account_id") or accounts[0]["account_id"]
            acc = next((a for a in accounts if a["account_id"] == acc_id), accounts[0])
            try:
                await pyrogram_manager.start_route_forwarder(
                    user_id=user_id,
                    route_id=r["route_id"],
                    session_string=acc["session_string"],
                    source_chat=r["source_chat"],
                    destination_chat=r["destination_chat"],
                    account_id=acc["account_id"],
                    media_filters=r.get("media_filters")
                )
                started += 1
            except Exception as e:
                logger.error(f"Error starting route {r['route_id']}: {e}")

    await callback.answer(f"Started {started}/{len(routes)} routes!", show_alert=True)
    routes = await db.get_user_routes(user_id)
    await safe_edit_menu(callback.message, "🔀 <b><u>ALL ROUTES UPDATED</u></b>", build_routes_keyboard(routes))

@router.callback_query(F.data == "btn_stop_all_routes")
async def cb_stop_all_routes(callback: CallbackQuery):
    """Stops all routes for user."""
    user_id = callback.from_user.id
    await pyrogram_manager.stop_forwarder(user_id)
    await callback.answer("Stopped all routes!", show_alert=True)

    routes = await db.get_user_routes(user_id)
    await safe_edit_menu(callback.message, "⏸ <b><u>ALL ROUTES STOPPED</u></b>", build_routes_keyboard(routes))
