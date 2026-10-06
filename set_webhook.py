import os
import sys

import telebot
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")
url = os.getenv("WEBHOOK_URL")
secret = os.getenv("WEBHOOK_SECRET") or None

if not token:
    sys.exit("Заполните BOT_TOKEN в файле .env")

bot = telebot.TeleBot(token)

if len(sys.argv) > 1 and sys.argv[1] == "delete":
    bot.remove_webhook()
    print("Webhook удалён")
else:
    if not url:
        sys.exit("Заполните WEBHOOK_URL в файле .env")
    bot.set_webhook(url=url, secret_token=secret)
    print("Webhook установлен:", url)