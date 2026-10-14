# bot/db_adapter.py - Unified DB Connection Adapter for Discord Bot (Neon PostgreSQL + SQLite Fallback)
import os
import re
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_u16miIQSLZGO@ep-morning-hat-b5421rgl-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require")
DB_PATH_VEYRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "VEYRA.db"))

PK_MAP = {
    'guild_bot_profiles': ['guild_id'],
    'active_bot_guilds': ['guild_id'],
    'guild_roles': ['role_id'],
    'guild_channels': ['channel_id'],
    'audit_logs': ['id'],
    'guild_settings': ['guild_id'],
    'welcome_settings': ['guild_id'],
    'leave_settings': ['guild_id'],
    'embed_settings': ['guild_id'],
    'invitetracker_settings': ['guild_id'],
    'sticky_messages': ['id'],
    'published_listings': ['guild_id'],
    'whitelists': ['guild_id', 'user_id'],
    'global_settings': ['setting_key'],
    'guild_subscriptions': ['guild_id'],
    'guild_emojis': ['emoji_id'],
    'pending_embed_posts': ['id'],
    'user_subscriptions': ['user_id'],
    'warnings': ['id'],
    'user_coins': ['user_id'],
    'joinable_ranks': ['role_id'],
    'autoroles': ['guild_id'],
    'sticky_settings': ['guild_id'],
    'member_roles': ['user_id'],
    'bot_permissions': ['permission'],
    'verification_settings': ['guild_id'],
    'invites_stats': ['user_id'],
    'messages_stats': ['user_id'],
    'blacklisted_channels': ['channel_id'],
    'giveaways': ['id'],
    'invited_users': ['user_id'],
    'guild_commands': ['guild_id'],
    'web_sessions': ['session_id'],
    'joindm_settings': ['guild_id'],
    'antinuke_settings': ['guild_id'],
    'ticket_panels': ['id'],
    'tickets': ['id'],
    'ticket_settings': ['guild_id'],
    'user_oauth_tokens': ['user_id'],
    'ticket_stats': ['guild_id'],
    'ticket_history': ['id'],
    'ticket_bot_profile': ['guild_id'],
    'beastmode_settings': ['guild_id'],
    'antiraid_settings': ['guild_id'],
    'subscription_history': ['id'],
    'reports_tracker': ['guild_id'],
    'bot_whitelists': ['action_type'],
    'cookies_consent': ['session_id'],
    'leavedm_settings': ['guild_id'],
    'contact_submissions': ['id'],
    'client_errors': ['id'],
    'embedmessages_settings': ['guild_id'],
    'ticket_blacklist': ['user_id'],
    'razorpay_transactions': ['id'],
    'moderation_overrides': ['user_id'],
    'leveling_settings': ['guild_id'],
    'leveling_rewards': ['role_id'],
    'leveling_ignored_channels': ['channel_id'],
    'reports_settings': ['guild_id'],
    'invites_settings': ['guild_id'],
    'invite_blacklist': ['user_id'],
    'leaderboard_hidden': ['user_id'],
    'voice_247_settings': ['guild_id'],
    'authorized_bot_roles': ['role_id'],
    'command_access_matrix': ['command_name'],
    'server_central_settings': ['guild_id'],
    'lockdown_states': ['channel_id'],
    'automod_settings': ['guild_id'],
    'custom_commands': ['command_name'],
    'scheduled_tasks': ['id'],
    'server_backups': ['backup_id'],
    'DiscordVerification': ['id'],
    'server_recovery_snapshots': ['snapshot_id'],
    'recovery_logs': ['id'],
    'moderation_cases': ['id'],
    'scheduled_automations': ['id'],
    'user_levels': ['user_id'],
    'user_reputation': ['user_id'],
    'custom_forms': ['id'],
    'form_submissions': ['id'],
    'suggestions': ['id'],
    'emergency_lockdowns': ['guild_id'],
    'liked_tracks': ['user_id', 'track_url'],
    'playlists': ['id'],
    'playlist_tracks': ['id'],
    'global_playlists': ['id'],
    'global_playlist_tracks': ['id'],
    'dj_roles': ['guild_id'],
    'announcements': ['guild_id'],
    'dj_modes': ['guild_id'],
    'global_stats': ['stat_name']
}

