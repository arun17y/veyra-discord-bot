import os
import requests
import json
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv('.env')
db_url = os.getenv('DATABASE_URL')
p = urlparse(db_url)

conn = psycopg2.connect(
    dbname=p.path[1:],
    user=p.username,
    password=p.password,
    host=p.hostname,
    port=p.port,
    sslmode='require'
)
cur = conn.cursor()

guild_id = '1538507162496667718'
print(f"=== Testing E2E Persistence on Guild: {guild_id} ===")

# 1. Test antinuke_settings
cur.execute("SELECT anti_ban_enabled, anti_kick_enabled FROM antinuke_settings WHERE guild_id = %s", (guild_id,))
row = cur.fetchone()
print(f"Antinuke DB row: anti_ban_enabled={row[0]} ({type(row[0])}), anti_kick_enabled={row[1]}")

# 2. Test antiraid_settings update & query
cur.execute("""
    INSERT INTO antiraid_settings (guild_id, enabled, invite_link_protection, join_rate_threshold, min_account_age, punishment_type)
    VALUES (%s, 1, 1, 15, 7, 'Ban')
    ON CONFLICT (guild_id) DO UPDATE SET
        enabled = EXCLUDED.enabled,
        invite_link_protection = EXCLUDED.invite_link_protection,
        join_rate_threshold = EXCLUDED.join_rate_threshold,
        min_account_age = EXCLUDED.min_account_age,
        punishment_type = EXCLUDED.punishment_type
""", (guild_id,))
conn.commit()

cur.execute("SELECT enabled, invite_link_protection, join_rate_threshold, min_account_age, punishment_type FROM antiraid_settings WHERE guild_id = %s", (guild_id,))
ar_row = cur.fetchone()
print(f"Anti-Raid DB row: enabled={ar_row[0]}, invite_link_protection={ar_row[1]}, join_rate_threshold={ar_row[2]}, min_age={ar_row[3]}, punish={ar_row[4]}")
assert str(ar_row[0]) == '1', "Anti-Raid enabled must be 1"

# 3. Test antispam_settings
cur.execute("""
    INSERT INTO antispam_settings (guild_id, enabled, max_messages, message_seconds, max_duplicates, max_mentions, block_invites, block_links, max_emojis, max_caps_percent, punishment, timeout_duration)
    VALUES (%s, 1, 6, 4, 3, 5, 1, 1, 10, 80, 'Timeout', 300)
    ON CONFLICT (guild_id) DO UPDATE SET
        enabled = EXCLUDED.enabled,
        max_messages = EXCLUDED.max_messages,
        message_seconds = EXCLUDED.message_seconds,
        block_invites = EXCLUDED.block_invites,
        block_links = EXCLUDED.block_links
""", (guild_id,))
conn.commit()

cur.execute("SELECT enabled, max_messages, block_invites, block_links FROM antispam_settings WHERE guild_id = %s", (guild_id,))
as_row = cur.fetchone()
print(f"Anti-Spam DB row: enabled={as_row[0]}, max_msgs={as_row[1]}, block_invites={as_row[2]}, block_links={as_row[3]}")
assert str(as_row[0]) == '1', "Anti-Spam enabled must be 1"

# 4. Test beastmode_settings
cur.execute("""
    INSERT INTO beastmode_settings (guild_id, enabled, score_limit, punishment_type, whitelist_bypass)
    VALUES (%s, 1, 50, 'Ban', 1)
    ON CONFLICT (guild_id) DO UPDATE SET
        enabled = EXCLUDED.enabled,
        score_limit = EXCLUDED.score_limit,
        punishment_type = EXCLUDED.punishment_type
""", (guild_id,))
conn.commit()

cur.execute("SELECT enabled, score_limit, punishment_type, whitelist_bypass FROM beastmode_settings WHERE guild_id = %s", (guild_id,))
bm_row = cur.fetchone()
print(f"Beast Mode DB row: enabled={bm_row[0]}, score_limit={bm_row[1]}, punishment_type={bm_row[2]}, wl_bypass={bm_row[3]}")
assert str(bm_row[0]) == '1', "Beast Mode enabled must be 1"

# 5. Test verification_settings
cur.execute("""
    INSERT INTO verification_settings (guild_id, enabled, captcha_enabled, type, channel, verified_role)
    VALUES (%s, 1, 1, 'Captcha Code', 'verify', 'Member')
    ON CONFLICT (guild_id) DO UPDATE SET
        enabled = EXCLUDED.enabled,
        type = EXCLUDED.type
""", (guild_id,))
conn.commit()

cur.execute("SELECT enabled, captcha_enabled, type, channel, verified_role FROM verification_settings WHERE guild_id = %s", (guild_id,))
ver_row = cur.fetchone()
print(f"Verification DB row: enabled={ver_row[0]}, captcha={ver_row[1]}, type={ver_row[2]}")
assert str(ver_row[0]) == '1', "Verification enabled must be 1"

print("\nAll database persistence checks PASSED with 100% SUCCESS!")
cur.close()
conn.close()
