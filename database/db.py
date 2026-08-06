import os
import json
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

DEFAULT_MEDIA_FILTERS = ["text", "photo", "video", "document", "audio", "voice", "sticker", "animation", "poll"]

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
                    failed_count INTEGER DEFAULT 0,
                    accounts_json TEXT DEFAULT '[]',
                    routes_json TEXT DEFAULT '[]',
                    logs_json TEXT DEFAULT '[]',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add missing columns if upgrading existing SQLite schema
            cursor = await db.execute("PRAGMA table_info(user_configs)")
            columns = [row[1] for row in await cursor.fetchall()]

            if "accounts_json" not in columns:
                await db.execute("ALTER TABLE user_configs ADD COLUMN accounts_json TEXT DEFAULT '[]'")
            if "routes_json" not in columns:
                await db.execute("ALTER TABLE user_configs ADD COLUMN routes_json TEXT DEFAULT '[]'")
            if "logs_json" not in columns:
                await db.execute("ALTER TABLE user_configs ADD COLUMN logs_json TEXT DEFAULT '[]'")
            if "failed_count" not in columns:
                await db.execute("ALTER TABLE user_configs ADD COLUMN failed_count INTEGER DEFAULT 0")

            await db.commit()
            logger.info("SQLite Database initialized with full schema support.")

    # Helper to clean and format user object with defaults and legacy migration
    def _normalize_user_doc(self, doc: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        if not doc:
            doc = {"user_id": user_id}

        accounts = doc.get("accounts")
        if accounts is None:
            accounts_json = doc.get("accounts_json")
            if accounts_json and isinstance(accounts_json, str):
                try:
                    accounts = json.loads(accounts_json)
                except Exception:
                    accounts = []
            else:
                accounts = []

        # Legacy single session migration
        if not accounts and doc.get("session_string"):
            accounts = [{
                "account_id": "acc_1",
                "session_string": doc["session_string"],
                "account_name": doc.get("account_name", "Primary Account"),
                "phone_number": doc.get("phone_number", "N/A")
            }]

        routes = doc.get("routes")
        if routes is None:
            routes_json = doc.get("routes_json")
            if routes_json and isinstance(routes_json, str):
                try:
                    routes = json.loads(routes_json)
                except Exception:
                    routes = []
            else:
                routes = []

        # Legacy single route migration
        if not routes and (doc.get("source_chat") or doc.get("destination_chat")):
            default_acc_id = accounts[0]["account_id"] if accounts else "acc_1"
            routes = [{
                "route_id": "route_1",
                "route_name": "Default Route",
                "account_id": default_acc_id,
                "source_chat": doc.get("source_chat", ""),
                "destination_chat": doc.get("destination_chat", ""),
                "media_filters": DEFAULT_MEDIA_FILTERS.copy(),
                "is_active": doc.get("is_forwarding", 0)
            }]

        logs = doc.get("logs")
        if logs is None:
            logs_json = doc.get("logs_json")
            if logs_json and isinstance(logs_json, str):
                try:
                    logs = json.loads(logs_json)
                except Exception:
                    logs = []
            else:
                logs = []

        doc["accounts"] = accounts
        doc["routes"] = routes
        doc["logs"] = logs
        doc.setdefault("forwarded_count", 0)
        doc.setdefault("failed_count", 0)
        doc.setdefault("is_forwarding", 1 if any(r.get("is_active") for r in routes) else 0)

        # Primary account & primary route getters for legacy code compatibility
        if accounts:
            doc["session_string"] = accounts[0]["session_string"]
            doc["account_name"] = accounts[0]["account_name"]
            doc["phone_number"] = accounts[0]["phone_number"]
        if routes:
            doc["source_chat"] = routes[0]["source_chat"]
            doc["destination_chat"] = routes[0]["destination_chat"]

        return doc

    async def get_user_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves user configuration by user_id."""
        if self.use_mongo:
            doc = await self.collection.find_one({"user_id": user_id}, {"_id": 0})
            if not doc:
                return None
            return self._normalize_user_doc(doc, user_id)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM user_configs WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._normalize_user_doc(dict(row), user_id)
                return None

    # --- ACCOUNTS MANAGEMENT ---
    async def get_user_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        config = await self.get_user_config(user_id)
        return config["accounts"] if config else []

    async def save_session(self, user_id: int, session_string: str, account_name: str, phone_number: str, account_id: Optional[str] = None):
        """Saves or updates a user Pyrogram session account."""
        config = await self.get_user_config(user_id) or {"user_id": user_id, "accounts": [], "routes": [], "logs": []}
        accounts = config.get("accounts", [])

        if not account_id:
            account_id = f"acc_{len(accounts) + 1}"

        existing_acc = next((a for a in accounts if a["account_id"] == account_id or a["phone_number"] == phone_number), None)
        if existing_acc:
            existing_acc["session_string"] = session_string
            existing_acc["account_name"] = account_name
            existing_acc["phone_number"] = phone_number
        else:
            accounts.append({
                "account_id": account_id,
                "session_string": session_string,
                "account_name": account_name,
                "phone_number": phone_number
            })

        config["accounts"] = accounts
        await self._save_user_config(user_id, config)

    async def delete_account(self, user_id: int, account_id: str):
        config = await self.get_user_config(user_id)
        if not config:
            return
        config["accounts"] = [a for a in config.get("accounts", []) if a["account_id"] != account_id]
        # Also remove routes linked to this account
        config["routes"] = [r for r in config.get("routes", []) if r.get("account_id") != account_id]
        await self._save_user_config(user_id, config)

    # --- ROUTES MANAGEMENT ---
    async def get_user_routes(self, user_id: int) -> List[Dict[str, Any]]:
        config = await self.get_user_config(user_id)
        return config["routes"] if config else []

    async def get_route(self, user_id: int, route_id: str) -> Optional[Dict[str, Any]]:
        routes = await self.get_user_routes(user_id)
        return next((r for r in routes if r["route_id"] == route_id), None)

    async def save_route(self, user_id: int, route_id: str, source_chat: str, destination_chat: str, account_id: Optional[str] = None, route_name: Optional[str] = None):
        config = await self.get_user_config(user_id) or {"user_id": user_id, "accounts": [], "routes": [], "logs": []}
        routes = config.get("routes", [])
        accounts = config.get("accounts", [])

        if not account_id:
            account_id = accounts[0]["account_id"] if accounts else "acc_1"

        existing_route = next((r for r in routes if r["route_id"] == route_id), None)
        if existing_route:
            existing_route["source_chat"] = source_chat
            existing_route["destination_chat"] = destination_chat
            if account_id:
                existing_route["account_id"] = account_id
            if route_name:
                existing_route["route_name"] = route_name
        else:
            r_name = route_name or f"Route {len(routes) + 1}"
            routes.append({
                "route_id": route_id,
                "route_name": r_name,
                "account_id": account_id,
                "source_chat": source_chat,
                "destination_chat": destination_chat,
                "media_filters": DEFAULT_MEDIA_FILTERS.copy(),
                "is_active": 0
            })

        config["routes"] = routes
        await self._save_user_config(user_id, config)

    async def save_source(self, user_id: int, source_chat: str, route_id: str = "route_1"):
        """Saves source chat for a specific route."""
        config = await self.get_user_config(user_id) or {"user_id": user_id, "accounts": [], "routes": [], "logs": []}
        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)

        if route:
            route["source_chat"] = source_chat
        else:
            default_acc = config["accounts"][0]["account_id"] if config.get("accounts") else "acc_1"
            routes.append({
                "route_id": route_id,
                "route_name": "Default Route",
                "account_id": default_acc,
                "source_chat": source_chat,
                "destination_chat": "",
                "media_filters": DEFAULT_MEDIA_FILTERS.copy(),
                "is_active": 0
            })

        config["routes"] = routes
        await self._save_user_config(user_id, config)

    async def save_destination(self, user_id: int, destination_chat: str, route_id: str = "route_1"):
        """Saves destination chat for a specific route."""
        config = await self.get_user_config(user_id) or {"user_id": user_id, "accounts": [], "routes": [], "logs": []}
        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)

        if route:
            route["destination_chat"] = destination_chat
        else:
            default_acc = config["accounts"][0]["account_id"] if config.get("accounts") else "acc_1"
            routes.append({
                "route_id": route_id,
                "route_name": "Default Route",
                "account_id": default_acc,
                "source_chat": "",
                "destination_chat": destination_chat,
                "media_filters": DEFAULT_MEDIA_FILTERS.copy(),
                "is_active": 0
            })

        config["routes"] = routes
        await self._save_user_config(user_id, config)

    async def toggle_route_filter(self, user_id: int, route_id: str, media_type: str) -> List[str]:
        """Toggles a media filter on/off for a route."""
        config = await self.get_user_config(user_id)
        if not config:
            return DEFAULT_MEDIA_FILTERS.copy()

        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)
        if not route:
            return DEFAULT_MEDIA_FILTERS.copy()

        filters = route.get("media_filters", DEFAULT_MEDIA_FILTERS.copy())
        if media_type in filters:
            filters.remove(media_type)
        else:
            filters.append(media_type)

        route["media_filters"] = filters
        config["routes"] = routes
        await self._save_user_config(user_id, config)
        return filters

    async def set_route_status(self, user_id: int, route_id: str, is_active: bool):
        config = await self.get_user_config(user_id)
        if not config:
            return
        routes = config.get("routes", [])
        route = next((r for r in routes if r["route_id"] == route_id), None)
        if route:
            route["is_active"] = 1 if is_active else 0

        config["routes"] = routes
        config["is_forwarding"] = 1 if any(r.get("is_active") for r in routes) else 0
        await self._save_user_config(user_id, config)

    async def set_forwarding_status(self, user_id: int, status: bool, route_id: Optional[str] = None):
        """Sets forwarding status for all routes or a specific route."""
        config = await self.get_user_config(user_id)
        if not config:
            return
        routes = config.get("routes", [])
        val = 1 if status else 0

        for r in routes:
            if not route_id or r["route_id"] == route_id:
                r["is_active"] = val

        config["routes"] = routes
        config["is_forwarding"] = 1 if any(r.get("is_active") for r in routes) else 0
        await self._save_user_config(user_id, config)

    async def delete_route(self, user_id: int, route_id: str):
        config = await self.get_user_config(user_id)
        if not config:
            return
        config["routes"] = [r for r in config.get("routes", []) if r["route_id"] != route_id]
        await self._save_user_config(user_id, config)

    # --- STATS & LOGGING ---
    async def log_forward_event(self, user_id: int, route_id: str, status: str, details: str, source_chat: str = "", dest_chat: str = ""):
        """Logs a forward success/failure event and updates counters."""
        config = await self.get_user_config(user_id) or {"user_id": user_id, "accounts": [], "routes": [], "logs": []}
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if status == "success":
            config["forwarded_count"] = config.get("forwarded_count", 0) + 1
        elif status == "failed":
            config["failed_count"] = config.get("failed_count", 0) + 1

        logs = config.get("logs", [])
        logs.insert(0, {
            "timestamp": now_iso,
            "status": status,
            "route_id": route_id,
            "source": source_chat,
            "dest": dest_chat,
            "details": details
        })
        # Keep recent 20 logs
        config["logs"] = logs[:20]

        await self._save_user_config(user_id, config)

    async def increment_forward_count(self, user_id: int, route_id: str = "route_1"):
        await self.log_forward_event(user_id, route_id, "success", "Message forwarded successfully")

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        config = await self.get_user_config(user_id)
        if not config:
            return {
                "total_forwarded": 0,
                "total_failed": 0,
                "active_routes_count": 0,
                "total_accounts_count": 0,
                "logs": []
            }

        routes = config.get("routes", [])
        accounts = config.get("accounts", [])
        active_routes = [r for r in routes if r.get("is_active") == 1]

        return {
            "total_forwarded": config.get("forwarded_count", 0),
            "total_failed": config.get("failed_count", 0),
            "active_routes_count": len(active_routes),
            "total_routes_count": len(routes),
            "total_accounts_count": len(accounts),
            "logs": config.get("logs", [])
        }

    async def _save_user_config(self, user_id: int, config: Dict[str, Any]):
        """Internal helper to save normalized user config to MongoDB or SQLite."""
        now_iso = datetime.now(timezone.utc).isoformat()
        accounts = config.get("accounts", [])
        routes = config.get("routes", [])
        logs = config.get("logs", [])

        primary_sess = accounts[0]["session_string"] if accounts else ""
        primary_acc_name = accounts[0]["account_name"] if accounts else ""
        primary_phone = accounts[0]["phone_number"] if accounts else ""

        primary_src = routes[0]["source_chat"] if routes else ""
        primary_dst = routes[0]["destination_chat"] if routes else ""
        is_fwd = 1 if any(r.get("is_active") for r in routes) else 0

        if self.use_mongo:
            doc_data = {
                "user_id": user_id,
                "session_string": primary_sess,
                "account_name": primary_acc_name,
                "phone_number": primary_phone,
                "source_chat": primary_src,
                "destination_chat": primary_dst,
                "is_forwarding": is_fwd,
                "forwarded_count": config.get("forwarded_count", 0),
                "failed_count": config.get("failed_count", 0),
                "accounts": accounts,
                "routes": routes,
                "logs": logs,
                "updated_at": now_iso
            }
            await self.collection.update_one({"user_id": user_id}, {"$set": doc_data}, upsert=True)
            return

        # SQLite update
        accounts_json = json.dumps(accounts)
        routes_json = json.dumps(routes)
        logs_json = json.dumps(logs)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_configs (
                    user_id, session_string, account_name, phone_number,
                    source_chat, destination_chat, is_forwarding,
                    forwarded_count, failed_count, accounts_json, routes_json, logs_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    session_string = excluded.session_string,
                    account_name = excluded.account_name,
                    phone_number = excluded.phone_number,
                    source_chat = excluded.source_chat,
                    destination_chat = excluded.destination_chat,
                    is_forwarding = excluded.is_forwarding,
                    forwarded_count = excluded.forwarded_count,
                    failed_count = excluded.failed_count,
                    accounts_json = excluded.accounts_json,
                    routes_json = excluded.routes_json,
                    logs_json = excluded.logs_json,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                user_id, primary_sess, primary_acc_name, primary_phone,
                primary_src, primary_dst, is_fwd,
                config.get("forwarded_count", 0), config.get("failed_count", 0),
                accounts_json, routes_json, logs_json
            ))
            await db.commit()

    async def reset_user_config(self, user_id: int):
        """Deletes user configuration from database."""
        if self.use_mongo:
            await self.collection.delete_one({"user_id": user_id})
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_configs WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_all_active_routes(self) -> List[Dict[str, Any]]:
        """Retrieves all active routes across all users for system startup restore."""
        active_items = []
        if self.use_mongo:
            cursor = self.collection.find({})
            docs = await cursor.to_list(length=None)
            for raw_doc in docs:
                doc = self._normalize_user_doc(raw_doc, raw_doc["user_id"])
                accounts_map = {a["account_id"]: a for a in doc.get("accounts", [])}
                for r in doc.get("routes", []):
                    if r.get("is_active") == 1 and r.get("source_chat") and r.get("destination_chat"):
                        acc = accounts_map.get(r.get("account_id")) or (doc["accounts"][0] if doc.get("accounts") else None)
                        if acc and acc.get("session_string"):
                            active_items.append({
                                "user_id": doc["user_id"],
                                "route_id": r["route_id"],
                                "route_name": r.get("route_name", "Route"),
                                "account_id": acc["account_id"],
                                "session_string": acc["session_string"],
                                "source_chat": r["source_chat"],
                                "destination_chat": r["destination_chat"],
                                "media_filters": r.get("media_filters", DEFAULT_MEDIA_FILTERS.copy())
                            })
            return active_items

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM user_configs") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    doc = self._normalize_user_doc(dict(row), row["user_id"])
                    accounts_map = {a["account_id"]: a for a in doc.get("accounts", [])}
                    for r in doc.get("routes", []):
                        if r.get("is_active") == 1 and r.get("source_chat") and r.get("destination_chat"):
                            acc = accounts_map.get(r.get("account_id")) or (doc["accounts"][0] if doc.get("accounts") else None)
                            if acc and acc.get("session_string"):
                                active_items.append({
                                    "user_id": doc["user_id"],
                                    "route_id": r["route_id"],
                                    "route_name": r.get("route_name", "Route"),
                                    "account_id": acc["account_id"],
                                    "session_string": acc["session_string"],
                                    "source_chat": r["source_chat"],
                                    "destination_chat": r["destination_chat"],
                                    "media_filters": r.get("media_filters", DEFAULT_MEDIA_FILTERS.copy())
                                })
                return active_items


# Global database instance
db = Database()