def transform_sql_for_pg(sql):
    s = sql.strip()
    if s.upper().startswith("PRAGMA "):
        return "SELECT 1;", True

    # Handle SQLite CREATE TABLE - If table is already known, it's a no-op in Postgres
    create_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_"]+)', s, re.IGNORECASE)
    if create_match:
        table_name = create_match.group(1).replace('"', '').replace('`', '').lower()
        if table_name in PK_MAP:
            return "SELECT 1;", True

    s = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', s, flags=re.IGNORECASE)
    s = re.sub(r'\bAUTOINCREMENT\b', '', s, flags=re.IGNORECASE)

    # Handle INSERT OR IGNORE INTO <table>
    if re.search(r'INSERT\s+OR\s+IGNORE\s+INTO', s, re.IGNORECASE):
        s = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', s, flags=re.IGNORECASE)
        if not re.search(r'ON\s+CONFLICT', s, re.IGNORECASE):
            s = re.sub(r';?\s*$', ' ON CONFLICT DO NOTHING;', s)

    # Handle INSERT OR REPLACE INTO <table> (col1, col2, ...) VALUES (...)
    replace_match = re.search(r'INSERT\s+OR\s+REPLACE\s+INTO\s+([a-zA-Z0-9_"]+)\s*\(([^)]+)\)\s*VALUES', s, re.IGNORECASE)
    if replace_match:
        raw_table = replace_match.group(1).replace('"', '').replace('`', '')
        cols_str = replace_match.group(2)
        cols = [c.strip().replace('"', '').replace('`', '') for c in cols_str.split(',')]
        s = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'INSERT INTO', s, flags=re.IGNORECASE)
        pks = PK_MAP.get(raw_table, ['id'])
        update_cols = [c for c in cols if c not in pks]
        if update_cols:
            set_clause = ", ".join([f'"{c}" = EXCLUDED."${c}"'.replace('$', '') for c in update_cols])
            pk_clause = ", ".join([f'"{p}"' for p in pks])
            s = re.sub(r';?\s*$', f' ON CONFLICT ({pk_clause}) DO UPDATE SET {set_clause};', s)
        else:
            pk_clause = ", ".join([f'"{p}"' for p in pks])
            s = re.sub(r';?\s*$', f' ON CONFLICT ({pk_clause}) DO NOTHING;', s)

    # Handle SQLite ROWID
    s = re.sub(r'\bORDER\s+BY\s+ROWID\b', 'ORDER BY 1', s, flags=re.IGNORECASE)
    s = re.sub(r'\bROWID\b', '1', s, flags=re.IGNORECASE)

    # Quote PostgreSQL reserved column 'user' in audit_logs
    s = re.sub(r'(\baudit_logs\s*\([^)]*)\buser\b([^)]*\))', r'\1"user"\2', s, flags=re.IGNORECASE)
    s = re.sub(r'(\bSELECT\s+[^FROM]+)\buser\b([^FROM]*FROM\s+audit_logs)', r'\1"user"\2', s, flags=re.IGNORECASE)

    # Convert ? placeholders to %s
    s = s.replace('?', '%s')
    return s, False

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    HAS_PG = True
except ImportError:
    HAS_PG = False

_pg_pool = None

def get_pg_pool():
    global _pg_pool
    if _pg_pool is None and HAS_PG and DATABASE_URL and DATABASE_URL.startswith("postgres"):
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor
        )
    return _pg_pool

class PostgresCursorWrapper:
    def __init__(self, raw_cursor, conn=None):
        self._cur = raw_cursor
        self._conn = conn
        self.lastrowid = 0

    def execute(self, sql, params=None):
        pg_sql, is_noop = transform_sql_for_pg(sql)
        if is_noop:
            return self
        try:
            if params is not None:
                if isinstance(params, list):
                    params = tuple(params)
                self._cur.execute(pg_sql, params)
            else:
                self._cur.execute(pg_sql)
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate" in err_msg or "no unique or exclusion constraint" in err_msg:
                # Column, table or constraint already exists or conflicts — ignore safely
                return self
            if self._conn:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            raise e
        return self

    def executemany(self, sql, seq_of_params):
        pg_sql, is_noop = transform_sql_for_pg(sql)
        if is_noop:
            return self
        try:
            self._cur.executemany(pg_sql, seq_of_params)
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            raise e
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size else self._cur.fetchmany()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class PostgresConnectionWrapper:
    def __init__(self, raw_conn, pool=None):
        self._conn = raw_conn
        self._pool = pool
        self.row_factory = None

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor(), self._conn)

    def commit(self):
        try:
            self._conn.commit()
        except Exception:
            pass

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        if self._pool:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

_sqlite_initialized = False

