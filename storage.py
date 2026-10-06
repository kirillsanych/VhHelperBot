import os
import sqlite3
from contextlib import closing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot.db")


def _connect():
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db():
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "chat_id INTEGER PRIMARY KEY, "
                "login TEXT NOT NULL, "
                "token TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pending ("
                "chat_id INTEGER PRIMARY KEY, "
                "step TEXT NOT NULL, "
                "login TEXT)"
            )


def save_user(chat_id, login, token):
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (chat_id, login, token) "
                "VALUES (?, ?, ?)",
                (chat_id, login, token),
            )


def get_user(chat_id):
    """Возвращает (login, token) или None."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT login, token FROM users WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return row


def delete_user(chat_id):
    with closing(_connect()) as conn:
        with conn:
            conn.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))


def set_pending(chat_id, step, login=None):
    """Запоминает, на каком шаге авторизации находится пользователь."""
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending (chat_id, step, login) "
                "VALUES (?, ?, ?)",
                (chat_id, step, login),
            )


def get_pending(chat_id):
    """Возвращает (step, login) или None."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT step, login FROM pending WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return row


def clear_pending(chat_id):
    with closing(_connect()) as conn:
        with conn:
            conn.execute("DELETE FROM pending WHERE chat_id = ?", (chat_id,))