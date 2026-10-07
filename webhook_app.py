import os
import time

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
    started = time.time()
    if WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header != WEBHOOK_SECRET:
            logger.warning("Webhook: неверный секрет")
            abort(403)
    logger.info("Webhook: получен запрос")
    try:
        update = telebot.types.Update.de_json(
            request.get_data().decode("utf-8")
        )
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Ошибка обработки обновления")
    logger.info("Webhook: обработан за %.2f c", time.time() - started)
    return "", 200