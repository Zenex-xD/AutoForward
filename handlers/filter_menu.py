from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import db, DEFAULT_MEDIA_FILTERS
from utils.helpers import build_filter_toggle_keyboard, safe_edit_menu

router = Router()

@router.callback_query(F.data.startswith("route_filters_"))
async def cb_route_filters_menu(callback: CallbackQuery):
    """Displays the media type filter settings for a route."""
    user_id = callback.from_user.id
    route_id = callback.data.replace("route_filters_", "")
    route = await db.get_route(user_id, route_id)

    if not route:
        await callback.answer("Route not found!", show_alert=True)
        return

    active_filters = route.get("media_filters", DEFAULT_MEDIA_FILTERS.copy())

    text = (
        f"🎯 <b><u>MEDIA TYPE FILTERS ({route.get('route_name', route_id)})</u></b>\n\n"
        "Tap any button below to toggle specific media types ON (✅) or OFF (❌).\n\n"
        "❖ Only media types marked with ✅ will be auto-forwarded to your destination chat."
    )

    await safe_edit_menu(callback.message, text, build_filter_toggle_keyboard(route_id, active_filters))
    await callback.answer()

@router.callback_query(F.data.startswith("filter_toggle_"))
async def cb_filter_toggle(callback: CallbackQuery):
    """Toggles a single media type filter for a route."""
    user_id = callback.from_user.id
    # Format: filter_toggle_<route_id>_<media_type>
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        return

    route_id = parts[2]
    media_type = parts[3]

    active_filters = await db.toggle_route_filter(user_id, route_id, media_type)

    text = (
        f"🎯 <b><u>MEDIA TYPE FILTERS ({route_id})</u></b>\n\n"
        "Tap any button below to toggle specific media types ON (✅) or OFF (❌).\n\n"
        "❖ Only media types marked with ✅ will be auto-forwarded to your destination chat."
    )

    await safe_edit_menu(callback.message, text, build_filter_toggle_keyboard(route_id, active_filters))
    await callback.answer(f"Toggled '{media_type.capitalize()}'")

@router.callback_query(F.data.startswith("filter_all_"))
async def cb_filter_enable_all(callback: CallbackQuery):
    """Enables all media type filters for a route."""
    user_id = callback.from_user.id
    route_id = callback.data.replace("filter_all_", "")

    config = await db.get_user_config(user_id)
    if config:
        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)
        if route:
            route["media_filters"] = DEFAULT_MEDIA_FILTERS.copy()
            config["routes"] = routes
            await db._save_user_config(user_id, config)

    text = f"🎯 <b><u>MEDIA TYPE FILTERS ({route_id})</u></b>\n\nAll media types ENABLED (✅)."
    await safe_edit_menu(callback.message, text, build_filter_toggle_keyboard(route_id, DEFAULT_MEDIA_FILTERS.copy()))
    await callback.answer("Enabled all media types!")

@router.callback_query(F.data.startswith("filter_none_"))
async def cb_filter_disable_all(callback: CallbackQuery):
    """Disables all media type filters for a route."""
    user_id = callback.from_user.id
    route_id = callback.data.replace("filter_none_", "")

    config = await db.get_user_config(user_id)
    if config:
        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)
        if route:
            route["media_filters"] = []
            config["routes"] = routes
            await db._save_user_config(user_id, config)

    text = f"🎯 <b><u>MEDIA TYPE FILTERS ({route_id})</u></b>\n\nAll media types DISABLED (❌)."
    await safe_edit_menu(callback.message, text, build_filter_toggle_keyboard(route_id, []))
    await callback.answer("Disabled all media types!")
