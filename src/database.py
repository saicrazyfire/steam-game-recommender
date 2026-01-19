import sqlite3
from typing import List

DB_FILE = "steam_recommender.db"

def initialize_db():
    """Initializes the database and creates the necessary tables."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manually_excluded_games (
                user_steam_id TEXT NOT NULL,
                game_appid INTEGER NOT NULL,
                PRIMARY KEY (user_steam_id, game_appid)
            )
        """)
        conn.commit()

def get_excluded_games(steam_id: str) -> List[int]:
    """Fetches a list of manually excluded appids for a given user."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT game_appid FROM manually_excluded_games WHERE user_steam_id = ?", (steam_id,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def add_exclusion(steam_id: str, appid: int):
    """Adds a game to a user's manual exclusion list."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # INSERT OR IGNORE to prevent errors if the entry already exists
        cursor.execute("INSERT OR IGNORE INTO manually_excluded_games (user_steam_id, game_appid) VALUES (?, ?)", (steam_id, appid))
        conn.commit()

def remove_exclusion(steam_id: str, appid: int):
    """Removes a game from a user's manual exclusion list."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manually_excluded_games WHERE user_steam_id = ? AND game_appid = ?", (steam_id, appid))
        conn.commit()
