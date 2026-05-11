from config import ADMIN_USER_IDS
from database.db import execute_query, fetch_one


def get_or_create_user(discord_user_id: str, username: str) -> dict:
    user = fetch_one("SELECT * FROM users WHERE discord_user_id = ?", (discord_user_id,))
    if user:
        return user
    is_admin = 1 if discord_user_id in ADMIN_USER_IDS else 0
    execute_query(
        "INSERT INTO users(discord_user_id, username, is_admin) VALUES (?, ?, ?)",
        (discord_user_id, username, is_admin),
    )
    return fetch_one("SELECT * FROM users WHERE discord_user_id = ?", (discord_user_id,)) or {}


def update_experience_level(user_id: int, level: str) -> None:
    execute_query("UPDATE users SET experience_level = ? WHERE id = ?", (level, user_id))


def set_preferred_topics(user_id: int, topics: str) -> None:
    execute_query("UPDATE users SET preferred_topics = ? WHERE id = ?", (topics, user_id))


def get_user_preferences(user_id: int) -> dict | None:
    return fetch_one("SELECT experience_level, preferred_topics FROM users WHERE id = ?", (user_id,))


def is_admin(discord_user_id: str) -> bool:
    if discord_user_id in ADMIN_USER_IDS:
        return True
    row = fetch_one("SELECT is_admin FROM users WHERE discord_user_id = ?", (discord_user_id,))
    return bool(row and row["is_admin"])
