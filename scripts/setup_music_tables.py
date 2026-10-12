import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "bot"))
import db_adapter

def setup_tables():
    db = db_adapter.get_db()
    cursor = db.cursor()
    print("Connected to DB:", type(db))
    queries = [
        """
        CREATE TABLE IF NOT EXISTS liked_tracks (
            user_id BIGINT,
            track_url TEXT,
            track_title TEXT,
            track_author TEXT,
            track_thumbnail TEXT,
            track_duration INTEGER,
            PRIMARY KEY (user_id, track_url)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS playlists (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            name TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            id SERIAL PRIMARY KEY,
            playlist_id INTEGER,
            title TEXT,
            author TEXT,
            url TEXT,
            thumbnail TEXT,
            duration INTEGER
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_playlists (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            name TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_playlist_tracks (
            id SERIAL PRIMARY KEY,
            playlist_id INTEGER,
            title TEXT,
            author TEXT,
            url TEXT,
            thumbnail TEXT,
            duration INTEGER
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dj_roles (
            guild_id BIGINT PRIMARY KEY,
            role_id BIGINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS announcements (
            guild_id BIGINT PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dj_modes (
            guild_id BIGINT PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_stats (
            stat_name TEXT PRIMARY KEY,
            stat_value BIGINT DEFAULT 0
        );
        """
    ]
    for q in queries:
        try:
            cursor.execute(q)
        except Exception as e:
            print("Error on query:", e)
    db.commit()
    db.close()
    print("Music tables configured successfully!")

if __name__ == "__main__":
    setup_tables()
