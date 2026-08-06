import os
import asyncio
from typing import Union, List, Optional
from pyrogram import Client
from pyrogram.types import Message
from database.db import db
from utils.logger import logger

# Global Bot reference for instant alert notifications
_bot_instance = None

def set_bot_instance(bot):
    """Sets the global aiogram Bot instance for sending instant alert notifications."""
    global _bot_instance
    _bot_instance = bot

def detect_media_type(message: Message) -> str:
    """Detects the media type category of an incoming message."""
    if message.text:
        return "text"
    elif message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.document:
        return "document"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.sticker:
        return "sticker"
    elif message.animation or message.video_note:
        return "animation"
    elif message.poll:
        return "poll"
    return "text"

async def notify_user_failure(user_id: int, route_id: str, source_chat: Union[int, str], dest_chat: Union[int, str], error_msg: str, message_id: int):
    """Sends an instant alert message to the user via Telegram Bot when a forward fails."""
    if not _bot_instance:
        return

    alert_text = (
        "⚠️ <b><u>FORWARDING FAILURE ALERT!</u></b>\n\n"
        f"<b>Route ID:</b> <code>{route_id}</code>\n"
        f"<b>Source Chat:</b> <code>{source_chat}</code>\n"
        f"<b>Destination Chat:</b> <code>{dest_chat}</code>\n"
        f"<b>Message ID:</b> <code>{message_id}</code>\n\n"
        f"<b>❌ Error Reason:</b> <code>{error_msg}</code>\n\n"
        "💡 <b>Troubleshooting Tips:</b>\n"
        "  • Verify your account is a member or admin in both chats.\n"
        "  • Ensure the destination channel allows posting messages.\n"
        "  • Check if content is protected (Restricted Saving/Forwarding)."
    )

    try:
        await _bot_instance.send_message(chat_id=user_id, text=alert_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send failure alert notification to user {user_id}: {e}")

async def forward_message_handler(client: Client, message: Message, user_id: int, route_id: str, dest_chat: Union[int, str], media_filters: Optional[List[str]] = None):
    """Core handler to filter and forward incoming messages with instant failure alerts."""
    source_chat = message.chat.id or message.chat.username or "Source"

    # 1. Media Type Filter Check
    msg_media_type = detect_media_type(message)
    if media_filters is not None and msg_media_type not in media_filters:
        logger.info(f"Skipping message {message.id} for user {user_id} (Media '{msg_media_type}' disabled in filter settings)")
        await db.log_forward_event(
            user_id=user_id,
            route_id=route_id,
            status="skipped",
            details=f"Media type '{msg_media_type}' filtered out",
            source_chat=str(source_chat),
            dest_chat=str(dest_chat)
        )
        return

    # 2. Forwarding Attempt
    try:
        # Strategy A: copy_message (lightweight, instant)
        try:
            await client.copy_message(
                chat_id=dest_chat,
                from_chat_id=message.chat.id,
                message_id=message.id
            )
            await db.log_forward_event(
                user_id=user_id,
                route_id=route_id,
                status="success",
                details=f"Copied {msg_media_type} message successfully",
                source_chat=str(source_chat),
                dest_chat=str(dest_chat)
            )
            logger.info(f"Successfully copied message {message.id} for user {user_id} on route {route_id}")
            return
        except Exception as copy_err:
            logger.warning(f"copy_message failed for message {message.id} (user {user_id}): {copy_err}. Attempting download + upload fallback...")

        # Strategy B: Download & Re-upload Fallback
        file_path = None
        caption = message.caption if message.caption else None

        try:
            if message.text:
                await client.send_message(
                    chat_id=dest_chat,
                    text=message.text,
                    entities=message.entities
                )

            elif message.photo:
                file_path = await client.download_media(message)
                await client.send_photo(chat_id=dest_chat, photo=file_path, caption=caption)

            elif message.video:
                file_path = await client.download_media(message)
                await client.send_video(chat_id=dest_chat, video=file_path, caption=caption)

            elif message.document:
                file_path = await client.download_media(message)
                await client.send_document(chat_id=dest_chat, document=file_path, caption=caption)

            elif message.audio:
                file_path = await client.download_media(message)
                await client.send_audio(chat_id=dest_chat, audio=file_path, caption=caption)

            elif message.voice:
                file_path = await client.download_media(message)
                await client.send_voice(chat_id=dest_chat, voice=file_path, caption=caption)

            elif message.sticker:
                file_path = await client.download_media(message)
                await client.send_sticker(chat_id=dest_chat, sticker=file_path)

            elif message.animation or message.video_note:
                file_path = await client.download_media(message)
                await client.send_animation(chat_id=dest_chat, animation=file_path, caption=caption)

            else:
                file_path = await client.download_media(message)
                if file_path:
                    await client.send_document(chat_id=dest_chat, document=file_path, caption=caption)

            await db.log_forward_event(
                user_id=user_id,
                route_id=route_id,
                status="success",
                details=f"Downloaded & re-uploaded {msg_media_type} message successfully",
                source_chat=str(source_chat),
                dest_chat=str(dest_chat)
            )
            logger.info(f"Successfully downloaded & uploaded message {message.id} for user {user_id} on route {route_id}")

        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Failed to remove temp file {file_path}: {e}")

    except Exception as err:
        error_reason = str(err)
        logger.error(f"Error auto-forwarding for user {user_id} on route {route_id}, msg {message.id}: {error_reason}")
        
        # Log failure in DB
        await db.log_forward_event(
            user_id=user_id,
            route_id=route_id,
            status="failed",
            details=f"Error: {error_reason}",
            source_chat=str(source_chat),
            dest_chat=str(dest_chat)
        )

        # Send instant failure alert to user via Telegram Bot
        await notify_user_failure(
            user_id=user_id,
            route_id=route_id,
            source_chat=source_chat,
            dest_chat=dest_chat,
            error_msg=error_reason,
            message_id=message.id
        )
