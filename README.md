# SIS File Bot

A beginner-friendly Telegram file bot with free files, a premium file catalogue, and Telegram Stars payments.

## Environment variables
- `BOT_TOKEN`: Token from Telegram BotFather (keep secret).
- `ADMIN_ID`: Your numeric Telegram user ID (not your username).

## Add files as admin
Send a document to the bot with one of these captions:
- `/addfree My free PDF`
- `/addpremium My premium template pack | 50`

The premium price is in Telegram Stars. Digital goods sold inside Telegram bots must use Telegram Stars (XTR).

## Important hosting note
This version uses long polling. It needs a host that supports a continuously running worker/process. Many free web-service plans sleep or do not allow always-on background workers, so free 24/7 hosting is not guaranteed. Also, this starter stores the file catalogue in `files.json`; on hosts with ephemeral storage, data may be lost on redeploy/restart. Use persistent storage or a database before relying on it for a real business.

## Run locally on Windows
1. Install Python 3.11+ from https://www.python.org/downloads/
2. Open Command Prompt in this folder.
3. Run `py -m pip install -r requirements.txt`
4. Set environment variables in Command Prompt:
   `set BOT_TOKEN=YOUR_BOT_TOKEN`
   `set ADMIN_ID=YOUR_NUMERIC_TELEGRAM_USER_ID`
5. Run: `py bot.py`

Never commit your bot token to GitHub or share it in chat.
