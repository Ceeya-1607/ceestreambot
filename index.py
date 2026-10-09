import os
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from scraper import search_movies, get_movie

TOKEN = "8640151446:AAHV_9j62tKvI2qtPwp05qTYeagjq0gXErk"
URL = "https://ceestreambot.vercel.app"

app = Flask(__name__)


async def welcome(update: Update, context) -> None:
    if update.message:
        await update.message.reply_text(
            "Hello Dear, Welcome to CeeStream Bot.\n"
            "🔥 Download Your Favourite Movies, Webseries & TV-Shows For 🎁 Free And 🥳 Enjoy it.\n"
            "👇 Enter Keyword Below 👇"
        )


async def find_movie(update: Update, context) -> None:
    if not update.message or not update.message.text:
        return

    query = update.message.text
    search_results = await update.message.reply_text("🔍 Searching, please wait...")
    
    try:
        movies_list = search_movies(query)

        if movies_list:
            keyboards = [
                # Trim title to 50 chars so inline button fits Telegram UI comfortably
                [InlineKeyboardButton(movie["title"][:50], callback_data=movie["id"])]
                for movie in movies_list
            ]
            reply_markup = InlineKeyboardMarkup(keyboards)
            await search_results.edit_text(f"🎬 Results for '{query}':", reply_markup=reply_markup)
        else:
            await search_results.edit_text(
                "Sorry 🙏, No result found!\nPlease check the spelling or try another title."
            )
    except Exception as e:
        print(f"[find_movie error]: {e}")
        await search_results.edit_text("⚠️ An error occurred while searching. Please try again.")


async def movie_result(update: Update, context) -> None:
    query = update.callback_query
    if not query:
        return

    # Acknowledge the button press so the loading spinner stops immediately
    await query.answer("Fetching download links...")
    
    try:
        s = get_movie(query.data)
        title = s.get("title", "Movie Details")
        img_url = s.get("img")
        links = s.get("links", {})

        # Build download link text
        if isinstance(links, dict) and links:
            link_text = "".join([f"🎬 {btn_name}\n👉 {url}\n\n" for btn_name, url in links.items()])
            caption = f"🎬 {title}\n\n📥 Direct Download Links:\n\n{link_text}"
        else:
            caption = f"🎬 {title}\n\n⚠️ No direct links found on the page."

        # 1. Attempt to send with photo directly via URL (no BytesIO download bottleneck)
        photo_sent = False
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            try:
                # Telegram photo captions are limited to 1024 characters
                photo_caption = caption[:1000] if len(caption) > 1000 else caption
                await query.message.reply_photo(photo=img_url, caption=photo_caption)
                photo_sent = True
                
                # If there is remaining text that didn't fit the photo caption, send as message
                if len(caption) > 1000:
                    await query.message.reply_text(caption[1000:])
            except Exception as photo_err:
                print(f"[Photo send failed, falling back to text]: {photo_err}")

        # 2. Fallback to clean text message if photo fails or doesn't exist
        if not photo_sent:
            if len(caption) > 4095:
                for x in range(0, len(caption), 4095):
                    await query.message.reply_text(text=caption[x : x + 4095])
            else:
                await query.message.reply_text(text=caption)

    except Exception as e:
        print(f"[movie_result error]: {e}")
        await query.message.reply_text("⚠️ Failed to load movie details. Please try another link.")


def get_application() -> Application:
    """Builds a fresh Application instance bound to the current event loop."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", welcome))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie))
    application.add_handler(CallbackQueryHandler(movie_result))
    return application


async def process_telegram_update(update_data):
    """Processes update within an isolated Application lifecycle."""
    application = get_application()
    async with application:
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)


# Catch-all routes for Vercel webhooks
@app.route("/", methods=["GET", "POST"])
@app.route("/api/index.py", methods=["GET", "POST"])
@app.route(f"/{TOKEN}", methods=["GET", "POST"])
def respond():
    if request.method == "POST":
        payload = request.get_json(force=True, silent=True)
        if payload:
            asyncio.run(process_telegram_update(payload))
            return "ok"
    return "Bot is running!"


@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    webhook_url = f"{URL}/{TOKEN}"

    async def _set():
        application = get_application()
        async with application:
            return await application.bot.set_webhook(webhook_url)

    success = asyncio.run(_set())
    if success:
        return f"webhook setup ok -> {webhook_url}"
    return "webhook setup failed"


if __name__ == "__main__":
    app.run(port=5000)
