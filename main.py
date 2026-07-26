import asyncio
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, validate_config
from database.db import db
from services.pyrogram_manager import pyrogram_manager
from utils.logger import logger

# Import handlers
from handlers.start import router as start_router
from handlers.login import router as login_router
from handlers.source import router as source_router
from handlers.destination import router as destination_router
from handlers.forward_control import router as forward_control_router
from handlers.status import router as status_router
from handlers.reset import router as reset_router

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

    # Initialize SQLite Database
    await db.init_db()

    # Initialize aiogram Bot & Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register router handlers
    dp.include_router(start_router)
    dp.include_router(login_router)
    dp.include_router(source_router)
    dp.include_router(destination_router)
    dp.include_router(forward_control_router)
    dp.include_router(status_router)
    dp.include_router(reset_router)

    # Register shutdown hook
    dp.shutdown.register(on_shutdown)

    # Automatically restore active Pyrogram sessions (Automatic reconnect after Railway restart)
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
