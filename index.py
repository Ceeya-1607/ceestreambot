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

# Kept hardcoded values as requested
TOKEN = "8640151446:AAHV_9j62tKvI2qtPwp05qTEyagjq0gXErk"
URL = "https://ceestreambot.vercel.app"

app = Flask(__name__)

# Initialize the Telegram Application (v20+ approach)
ptb_app = Application.builder().token(TOKEN).build()


async def welcome(update: Update, context) -> None:
    await update.message.reply_text(
        "Hello Dear, Welcome to Project - Name.\n"
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

    # Split message if it exceeds Telegram's 4096 character limit
    if len(caption) > 4095:
        for x in range(0, len(caption), 4095):
            await query.message.reply_text(text=caption[x : x + 4095])
    else:
        await query.message.reply_text(text=caption)


# Register Handlers
ptb_app.add_handler(CommandHandler("start", welcome))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie))
ptb_app.add_handler(CallbackQueryHandler(movie_result))


@app.route("/")
def index():
    return "Hello World!"


@app.route(f"/{TOKEN}", methods=["GET", "POST"])
def respond():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), ptb_app.bot)
        asyncio.run(ptb_app.process_update(update))
    return "ok"


@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    webhook_url = f"{URL}/{TOKEN}"
    
    async def _set():
        return await ptb_app.bot.set_webhook(webhook_url)

    success = asyncio.run(_set())
    if success:
        return "webhook setup ok"
    return "webhook setup failed"


if __name__ == "__main__":
    app.run(port=5000)
