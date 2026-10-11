-- database/schema.sql - Clean Database Schema for VEYRA Ultimate

-- 1. General Guild Configs
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id TEXT PRIMARY KEY,
    prefix TEXT DEFAULT '?',
    nickname TEXT DEFAULT 'VEYRA',
    timezone TEXT DEFAULT 'UTC',
    updates_channel TEXT DEFAULT '#welcome',
    disabled_commands TEXT DEFAULT '[]',
    moderation_logs TEXT DEFAULT 'none',
    security_logs TEXT DEFAULT 'none',
    reports_enabled INTEGER DEFAULT 0,
    reports_channel TEXT DEFAULT 'none',
    reports_frequency TEXT DEFAULT 'Monthly'
);

-- 2. Guild Bot Profiles
CREATE TABLE IF NOT EXISTS guild_bot_profiles (
    guild_id TEXT PRIMARY KEY,
    nickname TEXT DEFAULT 'VEYRA',
    bio TEXT,
    website TEXT,
    support TEXT,
    avatar TEXT,
    banner TEXT
);

-- 3. Anti-Nuke Settings (All parameters)
CREATE TABLE IF NOT EXISTS antinuke_settings (
    guild_id TEXT PRIMARY KEY,
    anti_ban_limit INTEGER DEFAULT 5,
    anti_ban_punish TEXT DEFAULT 'Ban',
    anti_ban_enabled INTEGER DEFAULT 1,
    anti_kick_limit INTEGER DEFAULT 5,
    anti_kick_punish TEXT DEFAULT 'Ban',
    anti_kick_enabled INTEGER DEFAULT 1,
    anti_role_create_limit INTEGER DEFAULT 8,
    anti_role_create_punish TEXT DEFAULT 'Ban',
    anti_role_create_enabled INTEGER DEFAULT 1,
    anti_role_delete_limit INTEGER DEFAULT 3,
    anti_role_delete_punish TEXT DEFAULT 'Ban',
    anti_role_delete_enabled INTEGER DEFAULT 1,
    anti_channel_create_limit INTEGER DEFAULT 8,
    anti_channel_create_punish TEXT DEFAULT 'Ban',
    anti_channel_create_enabled INTEGER DEFAULT 1,
    anti_channel_delete_limit INTEGER DEFAULT 3,
    anti_channel_delete_punish TEXT DEFAULT 'Ban',
    anti_channel_delete_enabled INTEGER DEFAULT 1,
    anti_mention_limit INTEGER DEFAULT 0,
    anti_mention_punish TEXT DEFAULT 'Kick',
    anti_mention_enabled INTEGER DEFAULT 1,
    anti_bot_add_punish TEXT DEFAULT 'Ban',
    anti_bot_add_enabled INTEGER DEFAULT 1,
    anti_prune_punish TEXT DEFAULT 'Ban',
    anti_prune_enabled INTEGER DEFAULT 1,
    anti_dangerous_role_update_punish TEXT DEFAULT 'Ban',
    anti_dangerous_role_update_enabled INTEGER DEFAULT 1,
    anti_dangerous_role_add_punish TEXT DEFAULT 'Ban',
    anti_dangerous_role_add_enabled INTEGER DEFAULT 1,
    anti_vanity_change_punish TEXT DEFAULT 'Kick',
    anti_vanity_change_enabled INTEGER DEFAULT 1,
    anti_server_rename_punish TEXT DEFAULT 'Kick',
    anti_server_rename_enabled INTEGER DEFAULT 1,
    anti_server_icon_change_punish TEXT DEFAULT 'Kick',
    anti_server_icon_change_enabled INTEGER DEFAULT 1,
    anti_role_rename_punish TEXT DEFAULT 'Kick',
    anti_role_rename_enabled INTEGER DEFAULT 1,
    anti_channel_rename_punish TEXT DEFAULT 'Kick',
    anti_channel_rename_enabled INTEGER DEFAULT 1
);

