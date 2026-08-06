import asyncio
from typing import Dict, Any, Optional, List, Tuple
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import AuthKeyInvalid, UserDeactivated, SessionRevoked
from config import API_ID, API_HASH
from database.db import db, DEFAULT_MEDIA_FILTERS
from services.forwarder import forward_message_handler
from utils.logger import logger

class PyrogramManager:
    def __init__(self):
        # Maps client_key (e.g. "user_123_acc_1") -> Client
        self.active_clients: Dict[str, Client] = {}
        # Maps handler_key (e.g. "user_123_route_1") -> (client_key, handler)
        self.active_handlers: Dict[str, Tuple[str, Any]] = {}

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

        # Handle Telegram Invite Links
        if "t.me/+" in chat_identifier or "t.me/joinchat/" in chat_identifier:
            try:
                chat = await client.join_chat(chat_identifier)
                return chat.id
            except Exception as e:
                try:
                    chat = await client.get_chat(chat_identifier)
                    return chat.id
                except Exception:
                    raise ValueError(f"Could not resolve or join invite link: {e}")

        clean_id = chat_identifier
        target_id: Optional[int] = None

        if clean_id.isdigit():
            if clean_id.startswith("100"):
                target_id = int(f"-{clean_id}")
            else:
                target_id = int(clean_id)
        elif clean_id.startswith("-") and clean_id[1:].isdigit():
            target_id = int(clean_id)

        try:
            query = target_id if target_id is not None else clean_id
            chat = await client.get_chat(query)
            return chat.id
        except Exception as first_err:
            logger.warning(f"First attempt to get_chat('{chat_identifier}') failed: {first_err}. Refreshing dialogs...")

        try:
            async for _ in client.get_dialogs(limit=200):
                pass
        except Exception as d_err:
            logger.warning(f"Failed to fetch dialogs: {d_err}")

        try:
            query = target_id if target_id is not None else clean_id
            chat = await client.get_chat(query)
            return chat.id
        except Exception as second_err:
            if target_id is not None:
                try:
                    async for dialog in client.get_dialogs():
                        if dialog.chat.id == target_id:
                            return dialog.chat.id
                except Exception:
                    pass

            raise ValueError(f"Could not find or access chat '{chat_identifier}'. Ensure account is a member or admin. Error: {second_err}")

    async def start_route_forwarder(
        self,
        user_id: int,
        route_id: str,
        session_string: str,
        source_chat: str,
        destination_chat: str,
        account_id: str = "acc_1",
        media_filters: Optional[List[str]] = None
    ) -> bool:
        """Starts forwarding for a specific route linked to a session account."""
        client_key = f"{user_id}_{account_id}"
        handler_key = f"{user_id}_{route_id}"

        # Stop existing route handler if already running
        await self.stop_route_forwarder(user_id, route_id)

        # Retrieve or instantiate Pyrogram Client for this account
        client = self.active_clients.get(client_key)
        if not client:
            client = Client(
                name=f"forwarder_{user_id}_{account_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True
            )
            await client.start()
            self.active_clients[client_key] = client

        try:
            source_id = await self.resolve_chat(client, source_chat)
            dest_id = await self.resolve_chat(client, destination_chat)

            m_filters = media_filters if media_filters is not None else DEFAULT_MEDIA_FILTERS.copy()

            async def msg_callback(c: Client, m):
                await forward_message_handler(c, m, user_id, route_id, dest_id, m_filters)

            handler = MessageHandler(msg_callback, filters.chat(source_id))
            client.add_handler(handler)
            self.active_handlers[handler_key] = (client_key, handler)

            await db.set_route_status(user_id, route_id, True)
            logger.info(f"Route '{route_id}' started for user {user_id} using account '{account_id}': {source_id} -> {dest_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start route '{route_id}' for user {user_id}: {e}")
            # If no other handlers are attached to this client, stop the client
            active_for_client = [hk for hk, (ck, _) in self.active_handlers.items() if ck == client_key]
            if not active_for_client:
                c = self.active_clients.pop(client_key, None)
                if c:
                    try:
                        await c.stop()
                    except Exception:
                        pass
            await db.set_route_status(user_id, route_id, False)
            raise e

    async def start_forwarder(self, user_id: int, session_string: str, source_chat: str, destination_chat: str) -> bool:
        """Backward compatible forwarder launcher for single route."""
        return await self.start_route_forwarder(
            user_id=user_id,
            route_id="route_1",
            session_string=session_string,
            source_chat=source_chat,
            destination_chat=destination_chat,
            account_id="acc_1"
        )

    async def stop_route_forwarder(self, user_id: int, route_id: str):
        """Stops forwarding for a specific route."""
        handler_key = f"{user_id}_{route_id}"
        if handler_key in self.active_handlers:
            client_key, handler = self.active_handlers.pop(handler_key)
            client = self.active_clients.get(client_key)
            if client:
                try:
                    client.remove_handler(*handler)
                except Exception as e:
                    logger.error(f"Error removing handler for route '{route_id}': {e}")

            # If no more active handlers for this client, stop client connection
            remaining_for_client = [hk for hk, (ck, _) in self.active_handlers.items() if ck == client_key]
            if not remaining_for_client:
                client_to_stop = self.active_clients.pop(client_key, None)
                if client_to_stop:
                    try:
                        await client_to_stop.stop()
                        logger.info(f"Stopped client '{client_key}' as no active routes remain.")
                    except Exception as e:
                        logger.error(f"Error stopping client '{client_key}': {e}")

        await db.set_route_status(user_id, route_id, False)

    async def stop_forwarder(self, user_id: int):
        """Stops all active forwarding routes for a user."""
        user_handler_keys = [hk for hk in list(self.active_handlers.keys()) if hk.startswith(f"{user_id}_")]
        for hk in user_handler_keys:
            r_id = hk.split("_", 1)[1]
            await self.stop_route_forwarder(user_id, r_id)

    def is_route_active(self, user_id: int, route_id: str) -> bool:
        return f"{user_id}_{route_id}" in self.active_handlers

    def is_active(self, user_id: int) -> bool:
        """Checks if user has any active route client running."""
        return any(hk.startswith(f"{user_id}_") for hk in self.active_handlers.keys())

    async def restore_all_sessions(self):
        """Restores all active forwarding routes across all users after bot start/restart."""
        logger.info("Restoring saved forwarding routes on startup...")
        active_items = await db.get_all_active_routes()

        restored_count = 0
        for item in active_items:
            u_id = item["user_id"]
            r_id = item["route_id"]
            acc_id = item["account_id"]
            sess_str = item["session_string"]
            source = item["source_chat"]
            dest = item["destination_chat"]
            filters_list = item.get("media_filters")

            try:
                await self.start_route_forwarder(
                    user_id=u_id,
                    route_id=r_id,
                    session_string=sess_str,
                    source_chat=source,
                    destination_chat=dest,
                    account_id=acc_id,
                    media_filters=filters_list
                )
                restored_count += 1
            except Exception as e:
                logger.error(f"Failed to restore route '{r_id}' for user {u_id}: {e}")
                await db.set_route_status(u_id, r_id, False)

        logger.info(f"Restored {restored_count}/{len(active_items)} active forwarding routes successfully.")


# Global Pyrogram Manager instance
pyrogram_manager = PyrogramManager()
