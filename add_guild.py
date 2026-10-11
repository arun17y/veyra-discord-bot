import sqlite3
import datetime
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'database/VEYRA.db'))

conn = sqlite3.connect(db_path)
c = conn.cursor()
guild_id = '1538041381132697610'
now = datetime.datetime.now().isoformat()

c.execute("INSERT OR REPLACE INTO active_bot_guilds (guild_id, name, icon) VALUES (?, ?, ?)", 
          (guild_id, 'VEYRA ADMIN DISCORD', 'assets/veyra_avatar.jpg'))

c.execute("INSERT OR REPLACE INTO guild_subscriptions (guild_id, plan_type, granted_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
          (guild_id, 'Premium', 'system', 'Lifetime', now))

conn.commit()
conn.close()
print("SUCCESS: Registered Discord Guild ID 1538041381132697610 in database/VEYRA.db with Lifetime Premium Plan!")
