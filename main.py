import os
import asyncio
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, validate_config
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from services.forwarder import set_bot_instance
from utils.logger import logger

# Import all handlers
from handlers.start import router as start_router
from handlers.login import router as login_router
from handlers.string_gen import router as string_gen_router
from handlers.source import router as source_router
from handlers.destination import router as destination_router
from handlers.forward_control import router as forward_control_router
from handlers.status import router as status_router
from handlers.reset import router as reset_router
from handlers.routes_menu import router as routes_router
from handlers.filter_menu import router as filter_router
from handlers.accounts_menu import router as accounts_router

async def start_heroku_web_server():
    """Starts a lightweight web server if PORT environment variable is present (for Heroku web dynos)."""
    port_env = os.getenv("PORT")
    if port_env and port_env.isdigit():
        port = int(port_env)
        async def handle_health_check(request):
            return web.Response(text="Telegram Auto Forwarder Bot is running 24/7!")

        app = web.Application()
        app.router.add_get("/", handle_health_check)
        app.router.add_get("/health", handle_health_check)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Heroku Web health-check server started successfully on port {port}.")

async def on_shutdown(bot: Bot):
    """Graceful shutdown hook to stop all Pyrogram clients."""
    logger.info("Shutdown initiated. Stopping active Pyrogram clients...")
    for user_id in list(pyrogram_manager.active_clients.keys()):
        await pyrogram_manager.stop_forwarder(user_id)
    logger.info("All Pyrogram clients stopped cleanly.")

async def main():
    """Main application entry point."""
    logger.info("Starting Telegram Auto-Forwarder Bot...")

    # Validate environment variables
    if not validate_config():
        logger.error("Configuration validation failed. Exiting...")
        sys.exit(1)

    # Initialize Database (MongoDB with SQLite fallback)
    await db.init_db()

    # Initialize aiogram Bot & Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Pass Bot instance to forwarder service for instant alert notifications
    set_bot_instance(bot)

    # Register router handlers
    dp.include_router(start_router)
    dp.include_router(login_router)
    dp.include_router(string_gen_router)
    dp.include_router(source_router)
    dp.include_router(destination_router)
    dp.include_router(routes_router)
    dp.include_router(filter_router)
    dp.include_router(accounts_router)
    dp.include_router(forward_control_router)
    dp.include_router(status_router)
    dp.include_router(reset_router)

    # Register shutdown hook
    dp.shutdown.register(on_shutdown)

    # Start Heroku web health check server if PORT environment variable is set
    await start_heroku_web_server()

    # Automatically restore active Pyrogram sessions & routes on startup
    try:
        await pyrogram_manager.restore_all_sessions()
    except Exception as e:
        logger.error(f"Error restoring Pyrogram sessions on startup: {e}")

    logger.info("Bot started successfully and polling for updates...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Critical error in main bot loop: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated by user.")
