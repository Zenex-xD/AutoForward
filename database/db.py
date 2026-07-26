import os
import aiosqlite
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH
from utils.logger import logger

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initializes database schema if it doesn't exist."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_configs (
                    user_id INTEGER PRIMARY KEY,
                    session_string TEXT,
                    account_name TEXT,
                    phone_number TEXT,
                    source_chat TEXT,
                    destination_chat TEXT,
                    is_forwarding INTEGER DEFAULT 0,
                    forwarded_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
            logger.info("SQLite Database initialized successfully.")

    async def get_user_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves user configuration by user_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_configs WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def save_session(self, user_id: int, session_string: str, account_name: str, phone_number: str):
        """Saves or updates user Pyrogram string session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_configs (user_id, session_string, account_name, phone_number, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    session_string = excluded.session_string,
                    account_name = excluded.account_name,
                    phone_number = excluded.phone_number,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, session_string, account_name, phone_number))
            await db.commit()

    async def save_source(self, user_id: int, source_chat: str):
        """Saves source chat configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_configs (user_id, source_chat, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    source_chat = excluded.source_chat,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, source_chat))
            await db.commit()

    async def save_destination(self, user_id: int, destination_chat: str):
        """Saves destination chat configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_configs (user_id, destination_chat, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    destination_chat = excluded.destination_chat,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, destination_chat))
            await db.commit()

    async def set_forwarding_status(self, user_id: int, status: bool):
        """Enables (1) or disables (0) auto forward."""
        val = 1 if status else 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_configs SET is_forwarding = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (val, user_id)
            )
            await db.commit()

    async def increment_forward_count(self, user_id: int):
        """Increments the count of forwarded messages for the user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_configs SET forwarded_count = forwarded_count + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def reset_user_config(self, user_id: int):
        """Deletes user configuration from database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_configs WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_active_forwarders(self) -> List[Dict[str, Any]]:
        """Retrieves all users who have active auto-forwarding enabled."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_configs WHERE is_forwarding = 1 AND session_string IS NOT NULL AND source_chat IS NOT NULL AND destination_chat IS NOT NULL"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

# Global database instance
db = Database()
