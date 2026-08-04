# 🚀 Telegram Auto-Forwarder Bot (Production Ready)

A lightweight, high-performance, modular Telegram Bot built with **Python 3.12**, **aiogram 3.x**, **Pyrogram 2.x**, and **SQLite** designed for 24/7 deployment on **Railway**.

---

## ⚡ Key Features

- **Built-in String Session Generator**: Generate Pyrogram v2 String Session directly inside Telegram using `/string` command (supports OTP & 2FA Password).
- **Automated Real-time Forwarding**: Forwards new messages immediately from source chat to destination chat.
- **Universal Media Support**:
  - Text & Formatted Messages
  - Photos & High-Res Images
  - Videos & Video Notes
  - Documents & Files
  - Audio & Voice Notes
  - Stickers & Animated Stickers
  - GIFs & Animations
- **Smart Copying & Fallback**:
  - Uses `copy_message()` for zero-bandwidth copying whenever allowed by Telegram.
  - Automatically falls back to Pyrogram download + re-upload when copy permissions are restricted.
- **Caption Preservation**: Maintains original text captions across all supported media.
- **Automatic Reconnection**: Automatically resumes all active user sessions after Railway restarts or container redeployments.
- **Memory Efficient**: Session strings are handled in-memory without disk overhead.
- **Secure Storage**: All configuration data is stored securely in local SQLite.

---

## 🛠 Tech Stack

- **Python 3.12**
- **aiogram 3.x** (Bot UI & Command Handler)
- **Pyrogram 2.x** (Userbot Engine & Listening Service)
- **TgCrypto** (Fast Encryption & Decryption for Pyrogram)
- **aiosqlite** (Asynchronous SQLite Database)
- **Docker** (Containerization)

---

## 📁 Project Structure

```
├── bot/                # Application handlers and controllers
├── handlers/           # aiogram 3 router handlers
│   ├── start.py        # /start and main menu
│   ├── login.py        # Session string login handler
│   ├── source.py       # Source chat setup
│   ├── destination.py  # Destination chat setup
│   ├── forward_control.py # Enable/Disable auto-forwarding
│   ├── status.py       # Bot status metrics
│   └── reset.py        # Configuration reset
├── services/           # Core background engines
│   ├── pyrogram_manager.py # In-memory Pyrogram client lifecycle manager
│   └── forwarder.py        # Copy / Download / Upload forwarding pipeline
├── database/           # Async SQLite database interface
│   └── db.py
├── utils/              # Helper utilities
│   ├── logger.py       # Standardized logger
│   ├── helpers.py      # Input parsing & inline keyboards
│   └── states.py       # aiogram FSM States
├── config.py           # Environment variable validator
├── main.py             # Bot initialization & entry point
├── Dockerfile          # Production Docker build specification
├── railway.json        # Railway deployment settings
├── requirements.txt    # Dependency list
├── .env.example        # Environment variable template
└── README.md           # Documentation
```

---

## ⚙️ Environment Variables

Create a `.env` file (or set environment variables in Railway):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram Bot Token from [@BotFather](https://t.me/BotFather) | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ` |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | `12345678` |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) | `0123456789abcdef0123456789abcdef` |
| `DATABASE_PATH` | Path for SQLite storage | `data/bot_database.db` |

---

## 🟣 Deploying to Heroku

### Option 1: 1-Click Deploy
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

1. Click the **Deploy to Heroku** button above or connect your GitHub repository in Heroku.
2. Fill in the required Config Vars:
   - `BOT_TOKEN` (from @BotFather)
   - `API_ID` (from my.telegram.org)
   - `API_HASH` (from my.telegram.org)
3. Click **Deploy App**.
4. Go to the **Resources** tab in your Heroku app dashboard, enable the `worker` or `web` dyno, and save!

---

## 🚂 Deploying to Railway

1. **Fork or Push** this repository to your GitHub account.
2. Log into [Railway](https://railway.app/).
3. Click **New Project** -> **Deploy from GitHub repo**.
4. Select your repository.
5. Go to **Variables** tab in Railway and add:
   - `BOT_TOKEN`
   - `API_ID`
   - `API_HASH`
6. Click **Deploy**. Railway will build the Docker container and start your bot 24/7!

---

## 📲 How to Use the Bot

1. Start a conversation with your bot in Telegram: `/start`
2. **🔐 Login Account**: Click and paste your Pyrogram String Session.
3. **📥 Set Source Chat**: Provide Chat ID (e.g. `-100123456789`), Username (e.g. `@mysource`), or Invite Link.
4. **📤 Set Destination Chat**: Provide Chat ID, Username, or Invite Link.
5. **▶️ Enable Auto Forward**: Click to start forwarding messages immediately!
6. **📊 Status**: View real-time connection status, chat setup, and total forwarded message count.
7. **⏸ Disable Auto Forward**: Stop message forwarding anytime.
8. **🗑 Reset Configuration**: Reset session and chat settings clean.

---

## 🔒 Security & Privacy

- String sessions and chat settings are stored locally in SQLite (`bot_database.db`).
- No credentials or sessions are transmitted to third parties.
