// database/init_db.js - SQLite Database Initialization & Seeding
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

const dbDir = __dirname;
const dbPath = path.join(dbDir, 'VEYRA.db');
const schemaPath = path.join(dbDir, 'schema.sql');

if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
}

const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('❌ Failed to open SQLite database:', err.message);
        process.exit(1);
    }
    console.log('✅ Opened SQLite database successfully.');
});

db.serialize(() => {
    const schemaSql = fs.readFileSync(schemaPath, 'utf8');
    
    // Execute multiple queries split by semicolon
    const statements = schemaSql.split(';').map(s => s.trim()).filter(s => s.length > 0);
    
    statements.forEach((statement) => {
        db.run(statement, (err) => {
            if (err) {
                console.error('❌ Schema statement failed:', err.message);
                console.error('Statement:', statement);
            }
        });
    });
    
    console.log('✅ Schema executed successfully.');

    // Seed default guild settings
    const sampleGuild = '125698688663185';
    
    db.run(`INSERT OR IGNORE INTO guild_settings (guild_id, prefix, nickname, timezone, updates_channel) 
            VALUES (?, '?', 'VEYRA', 'UTC', '#welcome')`, [sampleGuild], (err) => {
        if (err) console.error('Seed error:', err.message);
    });

    db.run(`INSERT OR IGNORE INTO antinuke_settings (
                guild_id,
                anti_ban_limit, anti_ban_punish, anti_ban_enabled,
                anti_kick_limit, anti_kick_punish, anti_kick_enabled,
                anti_role_create_limit, anti_role_create_punish, anti_role_create_enabled,
                anti_role_delete_limit, anti_role_delete_punish, anti_role_delete_enabled,
                anti_channel_create_limit, anti_channel_create_punish, anti_channel_create_enabled,
                anti_channel_delete_limit, anti_channel_delete_punish, anti_channel_delete_enabled,
                anti_mention_limit, anti_mention_punish, anti_mention_enabled,
                anti_bot_add_punish, anti_bot_add_enabled,
                anti_prune_punish, anti_prune_enabled,
                anti_dangerous_role_update_punish, anti_dangerous_role_update_enabled,
                anti_dangerous_role_add_punish, anti_dangerous_role_add_enabled,
                anti_vanity_change_punish, anti_vanity_change_enabled,
                anti_server_rename_punish, anti_server_rename_enabled,
                anti_server_icon_change_punish, anti_server_icon_change_enabled,
                anti_role_rename_punish, anti_role_rename_enabled,
                anti_channel_rename_punish, anti_channel_rename_enabled
            ) VALUES (?, 5, 'Ban', 1, 5, 'Ban', 1, 8, 'Ban', 1, 3, 'Ban', 1, 8, 'Ban', 1, 3, 'Ban', 1, 0, 'Kick', 1, 'Ban', 1, 'Ban', 1, 'Ban', 1, 'Ban', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1)`, 
        [sampleGuild], (err) => {
        if (err) console.error('Anti-nuke seed error:', err.message);
    });

    // Seed global active theme
    db.run(`INSERT OR REPLACE INTO global_settings (setting_key, setting_value) 
            VALUES ('active_theme', 'slate')`, (err) => {
        if (err) console.error('Global settings seed error:', err.message);
    });

    // Seed mock audit logs
    const seedLogs = [
        { user: '@demo_admin', action: 'Initialize', details: 'Configured security matrix modules for VEYRA' },
        { user: 'System', action: 'Core Boot', details: 'Anti-nuke filters initialized and waiting for guild triggers' }
    ];
    
    seedLogs.forEach((log) => {
        const timeStr = new Date().toISOString();
        db.run(`INSERT INTO audit_logs (guild_id, timestamp, user, action, details) 
                VALUES (?, ?, ?, ?, ?)`, [sampleGuild, timeStr, log.user, log.action, log.details], (err) => {
            if (err) console.error('Logs seed error:', err.message);
        });
    });

    // Seed mock whitelists
    db.run(`INSERT OR IGNORE INTO whitelists (guild_id, user_id, reason) 
            VALUES (?, '11223344556677', 'Bot Owner (Dev override)')`, [sampleGuild], (err) => {
        if (err) console.error('Whitelist seed error:', err.message);
    });

    console.log('✅ Sample database seeded with default configurations.');
});

db.close();

