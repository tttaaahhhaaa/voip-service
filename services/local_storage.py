import sqlite3
import json
import os
import threading
from datetime import datetime
from pathlib import Path


class LocalStorage:
    """Private local SQLite storage for SMS messages. Runs entirely on user's machine."""

    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = str(Path.home() / ".sms_receiver" / "messages.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL,
                sender TEXT,
                text TEXT,
                code TEXT,
                provider TEXT,
                received_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_message(self, number: str, sender: str, text: str, code: str = "", provider: str = ""):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO messages (number, sender, text, code, provider, received_at) VALUES (?, ?, ?, ?, ?, ?)",
            (number, sender, text, code, provider, datetime.utcnow().isoformat()),
        )
        conn.commit()

    def get_messages(self, limit: int = 200) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in reversed(rows):
            results.append({
                "number": r["number"],
                "sender": r["sender"],
                "text": r["text"],
                "code": r["code"],
                "provider": r["provider"],
                "received_at": r["received_at"],
            })
        return results

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def clear_messages(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM messages")
        conn.commit()

    @property
    def db_path(self) -> str:
        return self._db_path
