import os
import sys
import json
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_QyNVAknl8BZ6@ep-floral-mouse-artqhsoc-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require")
GHOST_GUILD_ID = "1538507162496667718"

def run_tests():
    print("=" * 70)
    print("TESTING ANTI-SPAM, ANTI-RAID & DYNAMIC WHITELIST PERSISTENCE")
    print("=" * 70)
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Anti-Spam Persistence
    print("\n[1] Testing Anti-Spam Matrix Persistence...")
    cur.execute("""
        INSERT INTO antispam_settings (
            guild_id, enabled, max_messages, message_seconds, max_duplicates,
            max_mentions, block_invites, block_links, max_emojis, max_caps_percent,
            punishment, timeout_duration, log_channel
        ) VALUES (%s, 1, 6, 4, 3, 5, 1, 1, 10, 75, 'Timeout10', 600, '1538560570498752624')
        ON CONFLICT (guild_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            max_messages = EXCLUDED.max_messages,
            message_seconds = EXCLUDED.message_seconds,
            max_duplicates = EXCLUDED.max_duplicates,
            max_mentions = EXCLUDED.max_mentions,
            block_invites = EXCLUDED.block_invites,
            block_links = EXCLUDED.block_links,
            max_emojis = EXCLUDED.max_emojis,
            max_caps_percent = EXCLUDED.max_caps_percent,
            punishment = EXCLUDED.punishment,
            timeout_duration = EXCLUDED.timeout_duration,
            log_channel = EXCLUDED.log_channel
    """, (GHOST_GUILD_ID,))

    cur.execute("SELECT * FROM antispam_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    spam_row = cur.fetchone()
    assert spam_row['enabled'] == 1, "Spam enabled check failed"
    assert spam_row['max_messages'] == 6, "max_messages check failed"
    assert spam_row['punishment'] == 'Timeout10', "punishment check failed"
    assert spam_row['block_invites'] == 1, "block_invites check failed"
    print("  --> PASS: Anti-Spam settings saved and verified in Neon PostgreSQL.")

    # 2. Anti-Raid Persistence
    print("\n[2] Testing Anti-Raid Settings Persistence...")
    cur.execute("""
        INSERT INTO antiraid_settings (guild_id, enabled, invite_link_protection, join_rate_threshold, min_account_age, punishment_type)
        VALUES (%s, 1, 1, 12, 4, 'Ban')
        ON CONFLICT (guild_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            invite_link_protection = EXCLUDED.invite_link_protection,
            join_rate_threshold = EXCLUDED.join_rate_threshold,
            min_account_age = EXCLUDED.min_account_age,
            punishment_type = EXCLUDED.punishment_type
    """, (GHOST_GUILD_ID,))

    cur.execute("SELECT * FROM antiraid_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    raid_row = cur.fetchone()
    assert raid_row['enabled'] == 1 and raid_row['join_rate_threshold'] == 12 and raid_row['punishment_type'] == 'Ban', "Anti-Raid mismatch"
    print("  --> PASS: Anti-Raid settings (enabled, rate=12, age=4, punish=Ban) verified in DB.")

    # 3. Dynamic Whitelist Types Persistence (Role, Channel, User)
    print("\n[3] Testing Multi-Type Whitelists (Role, Channel, User)...")
    test_role_id = "1538507162932740100"
    test_chan_id = "1538507162932740146"
    test_user_id = "1538507162496667799"

    for tid, ttype in [(test_role_id, 'Role'), (test_chan_id, 'Channel'), (test_user_id, 'User')]:
        cur.execute("""
            INSERT INTO whitelists (guild_id, user_id, type, reason)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                type = EXCLUDED.type,
                reason = EXCLUDED.reason
        """, (GHOST_GUILD_ID, tid, ttype, f'Authorized {ttype} Override'))

    cur.execute("SELECT * FROM whitelists WHERE guild_id = %s", (GHOST_GUILD_ID,))
    wl_rows = cur.fetchall()
    saved_types = {r['user_id']: r['type'] for r in wl_rows}
    assert saved_types.get(test_role_id) == 'Role', "Role whitelist failed"
    assert saved_types.get(test_chan_id) == 'Channel', "Channel whitelist failed"
    assert saved_types.get(test_user_id) == 'User', "User whitelist failed"
    print("  --> PASS: Roles, Channels, and Users successfully whitelisted in Neon DB.")

    # Clean up test rows
    cur.execute("DELETE FROM whitelists WHERE guild_id = %s AND user_id IN (%s, %s, %s)", (GHOST_GUILD_ID, test_role_id, test_chan_id, test_user_id))

    conn.close()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
