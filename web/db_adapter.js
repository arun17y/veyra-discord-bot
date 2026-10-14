// web/db_adapter.js - Unified Database Adapter for SQLite and Neon PostgreSQL
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

let sqlite3 = null;
try {
  sqlite3 = require('sqlite3').verbose();
} catch (e) {
  // Cloud runtime uses PostgreSQL; sqlite3 is not required
}

const { Pool } = require('pg');



const PK_MAP = {
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
};

function transformSql(sql) {
  let s = sql.trim();

  // Handle PRAGMAs (no-op in Postgres)
  if (/^PRAGMA /i.test(s)) {
    return { sql: 'SELECT 1', isNoop: true };
  }

  // Handle CREATE VIEW IF NOT EXISTS
  if (/CREATE\s+VIEW\s+IF\s+NOT\s+EXISTS/i.test(s)) {
    s = s.replace(/CREATE\s+VIEW\s+IF\s+NOT\s+EXISTS/i, 'CREATE OR REPLACE VIEW');
    return { sql: s, isNoop: false };
  }

  // Handle CREATE TABLE IF NOT EXISTS (tables are already migrated into Neon)
  if (/^CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS/i.test(s)) {
    s = s.replace(/INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT/gi, 'BIGSERIAL PRIMARY KEY');
    s = s.replace(/AUTOINCREMENT/gi, '');
  }

  // Handle INSERT OR IGNORE INTO <table>
  if (/INSERT\s+OR\s+IGNORE\s+INTO/i.test(s)) {
    s = s.replace(/INSERT\s+OR\s+IGNORE\s+INTO/i, 'INSERT INTO');
    if (!/ON\s+CONFLICT/i.test(s)) {
      s = s.replace(/;?\s*$/, ' ON CONFLICT DO NOTHING');
    }
  }

  // Handle INSERT OR REPLACE INTO <table> (col1, col2, ...) VALUES (...)
  const replaceMatch = s.match(/INSERT\s+OR\s+REPLACE\s+INTO\s+([a-zA-Z0-9_"]+)\s*\(([^)]+)\)\s*VALUES/i);
  if (replaceMatch) {
    const rawTable = replaceMatch[1].replace(/["`]/g, '');
    const colListStr = replaceMatch[2];
    const cols = colListStr.split(',').map(c => c.trim().replace(/["`]/g, ''));
    
    s = s.replace(/INSERT\s+OR\s+REPLACE\s+INTO/i, 'INSERT INTO');
    
    const pks = PK_MAP[rawTable] || ['id'];
    const updateCols = cols.filter(c => !pks.includes(c));
    
    if (updateCols.length > 0) {
      const setClause = updateCols.map(c => `"${c}" = EXCLUDED."${c}"`).join(', ');
      const pkClause = pks.map(p => `"${p}"`).join(', ');
      s = s.replace(/;?\s*$/, ` ON CONFLICT (${pkClause}) DO UPDATE SET ${setClause}`);
    } else {
      const pkClause = pks.map(p => `"${p}"`).join(', ');
      s = s.replace(/;?\s*$/, ` ON CONFLICT (${pkClause}) DO NOTHING`);
    }
  }

    // Quote PostgreSQL reserved column 'user' in audit_logs
    s = s.replace(/(\baudit_logs\s*\([^)]*)\buser\b([^)]*\))/gi, '$1"user"$2');
    s = s.replace(/(\bSELECT\s+[^FROM]+)\buser\b([^FROM]*FROM\s+audit_logs)/gi, '$1"user"$2');

    // Convert ? placeholders to $1, $2, ...
    let paramIndex = 1;
    s = s.replace(/\?/g, () => `$${paramIndex++}`);

    return { sql: s, isNoop: false };
}

class PostgresAdapter {
  constructor(connectionString) {
    this.pool = new Pool({
      connectionString,
      ssl: { rejectUnauthorized: false },
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000
    });
    this.pool.on('error', (err) => {
      console.error('Unexpected error on idle PG client:', err.message);
    });
    console.log('✅ Connected to Neon Cloud PostgreSQL Database via Pool');
  }

  serialize(fn) {
    if (typeof fn === 'function') fn();
  }

  all(sql, params, callback) {
    if (typeof params === 'function') {
      callback = params;
      params = [];
    }
    const { sql: pgSql, isNoop } = transformSql(sql);
    if (isNoop) {
      if (callback) callback(null, []);
      return;
    }

    this.pool.query(pgSql, params || [])
      .then(res => {
        if (callback) callback(null, res.rows || []);
      })
      .catch(err => {
        console.error('PostgreSQL all() error:', err.message, 'SQL:', pgSql);
        if (callback) callback(err, []);
      });
  }

  get(sql, params, callback) {
    if (typeof params === 'function') {
      callback = params;
      params = [];
    }
    const { sql: pgSql, isNoop } = transformSql(sql);
    if (isNoop) {
      if (callback) callback(null, null);
      return;
    }

    this.pool.query(pgSql, params || [])
      .then(res => {
        const row = (res.rows && res.rows.length > 0) ? res.rows[0] : null;
        if (callback) callback(null, row);
      })
      .catch(err => {
        console.error('PostgreSQL get() error:', err.message, 'SQL:', pgSql);
        if (callback) callback(err, null);
      });
  }

  run(sql, params, callback) {
    if (typeof params === 'function') {
      callback = params;
      params = [];
    }
    const { sql: pgSql, isNoop } = transformSql(sql);
    if (isNoop) {
      if (callback) callback.call({ lastID: 0, changes: 0 }, null);
      return;
    }

    this.pool.query(pgSql, params || [])
      .then(res => {
        const context = {
          lastID: (res.rows && res.rows[0] && (res.rows[0].id || res.rows[0].backup_id)) || 0,
          changes: res.rowCount || 0
        };
        if (callback) callback.call(context, null);
      })
      .catch(err => {
        console.error('PostgreSQL run() error:', err.message, 'SQL:', pgSql);
        if (callback) callback.call({ lastID: 0, changes: 0 }, err);
      });
  }

  close(callback) {
    this.pool.end(callback);
  }
}

function getDatabase(sqliteFallbackPath) {
  const dbUrl = process.env.DATABASE_URL;
  if (dbUrl && dbUrl.startsWith('postgres')) {
    return new PostgresAdapter(dbUrl);
  }
  
  console.log('ℹ️ Using local SQLite database at:', sqliteFallbackPath);
  const sqliteDb = new sqlite3.Database(sqliteFallbackPath);
  return sqliteDb;
}

module.exports = { getDatabase, PostgresAdapter, transformSql };