-- 4. Welcome Messages
CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    channel TEXT DEFAULT 'general',
    message TEXT,
    embed_json TEXT,
    color TEXT DEFAULT '#a855f7',
    title TEXT DEFAULT 'Welcome {user}!',
    description TEXT DEFAULT 'Welcome to the server!',
    image TEXT DEFAULT '',
    thumbnail TEXT DEFAULT '',
    footer TEXT DEFAULT '',
    author_name TEXT DEFAULT '',
    author_icon TEXT DEFAULT '',
    footer_icon TEXT DEFAULT ''
);

-- 5. Leave/Exit Messages
CREATE TABLE IF NOT EXISTS leave_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    channel TEXT DEFAULT 'general',
    message TEXT,
    embed_json TEXT,
    color TEXT DEFAULT '#ef4444',
    title TEXT DEFAULT 'Goodbye {user}!',
    description TEXT DEFAULT 'Thanks for visiting!',
    image TEXT DEFAULT '',
    thumbnail TEXT DEFAULT '',
    footer TEXT DEFAULT '',
    author_name TEXT DEFAULT '',
    author_icon TEXT DEFAULT '',
    footer_icon TEXT DEFAULT ''
);

-- 6. Join DM Settings
CREATE TABLE IF NOT EXISTS joindm_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    channel TEXT DEFAULT 'dm',
    color TEXT DEFAULT '#a855f7',
    title TEXT DEFAULT 'Welcome to the server!',
    description TEXT DEFAULT '',
    image TEXT DEFAULT '',
    footer TEXT DEFAULT '',
    message TEXT DEFAULT ''
);

-- 6b. Leave DM Settings
CREATE TABLE IF NOT EXISTS leavedm_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    channel TEXT DEFAULT 'dm',
    color TEXT DEFAULT '#ef4444',
    title TEXT DEFAULT 'Goodbye!',
    description TEXT DEFAULT '',
    image TEXT DEFAULT '',
    footer TEXT DEFAULT '',
    message TEXT DEFAULT ''
);

-- 7. Invite Tracker Settings
CREATE TABLE IF NOT EXISTS invitetracker_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    channel TEXT DEFAULT 'general',
    color TEXT DEFAULT '#a855f7',
    title TEXT DEFAULT 'Member joined!',
    description TEXT DEFAULT '{user} was invited by {inviter}',
    image TEXT DEFAULT '',
    footer TEXT DEFAULT '',
    message TEXT DEFAULT '',
    embed_json TEXT
);

-- 8. Custom Embed Settings
CREATE TABLE IF NOT EXISTS embed_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    channel TEXT DEFAULT '#general',
    message TEXT,
    embed_json TEXT
);

-- 9. Sticky Messages
CREATE TABLE IF NOT EXISTS sticky_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    channel TEXT,
    message TEXT,
    last_message_id TEXT
);

-- 10. Published Server Directory Listings
CREATE TABLE IF NOT EXISTS published_listings (
    guild_id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    category TEXT,
    invite_url TEXT,
    bump_role TEXT
);

-- 11. Active Bot Guilds Cache
CREATE TABLE IF NOT EXISTS active_bot_guilds (
    guild_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT
);

-- 12. Guild Roles Cache
CREATE TABLE IF NOT EXISTS guild_roles (
    guild_id TEXT,
    role_id TEXT,
    name TEXT,
    color TEXT,
    position INTEGER,
    PRIMARY KEY (guild_id, role_id)
);

-- 13. Guild Channels Cache
CREATE TABLE IF NOT EXISTS guild_channels (
    guild_id TEXT,
    channel_id TEXT,
    name TEXT,
    type TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

-- 14. Whitelisted Users
CREATE TABLE IF NOT EXISTS whitelists (
    guild_id TEXT,
    user_id TEXT,
    reason TEXT DEFAULT 'Trusted Administrator',
    PRIMARY KEY (guild_id, user_id)
);

-- 15. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    timestamp TEXT,
    user TEXT,
    action TEXT,
    details TEXT
);

-- 16. Global Settings
CREATE TABLE IF NOT EXISTS global_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT
);

