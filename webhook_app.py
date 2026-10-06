import os

import telebot
from flask import Flask, abort, request

from bot import bot, logger

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

app = Flask(__name__)


@app.route("/")
def index():
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header != WEBHOOK_SECRET:
            abort(403)
    try:
        update = telebot.types.Update.de_json(
            request.get_data().decode("utf-8")
        )
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Ошибка обработки обновления")
    return "", 200