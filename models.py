import sqlite3

DB_PATH = "gamehub.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Foreign keys must be enabled per connection in SQLite
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name  TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            bio           TEXT,
            created_at    TEXT NOT NULL,
            opted_out     BOOL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL UNIQUE,
            genre       TEXT NOT NULL,
            description TEXT,
            created_at  TEXT NOT NULL
        );

        -- A user can own many games, a game can be owned by many users
        CREATE TABLE IF NOT EXISTS user_games (
            user_id      INTEGER NOT NULL REFERENCES users(id),
            game_id      INTEGER NOT NULL REFERENCES games(id),
            hours_played INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, game_id)
        );

        -- Every activity is tied to a user AND a game
        CREATE TABLE IF NOT EXISTS activities (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            game_id    INTEGER NOT NULL REFERENCES games(id),
            action     TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Friendship is stored as two directional rows (user_id -> friend_id)
        CREATE TABLE IF NOT EXISTS friends (
            user_id   INTEGER NOT NULL REFERENCES users(id),
            friend_id INTEGER NOT NULL REFERENCES users(id),
            PRIMARY KEY (user_id, friend_id)
        );

        -- Notifications reference the user who receives it, who triggered it, and the activity that caused it
        CREATE TABLE IF NOT EXISTS notifications (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER NOT NULL REFERENCES users(id),
            triggered_by      INTEGER NOT NULL REFERENCES users(id),
            message           TEXT NOT NULL,
            activity_id       INTEGER NOT NULL REFERENCES activities(id),
            created_at        TEXT NOT NULL
        );
    """)

    conn.commit()
    conn.close()
