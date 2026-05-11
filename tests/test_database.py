import sqlite3

from database.db import get_connection, init_db


def test_database_connection_initializes_schema():
    init_db()
    with get_connection() as conn:
        assert isinstance(conn, sqlite3.Connection)
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        assert row is not None