-- 17. Guild Subscriptions
CREATE TABLE IF NOT EXISTS guild_subscriptions (
    guild_id TEXT PRIMARY KEY,
    plan_type TEXT DEFAULT 'Free',
    granted_by TEXT,
    expires_at TEXT,
    created_at TEXT
);

-- 18. User Subscriptions
CREATE TABLE IF NOT EXISTS user_subscriptions (
    user_id TEXT PRIMARY KEY,
    plan_type TEXT DEFAULT 'Free',
    granted_by TEXT,
    expires_at TEXT,
    created_at TEXT
);

-- 19. Guild Emojis
CREATE TABLE IF NOT EXISTS guild_emojis (
    guild_id TEXT,
    emoji_id TEXT,
    name TEXT,
    animated INTEGER,
    url TEXT,
    formatted TEXT,
    PRIMARY KEY (guild_id, emoji_id)
);

-- 20. Pending Embed Posts Queue
CREATE TABLE IF NOT EXISTS pending_embed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    channel TEXT,
    content TEXT,
    embed_json TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT
);

-- 21. Ticket Settings
CREATE TABLE IF NOT EXISTS ticket_settings (
    guild_id TEXT PRIMARY KEY,
    claim_mode TEXT DEFAULT 'private',
    max_tickets INTEGER DEFAULT 3,
    embed_color TEXT DEFAULT '#d4af37',
    ping_author INTEGER DEFAULT 1
);

-- 22. Ticket Panels
CREATE TABLE IF NOT EXISTS ticket_panels (
    id TEXT PRIMARY KEY,
    guild_id TEXT,
    name TEXT,
    support_roles TEXT,
    category_id TEXT,
    panel_title TEXT,
    panel_color TEXT,
    panel_description TEXT,
    panel_button_text TEXT,
    ticket_title TEXT,
    ticket_description TEXT,
    auto_close INTEGER DEFAULT 0,
    auto_delete INTEGER DEFAULT 0,
    categories TEXT
);

-- 23. Tickets
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    panel_id TEXT,
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

-- 24. Ticket Stats
CREATE TABLE IF NOT EXISTS ticket_stats (
    guild_id TEXT PRIMARY KEY,
    open INTEGER DEFAULT 3,
    progress INTEGER DEFAULT 3,
    resolved INTEGER DEFAULT 440,
    total INTEGER DEFAULT 443
);

-- 25. Ticket History
CREATE TABLE IF NOT EXISTS ticket_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    ticket_name TEXT,
    topic TEXT,
    status TEXT,
    open_time TEXT,
    author_name TEXT,
    author_id TEXT
);

-- 26. Ticket Bot Profile
CREATE TABLE IF NOT EXISTS ticket_bot_profile (
    guild_id TEXT PRIMARY KEY,
    name TEXT,
    bio TEXT,
    avatar TEXT,
    banner TEXT
);

-- 27. Verification Settings
CREATE TABLE IF NOT EXISTS verification_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    captcha_enabled INTEGER DEFAULT 1,
    verified_role TEXT,
    unverified_role TEXT,
    channel TEXT,
    type TEXT DEFAULT 'captcha',
    captcha_lines INTEGER DEFAULT 5,
    captcha_numbers INTEGER DEFAULT 1,
    captcha_sensitive INTEGER DEFAULT 0,
    captcha_timeout INTEGER DEFAULT 60,
    embed_title TEXT DEFAULT NULL,
    embed_desc TEXT DEFAULT NULL,
    embed_color TEXT DEFAULT NULL,
    embed_image TEXT DEFAULT NULL,
    embed_footer TEXT DEFAULT NULL,
    button_text TEXT DEFAULT 'Verify Account',
    button_color TEXT DEFAULT 'green'
);

