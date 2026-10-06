import logging
import os

import telebot
from dotenv import load_dotenv
from telebot import apihelper, types

import storage
from timeweb_api import AuthError, TimewebClient, TimewebError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("TIMEWEB_APP_KEY")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL")
if not BOT_TOKEN or not APP_KEY:
    raise SystemExit("Заполните BOT_TOKEN и TIMEWEB_APP_KEY в файле .env")

# Если хостинг не пускает к api.telegram.org, запросы идут через прокси
if TELEGRAM_API_URL:
    apihelper.API_URL = TELEGRAM_API_URL

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
client = TimewebClient(APP_KEY)
storage.init_db()

BTN_AUTH = "🔑 Авторизация"
BTN_LOGOUT = "🚴‍♂️ Выйти"
BTN_SITES = "🌍 Сайты"
BTN_DOMAINS = "🎯 Домены"
BTN_BALANCE = "💎 Баланс"


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(BTN_AUTH, BTN_LOGOUT)
    markup.row(BTN_SITES, BTN_DOMAINS)
    markup.row(BTN_BALANCE)
    return markup


def send(chat_id, text):
    bot.send_message(chat_id, text, reply_markup=main_menu())


def safe_delete(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as exc:
        logger.warning("Не удалось удалить сообщение: %s", exc)


def call_api(message, func):
    """Вызывает func(login, token) с обработкой ошибок. None при неудаче."""
    chat_id = message.chat.id
    user = storage.get_user(chat_id)
    if not user:
        send(chat_id, "Сначала авторизуйтесь: нажмите «" + BTN_AUTH + "».")
        return None
    login, token = user
    try:
        return func(login, token)
    except AuthError:
        logger.warning("Токен отклонён для %s", login)
        storage.delete_user(chat_id)
        send(chat_id, "Сессия недействительна. Авторизуйтесь заново.")
    except TimewebError as exc:
        send(chat_id, "⛔ " + str(exc))
    except Exception:
        logger.exception("Непредвиденная ошибка")
        send(chat_id, "⛔ Внутренняя ошибка, попробуйте позже.")
    return None


def format_sites(sites):
    if not sites:
        return "На аккаунте нет сайтов."
    blocks = []
    for site in sites:
        domains = ", ".join(site.get("domains") or []) or "—"
        blocks.append(
            "ID: {}\nПапка: {}\nДомены: {}\nPHP: {}, Python: {}".format(
                site.get("id"),
                site.get("directory"),
                domains,
                site.get("php_version", "—"),
                site.get("python_version", "—"),
            )
        )
    return "\n\n".join(blocks)


def collect_domains(sites):
    domains = set()
    for site in sites or []:
        domains.update(site.get("domains") or [])
    return sorted(domains)


@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    storage.clear_pending(message.chat.id)
    send(
        message.chat.id,
        "Привет! Я показываю данные вашего аккаунта на хостинге Timeweb.\n"
        "Для начала нажмите «" + BTN_AUTH + "».",
    )


@bot.message_handler(func=lambda m: m.text == BTN_AUTH)
def handle_auth_start(message):
    storage.set_pending(message.chat.id, "login")
    bot.send_message(
        message.chat.id,
        "Введите логин аккаунта (например, cn12345):",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@bot.message_handler(func=lambda m: m.text == BTN_LOGOUT)
def handle_logout(message):
    storage.clear_pending(message.chat.id)
    storage.delete_user(message.chat.id)
    send(message.chat.id, "Вы вышли из аккаунта.")


@bot.message_handler(func=lambda m: m.text == BTN_BALANCE)
def handle_balance(message):
    data = call_api(message, client.get_balance)
    if data is None:
        return
    currency = data.get("currency", "")
    text = (
        "Баланс: {:.2f} {}\n"
        "Доступно: {:.2f} {}\n"
        "Стоимость тарифа: {:.2f} {} в месяц"
    ).format(
        float(data.get("balance", 0)), currency,
        float(data.get("available_balance", 0)), currency,
        float(data.get("monthly_cost", 0)), currency,
    )
    send(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == BTN_SITES)
def handle_sites(message):
    sites = call_api(message, client.get_sites)
    if sites is None:
        return
    send(message.chat.id, format_sites(sites))


@bot.message_handler(func=lambda m: m.text == BTN_DOMAINS)
def handle_domains(message):
    sites = call_api(message, client.get_sites)
    if sites is None:
        return
    domains = collect_domains(sites)
    if not domains:
        send(message.chat.id, "Доменов не найдено.")
    else:
        send(message.chat.id, "Домены:\n" + "\n".join(domains))


@bot.message_handler(
    func=lambda m: storage.get_pending(m.chat.id) is not None,
    content_types=["text"],
)
def handle_auth_input(message):
    chat_id = message.chat.id
    state = storage.get_pending(chat_id)
    if state is None:
        return
    step, login = state
    text = (message.text or "").strip()

    if step == "login":
        storage.set_pending(chat_id, "password", text)
        bot.send_message(
            chat_id, "Теперь введите пароль. Я сразу удалю это сообщение."
        )
        return

    safe_delete(message)
    storage.clear_pending(chat_id)
    try:
        token = client.login(login, text)
    except AuthError:
        send(
            chat_id,
            "Не удалось войти. Проверьте логин и пароль, отключите "
            "подтверждение входа по SMS. Возможно, сервер запросил капчу, "
            "тогда попробуйте через 15-30 минут.",
        )
        return
    except TimewebError as exc:
        send(chat_id, "⛔ " + str(exc))
        return
    except Exception:
        logger.exception("Ошибка при авторизации")
        send(chat_id, "⛔ Внутренняя ошибка, попробуйте позже.")
        return

    storage.save_user(chat_id, login, token)
    logger.info("Пользователь %s авторизован", login)
    send(chat_id, "Готово, вы авторизованы как " + login + ".")


@bot.message_handler(func=lambda m: True)
def handle_other(message):
    send(message.chat.id, "Выберите действие в меню.")


if __name__ == "__main__":
    # Для локального запуска: webhook и polling несовместимы
    bot.remove_webhook()
    logger.info("Бот запущен (polling)")
    bot.infinity_polling()