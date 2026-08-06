import os
import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH, MONGO_URI, MONGO_DB_NAME
from utils.logger import logger

# Try importing Motor for MongoDB support
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False


class Database:
    def __init__(self, db_path: str = DATABASE_PATH, mongo_uri: str = MONGO_URI, mongo_db_name: str = MONGO_DB_NAME):
        self.db_path = db_path
        self.mongo_uri = mongo_uri
        self.mongo_db_name = mongo_db_name
        self.use_mongo = bool(self.mongo_uri and MOTOR_AVAILABLE)
        self.mongo_client = None
        self.mongo_db = None
        self.collection = None

    async def init_db(self):
        """Initializes MongoDB or SQLite database depending on MONGO_URI availability."""
        if self.use_mongo:
            try:
                self.mongo_client = AsyncIOMotorClient(self.mongo_uri)
                self.mongo_db = self.mongo_client[self.mongo_db_name]
                self.collection = self.mongo_db["user_configs"]
                # Ensure unique index on user_id
                await self.collection.create_index("user_id", unique=True)
                logger.info(f"MongoDB connected successfully to database '{self.mongo_db_name}'.")
                return
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB ({e}). Falling back to SQLite.")
                self.use_mongo = False

        # SQLite fallback if MONGO_URI is not set or failed
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

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
        if self.use_mongo:
            doc = await self.collection.find_one({"user_id": user_id}, {"_id": 0})
            if doc:
                doc.setdefault("is_forwarding", 0)
                doc.setdefault("forwarded_count", 0)
            return doc

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
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_mongo:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "session_string": session_string,
                        "account_name": account_name,
                        "phone_number": phone_number,
                        "updated_at": now_iso
                    }
                },
                upsert=True
            )
            return

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
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_mongo:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "source_chat": source_chat,
                        "updated_at": now_iso
                    }
                },
                upsert=True
            )
            return

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
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_mongo:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "destination_chat": destination_chat,
                        "updated_at": now_iso
                    }
                },
                upsert=True
            )
            return

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
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_mongo:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "is_forwarding": val,
                        "updated_at": now_iso
                    }
                }
            )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_configs SET is_forwarding = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (val, user_id)
            )
            await db.commit()

    async def increment_forward_count(self, user_id: int):
        """Increments the count of forwarded messages for the user."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_mongo:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"forwarded_count": 1},
                    "$set": {"updated_at": now_iso}
                }
            )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_configs SET forwarded_count = forwarded_count + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def reset_user_config(self, user_id: int):
        """Deletes user configuration from database."""
        if self.use_mongo:
            await self.collection.delete_one({"user_id": user_id})
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_configs WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_active_forwarders(self) -> List[Dict[str, Any]]:
        """Retrieves all users who have active auto-forwarding enabled."""
        if self.use_mongo:
            cursor = self.collection.find(
                {
                    "is_forwarding": 1,
                    "session_string": {"$ne": None},
                    "source_chat": {"$ne": None},
                    "destination_chat": {"$ne": None}
                },
                {"_id": 0}
            )
            docs = await cursor.to_list(length=None)
            for doc in docs:
                doc.setdefault("is_forwarding", 1)
                doc.setdefault("forwarded_count", 0)
            return docs

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_configs WHERE is_forwarding = 1 AND session_string IS NOT NULL AND source_chat IS NOT NULL AND destination_chat IS NOT NULL"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Global database instance
db = Database()
