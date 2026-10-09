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

# Initialize the Telegram Application (v20+)
ptb_app = Application.builder().token(TOKEN).build()


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


# Register Handlers
ptb_app.add_handler(CommandHandler("start", welcome))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie))
ptb_app.add_handler(CallbackQueryHandler(movie_result))


async def process_telegram_update(update_data):
    """Initializes and processes update cleanly for PTB v20+ serverless."""
    async with ptb_app:
        update = Update.de_json(update_data, ptb_app.bot)
        await ptb_app.process_update(update)


# Catch all incoming webhook paths so Vercel rewrites never 404
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
        async with ptb_app:
            return await ptb_app.bot.set_webhook(webhook_url)

    success = asyncio.run(_set())
    if success:
        return f"webhook setup ok -> {webhook_url}"
    return "webhook setup failed"


if __name__ == "__main__":
    app.run(port=5000)
