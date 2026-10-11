import os
import shutil
import sqlite3

project_dir = os.path.dirname(os.path.abspath(__file__))
assets_dir = os.path.join(project_dir, "web", "public", "assets")
db_dir = os.path.join(project_dir, "database")

avatar_src = os.path.join(assets_dir, "bypass_logs_avatar.webp")
banner_src = os.path.join(assets_dir, "bypass_logs_banner.webp")

avatar_dst_png = os.path.join(assets_dir, "eagle_logo.png")
banner_dst_jpg = os.path.join(assets_dir, "threat-simulation.jpg")

print("--- OVERWRITING LEGACY IMAGES WITH NEW WEBP IMAGES ---")
if os.path.exists(avatar_src):
    shutil.copyfile(avatar_src, avatar_dst_png)
    print(f"Copied {avatar_src} to {avatar_dst_png}")
else:
    print(f"ERROR: {avatar_src} does not exist!")

if os.path.exists(banner_src):
    shutil.copyfile(banner_src, banner_dst_jpg)
    print(f"Copied {banner_src} to {banner_dst_jpg}")
else:
    print(f"ERROR: {banner_src} does not exist!")


def migrate_db(db_name, filename):
    db_path = os.path.join(db_dir, filename)
    if not os.path.exists(db_path):
        print(f"Notice: Database {filename} not found, skipping migration.")
        return

    print(f"\n--- MIGRATING DATABASE: {db_name} ({db_path}) ---")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update guild_bot_profiles table
        # We set nickname to 'VEYRA', and set the default avatar and banner to point to the local files
        # Note: we update all rows to use the new avatar & banner
        cursor.execute("SELECT COUNT(*) FROM guild_bot_profiles")
        count = cursor.fetchone()[0]
        print(f"Found {count} rows in guild_bot_profiles")

        cursor.execute("""
            UPDATE guild_bot_profiles
            SET nickname = 'VEYRA',
                avatar = 'assets/bypass_logs_avatar.webp',
                banner = 'assets/bypass_logs_banner.webp'
        """)
        conn.commit()
        print("Updated guild_bot_profiles rows.")

        # Update ticket_bot_profile table
        cursor.execute("SELECT COUNT(*) FROM ticket_bot_profile")
        count_t = cursor.fetchone()[0]
        print(f"Found {count_t} rows in ticket_bot_profile")

        cursor.execute("""
            UPDATE ticket_bot_profile
            SET name = 'VEYRA',
                avatar = 'assets/bypass_logs_avatar.webp',
                banner = 'assets/bypass_logs_banner.webp'
        """)
        conn.commit()
        print("Updated ticket_bot_profile rows.")

        conn.close()
        print(f"Successfully migrated {filename}!")
    except Exception as e:
        print(f"Error migrating {filename}: {e}")

migrate_db("VEYRA", "VEYRA.db")
migrate_db("SENTRIX", "SENTRIX.db")
print("\nMigration Completed successfully!")