-- 28. Beast Mode Settings
CREATE TABLE IF NOT EXISTS beastmode_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    score_limit INTEGER DEFAULT 40,
    punishment_type TEXT DEFAULT 'Kick',
    whitelist_bypass INTEGER DEFAULT 0,
    score_bot_add INTEGER DEFAULT 0,
    score_ban INTEGER DEFAULT 0,
    score_kick INTEGER DEFAULT 0,
    score_role_create INTEGER DEFAULT 0,
    score_role_delete INTEGER DEFAULT 0,
    score_channel_create INTEGER DEFAULT 0,
    score_channel_delete INTEGER DEFAULT 0,
    score_prune INTEGER DEFAULT 0,
    score_mention INTEGER DEFAULT 0,
    score_vanity INTEGER DEFAULT 0,
    score_webhook INTEGER DEFAULT 0
);

-- 29. Anti-Raid Settings
CREATE TABLE IF NOT EXISTS antiraid_settings (
    guild_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    invite_link_protection INTEGER DEFAULT 0,
    join_rate_threshold INTEGER DEFAULT 10,
    min_account_age INTEGER DEFAULT 3,
    punishment_type TEXT DEFAULT 'Kick'
);

-- 30. User OAuth Tokens
CREATE TABLE IF NOT EXISTS user_oauth_tokens (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    access_token TEXT,
    updated_at TEXT
);

-- 31. Web Sessions
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_data TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 32. User Coins
CREATE TABLE IF NOT EXISTS user_coins (
    guild_id TEXT,
    user_id TEXT,
    balance INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- 33. Messages Stats
CREATE TABLE IF NOT EXISTS messages_stats (
    guild_id TEXT,
    user_id TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- 34. Blacklisted Channels
CREATE TABLE IF NOT EXISTS blacklisted_channels (
    guild_id TEXT,
    channel_id TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

-- 35. Moderation Cases
CREATE TABLE IF NOT EXISTS moderation_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    case_number INTEGER NOT NULL,
    moderator_id TEXT NOT NULL,
    moderator_tag TEXT,
    target_id TEXT NOT NULL,
    target_tag TEXT,
    action TEXT NOT NULL,
    reason TEXT DEFAULT 'No reason provided',
    duration TEXT,
    timestamp TEXT NOT NULL,
    evidence TEXT,
    status TEXT DEFAULT 'active'
);

-- 36. Scheduled Automations
CREATE TABLE IF NOT EXISTS scheduled_automations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    execute_at TEXT NOT NULL,
    recurring TEXT DEFAULT 'none',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL
);

-- 37. Server Backups / Snapshots
CREATE TABLE IF NOT EXISTS server_backups (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

-- 38. User Levels & XP
CREATE TABLE IF NOT EXISTS user_levels (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_xp_time TEXT,
    PRIMARY KEY (guild_id, user_id)
);

-- 39. User Reputation
CREATE TABLE IF NOT EXISTS user_reputation (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rep_points INTEGER DEFAULT 0,
    last_given TEXT,
    PRIMARY KEY (guild_id, user_id)
);

-- 40. Custom Forms
CREATE TABLE IF NOT EXISTS custom_forms (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    questions_json TEXT NOT NULL,
    channel_id TEXT,
    staff_role_id TEXT,
    created_at TEXT NOT NULL
);

-- 41. Form Submissions
CREATE TABLE IF NOT EXISTS form_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);

-- 42. Suggestions & Polls
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    message_id TEXT,
    staff_response TEXT,
    created_at TEXT NOT NULL
);

-- 43. Emergency Lockdowns
CREATE TABLE IF NOT EXISTS emergency_lockdowns (
    guild_id TEXT PRIMARY KEY,
    active INTEGER DEFAULT 0,
    activated_by TEXT,
    activated_at TEXT,
    reason TEXT,
    original_overwrites_json TEXT
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_mod_cases_guild ON moderation_cases(guild_id);
CREATE INDEX IF NOT EXISTS idx_automations_execute ON scheduled_automations(execute_at, status);
CREATE INDEX IF NOT EXISTS idx_backups_guild ON server_backups(guild_id);
CREATE INDEX IF NOT EXISTS idx_user_levels_xp ON user_levels(guild_id, xp DESC);
CREATE INDEX IF NOT EXISTS idx_suggestions_guild ON suggestions(guild_id);


