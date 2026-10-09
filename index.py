import os
import asyncio
from io import BytesIO
from flask import Flask, request
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from scraper import search_movies, get_movie

TOKEN = "8640151446:AAHV_9j62tKvI2qtPwp05qTEyagjq0gXErk"
URL = "https://ceestreambot.vercel.app"

app = Flask(__name__)


async def welcome(update: Update, context) -> None:
    await update.message.reply_text(
        "Hello Dear, Welcome to CeeStream Bot.\n"
        "🔥 Download Your Favourite Movies, Webseries & TV-Shows For 🎁 Free And 🥳 Enjoy it.\n"
        "👇 Enter Keyword Below 👇"
    )


async def find_movie(update: Update, context) -> None:
    search_results = await update.message.reply_text("Processing...")
    query = update.message.text
    movies_list = search_movies(query)

    if movies_list:
        keyboards = [
            [InlineKeyboardButton(movie["title"], callback_data=movie["id"])]
            for movie in movies_list
        ]
        reply_markup = InlineKeyboardMarkup(keyboards)
        await search_results.edit_text("Results", reply_markup=reply_markup)
    else:
        await search_results.edit_text(
            "Sorry 🙏, No result found!\nPlease retry Or contact admin."
        )


async def movie_result(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    
    s = get_movie(query.data)
    response = requests.get(s["img"])
    img = BytesIO(response.content)

    await query.message.reply_photo(
        photo=img, 
        caption=f"🎬 {s['title']}"
    )

    links = s["links"]
    link_text = "".join([f"🎬 {i}\n{link}\n\n" for i, link in links.items()]) if isinstance(links, dict) else ""
    caption = f"Direct Download Links:\n\n{link_text}"

    if len(caption) > 4095:
        for x in range(0, len(caption), 4095):
            await query.message.reply_text(text=caption[x : x + 4095])
    else:
        await query.message.reply_text(text=caption)


def get_application() -> Application:
    """Builds a fresh Application instance bound to the current event loop."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", welcome))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie))
    application.add_handler(CallbackQueryHandler(movie_result))
    return application


async def process_telegram_update(update_data):
    """Processes update within a clean, isolated Application lifecycle."""
    application = get_application()
    async with application:
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)


# Catch-all routes for webhooks
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
