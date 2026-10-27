import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_QyNVAknl8BZ6@ep-floral-mouse-artqhsoc-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require")
GHOST_GUILD_ID = "1538507162496667718"
TEST_GUILD_ID = "999999999999999999"

def run_tests():
    print("=" * 70)
    print("VEYRA DISCORD BOT - PERSISTENCE & CONFIGURATION AUDIT SUITE")
    print("=" * 70)
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # ----------------------------------------------------
    # TEST 1: Neon Cloud PostgreSQL Connection & Tables
    # ----------------------------------------------------
    print("\n[TEST 1] Verifying Neon PostgreSQL Connection & Schema...")
    cursor.execute("SELECT count(*) as total FROM information_schema.tables WHERE table_schema = 'public'")
    table_count = cursor.fetchone()['total']
    assert table_count > 50, f"Expected > 50 tables, found {table_count}"
    print(f"  --> PASS: Connected to Neon DB ({table_count} tables verified in public schema).")

    # ----------------------------------------------------
    # TEST 2: Round-Trip Persistence for Ghost Guild
    # ----------------------------------------------------
    print(f"\n[TEST 2] Testing Authoritative Round-Trip Persistence for Guild: {GHOST_GUILD_ID}...")

    # A. Welcome Settings
    cursor.execute("""
        INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET 
            enabled = EXCLUDED.enabled,
            channel = EXCLUDED.channel,
            color = EXCLUDED.color,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            message = EXCLUDED.message
    """, (GHOST_GUILD_ID, 1, "welcome-lounge", "#10b981", "Welcome to GHOST!", "Enjoy your stay in our server.", "Welcome {mention}!"))
    
    cursor.execute("SELECT * FROM welcome_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    w_row = cursor.fetchone()
    assert w_row['enabled'] == 1 and w_row['channel'] == "welcome-lounge" and w_row['color'] == "#10b981", "Welcome settings mismatch"
    print("  --> PASS: welcome_settings saved and verified in DB.")

    # B. Leave Settings
    cursor.execute("""
        INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET 
            enabled = EXCLUDED.enabled,
            channel = EXCLUDED.channel,
            color = EXCLUDED.color,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            message = EXCLUDED.message
    """, (GHOST_GUILD_ID, 1, "goodbye-logs", "#ef4444", "Farewell from GHOST", "User left the realm.", "Goodbye {user}!"))
    
    cursor.execute("SELECT * FROM leave_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    l_row = cursor.fetchone()
    assert l_row['enabled'] == 1 and l_row['channel'] == "goodbye-logs", "Leave settings mismatch"
    print("  --> PASS: leave_settings saved and verified in DB.")

    # C. Anti-Nuke (Security) Settings
    cursor.execute("""
        INSERT INTO antinuke_settings (guild_id, anti_ban_limit, anti_ban_punish, anti_ban_enabled, anti_bot_add_enabled, anti_kick_limit, anti_kick_punish)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET
            anti_ban_limit = EXCLUDED.anti_ban_limit,
            anti_ban_punish = EXCLUDED.anti_ban_punish,
            anti_ban_enabled = EXCLUDED.anti_ban_enabled,
            anti_bot_add_enabled = EXCLUDED.anti_bot_add_enabled,
            anti_kick_limit = EXCLUDED.anti_kick_limit,
            anti_kick_punish = EXCLUDED.anti_kick_punish
    """, (GHOST_GUILD_ID, 3, "Ban", 1, 1, 4, "Kick"))
    
    cursor.execute("SELECT * FROM antinuke_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    sec_row = cursor.fetchone()
    assert sec_row['anti_ban_limit'] == 3 and sec_row['anti_ban_punish'] == "Ban" and sec_row['anti_bot_add_enabled'] == 1, "Antinuke mismatch"
    print("  --> PASS: antinuke_settings saved and verified in DB.")

    # D. Verification Settings
    cursor.execute("""
        INSERT INTO verification_settings (guild_id, enabled, type, channel, verified_role, captcha_timeout)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            type = EXCLUDED.type,
            channel = EXCLUDED.channel,
            verified_role = EXCLUDED.verified_role,
            captcha_timeout = EXCLUDED.captcha_timeout
    """, (GHOST_GUILD_ID, 1, "Captcha Code", "verify", "Member", 90))
    
    cursor.execute("SELECT * FROM verification_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    ver_row = cursor.fetchone()
    assert ver_row['enabled'] == 1 and ver_row['captcha_timeout'] == 90, "Verification mismatch"
    print("  --> PASS: verification_settings saved and verified in DB.")

    # E. Guild Settings & Custom Prefixes
    cursor.execute("""
        INSERT INTO guild_settings (guild_id, prefix, custom_prefixes, disabled_commands)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET
            prefix = EXCLUDED.prefix,
            custom_prefixes = EXCLUDED.custom_prefixes,
            disabled_commands = EXCLUDED.disabled_commands
    """, (GHOST_GUILD_ID, "!", json.dumps(["!", "?"]), json.dumps(["space"])))
    
    cursor.execute("SELECT * FROM guild_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    g_row = cursor.fetchone()
    assert g_row['prefix'] == "!" and "space" in g_row['disabled_commands'], "Guild settings mismatch"
    print("  --> PASS: guild_settings (prefix, custom prefixes, disabled commands) saved and verified in DB.")

    # F. Leveling Settings
    cursor.execute("""
        INSERT INTO leveling_settings (guild_id, enabled, channel, message, level_modulo, min_level, color, title)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            channel = EXCLUDED.channel,
            message = EXCLUDED.message,
            level_modulo = EXCLUDED.level_modulo,
            min_level = EXCLUDED.min_level,
            color = EXCLUDED.color,
            title = EXCLUDED.title
    """, (GHOST_GUILD_ID, 1, "general", "GG {user}, level {lvl} reached!", 1, 1, "#a855f7", "LEVEL UP!"))
    
    cursor.execute("SELECT * FROM leveling_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    lvl_row = cursor.fetchone()
    assert lvl_row['enabled'] == 1 and lvl_row['channel'] == "general", "Leveling settings mismatch"
    print("  --> PASS: leveling_settings saved and verified in DB.")

    # ----------------------------------------------------
    # TEST 3: Multi-Guild Strict Isolation Check
    # ----------------------------------------------------
    print("\n[TEST 3] Testing Multi-Guild Strict Isolation (Ghost vs Test Guild)...")
    
    # Save contrasting settings for TEST_GUILD_ID
    cursor.execute("""
        INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET 
            enabled = EXCLUDED.enabled,
            channel = EXCLUDED.channel,
            color = EXCLUDED.color,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            message = EXCLUDED.message
    """, (TEST_GUILD_ID, 0, "test-disabled-channel", "#000000", "Test Title", "Test Desc", "Test Msg"))

    cursor.execute("""
        INSERT INTO antinuke_settings (guild_id, anti_ban_limit, anti_ban_punish, anti_ban_enabled)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE SET
            anti_ban_limit = EXCLUDED.anti_ban_limit,
            anti_ban_punish = EXCLUDED.anti_ban_punish,
            anti_ban_enabled = EXCLUDED.anti_ban_enabled
    """, (TEST_GUILD_ID, 99, "Kick", 0))

    # Verify GHOST_GUILD_ID is STILL unchanged!
    cursor.execute("SELECT * FROM welcome_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    ghost_w = cursor.fetchone()
    assert ghost_w['enabled'] == 1 and ghost_w['channel'] == "welcome-lounge", "ISOLATION BREACH: Ghost welcome settings modified!"

    cursor.execute("SELECT * FROM antinuke_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    ghost_sec = cursor.fetchone()
    assert ghost_sec['anti_ban_limit'] == 3 and ghost_sec['anti_ban_punish'] == "Ban", "ISOLATION BREACH: Ghost security settings modified!"

    cursor.execute("SELECT * FROM welcome_settings WHERE guild_id = %s", (TEST_GUILD_ID,))
    test_w = cursor.fetchone()
    assert test_w['enabled'] == 0 and test_w['channel'] == "test-disabled-channel", "Test guild settings mismatch"

    print(f"  --> PASS: Guild {GHOST_GUILD_ID} and Guild {TEST_GUILD_ID} are strictly isolated in DB.")

    # ----------------------------------------------------
    # TEST 4: Bot Handler Configuration Loading
    # ----------------------------------------------------
    print("\n[TEST 4] Simulating Bot Handler Configuration Load...")
    # Simulate fetch_welcome_settings as bot/bot.py does:
    cursor.execute("SELECT enabled, channel, color, title, description, message, image, thumbnail, footer FROM welcome_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    bot_w = cursor.fetchone()
    assert bot_w is not None and bot_w['enabled'] == 1, "Bot welcome settings fetch failed"
    print(f"  --> PASS: Bot fetch_welcome_settings reads enabled={bot_w['enabled']}, channel=#{bot_w['channel']}.")

    # Simulate get_prefix as bot/bot.py does:
    cursor.execute("SELECT prefix, custom_prefixes FROM guild_settings WHERE guild_id = %s", (GHOST_GUILD_ID,))
    bot_p = cursor.fetchone()
    prefixes = json.loads(bot_p['custom_prefixes']) if bot_p and bot_p['custom_prefixes'] else [bot_p['prefix']]
    assert "!" in prefixes, "Bot prefix resolution failed"
    print(f"  --> PASS: Bot get_prefix reads prefixes={prefixes}.")

    # Clean up TEST_GUILD_ID test rows
    cursor.execute("DELETE FROM welcome_settings WHERE guild_id = %s", (TEST_GUILD_ID,))
    cursor.execute("DELETE FROM antinuke_settings WHERE guild_id = %s", (TEST_GUILD_ID,))
    
    conn.close()
    print("\n" + "=" * 70)
    print("ALL PERSISTENCE, ISOLATION & BOT SYNC TESTS PASSED! (100% SUCCESS)")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[FATAL TEST FAILURE] {e}")
        sys.exit(1)
