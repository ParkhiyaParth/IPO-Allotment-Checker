from app.db.database import get_connection


def test_isolated_db_creates_tables():
    conn = get_connection()
    try:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "ipo_cache" in tables
        assert "push_tokens" in tables
    finally:
        conn.close()