def _ensure_sqlite_schema(conn):
    global _sqlite_initialized
    if _sqlite_initialized:
        return
    try:
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                prefix TEXT DEFAULT '?',
                nickname TEXT DEFAULT 'SENTRIX',
                timezone TEXT DEFAULT 'UTC',
                updates_channel TEXT DEFAULT '#welcome',
                moderation_logs TEXT DEFAULT 'none',
                security_logs TEXT DEFAULT 'none',
                reports_enabled INTEGER DEFAULT 0,
                reports_channel TEXT DEFAULT 'none',
                reports_frequency TEXT DEFAULT 'Monthly',
                disabled_commands TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS pending_embed_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                channel TEXT,
                content TEXT,
                embed_json TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ticket_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                name TEXT,
                support_roles TEXT DEFAULT '[]',
                category_id TEXT DEFAULT 'none',
                panel_title TEXT DEFAULT 'Create a Ticket',
                panel_description TEXT DEFAULT 'Click the button below to open a ticket.',
                panel_color TEXT DEFAULT '#a855f7',
                panel_button_text TEXT DEFAULT 'Create Ticket',
                ticket_title TEXT DEFAULT 'Support Ticket',
                ticket_description TEXT DEFAULT 'Thank you for contacting support.',
                ticket_count INTEGER DEFAULT 0,
                auto_close INTEGER DEFAULT 0,
                auto_delete INTEGER DEFAULT 0,
                categories TEXT,
                pending_channel_id TEXT
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                panel_id INTEGER,
                channel_id TEXT,
                user_id TEXT,
                username TEXT,
                ticket_number INTEGER,
                status TEXT DEFAULT 'open',
                claimed_by TEXT,
                open_time TEXT,
                close_time TEXT,
                close_reason TEXT,
                transcript TEXT,
                topic TEXT
            );
            CREATE TABLE IF NOT EXISTS ticket_settings (
                guild_id TEXT PRIMARY KEY,
                claim_mode TEXT DEFAULT 'private',
                ping_author INTEGER DEFAULT 1,
                max_tickets INTEGER DEFAULT 100,
                embed_color TEXT DEFAULT '#d4af37',
                close_allow_user INTEGER DEFAULT 1,
                close_allow_staff INTEGER DEFAULT 1,
                close_allow_roles TEXT DEFAULT '[]',
                cooldown_seconds INTEGER DEFAULT 60,
                lockdown INTEGER DEFAULT 0,
                logs_channel_id TEXT DEFAULT 'none',
                auto_close_hours INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS reports_tracker (
                guild_id TEXT PRIMARY KEY,
                last_report TEXT
            );
            CREATE TABLE IF NOT EXISTS voice_247_settings (
                guild_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_reconnect TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS server_central_settings (
                guild_id TEXT PRIMARY KEY,
                mod_log_channel TEXT,
                sec_log_channel TEXT,
                audit_log_channel TEXT,
                mute_role_id TEXT,
                bot_manager_role_id TEXT,
                auto_lockdown INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS welcome_settings (
                guild_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                channel TEXT DEFAULT '#welcome',
                message TEXT,
                embed_json TEXT,
                color TEXT DEFAULT '#a855f7',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                image TEXT DEFAULT '',
                footer TEXT DEFAULT '',
                author_name TEXT,
                author_icon TEXT,
                footer_icon TEXT,
                thumbnail TEXT
            );
            CREATE TABLE IF NOT EXISTS leave_settings (
                guild_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                channel TEXT DEFAULT '#welcome',
                message TEXT,
                embed_json TEXT,
                color TEXT DEFAULT '#a855f7',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                image TEXT DEFAULT '',
                footer TEXT DEFAULT '',
                thumbnail TEXT,
                author_name TEXT,
                author_icon TEXT,
                footer_icon TEXT
            );
        """)
        conn.commit()
        _sqlite_initialized = True
    except Exception as ex:
        print(f"[SQLITE INIT NOTICE] {ex}")

def get_db():
    """
    Returns Neon PostgreSQL connection wrapper if DATABASE_URL is set,
    otherwise falls back to local SQLite database.
    """
    if HAS_PG and DATABASE_URL and DATABASE_URL.startswith("postgres"):
        try:
            pool = get_pg_pool()
            raw_conn = pool.getconn()
            raw_conn.autocommit = True
            return PostgresConnectionWrapper(raw_conn, pool)
        except Exception as e:
            # Fallback to direct connection if pool exhausted
            try:
                raw_conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
                raw_conn.autocommit = True
                return PostgresConnectionWrapper(raw_conn)
            except Exception as direct_err:
                pass
                
    # Fallback to SQLite
    os.makedirs(os.path.dirname(DB_PATH_VEYRA), exist_ok=True)
    conn = sqlite3.connect(DB_PATH_VEYRA, timeout=30.0)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn
