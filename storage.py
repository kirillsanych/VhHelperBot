import sqlite3
from contextlib import closing

DB_PATH = "bot.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "chat_id INTEGER PRIMARY KEY, "
                "login TEXT NOT NULL, "
                "token TEXT NOT NULL)"
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