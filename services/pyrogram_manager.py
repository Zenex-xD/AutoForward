import asyncio
from typing import Dict, Any, Optional
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import AuthKeyInvalid, UserDeactivated, SessionRevoked
from config import API_ID, API_HASH
from database.db import db
from services.forwarder import forward_message_handler
from utils.logger import logger

class PyrogramManager:
    def __init__(self):
        self.active_clients: Dict[int, Client] = {}
        self.active_handlers: Dict[int, Any] = {}

    async def validate_session(self, session_string: str) -> Dict[str, str]:
        """Validates a Pyrogram String Session and returns user account info."""
        temp_client = Client(
            name="temp_validation",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )

        try:
            await temp_client.start()
            me = await temp_client.get_me()

            account_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            if not account_name:
                account_name = me.username or f"User_{me.id}"

            phone_number = me.phone_number or f"ID: {me.id}"
            if phone_number and not phone_number.startswith("+") and not phone_number.startswith("ID"):
                phone_number = f"+{phone_number}"

            return {
                "account_name": account_name,
                "phone_number": phone_number,
                "user_id": me.id
            }
        except (AuthKeyInvalid, UserDeactivated, SessionRevoked) as e:
            raise ValueError("Invalid or revoked string session.")
        except Exception as e:
            raise ValueError(f"Failed to connect session: {str(e)}")
        finally:
            try:
                await temp_client.stop()
            except Exception:
                pass

    async def resolve_chat(self, client: Client, chat_identifier: str):
        """Resolves chat ID or joins invite link if needed."""
        chat_identifier = chat_identifier.strip()

        # Handle Telegram Invite Links (t.me/+... or t.me/joinchat/...)
        if "t.me/+" in chat_identifier or "t.me/joinchat/" in chat_identifier:
            try:
                chat = await client.join_chat(chat_identifier)
                return chat.id
            except Exception as e:
                # If already joined or error, try get_chat
                try:
                    chat = await client.get_chat(chat_identifier)
                    return chat.id
                except Exception:
                    raise ValueError(f"Could not resolve or join invite link: {e}")

        # Handle Chat ID or @username
        try:
            # Try parsing as integer chat ID if numeric
            if chat_identifier.startswith("-100") or chat_identifier.isdigit() or (chat_identifier.startswith("-") and chat_identifier[1:].isdigit()):
                chat_id = int(chat_identifier)
                chat = await client.get_chat(chat_id)
                return chat.id
            else:
                chat = await client.get_chat(chat_identifier)
                return chat.id
        except Exception as e:
            raise ValueError(f"Could not find or access chat '{chat_identifier}': {e}")

    async def start_forwarder(self, user_id: int, session_string: str, source_chat: str, destination_chat: str) -> bool:
        """Starts a Pyrogram client and begins auto-forwarding for the user."""
        # Stop existing client if running
        await self.stop_forwarder(user_id)

        client = Client(
            name=f"forwarder_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )

        try:
            await client.start()

            # Resolve source and destination chat IDs
            source_id = await self.resolve_chat(client, source_chat)
            dest_id = await self.resolve_chat(client, destination_chat)

            # Create message handler specific to source chat
            async def msg_callback(c: Client, m):
                await forward_message_handler(c, m, user_id, dest_id)

            handler = MessageHandler(msg_callback, filters.chat(source_id))
            client.add_handler(handler)

            self.active_clients[user_id] = client
            self.active_handlers[user_id] = handler

            await db.set_forwarding_status(user_id, True)
            logger.info(f"Auto-forwarder started for user {user_id}: {source_id} -> {dest_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start forwarder for user {user_id}: {e}")
            try:
                await client.stop()
            except Exception:
                pass
            await db.set_forwarding_status(user_id, False)
            raise e

    async def stop_forwarder(self, user_id: int):
        """Stops auto-forwarding Pyrogram client for a user."""
        if user_id in self.active_clients:
            client = self.active_clients.pop(user_id, None)
            self.active_handlers.pop(user_id, None)

            if client:
                try:
                    await client.stop()
                    logger.info(f"Stopped forwarder client for user {user_id}")
                except Exception as e:
                    logger.error(f"Error stopping client for user {user_id}: {e}")

        await db.set_forwarding_status(user_id, False)

    def is_active(self, user_id: int) -> bool:
        """Checks if a user's forwarder client is currently running."""
        return user_id in self.active_clients

    async def restore_all_sessions(self):
        """Restores all active forwarding sessions after Railway restart."""
        logger.info("Restoring saved forwarding sessions on startup...")
        active_users = await db.get_active_forwarders()

        restored_count = 0
        for user in active_users:
            u_id = user["user_id"]
            session_str = user["session_string"]
            source = user["source_chat"]
            dest = user["destination_chat"]

            try:
                await self.start_forwarder(u_id, session_str, source, dest)
                restored_count += 1
            except Exception as e:
                logger.error(f"Failed to restore forwarding session for user {u_id}: {e}")
                await db.set_forwarding_status(u_id, False)

        logger.info(f"Restored {restored_count}/{len(active_users)} active forwarding sessions successfully.")

# Global Pyrogram Manager instance
pyrogram_manager = PyrogramManager()
