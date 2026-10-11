import discord
import os
import sqlite3
import asyncio

# Read .env file manually to avoid dependency on python-dotenv module
TOKEN = None
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("DISCORD_BOT_TOKEN="):
                TOKEN = stripped.split("=", 1)[1].strip().strip('"').strip("'")

DB_PATH_VEYRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/VEYRA.db"))

def get_db():
    return sqlite3.connect(DB_PATH_VEYRA)

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Connected as {client.user} - Starting Duplicate Cleanup...")
    
    for guild in client.guilds:
        print(f"Processing Guild: {guild.name} ({guild.id})")
        
        # 1. Clean categories
        try:
            fetched_chans = await guild.fetch_channels()
        except Exception as e:
            print(f"Error fetching channels: {e}")
            continue
            
        categories = [c for c in fetched_chans if isinstance(c, discord.CategoryChannel)]
        log_categories = [c for c in categories if c.name.lower() == "veyra logs"]
        
        # Keep the oldest category (smallest ID)
        if len(log_categories) > 1:
            log_categories.sort(key=lambda x: x.id)
            keeper_cat = log_categories[0]
            print(f"Keeping category: {keeper_cat.name} ({keeper_cat.id})")
            for cat in log_categories[1:]:
                try:
                    await cat.delete(reason="Cleanup duplicate categories")
                    print(f"Deleted duplicate category: {cat.name} ({cat.id})")
                except Exception as ex:
                    print(f"Failed to delete category {cat.id}: {ex}")
        elif len(log_categories) == 1:
            keeper_cat = log_categories[0]
        else:
            keeper_cat = None
            
        # 2. Clean channels
        text_channels = [c for c in fetched_chans if isinstance(c, discord.TextChannel)]
        target_names = ["verify", "autoroles", "server-news", "security-logs", "system-logs"]
        
        for name in target_names:
            matching = [c for c in text_channels if c.name.lower() == name]
            if len(matching) > 1:
                # Keep the oldest channel (smallest ID)
                matching.sort(key=lambda x: x.id)
                keeper_chan = matching[0]
                print(f"Keeping channel: #{keeper_chan.name} ({keeper_chan.id})")
                
                # Update DB reference to point to keeper channel ID
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    if name == "verify":
                        cursor.execute("UPDATE verification_settings SET channel = ? WHERE guild_id = ?", (str(keeper_chan.id), str(guild.id)))
                    elif name == "security-logs":
                        cursor.execute("UPDATE guild_settings SET security_logs = ? WHERE guild_id = ?", (str(keeper_chan.id), str(guild.id)))
                    elif name == "system-logs":
                        cursor.execute("UPDATE guild_settings SET moderation_logs = ? WHERE guild_id = ?", (str(keeper_chan.id), str(guild.id)))
                    elif name == "server-news":
                        cursor.execute("UPDATE guild_settings SET updates_channel = ? WHERE guild_id = ?", (str(keeper_chan.id), str(guild.id)))
                    conn.commit()
                    conn.close()
                except Exception as db_ex:
                    print(f"DB update error: {db_ex}")
                    
                # Delete duplicates
                for chan in matching[1:]:
                    try:
                        await chan.delete(reason="Cleanup duplicate channels")
                        print(f"Deleted duplicate channel: #{chan.name} ({chan.id})")
                    except Exception as ex:
                        print(f"Failed to delete channel {chan.id}: {ex}")
                        
    print("Cleanup Finished!")
    await client.close()

if __name__ == "__main__":
    if TOKEN:
        client.run(TOKEN)
    else:
        print("Error: No DISCORD_BOT_TOKEN found in .env file.")
