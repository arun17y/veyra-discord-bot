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
    'emergency_lockdowns': ['guild_id']
}

def transform_sql_for_pg(sql):
    s = sql.strip()
    if s.upper().startswith("PRAGMA "):
        return "SELECT 1;", True

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
    def __init__(self, raw_cursor):
        self._cur = raw_cursor
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
            # Re-raise with clean context
            raise e
        return self

    def executemany(self, sql, seq_of_params):
        pg_sql, is_noop = transform_sql_for_pg(sql)
        if is_noop:
            return self
        self._cur.executemany(pg_sql, seq_of_params)
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
        return PostgresCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

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

def get_db():
    """
    Returns Neon PostgreSQL connection wrapper if DATABASE_URL is set,
    otherwise falls back to local SQLite database.
    """
    if HAS_PG and DATABASE_URL and DATABASE_URL.startswith("postgres"):
        try:
            pool = get_pg_pool()
            raw_conn = pool.getconn()
            raw_conn.autocommit = False
            return PostgresConnectionWrapper(raw_conn, pool)
        except Exception as e:
            # Fallback to direct connection if pool exhausted
            try:
                raw_conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
                return PostgresConnectionWrapper(raw_conn)
            except Exception as direct_err:
                pass
                
    # Fallback to SQLite
    conn = sqlite3.connect(DB_PATH_VEYRA, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn
