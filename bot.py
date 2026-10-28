import os
import json
import logging
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else None
DATA_FILE = Path(os.environ.get("DATA_FILE", "files.json"))

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.exception("Could not read files.json")
    return {"free": [], "premium": []}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def is_admin(user_id):
    return ADMIN_ID is not None and user_id == ADMIN_ID

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Free Files", callback_data="free")],
        [InlineKeyboardButton("💎 Premium Files", callback_data="premium")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Welcome to SIS File Bot! 📁\n\nChoose an option below.",
        reply_markup=main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    extra = "\n\nAdmin upload format:\nSend a document with caption:\n/addfree File title\nor\n/addpremium File title | 50"
    await update.effective_message.reply_text(
        "SIS File Bot helps you browse files.\n"
        "Free files are available to everyone. Premium files can be unlocked with Telegram Stars."
        + (extra if is_admin(update.effective_user.id) else "")
    )

async def show_files(query, category):
    data = load_data()
    items = data.get(category, [])
    if not items:
        await query.edit_message_text(
            "No files have been added here yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="menu")]])
        )
        return
    rows = []
    for i, item in enumerate(items):
        title = item.get("title", f"File {i+1}")
        if category == "free":
            rows.append([InlineKeyboardButton(f"📄 {title}", callback_data=f"getfree:{i}")])
        else:
            price = int(item.get("price", 50))
            rows.append([InlineKeyboardButton(f"💎 {title} — {price} Stars", callback_data=f"buy:{i}")])
    rows.append([InlineKeyboardButton("⬅️ Menu", callback_data="menu")])
    await query.edit_message_text(
        "📂 Free files:" if category == "free" else "💎 Premium files:",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text("SIS File Bot 📁\nChoose an option:", reply_markup=main_menu())
    elif data == "help":
        await query.edit_message_text(
            "Browse free files or unlock premium files with Telegram Stars.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="menu")]])
        )
    elif data in ("free", "premium"):
        await show_files(query, data)
    elif data.startswith("getfree:"):
        try:
            index = int(data.split(":", 1)[1])
            item = load_data()["free"][index]
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=item["file_id"],
                caption=item.get("title", "SIS File Bot file")
            )
        except (IndexError, KeyError, ValueError):
            await query.message.reply_text("Sorry, this file is unavailable.")
    elif data.startswith("buy:"):
        try:
            index = int(data.split(":", 1)[1])
            item = load_data()["premium"][index]
            price = int(item.get("price", 50))
            title = item.get("title", "Premium file")
            await context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=title[:32],
                description=f"Unlock: {title}"[:255],
                payload=f"premium:{index}",
                currency="XTR",
                prices=[LabeledPrice(label=title[:32], amount=price)],
                provider_token=""
            )
        except (IndexError, KeyError, ValueError):
            await query.message.reply_text("Sorry, this file is unavailable.")

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.effective_message.successful_payment
    payload = payment.invoice_payload
    if not payload.startswith("premium:"):
        return
    try:
        index = int(payload.split(":", 1)[1])
        item = load_data()["premium"][index]
        await update.effective_message.reply_text("Payment successful! Here is your file. ✅")
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=item["file_id"],
            caption=item.get("title", "Premium file")
        )
    except (IndexError, KeyError, ValueError):
        await update.effective_message.reply_text(
            "Payment received, but I couldn't find that file. Please contact the bot admin."
        )

async def admin_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if not user or not is_admin(user.id):
        return
    if not message.document:
        await message.reply_text("Please send a document with a caption.")
        return

    caption = (message.caption or "").strip()
    if caption.startswith("/addfree"):
        title = caption[len("/addfree"):].strip() or message.document.file_name or "Free file"
        category = "free"
        price = None
    elif caption.startswith("/addpremium"):
        args = caption[len("/addpremium"):].strip()
        if "|" not in args:
            await message.reply_text("Format: /addpremium File title | 50\nThe number is the price in Telegram Stars.")
            return
        title, price_text = [part.strip() for part in args.rsplit("|", 1)]
        if not price_text.isdigit() or int(price_text) < 1:
            await message.reply_text("Price must be a whole number of Stars, at least 1.")
            return
        price = int(price_text)
        category = "premium"
        title = title or message.document.file_name or "Premium file"
    else:
        await message.reply_text(
            "To add a file, send a document with one of these captions:\n"
            "/addfree File title\n"
            "/addpremium File title | 50"
        )
        return

    db = load_data()
    item = {"title": title, "file_id": message.document.file_id}
    if price is not None:
        item["price"] = price
    db.setdefault(category, []).append(item)
    save_data(db)
    await message.reply_text(f"Added to {category} files: {title}")

async def post_init(app: Application):
    await app.bot.set_my_commands([
        ("start", "Open the main menu"),
        ("help", "Help and instructions")
    ])

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set BOT_TOKEN as an environment variable.")
    if ADMIN_ID is None:
        raise RuntimeError("Set ADMIN_ID to your numeric Telegram user ID.")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.Document.ALL, admin_upload))
    log.info("SIS File Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
