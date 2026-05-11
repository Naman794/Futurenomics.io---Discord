import logging
import sqlite3
from pathlib import Path
from typing import Any

from config import BASE_DIR, DATABASE_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    schema_path = BASE_DIR / "database" / "schema.sql"
    with get_connection() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    logger.info("Database initialized at %s", DATABASE_PATH)


def execute_query(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def log_command(
    discord_user_id: str,
    guild_id: str | None,
    command_name: str,
    command_input: str,
    response_status: str,
) -> None:
    try:
        execute_query(
            """
            INSERT INTO command_logs(discord_user_id, guild_id, command_name, command_input, response_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (discord_user_id, guild_id, command_name, command_input, response_status),
        )
    except Exception:
        logger.exception("Failed to log command %s", command_name)
