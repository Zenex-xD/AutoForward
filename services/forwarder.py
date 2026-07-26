import os
import asyncio
from typing import Union
from pyrogram import Client, enums
from pyrogram.types import Message
from database.db import db
from utils.logger import logger

async def forward_message_handler(client: Client, message: Message, user_id: int, dest_chat: Union[int, str]):
    """Core handler to forward incoming messages using copy_message or fallback download/upload."""
    try:
        # Try copy_message first (lightweight, zero bandwidth usage)
        try:
            await client.copy_message(
                chat_id=dest_chat,
                from_chat_id=message.chat.id,
                message_id=message.id
            )
            await db.increment_forward_count(user_id)
            logger.info(f"Successfully copied message {message.id} from user {user_id}'s source to {dest_chat}")
            return
        except Exception as copy_err:
            logger.warning(f"copy_message failed for message {message.id} (user {user_id}): {copy_err}. Attempting download + upload fallback...")

        # Fallback download + upload strategy
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
                # Any other media type default fallback
                file_path = await client.download_media(message)
                if file_path:
                    await client.send_document(chat_id=dest_chat, document=file_path, caption=caption)

            await db.increment_forward_count(user_id)
            logger.info(f"Successfully downloaded & re-uploaded message {message.id} for user {user_id}")

        finally:
            # Clean up temp file immediately to avoid disk accumulation
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Failed to remove temp file {file_path}: {e}")

    except Exception as err:
        logger.error(f"Error handling auto-forward for user {user_id}, message {message.id}: {err}")
