import sqlite3
import datetime
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'database/VEYRA.db'))

conn = sqlite3.connect(db_path)
c = conn.cursor()
user_id = '1538041381132697610'
now = datetime.datetime.now().isoformat()

# 1. Register in user_oauth_tokens
c.execute("""
    INSERT OR REPLACE INTO user_oauth_tokens (user_id, username, access_token, updated_at)
    VALUES (?, ?, ?, ?)
""", (user_id, 'ADMIN_USER', 'admin_token_1538041381132697610', now))

# 2. Register in active_bot_guilds if not present
c.execute("""
    INSERT OR REPLACE INTO active_bot_guilds (guild_id, name, icon)
    VALUES (?, ?, ?)
""", (user_id, 'VEYRA ADMIN GUILD', 'assets/veyra_avatar.jpg'))

# 3. Grant Lifetime Premium Plan for user and guild
c.execute("""
    INSERT OR REPLACE INTO guild_subscriptions (guild_id, plan_type, granted_by, expires_at, created_at)
    VALUES (?, ?, ?, ?, ?)
""", (user_id, 'Premium', 'system', 'Lifetime', now))

conn.commit()
conn.close()
print("SUCCESS: Registered User ID 1538041381132697610 as Admin in database/VEYRA.db!")
