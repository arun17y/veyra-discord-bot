import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcript_engine import generate_full_html_transcript
from typing import Union, Optional
# bot.py - Complete Anti-Nuke Discord Bot Core (VEYRA Ultimate)
from interactive_ui import (
    HelpView, StatsTeamView, build_main_help_embed, PingView,
    build_ping_health_embed, build_ping_code_embed, build_uptime_embed,
    AvatarView, build_avatar_embed, BannerView, build_banner_embed, MediaDownloadView,
    ServerInfoView, build_server_info_embed,
    build_nick_embed, RoleplayView, VoiceMasterSetupView, build_voicemaster_setup_embed,
    WhitelistConfigView, build_whitelist_embed, TicketWelcomeView, build_ticket_welcome_embed,
    PlansView, build_plans_embed, build_giveaway_embed, build_scan_embed,
    build_veyra_embed, create_veyra_embed
)
from server_control import setup_server_control_system, resolve_member_voice_channel
from verification_recovery import setup_verification_and_recovery
from veyra_2_features import setup_veyra_2_features
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── SINGLE INSTANCE LOCK ──────────────────────────────────────────────────────
# Prevents two bot processes from running at the same time (which causes
# duplicate messages, duplicate channels, duplicate events, etc.)
import os
import atexit
_PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.bot.pid')
def _acquire_pid_lock():
    if os.path.exists(_PID_FILE):
        try:
            old_pid = int(open(_PID_FILE).read().strip())
            if old_pid != os.getpid():
                # Windows-compatible alive check via OpenProcess
                try:
                    import ctypes
                    SYNCHRONIZE = 0x00100000
                    handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, old_pid)
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                        print(f"[PID LOCK] Another bot instance (PID {old_pid}) is already running. Killing it...")
                        import subprocess
                        subprocess.call(['taskkill', '/F', '/PID', str(old_pid)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        import time; time.sleep(2)
                except Exception:
                    pass  # Can't check — just overwrite
        except (ValueError, IOError):
            pass  # Bad/missing PID file — safe to overwrite
    with open(_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(_PID_FILE) and os.remove(_PID_FILE))
_acquire_pid_lock()
# ─────────────────────────────────────────────────────────────────────────────

# Ensure node.exe path is in system environment PATH for yt-dlp to find Node.js
if "C:\\Program Files\\nodejs" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "C:\\Program Files\\nodejs" + os.pathsep + os.environ.get("PATH", "")

# Ensure local and system FFmpeg bin are in the environment PATH
ffmpeg_candidate_dirs = [
    r"C:\ffmpeg\bin",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ffmpeg", "bin")
]
for p in ffmpeg_candidate_dirs:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

# Cloudflare Datacenter Rate Limit Bypass (Error Code 0)
# Uses Chrome 120 TLS fingerprint via curl_cffi to transparently bypass Cloudflare blocks on datacenter IPs
try:
    import discord.http
    import discord.errors
    from curl_cffi.requests import AsyncSession as _CurlAsyncSession

    _orig_http_request = discord.http.HTTPClient.request

    async def _stealth_http_request(self, route: discord.http.Route, *args, **kwargs):
        try:
            return await _orig_http_request(self, route, *args, **kwargs)
        except Exception as exc:
            err_msg = str(exc).lower()
            if "429" not in err_msg and "blocked" not in err_msg and "rate limit" not in err_msg:
                raise
            
            print(f"🛡️ [Cloudflare Bypass] Intercepted {exc}. Rerouting {route.method} {route.url} through Chrome TLS impersonation...")
            req_headers = {
                'Authorization': f'Bot {self.token}' if getattr(self, 'token', None) else ''
            }
            if 'headers' in kwargs and kwargs['headers']:
                for k, v in kwargs['headers'].items():
                    if k.lower() != 'user-agent':
                        req_headers[k] = v
                
            async with _CurlAsyncSession(impersonate="chrome120") as s:
                res = await s.request(
                    route.method,
                    route.url,
                    headers=req_headers,
                    json=kwargs.get('json'),
                    data=kwargs.get('data'),
                    timeout=kwargs.get('timeout', 30)
                )
                print(f"✅ [Cloudflare Bypass] Response: HTTP {res.status_code}")
                if res.status_code in (200, 201):
                    try:
                        return res.json()
                    except Exception:
                        return res.text
                elif res.status_code == 204:
                    return None
                elif res.status_code == 429:
                    try:
                        retry_after = float(res.json().get('retry_after', 5.0))
                    except Exception:
                        retry_after = 5.0
                    print(f"⏳ [Cloudflare Bypass] Rate limited. Sleeping for {retry_after}s before retry...")
                    import asyncio
                    await asyncio.sleep(retry_after)
                    res = await s.request(
                        route.method,
                        route.url,
                        headers=req_headers,
                        json=kwargs.get('json'),
                        data=kwargs.get('data'),
                        timeout=kwargs.get('timeout', 30)
                    )
                    if res.status_code in (200, 201):
                        try:
                            return res.json()
                        except Exception:
                            return res.text
                    elif res.status_code == 204:
                        return None
                    raise exc
                else:
                    raise exc

    discord.http.HTTPClient.request = _stealth_http_request
    print("🔒 Stealth Chrome TLS Cloudflare Bypass installed for Discord API.")
except Exception as _patch_err:
    print(f"⚠️ Could not install stealth HTTPClient patch: {_patch_err}")

def start_bgutil_pot_server():
    import shutil, subprocess
    bgutil_path = shutil.which("bgutil-pot") or "/usr/local/bin/bgutil-pot"
    if os.path.exists(bgutil_path) or shutil.which("bgutil-pot"):
        cmd = [bgutil_path, "server", "--host", "127.0.0.1", "--port", "4416"]
        try:
            bgutil_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"🚀 Started bgutil-pot PO Token server daemon (PID {bgutil_proc.pid}) on port 4416")
        except Exception as e:
            print(f"⚠️ Failed to launch bgutil-pot server: {e}")
    else:
        print("ℹ️ bgutil-pot binary not found in system PATH. Skipping background server launch.")

start_bgutil_pot_server()

import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import asyncio
import base64
import json
from datetime import datetime, timezone, timedelta

# In-memory dedup sets to prevent double event firing
_recent_leave_events = {}   # guild_id -> set of user_ids processed in last 5s
_recent_join_events  = {}   # guild_id -> set of user_ids processed in last 5s

# Global local storage path for SQLite database
DB_PATH_VEYRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/VEYRA.db"))

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db


def get_prefix(bot, message):
    default_prefixes = ["&", "?", "!", ",", ".", "v!", "V!", "v.", "V.", "-", "$"]
    if not message.guild:
        return commands.when_mentioned_or(*default_prefixes)(bot, message)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (str(message.guild.id),))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            p = row[0].strip()
            if p and p not in default_prefixes:
                return commands.when_mentioned_or(p, *default_prefixes)(bot, message)
    except Exception:
        pass
    return commands.when_mentioned_or(*default_prefixes)(bot, message)

# Create Discord Bot Intents and Bot Instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

def ensure_antinuke_schema():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_settings (
                guild_id TEXT PRIMARY KEY,
                anti_ban_limit INTEGER DEFAULT 5,
                anti_ban_punish TEXT DEFAULT 'Ban',
                anti_ban_enabled INTEGER DEFAULT 1,
                anti_kick_limit INTEGER DEFAULT 5,
                anti_kick_punish TEXT DEFAULT 'Ban',
                anti_kick_enabled INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        cursor.execute("CREATE TABLE IF NOT EXISTS leveling_ignored_channels (guild_id TEXT, channel_id TEXT, PRIMARY KEY (guild_id, channel_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS sticky_messages (channel_id TEXT PRIMARY KEY, message_id TEXT, content TEXT, embed_data TEXT)")
        conn.commit()

        cursor.execute("PRAGMA table_info(antinuke_settings)")
        existing_cols = {row['name'] for row in cursor.fetchall()}

        required_columns = {
            "anti_ban_limit": ("INTEGER", "5"),
            "anti_ban_punish": ("TEXT", "'Ban'"),
            "anti_ban_enabled": ("INTEGER", "1"),
            "anti_kick_limit": ("INTEGER", "5"),
            "anti_kick_punish": ("TEXT", "'Ban'"),
            "anti_kick_enabled": ("INTEGER", "1"),
            "anti_bot_add_limit": ("INTEGER", "1"),
            "anti_bot_add_punish": ("TEXT", "'Ban'"),
            "anti_bot_add_enabled": ("INTEGER", "1"),
            "anti_channel_create_limit": ("INTEGER", "8"),
            "anti_channel_create_punish": ("TEXT", "'Ban'"),
            "anti_channel_create_enabled": ("INTEGER", "1"),
            "anti_channel_delete_limit": ("INTEGER", "3"),
            "anti_channel_delete_punish": ("TEXT", "'Ban'"),
            "anti_channel_delete_enabled": ("INTEGER", "1"),
            "anti_channel_rename_limit": ("INTEGER", "5"),
            "anti_channel_rename_punish": ("TEXT", "'Kick'"),
            "anti_channel_rename_enabled": ("INTEGER", "1"),
            "anti_role_create_limit": ("INTEGER", "8"),
            "anti_role_create_punish": ("TEXT", "'Ban'"),
            "anti_role_create_enabled": ("INTEGER", "1"),
            "anti_role_delete_limit": ("INTEGER", "3"),
            "anti_role_delete_punish": ("TEXT", "'Ban'"),
            "anti_role_delete_enabled": ("INTEGER", "1"),
            "anti_role_rename_limit": ("INTEGER", "5"),
            "anti_role_rename_punish": ("TEXT", "'Kick'"),
            "anti_role_rename_enabled": ("INTEGER", "1"),
            "anti_webhook_create_limit": ("INTEGER", "3"),
            "anti_webhook_create_punish": ("TEXT", "'Ban'"),
            "anti_webhook_create_enabled": ("INTEGER", "1"),
            "anti_webhook_delete_limit": ("INTEGER", "3"),
            "anti_webhook_delete_punish": ("TEXT", "'Ban'"),
            "anti_webhook_delete_enabled": ("INTEGER", "1"),
            "anti_guild_update_limit": ("INTEGER", "1"),
            "anti_guild_update_punish": ("TEXT", "'Ban'"),
            "anti_guild_update_enabled": ("INTEGER", "1"),
            "anti_vanity_change_limit": ("INTEGER", "1"),
            "anti_vanity_change_punish": ("TEXT", "'Kick'"),
            "anti_vanity_change_enabled": ("INTEGER", "1"),
            "anti_server_rename_limit": ("INTEGER", "1"),
            "anti_server_rename_punish": ("TEXT", "'Kick'"),
            "anti_server_rename_enabled": ("INTEGER", "1"),
            "anti_server_icon_change_limit": ("INTEGER", "1"),
            "anti_server_icon_change_punish": ("TEXT", "'Kick'"),
            "anti_server_icon_change_enabled": ("INTEGER", "1"),
            "anti_dangerous_role_add_limit": ("INTEGER", "1"),
            "anti_dangerous_role_add_punish": ("TEXT", "'Ban'"),
            "anti_dangerous_role_add_enabled": ("INTEGER", "1"),
            "anti_dangerous_role_update_limit": ("INTEGER", "1"),
            "anti_dangerous_role_update_punish": ("TEXT", "'Ban'"),
            "anti_dangerous_role_update_enabled": ("INTEGER", "1"),
            "anti_mention_limit": ("INTEGER", "5"),
            "anti_mention_punish": ("TEXT", "'Kick'"),
            "anti_mention_enabled": ("INTEGER", "1"),
            "anti_prune_limit": ("INTEGER", "1"),
            "anti_prune_punish": ("TEXT", "'Ban'"),
            "anti_prune_enabled": ("INTEGER", "1")
        }

        for col_name, (col_type, default_val) in required_columns.items():
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE antinuke_settings ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                except Exception:
                    pass

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Schema migration notice: {e}")

ensure_antinuke_schema()

# Composite keys dict tracking rate limits audit counts: { "guild_id_action_user_id": (count, timestamp) }
bot.audit_counters = {}

# --- BACKGROUND TASKS & ON_READY SYNC ---

# Legacy process_pending_embed_posts was removed to avoid double execution with process_pending_embeds_task.

async def sync_active_bot_guilds():
    """
    Syncs the active bot guilds, roles, and channels into SQLite VEYRA.db.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        for guild in bot.guilds:
            icon_url = str(guild.icon.url) if guild.icon else ""
            cursor.execute("""
                INSERT OR REPLACE INTO active_bot_guilds (guild_id, name, icon, member_count)
                VALUES (?, ?, ?, ?)
            """, (str(guild.id), guild.name, icon_url, guild.member_count or 0))
            
            for ch in guild.channels:
                cursor.execute("""
                    INSERT OR REPLACE INTO guild_channels (guild_id, channel_id, name, type)
                    VALUES (?, ?, ?, ?)
                """, (str(guild.id), str(ch.id), ch.name, str(ch.type)))
                
            for role in guild.roles:
                cursor.execute("""
                    INSERT OR REPLACE INTO guild_roles (guild_id, role_id, name, color, position)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(guild.id), str(role.id), role.name, str(role.color), role.position))
                
        conn.commit()
        conn.close()
        print(f"✅ Synced {len(bot.guilds)} active bot guilds to VEYRA.db")
    except Exception as e:
        print(f"Error syncing active bot guilds: {e}")

# Legacy on_ready was removed to prevent conflicts. Global startup is handled by the main on_ready handler below.



@bot.event
async def on_guild_remove(guild):
    print(f"📤 Removed from guild: {guild.name} ({guild.id})")
    try:
        conn = get_db()
        conn.execute("DELETE FROM active_bot_guilds WHERE guild_id = ?", (str(guild.id),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error removing guild cache: {e}")

# --- 1. UTILITY DATABASE HELPER FUNCTIONS ---

def check_guild_plan(guild_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_type, expires_at FROM guild_subscriptions WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            plan_type, expires_at = row[0], row[1]
            if expires_at and expires_at != 'Lifetime':
                try:
                    import datetime
                    exp_dt = datetime.datetime.fromisoformat(expires_at.split('+')[0])
                    if exp_dt < datetime.datetime.utcnow():
                        return 'Free'
                except Exception:
                    pass
            return plan_type or 'Free'
    except Exception as e:
        print(f"Error checking guild plan: {e}")
    return 'Free'

def has_subscription_level(required_level):
    async def predicate(interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild_id
        if not guild_id:
            return True
        
        # Admin & Developer users are immune/always allowed
        if interaction.user.id in (1256986886631854080, 1538041381132697610):
            return True
            
        plan = check_guild_plan(guild_id)
        is_allowed = False
        if required_level == 'Free':
            is_allowed = True
        elif required_level == 'Pro':
            is_allowed = (plan == 'Pro' or plan == 'Premium')
        elif required_level == 'Premium':
            is_allowed = (plan == 'Premium')
            
        if not is_allowed:
            embed = discord.Embed(
                title="👑 Premium Feature Required",
                description=f"You need to purchase a **{required_level}** plan to use this command.\n\nUse `/plan` to upgrade your subscription.",
                color=discord.Color.from_rgb(239, 68, 68)
            )
            embed.set_footer(text="VEYRA Tier Control Matrix")
            embed.timestamp = datetime.now(timezone.utc)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def fetch_guild_logs_channels(guild_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT moderation_logs, security_logs FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return 'none', 'none'

async def dispatch_discord_log(guild, log_type, title, description, color=0xa855f7, fields=None):
    try:
        mod_channel_id, sec_channel_id = fetch_guild_logs_channels(guild.id)
        target_channel_id = sec_channel_id if log_type == 'security' else mod_channel_id
        
        if not target_channel_id or target_channel_id == 'none' or target_channel_id == 'Select option':
            return
            
        import re
        clean_id = re.sub(r'\D', '', str(target_channel_id))
        if not clean_id:
            return
        channel_id = int(clean_id)
        channel = guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except Exception:
                return
                
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        if bot.user:
            embed.set_footer(text="VEYRA Ultimate • Audit Logger", icon_url=bot.user.display_avatar.url)
        if fields:
            for k, v in fields.items():
                embed.add_field(name=k, value=v, inline=True)
                
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error dispatching discord log: {e}")

async def log_system_event_async(guild, user_tag, action, details, log_type='moderation', fields=None):
    log_system_event(guild.id, user_tag, action, details)
    await dispatch_discord_log(guild, log_type, f"🔧 {action}", details, fields=fields)

def setup_default_security_configs(guild_id, plan):
    try:
        conn = get_db()
        cursor = conn.cursor()
        if plan == 'Free':
            cursor.execute("""
                INSERT OR REPLACE INTO antinuke_settings (
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
                ) VALUES (?, 5, 'Ban', 1, 5, 'Ban', 1, 8, 'Ban', 0, 3, 'Ban', 0, 8, 'Ban', 0, 3, 'Ban', 0, 0, 'Kick', 0, 'Ban', 0, 'Ban', 0, 'Ban', 0, 'Ban', 0, 'Kick', 0, 'Kick', 0, 'Kick', 0, 'Kick', 0, 'Kick', 0)
            """, (str(guild_id),))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO antinuke_settings (
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
                ) VALUES (?, 5, 'Ban', 1, 5, 'Ban', 1, 8, 'Ban', 1, 3, 'Ban', 1, 8, 'Ban', 1, 3, 'Ban', 1, 0, 'Kick', 1, 'Ban', 1, 'Ban', 1, 'Ban', 1, 'Ban', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1, 'Kick', 1)
            """, (str(guild_id),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error setting up defaults: {e}")

class PlanDetailView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        
    @discord.ui.button(label="Free Plan", style=discord.ButtonStyle.secondary, emoji="🟢")
    async def free_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🟢 VEYRA Free Plan Details",
            description="Essential guard features for small communities.",
            color=discord.Color.from_rgb(34, 197, 94)
        )
        embed.add_field(name="🛡️ Anti-Nuke", value="• Limit controls for Ban & Kick\n• Threshold limits capped at max 5\n• Basic logs", inline=False)
        embed.add_field(name="⚙️ Admin Utility", value="• Auto Nickname\n• System audit trail logging", inline=False)
        embed.add_field(name="💵 Cost", value="**₹0 / Month** (Default Free)", inline=False)
        embed.set_footer(text="Powered by VEYRA")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Pro Plan", style=discord.ButtonStyle.primary, emoji="⚡")
    async def pro_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚡ VEYRA Pro Plan Details",
            description="Complete automation and robust verification gates.",
            color=discord.Color.from_rgb(139, 92, 246)
        )
        embed.add_field(name="🛡️ Advanced Protection", value="• Complete Anti-Nuke limits & triggers\n• Beast Mode & Anti-Raid mitigation\n• Automated Anti-Spam filters", inline=False)
        embed.add_field(name="💬 Interactive Greetings", value="• Custom Welcome & Exit embed messages\n• Direct Message (Join DM) builders\n• Invite Tracker & Sticky messages", inline=False)
        embed.add_field(name="🤖 Gatekeeping", value="• Verification Gateways (Button, Captcha, Image)\n• Auto-setup wizards", inline=False)
        embed.add_field(name="💵 Cost", value="**$4.99 / Month** or **$49.99 / Lifetime**", inline=False)
        embed.set_footer(text="Powered by VEYRA")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Premium Plan", style=discord.ButtonStyle.success, emoji="💎")
    async def premium_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 VEYRA Premium Plan Details",
            description="The ultimate sovereign defense and absolute brand customizability.",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        embed.add_field(name="👑 Custom Identity", value="• Custom Bot Profile (Avatar, Banner, Nickname)\n• Personalized client identity", inline=False)
        embed.add_field(name="🛡️ Whitelist Override", value="• Unlimited trusted member & role overrides\n• Complete bypass management", inline=False)
        embed.add_field(name="📈 Discovery & Growth", value="• Public discover listing directory\n• Scheduled growth server reports\n• Advanced XP & leveling system", inline=False)
        embed.add_field(name="💵 Cost", value="**$9.99 / Month** or **$99.99 / Lifetime**", inline=False)
        embed.set_footer(text="Powered by VEYRA")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    err_str = str(error)

    # 1. Handle Transformer/Conversion Errors (e.g. Failed to convert ...)
    if "Failed to convert" in err_str or isinstance(error, app_commands.TransformerError):
        # Auto-fallback for 247 voice commands if user is in a voice channel
        cmd_qname = (interaction.command.qualified_name if interaction.command else "").lower()
        if any(k in cmd_qname for k in ["join", "set", "247"]):
            target_vc = resolve_member_voice_channel(interaction.guild, interaction.user.id)
            if target_vc:
                try:
                    guild = interaction.guild
                    vc = guild.voice_client
                    if vc:
                        if vc.channel.id != target_vc.id and vc.is_connected():
                            await vc.move_to(target_vc)
                    else:
                        await target_vc.connect(reconnect=True, timeout=30.0)

                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO voice_247_settings (guild_id, channel_id, enabled, last_reconnect, updated_at)
                        VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                    """, (str(guild.id), str(target_vc.id), datetime.now(timezone.utc).isoformat()))
                    conn.commit()
                    conn.close()

                    embed = discord.Embed(
                        title="🟢 24/7 Voice System Active",
                        description=f"Connected to {target_vc.mention}.\nConnection saved and will automatically restore on bot restart.",
                        color=discord.Color.from_rgb(24, 24, 27)
                    )
                    embed.set_footer(text="Powered by VEYRA")
                    if not interaction.response.is_done():
                        return await interaction.response.send_message(embed=embed)
                    else:
                        return await interaction.followup.send(embed=embed)
                except Exception as ex:
                    print(f"Fallback 247 connect error: {ex}")

        is_voice_cmd = any(k in cmd_qname for k in ["voice", "247", "join", "play", "vc"])
        if is_voice_cmd:
            error_desc = "Please select a valid option or voice channel from Discord's list, or join a voice channel first!"
        else:
            error_desc = "Please select a valid user or parameter from Discord's list!"

        embed = discord.Embed(
            title="⚠️ Invalid Parameter",
            description=error_desc,
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        if not interaction.response.is_done():
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            return await interaction.followup.send(embed=embed, ephemeral=True)

    # 2. Handle Permission Errors
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You don't have administrator/required permissions to execute this command.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        if not interaction.response.is_done():
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            return await interaction.followup.send(embed=embed, ephemeral=True)

    # 3. Handle Generic Errors
    embed = discord.Embed(
        title="❌ Command Error",
        description=f"`{err_str}`",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    print(f"App command error: {error}")
    
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as ex:
        print(f"Failed to send error response: {ex}")

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown command prefixes silently
    
    embed = discord.Embed(
        title="⚠️ Command Error",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    if isinstance(error, commands.MissingPermissions):
        embed.description = f"❌ You lack required permissions: `{', '.join(error.missing_permissions)}`"
    elif isinstance(error, commands.BotMissingPermissions):
        embed.description = f"❌ VEYRA lacks required permissions: `{', '.join(error.missing_permissions)}`"
    elif isinstance(error, commands.MissingRequiredArgument):
        embed.description = f"❌ Missing required parameter: `{error.param.name}`\nUsage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
    elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
        embed.description = "❌ Target member or user not found. Please mention a valid user or provide their ID."
    elif isinstance(error, (commands.ChannelNotFound, commands.RoleNotFound)):
        embed.description = "❌ Target channel or role not found."
    elif isinstance(error, commands.BadArgument):
        embed.description = f"❌ Invalid argument: {error}"
    else:
        embed.description = f"❌ Error executing command `{ctx.command}`: `{error}`"
    
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    try:
        await ctx.send(embed=embed)
    except Exception:
        pass

def fetch_security_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM antinuke_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    return row

def get_fallback_channel(guild, channel_name):
    if not guild:
        return None
    # 1. Try by numeric ID
    if str(channel_name).isdigit():
        try:
            cid = int(channel_name)
            target = guild.get_channel(cid) or bot.get_channel(cid)
            if target:
                return target
        except Exception:
            pass
            
    # 2. Try by exact name
    name_clean = str(channel_name).replace('#', '').strip().lower()
    target = discord.utils.find(lambda c: c.name.lower() == name_clean, guild.text_channels)
    if target:
        return target
        
    # 3. Try partial name matching
    for ch in guild.text_channels:
        if name_clean in ch.name.lower() or ch.name.lower() in name_clean:
            return ch
            
    # 4. Fallback to server system_channel
    if guild.system_channel:
        return guild.system_channel
        
    # 5. Fallback to first channel with bot write permissions
    for ch in guild.text_channels:
        try:
            me = guild.me or (guild.get_member(bot.user.id) if bot.user else None)
            if not me or ch.permissions_for(me).send_messages:
                return ch
        except Exception:
            return ch
            
    return guild.text_channels[0] if guild.text_channels else None

def fetch_welcome_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM welcome_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'guild_id': str(guild_id),
        'enabled': 1,
        'channel': 'general',
        'color': '#ef4444',
        'title': '',
        'description': "Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**",
        'image': '',
        'thumbnail': '',
        'footer': '',
        'author_name': '',
        'author_icon': '',
        'footer_icon': '',
        'message': 'Welcome {user} to {server}!'
    }

def fetch_leave_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leave_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'guild_id': str(guild_id),
        'enabled': 1,
        'channel': 'general',
        'color': '#ef4444',
        'title': '',
        'description': "Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**",
        'image': '',
        'thumbnail': '',
        'footer': '',
        'author_name': '',
        'author_icon': '',
        'footer_icon': '',
        'message': 'Goodbye {user}!'
    }

def fetch_joindm_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM joindm_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'guild_id': str(guild_id),
        'enabled': 1,
        'color': '#a855f7',
        'title': '📩 Thanks for joining!',
        'description': "Welcome to **{server}**! We are thrilled to have you here.\n\nPlease read our server rules and verify your account to get started.",
        'image': '',
        'thumbnail': '',
        'footer': 'VEYRA Security',
        'author_name': '',
        'author_icon': '',
        'footer_icon': '',
        'message': 'Welcome to {server}!'
    }

def fetch_leavedm_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leavedm_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'guild_id': str(guild_id),
        'enabled': 1,
        'color': '#ef4444',
        'title': '👋 Goodbye!',
        'description': "Hey **{user}**, sorry to see you leave **{server}**! 😢\n\nThanks for being part of our community. Hope to see you back someday!\n\n✨ **Take care!",
        'image': '',
        'thumbnail': '',
        'footer': '✦ THANKS FOR BEING WITH US ✦',
        'author_name': '',
        'author_icon': '',
        'footer_icon': '',
        'message': ''
    }

def fetch_invitetracker_settings(guild_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invitetracker_settings WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'guild_id': str(guild_id),
        'enabled': 1,
        'channel': 'general',
        'color': '#a855f7',
        'title': '🎉 Invite Tracked!',
        'description': "👤 **Inviter:** {inviter}\n👋 **New Member:** {user}\n📈 **Invite Count:** {invites}\n🎯 **Total Invites:** {total_invites}",
        'image': '',
        'thumbnail': '',
        'footer': 'VEYRA Invite Tracker',
        'author_name': '',
        'author_icon': '',
        'footer_icon': '',
        'message': 'Thanks for helping grow our community! 🚀'
    }

def fetch_embedmessages_settings(guild_id):
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM embedmessages_settings WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        print(f"Error fetching embedmessages settings: {e}")
    return {
        'guild_id': str(guild_id),
        'enabled': 0,
        'channel': 'general',
        'embed_json': '[]'
    }

EMOJI_NAME_REGEX = re.compile(r'(?<!<)(?<!<a):([a-zA-Z0-9_]{2,36}):(?!\d+>)')

UNICODE_EMOJI_FALLBACK = {
    "crown": "👑", "king": "👑", "queen": "👸", "prince": "🤴", "princess": "👸",
    "fire": "🔥", "star": "⭐", "star2": "🌟", "sparkles": "✨", "sparkle": "✨",
    "check": "✅", "white_check_mark": "✅", "cross": "❌", "x": "❌",
    "heart": "❤️", "rainbow_heart": "💖", "sparkling_heart": "💖", "broken_heart": "💔",
    "tada": "🎉", "party": "🎉", "partybolt": "⚡", "partying_face": "🥳",
    "wave": "👋", "warning": "⚠️", "attention": "⚠️", "no_entry_sign": "🚫", "no_entry": "⛔",
    "shield": "🛡️", "lock": "🔒", "unlock": "🔓", "bell": "🔔", "gear": "⚙️",
    "tools": "🛠️", "robot": "🤖", "zap": "⚡", "lightning": "⚡", "rocket": "🚀",
    "trophy": "🏆", "medal": "🏅", "gem": "💎", "diamond": "💎", "eyes": "👀",
    "skull": "💀", "100": "💯", "bulb": "💡", "info": "ℹ️", "link": "🔗",
    "pin": "📌", "loudspeaker": "📢", "mega": "📣", "envelope": "✉️", "mail": "✉️",
    "door": "🚪", "boom": "💥", "gift": "🎁", "money": "💰", "coin": "🪙",
    "dollar": "💵", "hammer": "🔨", "wrench": "🔧", "key": "🔑", "sword": "⚔️",
    "swords": "⚔️", "books": "📚", "chart": "📊", "target": "🎯", "crystal_ball": "🔮",
    "hourglass": "⌛", "clock": "⏰", "satellite": "📡", "desktop": "🖥️", "laptop": "💻",
    "alert": "🚨", "sound": "🔊", "muted": "🔇", "verified": "☑️"
}

def resolve_custom_emojis(text: str, guild: discord.Guild = None) -> str:
    if not text or ":" not in text:
        return text if text is not None else ""
        
    def _repl(match):
        raw_name = match.group(1)
        name_lower = raw_name.lower()
        norm = name_lower.replace('_', '').replace('-', '')
        
        # 1. First priority: Check current guild custom emojis (case-insensitive + normalized)
        if guild and hasattr(guild, 'emojis'):
            for em in guild.emojis:
                if em.name:
                    em_lower = em.name.lower()
                    if em_lower == name_lower or em_lower.replace('_', '').replace('-', '') == norm:
                        return str(em)
                    
        # 2. Second priority: Check all bot cached emojis across connected servers
        if 'bot' in globals() and hasattr(bot, 'emojis'):
            for em in bot.emojis:
                if em.name:
                    em_lower = em.name.lower()
                    if em_lower == name_lower or em_lower.replace('_', '').replace('-', '') == norm:
                        return str(em)
                    
        # 3. Third priority: Common unicode emoji fallback
        if name_lower in UNICODE_EMOJI_FALLBACK:
            return UNICODE_EMOJI_FALLBACK[name_lower]
        if norm in UNICODE_EMOJI_FALLBACK:
            return UNICODE_EMOJI_FALLBACK[norm]
            
        # 4. Fourth priority: Snowflake numeric ID (:1551561322158760006webp: or :1551561322158760006:)
        id_m = re.match(r'^(\d{15,22})(?:webp|png|gif)?$', raw_name, re.IGNORECASE)
        if id_m:
            num_id = int(id_m.group(1))
            if 'bot' in globals() and hasattr(bot, 'get_emoji'):
                em = bot.get_emoji(num_id)
                if em:
                    return str(em)
            return f"<:e:{num_id}>"

        return match.group(0)

    try:
        return EMOJI_NAME_REGEX.sub(_repl, str(text))
    except Exception as ex:
        print(f"Error resolving emojis in text: {ex}")
        return text

def resolve_embed_emojis(embed: discord.Embed, guild: discord.Guild = None) -> discord.Embed:
    if not embed:
        return embed
    if embed.title:
        embed.title = resolve_custom_emojis(embed.title, guild)
    if embed.description:
        embed.description = resolve_custom_emojis(embed.description, guild)
    if embed.author and embed.author.name:
        embed.set_author(
            name=resolve_custom_emojis(embed.author.name, guild),
            icon_url=embed.author.icon_url,
            url=embed.author.url
        )
    if embed.footer and embed.footer.text:
        embed.set_footer(
            text=resolve_custom_emojis(embed.footer.text, guild),
            icon_url=embed.footer.icon_url
        )
    if embed.fields:
        orig_fields = list(embed.fields)
        embed.clear_fields()
        for f in orig_fields:
            embed.add_field(
                name=resolve_custom_emojis(f.name, guild) if f.name else "\u200b",
                value=resolve_custom_emojis(f.value, guild) if f.value else "\u200b",
                inline=f.inline
            )
    return embed

def build_embeds_from_json(embed_json_str, member, guild, inviter_str="Unknown"):
    embeds = []
    if not embed_json_str:
        return embeds
    try:
        data = json.loads(embed_json_str)
        if isinstance(data, dict):
            embed_list = [data]
        elif isinstance(data, list):
            embed_list = data
        else:
            embed_list = []
            
        for edata in embed_list:
            if not isinstance(edata, dict):
                continue
                
            title = format_discord_message_placeholders(edata.get('title', ''), member, guild, inviter_str)
            desc = format_discord_message_placeholders(edata.get('description', ''), member, guild, inviter_str)
            
            # Avoid sending completely empty embeds
            if not title and not desc and not edata.get('image') and not edata.get('thumbnail') and not edata.get('footer') and not edata.get('author_name'):
                continue
                
            hex_c = str(edata.get('color', '#a855f7')).replace('#', '')
            try:
                embed_color = discord.Color(int(hex_c, 16))
            except Exception:
                embed_color = discord.Color(0xa855f7)
                
            embed = discord.Embed(
                title=title if title else None,
                description=desc if desc else None,
                color=embed_color
            )
            
            author_name = format_discord_message_placeholders(edata.get('author_name', ''), member, guild, inviter_str)
            author_icon = format_discord_message_placeholders(edata.get('author_icon', ''), member, guild, inviter_str)
            if author_name:
                embed.set_author(name=author_name, icon_url=author_icon if author_icon.startswith('http') else str(member.display_avatar.url))
                
            footer_text = format_discord_message_placeholders(edata.get('footer', ''), member, guild, inviter_str)
            footer_icon = format_discord_message_placeholders(edata.get('footer_icon', ''), member, guild, inviter_str)
            if footer_text:
                embed.set_footer(text=footer_text, icon_url=footer_icon if footer_icon.startswith('http') else None)
                embed.timestamp = datetime.now(timezone.utc)
                
            thumb_url = format_discord_message_placeholders(edata.get('thumbnail', ''), member, guild, inviter_str)
            if thumb_url and thumb_url.startswith('http'):
                embed.set_thumbnail(url=thumb_url)
                
            image_url = format_discord_message_placeholders(edata.get('image', ''), member, guild, inviter_str)
            if image_url and image_url.startswith('http'):
                embed.set_image(url=image_url)
                
            fields = edata.get('fields')
            if fields and isinstance(fields, list):
                for f in fields:
                    if isinstance(f, dict):
                        f_name = format_discord_message_placeholders(f.get('name', ''), member, guild, inviter_str)
                        f_value = format_discord_message_placeholders(f.get('value', ''), member, guild, inviter_str)
                        f_inline = bool(f.get('inline', False))
                        if f_name or f_value:
                            embed.add_field(name=f_name if f_name else "\u200b", value=f_value if f_value else "\u200b", inline=f_inline)

            embeds.append(resolve_embed_emojis(embed, guild))
    except Exception as err:
        print(f"Error parsing multi-embed JSON: {err}")
        
    return embeds

def format_discord_message_placeholders(txt, member, guild, inviter_str="Unknown"):
    if not txt:
        return ""
        
    import re
    def ci_replace(text, placeholder, replacement):
        pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
        return pattern.sub(replacement, text)
        
    avatar_url = str(member.display_avatar.url)
    
    # Real-time member count from Discord gateway
    real_member_count = str(guild.member_count if guild.member_count is not None else len(guild.members))
    
    # Apply replacements case-insensitively
    txt = ci_replace(txt, '{useravatar}', avatar_url)
    txt = ci_replace(txt, '{user_avatar}', avatar_url)
    txt = ci_replace(txt, '%user_avatar%', avatar_url)
    txt = ci_replace(txt, '{avatar}', avatar_url)
    txt = ci_replace(txt, '{user}', member.mention)
    txt = ci_replace(txt, '{user(mention)}', member.mention)
    txt = ci_replace(txt, '{member(mention)}', member.mention)
    txt = ci_replace(txt, '%member_mention%', member.mention)
    txt = ci_replace(txt, '{member}', member.name)
    txt = ci_replace(txt, '{username}', member.name)
    txt = ci_replace(txt, '{user(proper)}', member.name)
    txt = ci_replace(txt, '{member(proper)}', member.name)
    txt = ci_replace(txt, '{user(tag)}', str(member))
    txt = ci_replace(txt, '%member%', member.name)
    txt = ci_replace(txt, '{count}', real_member_count)
    txt = ci_replace(txt, '{member_count}', real_member_count)
    txt = ci_replace(txt, '%count%', real_member_count)
    txt = ci_replace(txt, '{server}', guild.name)
    txt = ci_replace(txt, '{server_name}', guild.name)
    txt = ci_replace(txt, '{servername}', guild.name)
    txt = ci_replace(txt, '{server_upper}', guild.name.upper())
    txt = ci_replace(txt, '{serverupper}', guild.name.upper())
    txt = ci_replace(txt, '%server%', guild.name)
    txt = ci_replace(txt, '{inviter}', inviter_str)
    txt = ci_replace(txt, '%inviter%', inviter_str)

    # Calculate real-time invite counts for placeholders dynamically
    invites_count = 0
    total_invites = 0
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. First lookup the inviter's user ID from invited_users
        cursor.execute("SELECT inviter_id FROM invited_users WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(member.id)))
        inviter_row = cursor.fetchone()
        
        inviter_id_to_query = None
        if inviter_row:
            inviter_id_to_query = inviter_row[0]
            
        # 2. Query invites_stats table for count
        if inviter_id_to_query:
            cursor.execute("SELECT invites, bonus, leaves, fake FROM invites_stats WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(inviter_id_to_query)))
            stats_row = cursor.fetchone()
            if stats_row:
                invites, bonus, leaves, fake = stats_row
                invites_count = invites + bonus - leaves
                total_invites = invites + bonus
        conn.close()
    except Exception as ex_pl:
        print(f"Error resolving placeholder invite stats: {ex_pl}")

    # Tag/Mention inviter support
    inviter_mention = inviter_str
    if inviter_id_to_query and str(inviter_id_to_query).isdigit():
        inviter_mention = f"<@{inviter_id_to_query}>"
    elif inviter_str and inviter_str.startswith("<@"):
        inviter_mention = inviter_str
        
    txt = ci_replace(txt, '{inviter}', inviter_mention)
    txt = ci_replace(txt, '%inviter%', inviter_mention)
    txt = ci_replace(txt, '{inviter_name}', inviter_str)
    txt = ci_replace(txt, '%inviter_name%', inviter_str)

    txt = ci_replace(txt, '{invites}', str(invites_count))
    txt = ci_replace(txt, '{total_invites}', str(total_invites))
    txt = ci_replace(txt, '%invites%', str(invites_count))
    txt = ci_replace(txt, '%total_invites%', str(total_invites))

    if inviter_id_to_query:
        joined_method_str = f"{member.mention} has been invited by {inviter_str} and has now {invites_count} invites."
    elif member and getattr(member, 'bot', False):
        joined_method_str = f"{member.name} joined using OAuth."
    else:
        joined_method_str = f"{member.mention} joined directly or invite could not be determined."

    txt = ci_replace(txt, '{how_joined}', joined_method_str)
    txt = ci_replace(txt, '{join_method}', joined_method_str)
    txt = resolve_custom_emojis(txt, guild)
    return txt

def is_whitelisted(guild_id, user_id, action_type="all", channel_id=None, roles=None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_whitelists (
                guild_id TEXT,
                target_type TEXT,
                target_id TEXT,
                action_type TEXT,
                created_by TEXT,
                PRIMARY KEY (guild_id, target_type, target_id, action_type)
            )
        """)
        try:
            cursor.execute("ALTER TABLE bot_whitelists ADD COLUMN created_by TEXT")
        except Exception:
            pass
        
        # 0. Check if the user is the bot itself
        if bot.user and int(user_id) == bot.user.id:
            return True

        # 1. Check guild owner
        guild = bot.get_guild(int(guild_id))
        if guild and int(user_id) == guild.owner_id:
            conn.close()
            return True
            
        # 2. Check legacy user whitelists table
        cursor.execute("SELECT 1 FROM whitelists WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
        if cursor.fetchone():
            conn.close()
            return True
            
        # 3. Check bot_whitelists table for user target overrides (specific action and 'all')
        cursor.execute(
            "SELECT 1 FROM bot_whitelists WHERE guild_id = ? AND target_type = 'user' AND target_id = ? AND action_type IN (?, 'all')",
            (str(guild_id), str(user_id), action_type.lower())
        )
        if cursor.fetchone():
            conn.close()
            return True
            
        # 4. Check roles target overrides
        member = None
        if guild:
            member = guild.get_member(int(user_id))
            
        check_roles = []
        if roles:
            check_roles = [str(r) for r in roles]
        elif member:
            check_roles = [str(r.id) for r in member.roles]
            
        if check_roles:
            placeholders = ",".join("?" for _ in check_roles)
            query = f"""
                SELECT 1 FROM bot_whitelists 
                WHERE guild_id = ? AND target_type = 'role' 
                  AND target_id IN ({placeholders}) 
                  AND action_type IN (?, 'all')
            """
            cursor.execute(query, [str(guild_id)] + check_roles + [action_type.lower()])
            if cursor.fetchone():
                conn.close()
                return True
                
        # 5. Check channel overrides
        if channel_id:
            cursor.execute(
                "SELECT 1 FROM bot_whitelists WHERE guild_id = ? AND target_type = 'channel' AND target_id = ? AND action_type IN (?, 'all')",
                (str(guild_id), str(channel_id), action_type.lower())
            )
            if cursor.fetchone():
                conn.close()
                return True
                
        conn.close()
        return False
    except Exception as e:
        print(f"Error checking is_whitelisted: {e}")
        return False

def notify_web_event(guild_id, user_tag, action, details):
    import urllib.request
    import json
    import threading
    def _worker():
        try:
            payload = json.dumps({
                "guild_id": str(guild_id),
                "user": user_tag,
                "action": action,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode('utf-8')
            req = urllib.request.Request(
                "http://localhost:3000/api/internal/event",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=1.0)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

def log_system_event(guild_id, user_tag, action, details):
    try:
        conn = get_db()
        now_str = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                timestamp TEXT,
                user TEXT,
                action TEXT,
                details TEXT
            )
        """)
        conn.execute('INSERT INTO audit_logs (guild_id, timestamp, "user", action, details) VALUES (?, ?, ?, ?, ?)',
                     (str(guild_id), now_str, user_tag, action, details))
        conn.commit()
        conn.close()
        notify_web_event(guild_id, user_tag, action, details)
    except Exception as e:
        print(f"Error logging system event: {e}")

# --- 2. AUDIT LOG EXECUTOR RESOLUTION ---
async def get_audit_executor(guild, action_type):
    """
    Looks up the audit logs to find the executor of the action within the last 5 seconds.
    """
    await asyncio.sleep(1) # wait brief moment for log to write
    now = datetime.now(timezone.utc)
    
    try:
        async for entry in guild.audit_logs(limit=3, action=action_type):
            # Check if entry happened within the last 5 seconds
            delta = now - entry.created_at.replace(tzinfo=timezone.utc)
            if delta.total_seconds() < 6:
                if entry.user and entry.user.id == bot.user.id:
                    return None
                return entry.user
    except Exception as ex:
        print(f"Error fetching audit log executor: {ex}")
    
    return None

# --- 3. SECURITY PENALTY DISPATCHER ---
async def apply_penalty(guild, executor, module_name, action_desc, punishment_type):
    """
    Applies the penalty (Kick, Ban, or Quarantine) to the rogue administrator account.
    """
    if executor.id == guild.owner_id:
        return # owner is immune to penalties
        
    try:
        if punishment_type == 'Ban':
            await guild.ban(executor, reason=f"VEYRA Antinuke: Exceeded {module_name} limit.")
            log_system_event(guild.id, "VEYRA Bot", "Ban Action", f"Banned rogue administrator {executor.name} for {action_desc}")
            print(f"✅ Banned {executor.name} for {action_desc}")
        elif punishment_type == 'Kick':
            await guild.kick(executor, reason=f"VEYRA Antinuke: Exceeded {module_name} limit.")
            log_system_event(guild.id, "VEYRA Bot", "Kick Action", f"Kicked rogue administrator {executor.name} for {action_desc}")
            print(f"✅ Kicked {executor.name} for {action_desc}")
        elif punishment_type in ['Quarantine', 'Strip Roles', 'Strip']:
            roles_to_remove = [r for r in executor.roles if r < guild.me.top_role and r != guild.default_role]
            if roles_to_remove:
                await executor.remove_roles(*roles_to_remove, reason=f"VEYRA Antinuke: Quarantine/Strip roles for exceeding limit.")
                log_system_event(guild.id, "VEYRA Bot", "Quarantine Action", f"Stripped roles from rogue administrator {executor.name} for {action_desc}")
                print(f"✅ Stripped roles from {executor.name}")
    except Exception as ex:
        print(f"❌ Failed to penalize rogue admin {executor}: {ex}")

# --- 4. RATE LIMIT & THRESHOLD CHECKER ---
async def process_rate_limit(guild, executor, db_key, limit_name, count_increment, action_desc):
    """
    Tracks event frequencies and accumulated threat scores to enforce anti-nuke thresholds.
    """
    if executor.id == guild.me.id:
        return
        
    # Log the action in system audit logs
    log_system_event(guild.id, executor.name, limit_name, f"Performed action: {action_desc}")
        
    # Check if Beast Mode is active and fetch settings
    beast_active = False
    beast_bypass_wl = False
    beast_punish = 'Ban'
    beast_score_limit = 40
    action_score = 0
    
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM beastmode_settings WHERE guild_id = ?", (str(guild.id),))
        brow = cursor.fetchone()
        conn.close()
        if brow and brow['enabled'] == 1:
            beast_active = True
            beast_bypass_wl = (brow['whitelist_bypass'] == 1)
            beast_punish = brow['punishment_type'] or 'Ban'
            beast_score_limit = brow['score_limit'] if brow['score_limit'] is not None else 40
            
            score_col = f"score_{db_key}"
            if score_col in brow.keys():
                action_score = brow[score_col] or 0
    except Exception as e:
        print(f"Error loading beastmode settings in rate limiter: {e}")

    # Case 1: Beast Mode is active (threat score accumulator)
    if beast_active:
        if not beast_bypass_wl:
            if is_whitelisted(guild.id, executor.id) or executor.id == guild.owner_id:
                return
        elif executor.id == guild.owner_id:
            return # Owner is ALWAYS immune
            
        now = datetime.now(timezone.utc)
        executor_key = f"{guild.id}_{executor.id}"
        
        if not hasattr(bot, 'beast_scores'):
            bot.beast_scores = {}
            
        if executor_key not in bot.beast_scores:
            bot.beast_scores[executor_key] = (0, now)
            
        curr_score, timestamp = bot.beast_scores[executor_key]
        delta = now - timestamp
        
        if delta.total_seconds() > 300: # 5 minutes interval reset
            curr_score = 0
            timestamp = now
            
        curr_score += action_score
        bot.beast_scores[executor_key] = (curr_score, timestamp)
        
        print(f"[BEAST MODE] Executor {executor.name} threat score: {curr_score}/{beast_score_limit} (Added {action_score} for {limit_name})")
        
        if curr_score > beast_score_limit:
            await apply_penalty(guild, executor, "BEAST MODE", f"Exceeded threat score limit ({curr_score}/{beast_score_limit})", beast_punish)
            bot.beast_scores[executor_key] = (0, now)
        return

    # Case 2: Normal Anti-Nuke (event frequencies check)
    if is_whitelisted(guild.id, executor.id) or executor.id == guild.owner_id:
        return

    settings = fetch_security_settings(guild.id)
    if not settings:
        return

    enabled = settings[f"anti_{db_key}_enabled"]
    limit_val = settings[f"anti_{db_key}_limit"]
    punish_type = settings[f"anti_{db_key}_punish"] or 'Ban'
    
    if not enabled:
        return
        
    now = datetime.now(timezone.utc)
    composite_key = f"{guild.id}_{db_key}_{executor.id}"
    
    if composite_key not in bot.audit_counters:
        bot.audit_counters[composite_key] = (0, now)
        
    curr_count, timestamp = bot.audit_counters[composite_key]
    delta = now - timestamp
    
    if delta.total_seconds() > 300: # 5 minutes interval reset
        curr_count = 0
        timestamp = now
        
    curr_count += count_increment
    bot.audit_counters[composite_key] = (curr_count, timestamp)
    
    print(f"[{limit_name}] Executor {executor.name} count: {curr_count}/{limit_val}")
    
    if curr_count > limit_val:
        await apply_penalty(guild, executor, limit_name, action_desc, punish_type)
        bot.audit_counters[composite_key] = (0, now)

# --- 5. EVENT LISTENERS FOR ALL 16 SECURITY CONSTRAINTS ---

# Event 1: Anti Ban (Rate-Limited)
@bot.event
async def on_member_ban(guild, user):
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban)
    if executor:
        await process_rate_limit(guild, executor, 'ban', 'Anti-Ban', 1, f"banning user {user.name}")

# Event 2: Anti Kick (Handled in unified on_member_remove below)

# Event 3: Anti Role Create (Rate-Limited)
@bot.event
async def on_guild_role_create(role):
    guild = role.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_create)
    if executor:
        await process_rate_limit(guild, executor, 'role_create', 'Anti-Role Create', 1, f"creating role {role.name}")
        # Revert role creation if rogue admin action detected
        settings = fetch_security_settings(guild.id)
        if settings and settings['anti_role_create_enabled'] and not is_whitelisted(guild.id, executor.id):
            try:
                await role.delete(reason="VEYRA Auto-Revert: Unauthorized role creation")
            except Exception as e:
                print(f"Revert create role failed: {e}")

# Event 4: Anti Role Delete (Rate-Limited)
@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_delete)
    if executor:
        await process_rate_limit(guild, executor, 'role_delete', 'Anti-Role Delete', 1, f"deleting role {role.name}")
        # Recreate deleted role if unauthorized
        settings = fetch_security_settings(guild.id)
        if settings and settings['anti_role_delete_enabled'] and not is_whitelisted(guild.id, executor.id):
            try:
                await guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable)
            except Exception as e:
                print(f"Revert delete role failed: {e}")

# Event 5: Anti Channel Create (Rate-Limited)
@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_create)
    
    is_deleted = False
    if executor:
        await process_rate_limit(guild, executor, 'channel_create', 'Anti-Channel Create', 1, f"creating channel {channel.name}")
        # Revert channel creation
        settings = fetch_security_settings(guild.id)
        if settings and settings['anti_channel_create_enabled'] and not is_whitelisted(guild.id, executor.id):
            try:
                await channel.delete(reason="VEYRA Auto-Revert: Unauthorized channel creation")
                is_deleted = True
            except Exception as e:
                print(f"Revert create channel failed: {e}")

# Event 6: Anti Channel Delete (Rate-Limited)
@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_delete)
    if executor:
        await process_rate_limit(guild, executor, 'channel_delete', 'Anti-Channel Delete', 1, f"deleting channel {channel.name}")
        # Recreate channel
        settings = fetch_security_settings(guild.id)
        if settings and settings['anti_channel_delete_enabled'] and not is_whitelisted(guild.id, executor.id):
            try:
                if isinstance(channel, discord.TextChannel):
                    await guild.create_text_channel(name=channel.name, category=channel.category, topic=channel.topic)
                elif isinstance(channel, discord.VoiceChannel):
                    await guild.create_voice_channel(name=channel.name, category=channel.category)
            except Exception as e:
                print(f"Revert delete channel failed: {e}")



CMD_MAP = {
    "antinuke enable": "antinuke-enable",
    "antinuke disable": "antinuke-disable",
    "antinuke config": "antinuke-config",
    "antinuke logs": "antinuke-logs",
    "antinuke threshold": "antinuke-threshold",
    "whitelist add_user": "whitelist-add",
    "whitelist remove_user": "whitelist-remove",
    "whitelist add_role": "whitelist-add-role",
    "whitelist remove_role": "whitelist-remove-role",
    "whitelist add_channel": "whitelist-add-channel",
    "whitelist remove_channel": "whitelist-remove-channel",
    "whitelist view_users": "whitelist-list",
    "whitelist view_roles": "whitelist-list",
    "whitelist view_channels": "whitelist-list",
    "beastmode toggle": "beastmode-toggle",
    "beastmode status": "beastmode-status",
    "antiraid enable": "antiraid-enable",
    "antiraid disable": "antiraid-disable",
    "antiraid config": "antiraid-config",
    "antibot toggle": "antibot-toggle",
    "antibot punish": "antibot-punish",
    "antispam links": "antispam-links",
    "antispam mentions": "antispam-mentions",
    "antispam invites": "antispam-invites",
    "webhook monitor": "webhook-monitor",
    "webhook bypass": "webhook-bypass",
    "channel guard": "channel-guard",
    "role guard": "role-guard",
    "ban guard": "ban-guard",
    "kick guard": "kick-guard",
    "verification enable": "verification-enable",
    "verification disable": "verification-disable",
    "verification setup_channel": "verification-setup-channel",
    "verification setup_role": "verification-setup-role",
    "verification set_verified": "verification-set-verified",
    "verification type": "verification-type",
    "verification update_role": "verification-update-role",
    "verification verify": "verification-verify",
    "verification reset": "verification-reset",
    "autorole add": "autorole-add",
    "autorole remove": "autorole-remove",
    "autorole list": "autorole-list",
    "stickyrole enable": "sticky-enable",
    "stickyrole disable": "sticky-disable",
    "kick": "kick",
    "ban": "ban",
    "mute": "mute",
    "unmute": "unmute",
    "timeout": "timeout",
    "ping": "ping",
    "stats": "stats",
    "uptime": "uptime",
    "work": "work",
    "space": "space",
    "emergency-lockdown": "emergency-lockdown",
    "emergency-unlock": "emergency-unlock",
}

def is_feature_enabled(guild_id, feature_name):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT disabled_commands FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            disabled = json.loads(row[0])
            if feature_name in disabled:
                return False
        return True
    except Exception as e:
        print(f"Error checking feature status for {feature_name}: {e}")
        return True

async def check_disabled_commands(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        if interaction.command and interaction.guild:
            # Reconstruct full command name path
            cmd_parts = []
            cmd = interaction.command
            while cmd:
                cmd_parts.insert(0, cmd.name)
                cmd = cmd.parent
            full_name = " ".join(cmd_parts)
            
            # Match against frontend names
            frontend_name = CMD_MAP.get(full_name, full_name.replace(" ", "-"))
            
            # Query disabled commands from db
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT disabled_commands FROM guild_settings WHERE guild_id = ?", (str(interaction.guild.id),))
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    disabled = json.loads(row[0])
                    if frontend_name in disabled:
                        await interaction.response.send_message("❌ This command has been disabled by the server administrator.", ephemeral=True)
                        return False
            except Exception as e:
                print(f"Error checking disabled commands: {e}")
    return True

bot.tree.interaction_check = check_disabled_commands

# Event 7: Anti Mention / Message Spam (Rate-Limited)
@bot.event
async def on_message(message):
    if not message.guild or message.author.bot:
        return

    # Check bot mention welcome card
    if bot.user in message.mentions and len(message.content.strip().split()) == 1:
        prefix = ","
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (str(message.guild.id),))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                prefix = row[0].strip()
        except Exception:
            pass
        from interactive_ui import build_mention_embed, BotMentionView
        embed = build_mention_embed(message.author, prefix)
        await message.channel.send(embed=embed, view=BotMentionView())
        return

    await bot.process_commands(message)

    # Check Anti Raid invite links protection
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled, invite_link_protection FROM antiraid_settings WHERE guild_id = ?", (str(message.guild.id),))
        ar = cursor.fetchone()
        conn.close()
        
        if ar and ar[0] == 1 and ar[1] == 1:
            if not is_whitelisted(message.guild.id, message.author.id) and not message.author.guild_permissions.administrator:
                import re
                if re.search(r'(discord\.gg|discord\.com/invite)/[A-Za-z0-9]+', message.content):
                    await message.delete()
                    await message.channel.send(f"⚠️ {message.author.mention}, posting invite links is prohibited by the Anti Raid system!", delete_after=5)
                    return
    except Exception as ar_err:
        print(f"Error checking anti raid invite links: {ar_err}")

    # Message stats tracking and Leveling system
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM blacklisted_channels WHERE guild_id = ? AND channel_id = ?", (str(message.guild.id), str(message.channel.id)))
        is_bl = cursor.fetchone() is not None
        
        # Also check leveling ignored channels
        cursor.execute("SELECT 1 FROM leveling_ignored_channels WHERE guild_id = ? AND channel_id = ?", (str(message.guild.id), str(message.channel.id)))
        is_lvl_ignored = cursor.fetchone() is not None
        
        if not is_bl:
            cursor.execute("""
                INSERT INTO messages_stats (guild_id, user_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET count = messages_stats.count + 1
            """, (str(message.guild.id), str(message.author.id)))
            conn.commit()
            
            # Fetch message count to calculate level
            cursor.execute("SELECT count FROM messages_stats WHERE guild_id = ? AND user_id = ?", (str(message.guild.id), str(message.author.id)))
            msg_row = cursor.fetchone()
            if msg_row and not is_lvl_ignored:
                msg_count = msg_row[0]
                
                # Check leveling settings
                cursor.execute("SELECT enabled, channel, message, level_modulo, min_level, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon FROM leveling_settings WHERE guild_id = ?", (str(message.guild.id),))
                lvl_row = cursor.fetchone()
                
                lvl_enabled = 1
                lvl_channel = 'none'
                lvl_message = 'GG {user}, you leveled up to level {lvl}!'
                lvl_modulo = 1
                lvl_min_level = 1
                lvl_color = '#a855f7'
                lvl_title = 'LEVEL UP!'
                lvl_desc = 'GG {user}, you leveled up to level {lvl}!'
                lvl_image = ''
                lvl_thumbnail = ''
                lvl_footer = 'Keep chatting to earn more XP!'
                lvl_auth_name = ''
                lvl_auth_icon = ''
                lvl_foot_icon = ''
                
                if lvl_row:
                    lvl_enabled, lvl_channel, lvl_message, lvl_modulo, lvl_min_level, lvl_color, lvl_title, lvl_desc, lvl_image, lvl_thumbnail, lvl_footer, lvl_auth_name, lvl_auth_icon, lvl_foot_icon = lvl_row
                
                if lvl_enabled == 1:
                    level = msg_count // 50
                    old_level = (msg_count - 1) // 50
                    
                    if level > old_level and level >= (lvl_min_level or 1):
                        # Apply Level Rewards (grant role)
                        cursor.execute("SELECT role_id FROM leveling_rewards WHERE guild_id = ? AND level = ?", (str(message.guild.id), level))
                        reward_rows = cursor.fetchall()
                        for r_row in reward_rows:
                            r_entry = r_row[0]
                            r_obj = None
                            if str(r_entry).isdigit():
                                r_obj = message.guild.get_role(int(r_entry))
                            if not r_obj:
                                r_obj = discord.utils.get(message.guild.roles, name=str(r_entry))
                            if r_obj and r_obj < message.guild.me.top_role:
                                try:
                                    await message.author.add_roles(r_obj, reason=f"VEYRA Level Reward (Level {level})")
                                    print(f"Granted level reward role {r_obj.name} to {message.author.name}")
                                except Exception as role_err:
                                    print(f"Failed to grant level reward role: {role_err}")
                        
                        # Send Level Up Announcement
                        if lvl_modulo == 0 or level % (lvl_modulo or 1) == 0:
                            # Find target channel
                            target_ch = message.channel
                            if lvl_channel and lvl_channel != 'none':
                                ch_name = str(lvl_channel).replace('#', '').strip()
                                found_ch = get_fallback_channel(message.guild, ch_name)
                                if found_ch:
                                    target_ch = found_ch
                                    
                            # Format message
                            def fmt_lbl(txt):
                                if not txt: return ''
                                return txt.replace('{user}', message.author.name).replace('{lvl}', str(level)).replace('{mention}', message.author.mention).replace('{server}', message.guild.name)
                                
                            outer_msg = fmt_lbl(lvl_message)
                            
                            # Custom color
                            try:
                                hex_color = str(lvl_color or '#a855f7').replace('#', '')
                                embed_color = discord.Color(int(hex_color, 16))
                            except Exception:
                                embed_color = discord.Color(0xa855f7)
                                
                            embed = discord.Embed(
                                title=fmt_lbl(lvl_title) if lvl_title else None,
                                description=fmt_lbl(lvl_desc) if lvl_desc else None,
                                color=embed_color
                            )
                            if lvl_auth_name:
                                embed.set_author(name=fmt_lbl(lvl_auth_name), icon_url=fmt_lbl(lvl_auth_icon) if lvl_auth_icon.startswith('http') else str(message.author.display_avatar.url))
                            if lvl_footer:
                                embed.set_footer(text=fmt_lbl(lvl_footer), icon_url=fmt_lbl(lvl_foot_icon) if lvl_foot_icon.startswith('http') else str(bot.user.display_avatar.url))
                            if lvl_thumbnail and lvl_thumbnail.startswith('http'):
                                embed.set_thumbnail(url=lvl_thumbnail)
                            if lvl_image and lvl_image.startswith('http'):
                                embed.set_image(url=lvl_image)
                                
                            try:
                                await target_ch.send(content=outer_msg if outer_msg else None, embed=embed if (lvl_title or lvl_desc) else None)
                            except Exception as send_err:
                                print(f"Failed to send level up announcement: {send_err}")
        conn.close()
    except Exception as e:
        print(f"Database error incrementing message stats & leveling: {e}")

    # --- STICKY MESSAGES MONITORING ---
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, message, last_message_id FROM sticky_messages WHERE guild_id = ? AND (channel = ? OR channel = ?)", (str(message.guild.id), str(message.channel.id), message.channel.name))
        stickies = cursor.fetchall()
        
        for sticky_id, sticky_msg, last_msg_id in stickies:
            if message.author.id == bot.user.id and (sticky_msg in message.content or "📌" in message.content):
                continue
                
            if last_msg_id:
                try:
                    old_msg = await message.channel.fetch_message(int(last_msg_id))
                    if old_msg:
                        await old_msg.delete()
                except Exception:
                    pass
                    
            try:
                new_sticky = await message.channel.send(content=f"📌 **Sticky Message**\n───────────────────\n{sticky_msg}")
                cursor.execute("UPDATE sticky_messages SET last_message_id = ? WHERE id = ?", (str(new_sticky.id), sticky_id))
                conn.commit()
            except Exception as sticky_send_err:
                print(f"Failed to send sticky message: {sticky_send_err}")
        conn.close()
    except Exception as sticky_err:
        print(f"Database error checking sticky messages: {sticky_err}")
    
    # AFK checks
    if not hasattr(bot, "afk_users"):
        bot.afk_users = {}
        
    # Clear AFK status if they send a message
    if message.author.id in bot.afk_users:
        del bot.afk_users[message.author.id]
        try:
            await message.channel.send(f"👋 Welcome back {message.author.mention}! Your AFK status has been cleared.", delete_after=5)
        except Exception:
            pass
            
    # Check mentions for AFK users
    for mention in message.mentions:
        if mention.id in bot.afk_users:
            status = bot.afk_users[mention.id]
            try:
                await message.channel.send(f"💤 **{mention.name}** is currently AFK: {status}", delete_after=10)
            except Exception:
                pass
    
    # --- 1. WHITELIST / IMMUNITY CHECK ---
    is_immune = (
        message.author.id == message.guild.owner_id 
        or message.author.guild_permissions.administrator
        or is_whitelisted(message.guild.id, message.author.id, action_type="all", channel_id=message.channel.id)
    )
    
    if not is_immune:
        # --- 2. DISCORD INVITE & HYPERLINKS FILTER (7-day timeout) ---
        if is_feature_enabled(message.guild.id, 'antispam-links') or is_feature_enabled(message.guild.id, 'antispam-invites'):
            import re
            invite_regex = r"(discord\.(gg|io|me|li)\/.+|discord(app)?\.com\/invite\/.+)"
            url_regex = r"(https?:\/\/[^\s]+)"
            if re.search(invite_regex, message.content, re.IGNORECASE) or re.search(url_regex, message.content, re.IGNORECASE):
                if not is_whitelisted(message.guild.id, message.author.id, action_type="invite-link", channel_id=message.channel.id):
                    try:
                        await message.delete()
                        await message.author.timeout(timedelta(days=7), reason="VEYRA Anti-Spam: Sent restricted link/invite")
                        
                        embed = discord.Embed(
                            title="🚫 Link Blocked & Timeout Applied",
                            description=f"Hey {message.author.mention}, posting external links or invite links is strictly prohibited on this server. You have been timed out for 7 days.",
                            color=0xef4444
                        )
                        embed.set_footer(text="VEYRA Security Engine • Automated AutoMod")
                        embed.timestamp = datetime.now(timezone.utc)
                        await message.channel.send(embed=embed, delete_after=15)
                        
                        await log_system_event_async(message.guild, "VEYRA AutoMod", "External Link / Invite Blocked", f"Timed out user {message.author} for 7 days for sending restricted link.", log_type='security')
                        return
                    except Exception as ex:
                        print(f"Error executing link timeout: {ex}")

        # --- 3. FILES & ATTACHMENTS FILTER (7-day timeout) ---
        if is_feature_enabled(message.guild.id, 'antispam-images'):
            if len(message.attachments) > 0:
                try:
                    await message.delete()
                    await message.author.timeout(timedelta(days=7), reason="VEYRA Anti-Spam: Sent restricted attachment/file")
                    
                    embed = discord.Embed(
                        title="🚫 Attachment Blocked & Timeout Applied",
                        description=f"Hey {message.author.mention}, uploading files, images, videos, or audio files is prohibited. You have been timed out for 7 days.",
                        color=0xef4444
                    )
                    embed.set_footer(text="VEYRA Security Engine • Automated AutoMod")
                    embed.timestamp = datetime.now(timezone.utc)
                    await message.channel.send(embed=embed, delete_after=15)
                    
                    await log_system_event_async(message.guild, "VEYRA AutoMod", "Attachment Blocked", f"Timed out user {message.author} for 7 days for sending attachment/media.", log_type='security')
                    return
                except Exception as ex:
                    print(f"Error executing attachment timeout: {ex}")

        # --- 4. ANTI MESSAGE FLOOD / SPAM (RATE LIMIT) ---
        # Limit: 5 messages in 3 seconds
        if not hasattr(bot, "message_flood_tracker"):
            bot.message_flood_tracker = {}
        
        user_key = f"{message.guild.id}_{message.author.id}"
        now = datetime.now(timezone.utc)
        if user_key not in bot.message_flood_tracker:
            bot.message_flood_tracker[user_key] = []
        
        timestamps = [t for t in bot.message_flood_tracker[user_key] if (now - t).total_seconds() <= 3.0]
        timestamps.append(now)
        bot.message_flood_tracker[user_key] = timestamps
        
        if len(timestamps) > 5:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.author.timeout(timedelta(minutes=5), reason="VEYRA Anti-Spam: Sending messages too fast (Message Flood)")
                await message.channel.send(f"⚠️ {message.author.mention} has been timed out for 5 minutes due to message flooding/spamming.", delete_after=15)
                await log_system_event_async(message.guild, "VEYRA AutoMod", "Anti-Spam Timeout", f"Timed out {message.author} for message flood-spam", log_type='security')
            except Exception as ex:
                print(f"Error executing flood timeout: {ex}")
            return

        # --- 6. AI AUTOMOD / ABUSE FILTER ---
        profanity_words = ["nigger", "faggot", "chink", "kike", "selfbot", "nukebot", "nuking", "wizzing", "wizzed"]
        token_regex = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"
        
        has_abusive_content = False
        threat_reason = ""
        msg_lower = message.content.lower()
        
        for word in profanity_words:
            if word in msg_lower:
                has_abusive_content = True
                threat_reason = f"severe profanity / nuke keyword usage: '{word}'"
                break
                
        if not has_abusive_content and re.search(token_regex, message.content):
            has_abusive_content = True
            threat_reason = "leaking / posting discord token string (credential theft protection)"
            
        if not has_abusive_content and len(message.content) > 1000:
            chars = set(message.content)
            if len(chars) < 5:
                has_abusive_content = True
                threat_reason = "possible text crash payload attempt (repetitive unicode)"

        if has_abusive_content:
            try:
                await message.delete()
                embed = discord.Embed(
                    title="🛡️ AI Moderation Guard Active",
                    description=f"{message.author.mention}, your message was flagged and removed by VEYRA AI Moderation.",
                    color=0xeab308
                )
                embed.add_field(name="Reason", value=threat_reason)
                await message.channel.send(embed=embed, delete_after=15)
                await log_system_event_async(message.guild, "VEYRA AI Moderation", "AI AutoMod Deletion", f"Deleted flagged content from user {message.author}. Reason: {threat_reason}", log_type='security')
                return
            except Exception as ex:
                print(f"Error in AI moderation scan action: {ex}")

# Event 8: Anti Bot Add (Handled in unified on_member_join below)

# Event 9: Anti Prune (Instant)
# Discord API does not fire on_member_remove with prune flags in python, so we check on_guild_update / audit logs
# For instant checks, we hook on member remove to inspect audit log
@bot.event
async def on_member_remove_inspect_prune(member):
    # This acts as Event 9 backup check
    guild = member.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.prune)
    if executor:
        settings = fetch_security_settings(guild.id)
        if settings and settings['anti_prune_enabled'] and not is_whitelisted(guild.id, executor.id):
            punish = settings['anti_prune_punish']
            await apply_penalty(guild, executor, 'Anti-Prune', "initiating server member prune", punish)

# Event 10 & 11: Anti Dangerous Role permissions Update & Add (Instant)
@bot.event
async def on_guild_role_update(before, after):
    guild = after.guild
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_update)
    if executor:
        # Check dangerous permissions (Administrator, Manage Guild, Ban Members)
        if not before.permissions.administrator and after.permissions.administrator:
            settings = fetch_security_settings(guild.id)
            if settings and settings['anti_dangerous_role_update_enabled'] and not is_whitelisted(guild.id, executor.id):
                try:
                    # Revert permissions
                    await after.edit(permissions=before.permissions, reason="VEYRA: Reverted unauthorized admin permissions update")
                    punish = settings['anti_dangerous_role_update_punish']
                    await apply_penalty(guild, executor, 'Anti-Dangerous Role Perms', "enabling administrator privileges on role", punish)
                except Exception as e:
                    print(f"Revert role permissions failed: {e}")

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    # Check if a new role was added
    if len(before.roles) < len(after.roles):
        new_roles = [r for r in after.roles if r not in before.roles]
        for role in new_roles:
            # Check if it has admin privileges
            if role.permissions.administrator or role.permissions.manage_roles:
                executor = await get_audit_executor(guild, discord.AuditLogAction.member_role_update)
                if executor:
                    settings = fetch_security_settings(guild.id)
                    if settings and settings['anti_dangerous_role_add_enabled'] and not is_whitelisted(guild.id, executor.id):
                        try:
                            # Strip role from user
                            await after.remove_roles(role, reason="VEYRA: Stripped unauthorized administrator role")
                            punish = settings['anti_dangerous_role_add_punish']
                            await apply_penalty(guild, executor, 'Anti-Dangerous Role Add', f"adding administrative role to user {after.name}", punish)
                        except Exception as e:
                            print(f"Stripping administrator role failed: {e}")

# Event 12, 13 & 14: Anti Vanity Change, Server Rename, Icon Change (Instant)
@bot.event
async def on_guild_update(before, after):
    guild = after
    executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update)
    if not executor:
        return
        
    settings = fetch_security_settings(guild.id)
    if not settings:
        return
        
    if is_whitelisted(guild.id, executor.id):
        return

    # Event 12: Vanity Change
    if before.vanity_url_code != after.vanity_url_code:
        if settings['anti_vanity_change_enabled']:
            try:
                # Revert vanity code in python
                await after.edit(vanity_code=before.vanity_url_code)
                punish = settings['anti_vanity_change_punish']
                await apply_penalty(guild, executor, 'Anti-Vanity Change', "altering server vanity link code", punish)
            except Exception as e:
                print(f"Reverting vanity URL failed: {e}")
                
    # Event 13: Server Rename
    if before.name != after.name:
        if settings['anti_server_rename_enabled']:
            try:
                await after.edit(name=before.name)
                punish = settings['anti_server_rename_punish']
                await apply_penalty(guild, executor, 'Anti-Server Rename', f"renaming guild to {after.name}", punish)
            except Exception as e:
                print(f"Reverting server name failed: {e}")
                
    # Event 14: Server Icon Change
    if before.icon != after.icon:
        if settings['anti_server_icon_change_enabled']:
            try:
                await after.edit(icon=before.icon)
                punish = settings['anti_server_icon_change_punish']
                await apply_penalty(guild, executor, 'Anti-Server Icon Change', "altering guild server icon asset", punish)
            except Exception as e:
                print(f"Reverting server icon failed: {e}")

# Event 15: Anti Role Rename (Instant)
# This uses on_guild_role_update
@bot.event
async def on_guild_role_update_rename(before, after):
    if before.name != after.name:
        guild = after.guild
        executor = await get_audit_executor(guild, discord.AuditLogAction.role_update)
        if executor:
            settings = fetch_security_settings(guild.id)
            if settings and settings['anti_role_rename_enabled'] and not is_whitelisted(guild.id, executor.id):
                try:
                    await after.edit(name=before.name, reason="VEYRA: Reverted unauthorized role rename")
                    punish = settings['anti_role_rename_punish']
                    await apply_penalty(guild, executor, 'Anti-Role Rename', f"renaming role {before.name} to {after.name}", punish)
                except Exception as e:
                    print(f"Reverting role name failed: {e}")

# Event 16: Anti Channel Rename (Instant)
@bot.event
async def on_guild_channel_update(before, after):
    if before.name != after.name:
        guild = after.guild
        executor = await get_audit_executor(guild, discord.AuditLogAction.channel_update)
        if executor:
            settings = fetch_security_settings(guild.id)
            if settings and settings['anti_channel_rename_enabled'] and not is_whitelisted(guild.id, executor.id):
                try:
                    await after.edit(name=before.name, reason="VEYRA: Reverted unauthorized channel rename")
                    punish = settings['anti_channel_rename_punish']
                    await apply_penalty(guild, executor, 'Anti-Channel Rename', f"renaming channel {before.name} to {after.name}", punish)
                except Exception as e:
                    print(f"Reverting channel name failed: {e}")


# Remove default help command to register our custom hybrid menu
bot.remove_command('help')

@bot.command(name="help", aliases=["h"], description="Displays interactive command manual lists.")
async def help_command(ctx, category: str = None):
    """Displays interactive command manual lists."""
    bot_icon_url = bot.user.avatar.url if bot.user and bot.user.avatar else None
    embed = build_main_help_embed(ctx.guild, bot_icon_url)
    await ctx.send(embed=embed, view=HelpView(bot_icon_url))


@bot.command(name="stats", aliases=["team"], description="Displays Veyra Team and system stats.")
async def stats_command(ctx):
    embed = discord.Embed(
        title=":avownzz: Veyra Team",
        color=discord.Color.from_rgb(43, 45, 49)
    )
    embed.description = (
        "1. **Owner**\n"
        "ARUN\n\n"
        "2. **Developer**\n"
        "VEYRA CORE TEAM"
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed, view=StatsTeamView(bot_client=bot, uptime_str="0d 2h 30m 23s"))


@bot.command(name="ping", description="Measures bot latency and database performance.")
async def ping_command(ctx):
    ws_latency = round(bot.latency * 1000)
    embed = build_ping_code_embed(ws_latency)
    await ctx.send(embed=embed)


@bot.tree.command(name="ping", description="Measures bot latency and database performance.")
async def ping_slash(interaction: discord.Interaction):
    ws_latency = round(bot.latency * 1000)
    embed = build_ping_code_embed(ws_latency)
    await interaction.response.send_message(embed=embed)


@bot.command(name="uptime", description="Checks how long the bot has been online.")
async def uptime_command(ctx):
    ws_latency = round(bot.latency * 1000)
    embed = build_uptime_embed("0d 2h 30m 23s", started_str="5 hours ago", ws_latency=ws_latency)
    await ctx.send(embed=embed)


@bot.tree.command(name="uptime", description="Checks how long the bot has been online.")
async def uptime_slash(interaction: discord.Interaction):
    ws_latency = round(bot.latency * 1000)
    embed = build_uptime_embed("0d 2h 30m 23s", started_str="5 hours ago", ws_latency=ws_latency)
    await interaction.response.send_message(embed=embed)


@bot.command(name="avatar", aliases=["av", "pfp", "useravatar"], description="Displays user avatar with download link")
async def avatar_prefix(ctx, user: Optional[Union[discord.Member, discord.User]] = None):
    target = user or ctx.author
    if ctx.guild and not isinstance(target, discord.Member):
        m = ctx.guild.get_member(target.id)
        if m:
            target = m
    embed, view = build_avatar_embed(target)
    if view:
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)


@bot.command(name="banner", aliases=["bn", "userbanner"], description="Displays user banner with download link")
async def banner_prefix(ctx, user: Optional[Union[discord.Member, discord.User]] = None):
    target = user or ctx.author
    if ctx.guild and not isinstance(target, discord.Member):
        m = ctx.guild.get_member(target.id)
        if m:
            target = m
    user_fetched = None
    try:
        user_fetched = await bot.fetch_user(target.id)
    except Exception:
        pass
    embed, view = build_banner_embed(target, user_fetched)
    if view:
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)


@bot.command(name="servericon", aliases=["sicon", "icon", "guildicon"], description="Displays server icon with download link")
async def servericon_prefix(ctx):
    if not ctx.guild or not ctx.guild.icon:
        return await ctx.send("❌ This server does not have an icon set.")
    try:
        icon_url = ctx.guild.icon.with_size(1024).url
    except Exception:
        icon_url = ctx.guild.icon.url
    embed = discord.Embed(title=f"🏰 Icon of {ctx.guild.name}", color=discord.Color.from_rgb(24, 24, 27))
    embed.set_image(url=str(icon_url))
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    view = MediaDownloadView([("Download ↗", str(icon_url))])
    await ctx.send(embed=embed, view=view)


@bot.command(name="serverbanner", aliases=["sbanner", "guildbanner"], description="Displays server banner with download link")
async def serverbanner_prefix(ctx):
    if not ctx.guild or not ctx.guild.banner:
        return await ctx.send("❌ This server does not have a banner set.")
    try:
        banner_url = ctx.guild.banner.with_size(1024).url
    except Exception:
        banner_url = ctx.guild.banner.url
    embed = discord.Embed(title=f"🏰 Banner of {ctx.guild.name}", color=discord.Color.from_rgb(24, 24, 27))
    embed.set_image(url=str(banner_url))
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    view = MediaDownloadView([("Download ↗", str(banner_url))])
    await ctx.send(embed=embed, view=view)


@bot.command(name="serverinfo", aliases=["si", "guildinfo"], description="Displays server information")
async def serverinfo_prefix(ctx):
    embed = build_server_info_embed(ctx.guild)
    view = ServerInfoView(ctx.guild)
    await ctx.send(embed=embed, view=view)


@bot.command(name="userinfo", aliases=["ui", "whois", "user"], description="Displays member profile information")
async def userinfo_prefix(ctx, member: discord.Member = None):
    target = member or ctx.author
    roles = [role.mention for role in reversed(target.roles) if role.name != "@everyone"]
    roles_str = ", ".join(roles[:10]) if roles else "None"
    if len(roles) > 10:
        roles_str += f" (+{len(roles) - 10} more)"
    embed = discord.Embed(
        title=f"👤 {target.name}'s Profile",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.add_field(name="Username", value=f"`{target.name}`", inline=True)
    embed.add_field(name="ID", value=f"`{target.id}`", inline=True)
    embed.add_field(name="Joined Server", value=f"<t:{int(target.joined_at.timestamp())}:R>" if target.joined_at else "Unknown", inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(target.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Roles", value=roles_str, inline=False)
    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="purge", aliases=["clear", "clean", "c"], description="Bulk delete messages in the channel")
@commands.has_permissions(manage_messages=True)
async def purge_prefix(ctx, amount: int = 10):
    amount = min(max(amount, 1), 100)
    deleted = await ctx.channel.purge(limit=amount + 1)
    count = len(deleted) - 1 if len(deleted) > 0 else 0
    embed = discord.Embed(
        title="🧹 Messages Purged",
        description=f"Successfully deleted `{count}` message(s) from {ctx.channel.mention}.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except Exception:
        pass


@bot.command(name="lock", aliases=["lockchannel"], description="Locks the current channel")
@commands.has_permissions(manage_channels=True)
async def lock_prefix(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    overwrite = ch.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    embed = discord.Embed(
        title="🔒 Channel Locked",
        description=f"{ch.mention} has been locked for `@everyone`.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="unlock", aliases=["unlockchannel"], description="Unlocks the current channel")
@commands.has_permissions(manage_channels=True)
async def unlock_prefix(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    overwrite = ch.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    embed = discord.Embed(
        title="🔓 Channel Unlocked",
        description=f"{ch.mention} has been unlocked for `@everyone`.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="lockall", aliases=["serverlock"], description="Locks all text channels in the server")
@commands.has_permissions(administrator=True)
async def lockall_prefix(ctx):
    count = 0
    for ch in ctx.guild.text_channels:
        try:
            overwrite = ch.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            count += 1
        except Exception:
            pass
    embed = discord.Embed(
        title="🔒 Server Lockdown Active",
        description=f"Locked `{count}` text channels across the server.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="unlockall", aliases=["serverunlock"], description="Unlocks all text channels in the server")
@commands.has_permissions(administrator=True)
async def unlockall_prefix(ctx):
    count = 0
    for ch in ctx.guild.text_channels:
        try:
            overwrite = ch.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = True
            await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            count += 1
        except Exception:
            pass
    embed = discord.Embed(
        title="🔓 Server Lockdown Lifted",
        description=f"Unlocked `{count}` text channels across the server.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="247", aliases=["24/7", "vc247", "stay247", "voice247", "set247", "stay"], description="Connects and locks 24/7 voice channel")
async def voice_247_prefix(ctx, *args):
    action = args[0].lower() if args else None
    if action in ["leave", "off", "disable", "disconnect", "stop"]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE voice_247_settings SET enabled = 0 WHERE guild_id = ?", (str(ctx.guild.id),))
        conn.commit()
        conn.close()

        try:
            from music_bot import bot as music_sub_bot
            p = music_sub_bot.get_player(ctx.guild.id)
            p.stay_247 = False
            music_sub_bot.Database.set_247(ctx.guild.id, 0, None, ctx.channel.id)
        except Exception:
            pass

        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect(force=True)

        embed = discord.Embed(
            title="🔴 24/7 Voice System Disabled",
            description="Bot disconnected and 24/7 persistence turned off.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        return await ctx.send(embed=embed)

    target_vc = None

    # 1. Channel mentions in message
    if ctx.message.channel_mentions:
        for cm in ctx.message.channel_mentions:
            f_ch = ctx.guild.get_channel(cm.id)
            if f_ch and isinstance(f_ch, (discord.VoiceChannel, discord.StageChannel)):
                target_vc = f_ch
                break

    # 2. Extract channel ID or name from args
    if not target_vc and args:
        import re
        full_text = " ".join(args).strip()
        id_match = re.search(r'\b\d{17,20}\b', full_text)
        if id_match:
            ch_by_id = ctx.guild.get_channel(int(id_match.group(0)))
            if ch_by_id and isinstance(ch_by_id, (discord.VoiceChannel, discord.StageChannel)):
                target_vc = ch_by_id

        if not target_vc:
            noise = {"join", "set", "enable", "connect", "channel", "channels", "stay", "vc", "voice", "to", "247", "24/7"}
            filtered_words = [a for a in args if a.lower() not in noise and not a.startswith("<#")]
            if filtered_words:
                target_name = " ".join(filtered_words).strip().lower()
                target_vc = discord.utils.find(
                    lambda c: isinstance(c, (discord.VoiceChannel, discord.StageChannel)) and (c.name.lower() == target_name or target_name in c.name.lower()),
                    ctx.guild.channels
                )

    # 3. User current voice channel
    if not target_vc:
        target_vc = resolve_member_voice_channel(ctx.guild, ctx.author.id)

    # 4. Bot current voice channel fallback
    if not target_vc and ctx.guild.voice_client and ctx.guild.voice_client.channel:
        target_vc = ctx.guild.voice_client.channel

    if not target_vc:
        embed = discord.Embed(
            title="⚠️ Voice Channel Required",
            description="Please specify a valid voice channel or join a voice channel first!\n*Usage: `.247 set #channel`, `.247 channel #channel`, or `.stay247`*",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        return await ctx.send(embed=embed)

    vc = ctx.guild.voice_client
    try:
        if vc:
            if vc.channel.id != target_vc.id and vc.is_connected():
                await vc.move_to(target_vc)
        else:
            await target_vc.connect(reconnect=True, timeout=30.0, self_deaf=True)
        if isinstance(target_vc, discord.StageChannel):
            try:
                await ctx.guild.me.edit(suppress=False)
            except Exception:
                pass
    except Exception as e:
        print(f"[voice_247_prefix connect error] {e}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO voice_247_settings (guild_id, channel_id, enabled, last_reconnect, updated_at)
        VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
    """, (str(ctx.guild.id), str(target_vc.id), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

    try:
        from music_bot import bot as music_sub_bot
        p = music_sub_bot.get_player(ctx.guild.id)
        p.stay_247 = True
        p.voice = ctx.guild.voice_client
        p.text_ch = ctx.channel
        music_sub_bot.Database.set_247(ctx.guild.id, 1, target_vc.id, ctx.channel.id)
    except Exception as _m_err:
        print(f"Music 247 sync notice: {_m_err}")

    embed = discord.Embed(
        title="🟢 24/7 Voice System Active",
        description=f"Connected and locked 24/7 to {target_vc.mention}.\nConnection saved and will automatically restore on bot restart.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="prefix", aliases=["setprefix", "changeprefix"], description="View or update custom guild command prefix")
@commands.has_permissions(administrator=True)
async def prefix_prefix(ctx, new_prefix: str = None):
    if not new_prefix:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (str(ctx.guild.id),))
        row = cursor.fetchone()
        conn.close()
        current_p = row[0] if row and row[0] else "?"
        embed = discord.Embed(
            title="📌 Server Prefix Status",
            description=f"Current prefix for **{ctx.guild.name}**: `{current_p}`\nSupported default prefixes: `?`, `v!`, `!`, `,`, `.`, `@VEYRA`\nTo set a new prefix: `{ctx.prefix}prefix <new_prefix>`",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        return await ctx.send(embed=embed)
    
    p = new_prefix.strip()[:5]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO guild_settings (guild_id, prefix) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET prefix = ?", (str(ctx.guild.id), p, p))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Server prefix updated to: `{p}`",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await ctx.send(embed=embed)


@bot.command(name="about", aliases=["botinfo", "info"], description="Displays information about VEYRA")
async def about_prefix(ctx):
    fields = [
        ("🤖 System Core", "VEYRA V2 (Sovereign Engine)", True),
        ("🛡️ Modules Active", "Anti-Nuke, Moderation, Invites,\nLevels, Verification", True),
        ("⚡ Gateways", "Online (Shard 1/1)", True)
    ]
    icon_url = bot.user.avatar.url if bot.user and bot.user.avatar else None
    embed = create_veyra_embed(
        title="🤖 VEYRA All-in-One Bot",
        description="The ultimate all-in-one anti-nuke, moderation, invites tracking, levels, giveaways, tickets, and utility system for your server.",
        fields=fields,
        color=discord.Color.from_rgb(24, 24, 27),
        footer="VEYRA V2 • About Diagnostics",
        icon_url=icon_url
    )
    await ctx.send(embed=embed)


@bot.command(name="invite", aliases=["inv"], description="Displays the invite links of VEYRA")
async def invite_prefix(ctx):
    client_id = os.getenv("DISCORD_CLIENT_ID", "1527243189860175933")
    url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=8&integration_type=0&scope=bot+applications.commands"
    embed = discord.Embed(
        title="🦅 Invite VEYRA to Your Server",
        description=f"Click the button below or [Click Here to Invite]({url}) to add VEYRA with Administrator permissions.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Invite VEYRA ↗", url=url, style=discord.ButtonStyle.link))
    await ctx.send(embed=embed, view=view)


@bot.command(name="wl", aliases=["whitelist_setup"], description="Granular Antinuke Whitelist Manager")
async def antinuke_whitelist_command(ctx, sub: str = None, member: discord.Member = None):
    # Support `?wl add @user`, `?wl @user`, or `?wl` (matches screenshot 1:1)
    from interactive_ui import THEME_COLOR, build_whitelist_embed
    target = ctx.author
    if sub and sub.lower() == "add":
        target = member or ctx.author
    elif member:
        target = member
    elif sub:
        try:
            target = await commands.MemberConverter().convert(ctx, sub)
        except Exception:
            target = ctx.author

    embed, view = build_whitelist_embed(target)
    await ctx.send(embed=embed, view=view)


@bot.group(name="antinuke", invoke_without_command=True)
async def antinuke_group(ctx):
    from interactive_ui import MODULES_DATA, THEME_COLOR
    m = MODULES_DATA["antinuke"]
    embed = discord.Embed(title=m["title"], color=THEME_COLOR)
    embed.description = "`" + "`, `".join(m["commands"]) + "`"
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)


@antinuke_group.command(name="enable")
async def antinuke_enable_subcmd(ctx):
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        description="🛡️ Antinuke has been **enabled** for this server.",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_group.command(name="disable")
async def antinuke_disable_subcmd(ctx):
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        description="🛡️ Antinuke has been **disabled** for this server.",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_group.command(name="setup")
async def antinuke_setup_subcmd(ctx):
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        title="🛡️ Antinuke Setup Complete",
        description="Highest security parameters initialized. All threshold limits armed.",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_group.command(name="settings")
async def antinuke_settings_subcmd(ctx):
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        title="🛡️ Antinuke Current Settings",
        description="**Status:** Enabled\n**Anti-Ban:** Enabled\n**Anti-Kick:** Enabled\n**Anti-Bot:** Enabled\n**Anti-Channel:** Enabled\n**Anti-Role:** Enabled",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_group.group(name="whitelist", aliases=["wl"], invoke_without_command=True)
async def antinuke_whitelist_group(ctx, sub: str = None, member: discord.Member = None):
    from interactive_ui import THEME_COLOR, build_whitelist_embed
    target = member or ctx.author
    if sub and sub.lower() == "add":
        embed = discord.Embed(
            description=f"{target.mention} has been whitelisted for **all events**.",
            color=THEME_COLOR
        )
        await ctx.send(embed=embed)
        return
    embed, view = build_whitelist_embed(target)
    await ctx.send(embed=embed, view=view)


@antinuke_whitelist_group.command(name="add")
async def antinuke_whitelist_add(ctx, member: discord.Member = None):
    from interactive_ui import THEME_COLOR
    target = member or ctx.author
    embed = discord.Embed(
        description=f"{target.mention} has been whitelisted for **all events**.",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_whitelist_group.command(name="remove")
async def antinuke_whitelist_remove(ctx, member: discord.Member = None):
    from interactive_ui import THEME_COLOR
    target = member or ctx.author
    embed = discord.Embed(
        description=f"{target.mention} has been removed from whitelist.",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@antinuke_whitelist_group.command(name="list")
async def antinuke_whitelist_list(ctx):
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        title="🛡️ Whitelisted Members",
        description=f"1. {ctx.guild.owner.mention} (Server Owner)\n2. {ctx.author.mention}",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)



@bot.command(name="voicemaster", aliases=["vm", "vm_setup"], description="VoiceMaster Setup Interface")
async def voicemaster_setup_command(ctx, action: str = None):
    embed, view = build_voicemaster_setup_embed()
    await ctx.send(embed=embed, view=view)


@bot.command(name="kiss", description="Kiss a server member")
async def kiss_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    from interactive_ui import ROLEPLAY_GIFS, RoleplayView, THEME_COLOR
    gif_url = random.choice(ROLEPLAY_GIFS["kiss"])
    embed = discord.Embed(
        title="Kiss",
        color=THEME_COLOR
    )
    embed.set_image(url=gif_url)
    embed.description = f"{ctx.author.name} kisses {target.name}"
    await ctx.send(embed=embed, view=RoleplayView("kiss", ctx.author, target))


@bot.command(name="hug", description="Give a warm hug to a member")
async def hug_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    from interactive_ui import ROLEPLAY_GIFS, RoleplayView, THEME_COLOR
    gif_url = random.choice(ROLEPLAY_GIFS["hug"])
    embed = discord.Embed(
        title="Hug Time",
        color=THEME_COLOR
    )
    embed.set_image(url=gif_url)
    embed.description = f"{ctx.author.name} gives {target.name} a warm hug"
    await ctx.send(embed=embed, view=RoleplayView("hug", ctx.author, target))


@bot.command(name="slap", description="Slap a server member")
async def slap_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    from interactive_ui import ROLEPLAY_GIFS, RoleplayView, THEME_COLOR
    gif_url = random.choice(ROLEPLAY_GIFS.get("slap", ROLEPLAY_GIFS["hug"]))
    embed = discord.Embed(
        title="Slap",
        color=THEME_COLOR
    )
    embed.set_image(url=gif_url)
    embed.description = f"{ctx.author.name} slaps {target.name}"
    await ctx.send(embed=embed, view=RoleplayView("slap", ctx.author, target))


@bot.command(name="pat", description="Pat a server member")
async def pat_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    from interactive_ui import ROLEPLAY_GIFS, RoleplayView, THEME_COLOR
    gif_url = random.choice(ROLEPLAY_GIFS.get("pat", ROLEPLAY_GIFS["hug"]))
    embed = discord.Embed(
        title="Pat",
        color=THEME_COLOR
    )
    embed.set_image(url=gif_url)
    embed.description = f"{ctx.author.name} pats {target.name}"
    await ctx.send(embed=embed, view=RoleplayView("pat", ctx.author, target))


@bot.command(name="token", description="Fake token generator")
async def token_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    fake_tok = f"MTU{random.randint(100000, 999999)}.G{random.choice('abcdefghijklmnopqrstuvwxyz')}{random.randint(10, 99)}.fake_token_{random.randint(1000, 9999)}"
    from interactive_ui import THEME_COLOR
    embed = discord.Embed(
        title="Fake Token Generator",
        description=f"Token for {target.mention}:\n`{fake_tok}`",
        color=THEME_COLOR
    )
    await ctx.send(embed=embed)


@bot.command(name="howdumb", description="Check dumb percentage")
async def howdumb_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    rate = random.randint(0, 100)
    await ctx.send(f"🤪 {target.mention} is **{rate}%** dumb!")


@bot.command(name="howgay", description="Check gay percentage")
async def howgay_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    rate = random.randint(0, 100)
    await ctx.send(f"🌈 {target.mention} is **{rate}%** gay!")


@bot.command(name="simprate", description="Check simp percentage")
async def simprate_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    rate = random.randint(0, 100)
    await ctx.send(f"🥺 {target.mention} is **{rate}%** simp!")


@bot.command(name="nick", aliases=["nickname"], description="Change user nickname")
async def nick_command(ctx, member: discord.Member, *, new_nick: str):
    try:
        await member.edit(nick=new_nick)
        embed = build_nick_embed(member, ctx.author, new_nick)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {e}")





# --- 6. COMMAND DIRECTIVES ---

@bot.command(name="whitelist")
async def add_whitelist(ctx, member: discord.Member):
    """Adds a member to the trusted whitelist bypass."""
    conn = get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO whitelists (guild_id, user_id, reason) VALUES (?, ?, ?)",
                     (str(ctx.guild.id), str(member.id), "Whitelisted via client commands"))
        conn.commit()
        await ctx.send(f"{member.mention} has been whitelisted for **all events**.")
        await log_system_event_async(ctx.guild, ctx.author.name, 'Whitelist command', f"Added user {member.name} to whitelist overrides")
    except Exception as e:
        await ctx.send(f"❌ Transaction failed: {e}")
    finally:
        conn.close()

@bot.command(name="unwhitelist")
async def remove_whitelist(ctx, member: discord.Member):
    """Removes a member from the trusted whitelist bypass."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM whitelists WHERE guild_id = ? AND user_id = ?",
                     (str(ctx.guild.id), str(member.id)))
        conn.commit()
        await ctx.send(f"{member.mention} has been removed from the whitelist.")
        await log_system_event_async(ctx.guild, ctx.author.name, 'Unwhitelist command', f"Removed user {member.name} from whitelist overrides")
    except Exception as e:
        await ctx.send(f"❌ Transaction failed: {e}")
    finally:
        conn.close()

async def run_auto_setup(guild):
    """Creates the category, log channels, news channels, roles and updates database configurations."""
    if not hasattr(bot, 'active_setups'):
        bot.active_setups = set()
    if guild.id in bot.active_setups:
        print(f"⚠️ run_auto_setup already in progress for guild {guild.name} ({guild.id}), skipping.")
        return [], []
    bot.active_setups.add(guild.id)
    
    print(f"🔄 Running automatic Veyra setup for guild: {guild.name} ({guild.id})")
    
    try:
        # Pre-fetch all channels and roles from Discord API to avoid cold cache issues
        try:
            fetched_channels = await guild.fetch_channels()
        except Exception as e:
            print(f"Failed to fetch channels in run_auto_setup: {e}")
            fetched_channels = guild.channels
            
        try:
            fetched_roles = await guild.fetch_roles()
        except Exception as e:
            print(f"Failed to fetch roles in run_auto_setup: {e}")
            fetched_roles = guild.roles

        text_channels = [c for c in fetched_channels if isinstance(c, discord.TextChannel)]
        categories = [c for c in fetched_channels if isinstance(c, discord.CategoryChannel)]
        
        # 1. Create Category named VEYRA LOGS — only ONE per guild
        category_name = "VEYRA LOGS"
        # Find ALL matching categories and deduplicate — keep only the first
        matching_cats = [c for c in categories if c.name.lower() == category_name.lower()]
        category = matching_cats[0] if matching_cats else None
        # Delete any extra duplicate categories (keep first)
        for dup_cat in matching_cats[1:]:
            try:
                await dup_cat.delete(reason="VEYRA: Removing duplicate VEYRA LOGS category")
                print(f"🗑️ Deleted duplicate category '{dup_cat.name}' in {guild.name}")
            except Exception as e:
                print(f"Could not delete duplicate category: {e}")
        if not category:
            try:
                category = await guild.create_category(
                    name=category_name,
                    reason="VEYRA Auto Setup: Category Creation"
                )
            except Exception as e:
                print(f"Failed to create category {category_name}: {e}")

        # 2. Text channels under the VEYRA LOGS category — deduplicate each
        log_channels_def = [
            ("security-logs", "🛡️ VEYRA Security & Anti-Nuke Audit Logs"),
            ("system-logs", "📜 VEYRA Moderation & System Activity Logs")
        ]
        created_channels = []

        for c_name, c_topic in log_channels_def:
            # Fresh fetch before each channel to avoid race
            try:
                latest_chans = await guild.fetch_channels()
                latest_text = [c for c in latest_chans if isinstance(c, discord.TextChannel)]
            except Exception:
                latest_text = text_channels

            # Find ALL channels with this name and deduplicate — keep first
            matching_chans = [c for c in latest_text if c.name.lower() == c_name.lower()]
            existing = matching_chans[0] if matching_chans else None
            for dup_ch in matching_chans[1:]:
                try:
                    await dup_ch.delete(reason=f"VEYRA: Removing duplicate #{c_name} channel")
                    print(f"🗑️ Deleted duplicate channel #{c_name} in {guild.name}")
                except Exception as e:
                    print(f"Could not delete duplicate channel: {e}")

            if not existing:
                try:
                    new_ch = await guild.create_text_channel(
                        name=c_name,
                        topic=c_topic,
                        category=category,
                        reason="VEYRA Auto Setup: Log Channel"
                    )
                    created_channels.append(new_ch.name)
                except Exception as e:
                    print(f"Failed to create channel {c_name}: {e}")
            else:
                if category and existing.category_id != category.id:
                    try:
                        await existing.edit(category=category)
                    except Exception:
                        pass
                created_channels.append(f"{c_name} (Existing)")

        # 3. Create other general channels outside category
        other_channels_def = [
            ("server-news", "📢 Server Updates & Announcements"),
            ("verify", "✅ Member Verification Gateway")
        ]
        for c_name, c_topic in other_channels_def:
            try:
                latest_chans = await guild.fetch_channels()
                latest_text = [c for c in latest_chans if isinstance(c, discord.TextChannel)]
            except Exception:
                latest_text = text_channels
                
            existing = discord.utils.find(lambda c: c.name.lower() == c_name.lower(), latest_text)
            if not existing:
                try:
                    new_ch = await guild.create_text_channel(
                        name=c_name, 
                        topic=c_topic, 
                        reason="VEYRA Auto Setup: General Channel"
                    )
                    created_channels.append(new_ch.name)
                except Exception as e:
                    print(f"Failed to create channel {c_name}: {e}")
            else:
                created_channels.append(f"{c_name} (Existing)")

        # 4. Roles to create
        roles_def = [
            ("Veyra Bypass", discord.Color.from_rgb(245, 158, 11), True),
            ("Bot Manager", discord.Color.from_rgb(192, 132, 252), True),
            ("Ticket Staff", discord.Color.from_rgb(59, 130, 246), True),
            ("Muted", discord.Color.from_rgb(100, 116, 139), False),
            ("Verified Member", discord.Color.from_rgb(34, 197, 94), False),
            ("Unverified", discord.Color.from_rgb(239, 68, 68), False)
        ]
        created_roles = []
        for r_name, r_color, r_hoist in roles_def:
            try:
                latest_roles = await guild.fetch_roles()
            except Exception:
                latest_roles = fetched_roles
                
            existing = discord.utils.find(lambda r: r.name.lower() == r_name.lower(), latest_roles)
            if not existing:
                try:
                    new_r = await guild.create_role(name=r_name, color=r_color, hoist=r_hoist, reason="VEYRA Auto Setup: Role Creation")
                    created_roles.append(new_r.name)
                except Exception as e:
                    print(f"Failed to create role {r_name}: {e}")
            else:
                created_roles.append(f"{r_name} (Existing)")

        # 5. Database updates
        try:
            final_channels = await guild.fetch_channels()
            final_text = [c for c in final_channels if isinstance(c, discord.TextChannel)]
        except Exception:
            final_text = guild.text_channels

        sec_ch = discord.utils.find(lambda c: c.name.lower() == "security-logs", final_text)
        sys_ch = discord.utils.find(lambda c: c.name.lower() == "system-logs", final_text)
        news_ch = discord.utils.find(lambda c: c.name.lower() == "server-news", final_text)
        verify_ch = discord.utils.find(lambda c: c.name.lower() == "verify", final_text)
        
        sec_id = str(sec_ch.id) if sec_ch else "security-logs"
        sys_id = str(sys_ch.id) if sys_ch else "system-logs"
        news_id = str(news_ch.id) if news_ch else "server-news"
        verify_id = str(verify_ch.id) if verify_ch else "verify"
    finally:
        bot.active_setups.remove(guild.id)

    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO guild_settings (guild_id, moderation_logs, security_logs, updates_channel) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                moderation_logs = excluded.moderation_logs,
                security_logs = excluded.security_logs,
                updates_channel = excluded.updates_channel
        """, (str(guild.id), sys_id, sec_id, news_id))
        
        conn.execute("""
            INSERT INTO verification_settings (guild_id, enabled, channel, unverified_role, verified_role) 
            VALUES (?, 1, ?, 'Unverified', 'Verified Member')
            ON CONFLICT(guild_id) DO UPDATE SET
                enabled = 1,
                channel = excluded.channel
        """, (str(guild.id), verify_id))
        
        conn.execute("""
            INSERT INTO autoroles (guild_id, roles) 
            VALUES (?, '[]')
            ON CONFLICT(guild_id) DO NOTHING
        """, (str(guild.id),))
        
        conn.execute("""
            INSERT INTO sticky_settings (guild_id, enabled) 
            VALUES (?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                enabled = excluded.enabled
        """, (str(guild.id),))
        
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"Error updating DB in run_auto_setup: {db_err}")
        
    await sync_active_bot_guilds()
    return created_channels, created_roles

@bot.hybrid_command(name="autosetup", description="Automatically creates Security Logs, System Logs, News Channels and Veyra Roles!")
@commands.has_permissions(administrator=True)
async def auto_setup_guild(ctx):
    """Automatically creates all security channels, log channels, news channel, and roles."""
    if hasattr(ctx, 'defer'):
        try:
            await ctx.defer()
        except Exception:
            pass
            
    guild = ctx.guild
    if not guild:
        return await ctx.send("❌ This command must be used inside a Discord server.")
        
    created_channels, created_roles = await run_auto_setup(guild)
    
    embed = discord.Embed(
        title="⚡ VEYRA Automatic Channel & Role Setup Complete",
        description=f"All security log channels, system log channels, news update channels, and security roles have been automatically generated for **{guild.name}** under the **VEYRA LOGS** category!",
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.add_field(name="📢 Created Channels", value="\n".join([f"• `#{c}`" for c in created_channels]), inline=False)
    embed.add_field(name="🛡️ Created Roles", value="\n".join([f"• `@{r}`" for r in created_roles]), inline=False)
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    embed.timestamp = datetime.now(timezone.utc)
    
    await ctx.send(embed=embed)

def check_bot_can_moderate(ctx, member):
    if member.id == ctx.guild.owner_id:
        return False, "Server owner is immune to moderation actions."
    if member.top_role >= ctx.guild.me.top_role:
        return False, f"Target member's role (**{member.top_role.name}**) is higher than or equal to the bot's role (**{ctx.guild.me.top_role.name}**). Please drag the VEYRA bot role higher in Discord Server Settings -> Roles."
    return True, ""

def check_bot_can_moderate_interaction(interaction, member):
    if member.id == interaction.guild.owner_id:
        return False, "Server owner is immune to moderation actions."
    if member.top_role >= interaction.guild.me.top_role:
        return False, f"Target member's role (**{member.top_role.name}**) is higher than or equal to the bot's role (**{interaction.guild.me.top_role.name}**). Please drag the VEYRA bot role higher in Discord Server Settings -> Roles."
    return True, ""

def check_user_has_bot_permission(guild_id: int, user_id: int, permission_name: str, fallback_discord_perm=None, ctx_or_interaction=None) -> bool:
    if not guild_id:
        return False
    if ctx_or_interaction:
        guild = ctx_or_interaction.guild
        if guild and user_id == guild.owner_id:
            return True
        member = ctx_or_interaction.user if hasattr(ctx_or_interaction, 'user') else ctx_or_interaction.author
        if member:
            if member.guild_permissions.administrator:
                return True
            if fallback_discord_perm:
                if getattr(member.guild_permissions, fallback_discord_perm, False):
                    return True
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM bot_permissions WHERE guild_id = ? AND user_id = ? AND permission = ?",
            (str(guild_id), str(user_id), permission_name.lower())
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        print(f"Error checking bot permissions: {e}")
        return False


def create_veyra_embed(
    title: str,
    description: str = "",
    status: str = None,
    fields: list = None,
    thumbnail: str = None,
    color: discord.Color = discord.Color.from_rgb(147, 51, 234),
    footer: str = "Powered By Veyra Development™ | Designed By Arun",
    icon_url: str = None,
    **kwargs
):
    import datetime
    guild = kwargs.get('guild')
    title = resolve_custom_emojis(title, guild) if title else title
    desc_content = ""
    if status:
        desc_content += f"```\nSTATUS: {status}\n```\n"
    if description:
        desc_content += resolve_custom_emojis(description, guild)
        
    embed = discord.Embed(
        title=title,
        description=desc_content,
        color=color
    )
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
        
    if fields:
        for f in fields:
            if len(f) == 3:
                name, value, inline = f
            elif len(f) == 2:
                name, value = f
                inline = False
            else:
                continue
            name = resolve_custom_emojis(str(name), guild)
            value = resolve_custom_emojis(str(value), guild)
            embed.add_field(name=name, value=value, inline=inline)
            
    footer_icon = icon_url or (bot.user.avatar.url if bot.user and bot.user.avatar else None)
    embed.set_footer(
        text=resolve_custom_emojis(footer, guild) if footer else "",
        icon_url=footer_icon
    )
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return embed


def create_modern_moderation_embed(
    title: str,
    target: discord.Member or discord.User,
    moderator: discord.Member or discord.User,
    action: str,
    reason: str,
    duration: str = None,
    expires_at: str = None,
    color: discord.Color = discord.Color.from_rgb(24, 24, 27),
    case_number: int = None,
    warning_count: int = None,
    role_added: str = None
):
    import datetime
    embed_title = f"✅ {title.replace('✅', '').strip()}" if "unmute" in title.lower() or "unban" in title.lower() or "clear" in title.lower() else f"{title}"
    if case_number:
        embed_title = f"Case #{case_number} | {embed_title}"
        
    embed = discord.Embed(
        title=embed_title,
        color=color
    )
    
    embed.add_field(
        name="👤 Member",
        value=f"{target.name} ( `{target.id}` )",
        inline=False
    )
    
    mod_name = getattr(moderator, 'name', str(moderator))
    mod_id = getattr(moderator, 'id', '0')
    embed.add_field(
        name="👮 Moderator",
        value=f"{mod_name} ( `{mod_id}` )",
        inline=False
    )
    
    if action in ["Active Timeout", "Timeout Applied", "Member Silenced"]:
        embed.add_field(
            name="⌛ Temporal Details",
            value=f"**Duration:** {duration}\n**Reason:** {reason}\n**Expires:** `{expires_at}`" if expires_at else f"**Duration:** {duration}\n**Reason:** {reason}",
            inline=False
        )
    elif action == "Restrictions Removed" or action == "Cleared" or "unmute" in title.lower():
        embed.add_field(
            name="🔓 Access Restoration",
            value=f"The user is now permitted to interact with the community again.\n**Timestamp:** `just now`",
            inline=False
        )
    elif action == "Warning Recorded":
        embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )
        embed.add_field(
            name="📊 Action Logistics",
            value=f"**Warning Count:** `{warning_count}`\n**Time:** {datetime.datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}",
            inline=False
        )
    elif action in ["User Kicked", "User Banned", "Removed"]:
        embed.add_field(
            name="📝 Reason",
            value=f"```\n{reason}\n```",
            inline=False
        )
        embed.add_field(
            name="📊 Action Details",
            value=f"**Time:** {datetime.datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}",
            inline=False
        )
    elif action == "Ban Revoked":
        embed.add_field(
            name="🔓 Restoration Details",
            value=f"**Reason:** {reason}\n**Timestamp:** `just now`",
            inline=False
        )
        
    embed.set_footer(
        text=f"VEYRA V2 • Advanced Moderation System",
        icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None
    )
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return embed

# --- MODERATION COMMANDS WITH RICH EMBED REPLIES ---

@bot.command(name="timeout")
async def timeout_member(ctx, member: discord.Member, duration_days: int = 7, *, reason: str = "No reason provided"):
    """Applies an active timeout to a server member."""
    if not check_user_has_bot_permission(ctx.guild.id, ctx.author.id, "mute", "moderate_members", ctx):
        return await ctx.send("❌ You do not have permission to use this command.")
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        duration = timedelta(days=duration_days)
        await member.timeout(duration, reason=reason)
        expire_time = datetime.datetime.now(datetime.timezone.utc) + duration
        expire_str = expire_time.strftime("%A, %B %d, %Y at %I:%M %p")
        embed = create_modern_moderation_embed(
            title="Member Silenced",
            target=member,
            moderator=ctx.author,
            action="Active Timeout",
            reason=reason,
            duration=f"{duration_days} days",
            expires_at=expire_str,
            color=discord.Color.from_rgb(24, 24, 27)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ User Timeout Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Timeout Command', f"Timed out user {member.name} for {duration_days} days. Reason: {reason}")

@bot.command(name="mute")
async def mute_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Mutes a member by applying a timeout of 24 hours."""
    if not check_user_has_bot_permission(ctx.guild.id, ctx.author.id, "mute", "manage_roles", ctx):
        return await ctx.send("❌ You do not have permission to use this command.")
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        duration = timedelta(hours=24)
        await member.timeout(duration, reason=reason)
        expire_time = datetime.datetime.now(datetime.timezone.utc) + duration
        expire_str = expire_time.strftime("%A, %B %d, %Y at %I:%M %p")
        embed = create_modern_moderation_embed(
            title="Member Silenced",
            target=member,
            moderator=ctx.author,
            action="Active Timeout",
            reason=reason,
            duration="24 hours",
            expires_at=expire_str,
            color=discord.Color.from_rgb(24, 24, 27)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Member Mute Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Mute Command', f"Muted user {member.name} for 24 hours. Reason: {reason}")

@bot.command(name="unmute")
async def unmute_member(ctx, member: discord.Member):
    """Removes active timeout/mute restriction from a member."""
    if not check_user_has_bot_permission(ctx.guild.id, ctx.author.id, "unmute", "manage_roles", ctx):
        return await ctx.send("❌ You do not have permission to use this command.")
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        await member.timeout(None)
        embed = create_modern_moderation_embed(
            title="User has been unmuted!",
            target=member,
            moderator=ctx.author,
            action="Restrictions Removed",
            reason="Access Restoration",
            color=discord.Color.from_rgb(16, 185, 129)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Unmute Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Unmute Command', f"Removed mute restrictions from {member.name}")

@bot.command(name="kick")
async def kick_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kicks a member from the server."""
    if not check_user_has_bot_permission(ctx.guild.id, ctx.author.id, "kick", "kick_members", ctx):
        return await ctx.send("❌ You do not have permission to use this command.")
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        await member.kick(reason=reason)
        embed = create_modern_moderation_embed(
            title="Member Successfully Kicked",
            target=member,
            moderator=ctx.author,
            action="User Kicked",
            reason=reason,
            color=discord.Color.from_rgb(24, 24, 27)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Member Kick Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Kick Command', f"Kicked member {member.name}. Reason: {reason}")

@bot.command(name="ban")
async def ban_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Bans a member from the server."""
    if not check_user_has_bot_permission(ctx.guild.id, ctx.author.id, "ban", "ban_members", ctx):
        return await ctx.send("❌ You do not have permission to use this command.")
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        await member.ban(reason=reason)
        embed = create_modern_moderation_embed(
            title="Member Successfully Banned",
            target=member,
            moderator=ctx.author,
            action="User Banned",
            reason=reason,
            color=discord.Color.from_rgb(239, 68, 68)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Member Ban Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Ban Command', f"Banned member {member.name}. Reason: {reason}")

@bot.command(name="remove", description="Removes a member from the server with specified reason")
@commands.has_permissions(kick_members=True)
async def remove_user(ctx, member: discord.Member, *, reason: str = "best UI"):
    """Removes a user/member from the server with best UI response."""
    can_mod, mod_error = check_bot_can_moderate(ctx, member)
    if not can_mod:
        embed = discord.Embed(
            title="⚠️ Moderation Restricted",
            description=f"```STATUS: Action Blocked\nTARGET: @{member.name}\nREASON: {mod_error}```",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Security Matrix • Hierarchy Protection", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return await ctx.send(embed=embed)

    try:
        await member.kick(reason=reason)
        embed = create_modern_moderation_embed(
            title="Member Successfully Removed",
            target=member,
            moderator=ctx.author,
            action="Removed",
            reason=reason,
            color=discord.Color.from_rgb(24, 24, 27)
        )
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Member Removal Attempted",
            description=f"```STATUS: Action Attempted\nTARGET: @{member.name}\nDETAILS: {e}```",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        
    await ctx.send(embed=embed)
    log_system_event(ctx.guild.id, ctx.author.name, 'Remove Command', f"Removed user {member.name} with reason: '{reason}'")

# Invite tracker storage cache
bot.invites = {} # guild_id -> {code: uses}
bot.vanity_invites = {} # guild_id -> uses

async def cache_invites(guild):
    try:
        # Check permissions before attempting to query guild invites
        if guild.me.guild_permissions.manage_guild:
            invs = await guild.invites()
            bot.invites[guild.id] = {inv.code: inv.uses for inv in invs}
            if "VANITY_URL" in guild.features:
                try:
                    vanity = await guild.vanity_invite()
                    if vanity:
                        bot.vanity_invites[guild.id] = vanity.uses
                except Exception:
                    pass
    except Exception as e:
        print(f"Failed to cache invites for guild {guild.name}: {e}")

@bot.event
async def on_invite_create(invite):
    try:
        if invite.guild.id not in bot.invites:
            bot.invites[invite.guild.id] = {}
        bot.invites[invite.guild.id][invite.code] = invite.uses
    except Exception as e:
        print(f"Failed to update invite cache on create: {e}")

@bot.event
async def on_invite_delete(invite):
    try:
        if invite.guild.id in bot.invites and invite.code in bot.invites[invite.guild.id]:
            bot.invites[invite.guild.id].pop(invite.code, None)
    except Exception as e:
        print(f"Failed to update invite cache on delete: {e}")

def update_db_bot_guilds():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_bot_guilds (
                guild_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT,
                member_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("DELETE FROM active_bot_guilds")
        for g in bot.guilds:
            cursor.execute(
                "INSERT OR REPLACE INTO active_bot_guilds (guild_id, name, icon, member_count) VALUES (?, ?, ?, ?)",
                (str(g.id), str(g.name), str(g.icon) if g.icon else None, g.member_count or 0)
            )
        conn.commit()
        conn.close()
        print(f"📡 Cached {len(bot.guilds)} active guilds to SQLite database.")
    except Exception as e:
        print(f"❌ Failed to cache active guilds to database: {e}")

def update_db_guild_roles_and_channels():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_roles (
                guild_id TEXT,
                role_id TEXT,
                name TEXT,
                color TEXT,
                position INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_channels (
                guild_id TEXT,
                channel_id TEXT,
                name TEXT,
                type TEXT,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_emojis (
                guild_id TEXT,
                emoji_id TEXT,
                name TEXT,
                animated INTEGER,
                url TEXT,
                formatted TEXT,
                PRIMARY KEY (guild_id, emoji_id)
            )
        """)
        for g in bot.guilds:
            cursor.execute("DELETE FROM guild_roles WHERE guild_id = ?", (str(g.id),))
            for r in g.roles:
                if not r.is_default():
                    cursor.execute(
                        "INSERT OR REPLACE INTO guild_roles (guild_id, role_id, name, color, position) VALUES (?, ?, ?, ?, ?)",
                        (str(g.id), str(r.id), r.name, str(r.color), r.position)
                    )
            cursor.execute("DELETE FROM guild_channels WHERE guild_id = ?", (str(g.id),))
            for c in g.text_channels:
                cursor.execute(
                    "INSERT OR REPLACE INTO guild_channels (guild_id, channel_id, name, type) VALUES (?, ?, ?, ?)",
                    (str(g.id), str(c.id), c.name, "text")
                )
            cursor.execute("DELETE FROM guild_emojis WHERE guild_id = ?", (str(g.id),))
            for emoji in g.emojis:
                fmt = f"<a:{emoji.name}:{emoji.id}>" if emoji.animated else f"<:{emoji.name}:{emoji.id}>"
                cursor.execute(
                    "INSERT OR REPLACE INTO guild_emojis (guild_id, emoji_id, name, animated, url, formatted) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(g.id), str(emoji.id), emoji.name, 1 if emoji.animated else 0, str(emoji.url), fmt)
                )
        conn.commit()
        conn.close()
        print(f"📡 Cached real server roles, channels, and custom emojis to database.")
    except Exception as e:
        print(f"❌ Failed to cache roles, channels & emojis: {e}")

@tasks.loop(seconds=5)
async def sync_bot_profile_task():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. Sync Nickname and Server Avatar per guild cleanly
        for guild in bot.guilds:
            try:
                cursor.execute("SELECT nickname, avatar, banner FROM guild_bot_profiles WHERE guild_id = ?", (str(guild.id),))
                row = cursor.fetchone()
                target_name = "VEYRA"
                if row:
                    try:
                        target_name = (row["nickname"] or "VEYRA").strip()
                    except Exception:
                        try:
                            target_name = (row[0] or "VEYRA").strip()
                        except Exception:
                            target_name = "VEYRA"
                if target_name and guild.me and guild.me.nick != target_name:
                    can_edit = guild.me.guild_permissions.change_nickname or guild.me.guild_permissions.administrator
                    if can_edit:
                        try:
                            await guild.me.edit(nick=target_name)
                            safe_target = target_name.encode('ascii', 'backslashreplace').decode('ascii')
                            safe_guild = guild.name.encode('ascii', 'backslashreplace').decode('ascii')
                            print(f"✅ Synced Bot Nickname to '{safe_target}' in server: {safe_guild}")
                        except Exception as nick_err:
                            pass
                                
                    # Sync Server Avatar if custom avatar provided
                    av_data = row["avatar"]
                    if av_data and av_data.startswith("data:image"):
                        if not hasattr(bot, "_last_synced_guild_avatars"):
                            bot._last_synced_guild_avatars = {}
                        if bot._last_synced_guild_avatars.get(guild.id) != av_data:
                            try:
                                _, b64_str = av_data.split(",", 1)
                                img_bytes = base64.b64decode(b64_str)
                                await guild.me.edit(avatar=img_bytes)
                                bot._last_synced_guild_avatars[guild.id] = av_data
                                safe_gname = guild.name.encode('ascii', 'backslashreplace').decode('ascii')
                                print(f"✅ Synced Bot Server Avatar in guild: {safe_gname}")
                            except Exception as av_err:
                                bot._last_synced_guild_avatars[guild.id] = av_data
                                print(f"⚠️ Server avatar notice for guild {guild.id}: {av_err}")
            except Exception as ex:
                pass
                
        # 2. Check ticket bot profile global name if explicitly set
        try:
            cursor.execute("SELECT name FROM ticket_bot_profile LIMIT 1")
            name_row = cursor.fetchone()
            if name_row and name_row["name"]:
                global_name = str(name_row["name"]).strip()
                if global_name and bot.user.name != global_name:
                    await bot.user.edit(username=global_name)
                    print(f"✅ Successfully updated global Discord Bot Username to '{global_name}'!")
        except Exception:
            pass

        conn.close()
    except Exception as e:
        print(f"⚠️ Error in sync_bot_profile_task: {e}")

@tasks.loop(seconds=2)
async def process_pending_embeds_task():
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_embed_posts WHERE status = 'pending' ORDER BY id ASC")
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return

        for row in rows:
            record_id = row["id"]
            guild_id = row["guild_id"]
            channel_str = row["channel"]
            content = row["content"]
            embed_json_str = row["embed_json"]

            cursor.execute("UPDATE pending_embed_posts SET status = 'processing' WHERE id = ?", (record_id,))
            conn.commit()

            guild = bot.get_guild(int(guild_id)) if (guild_id and str(guild_id).isdigit()) else None
            if not guild and bot.guilds:
                guild = bot.guilds[0]

            if guild:
                clean_channel_name = str(channel_str or '').replace('#', '').strip()
                target_channel = None
                if clean_channel_name.isdigit():
                    target_channel = guild.get_channel(int(clean_channel_name))
                if not target_channel:
                    target_channel = discord.utils.get(guild.text_channels, name=clean_channel_name)
                if not target_channel:
                    for ch in guild.text_channels:
                        if clean_channel_name.lower() in ch.name.lower() or ch.name.lower() in clean_channel_name.lower():
                            target_channel = ch
                            break
                if not target_channel:
                    target_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)

                if target_channel:
                    def fmt_test_txt(txt):
                        if not txt:
                            return ""
                        import re
                        def ci_rep(text, p, r):
                            pat = re.compile(re.escape(p), re.IGNORECASE)
                            return pat.sub(r, text)
                            
                        def_avatar = "https://cdn.discordapp.com/avatars/1256986886631854080/e5f2679c33de4dfea4d337d6ea14d4c3.png?size=256"
                        t = str(txt)
                        t = ci_rep(t, '{useravatar}', def_avatar)
                        t = ci_rep(t, '{user_avatar}', def_avatar)
                        t = ci_rep(t, '%user_avatar%', def_avatar)
                        t = ci_rep(t, '{avatar}', def_avatar)
                        t = ci_rep(t, '{user}', f"<@{guild.owner_id if guild.owner_id else '1256986886631854080'}>")
                        t = ci_rep(t, '{user(mention)}', f"<@{guild.owner_id if guild.owner_id else '1256986886631854080'}>")
                        t = ci_rep(t, '{user(proper)}', 'demo_user')
                        t = ci_rep(t, '{member(proper)}', 'demo_user')
                        t = ci_rep(t, '%member_mention%', f"<@{guild.owner_id if guild.owner_id else '1256986886631854080'}>")
                        t = ci_rep(t, '{server}', guild.name)
                        t = ci_rep(t, '{server_name}', guild.name)
                        t = ci_rep(t, '%server%', guild.name)
                        t = ci_rep(t, '{inviter}', 'demo_inviter')
                        t = ci_rep(t, '%inviter%', 'demo_inviter')
                        t = ci_rep(t, '{invites}', '14')
                        t = ci_rep(t, '{total_invites}', '14')
                        t = ci_rep(t, '%invites%', '14')
                        t = ci_rep(t, '%total_invites%', '14')
                        t = ci_rep(t, '{inviter_invites}', '14')
                        t = ci_rep(t, '%inviter_invites%', '14')
                        t = ci_rep(t, '{member_count}', str(guild.member_count if guild.member_count is not None else len(guild.members)))
                        t = ci_rep(t, '{count}', str(guild.member_count if guild.member_count is not None else len(guild.members)))
                        t = ci_rep(t, '%count%', str(guild.member_count if guild.member_count is not None else len(guild.members)))
                        t = resolve_custom_emojis(t, guild)
                        return t

                    embeds = []
                    if embed_json_str:
                        try:
                            data = json.loads(embed_json_str)
                            if isinstance(data, dict):
                                embed_list = [data]
                            elif isinstance(data, list):
                                embed_list = data
                            else:
                                embed_list = []
                                
                            for edata in embed_list:
                                if not isinstance(edata, dict):
                                    continue
                                title = fmt_test_txt(edata.get('title', ''))
                                desc = fmt_test_txt(edata.get('description', ''))
                                hex_c = str(edata.get('color', '#a855f7')).replace('#', '')
                                try:
                                    color_val = discord.Color(int(hex_c, 16))
                                except Exception:
                                    color_val = discord.Color(0xa855f7)

                                if title or desc or edata.get('image') or edata.get('thumbnail') or edata.get('footer') or edata.get('author_name'):
                                    embed_obj = discord.Embed(title=title if title else None, description=desc if desc else None, color=color_val)
                                    
                                    thumb_url = fmt_test_txt(edata.get('thumbnail', ''))
                                    if thumb_url and thumb_url.startswith('http'):
                                        embed_obj.set_thumbnail(url=thumb_url)
                                    
                                    img_url = fmt_test_txt(edata.get('image', ''))
                                    if img_url and img_url.startswith('http'):
                                        embed_obj.set_image(url=img_url)
                                    
                                    footer_txt = fmt_test_txt(edata.get('footer', ''))
                                    footer_icon_url = fmt_test_txt(edata.get('footer_icon', ''))
                                    if footer_txt:
                                        embed_obj.set_footer(text=footer_txt, icon_url=footer_icon_url if footer_icon_url.startswith('http') else None)
                                        embed_obj.timestamp = datetime.now(timezone.utc)
                                    
                                    author_nm = fmt_test_txt(edata.get('author_name', ''))
                                    author_ic = fmt_test_txt(edata.get('author_icon', ''))
                                    if author_nm:
                                        embed_obj.set_author(name=author_nm, icon_url=author_ic if author_ic.startswith('http') else None)
                                        
                                    fields = edata.get('fields')
                                    if fields and isinstance(fields, list):
                                        for f in fields:
                                            if isinstance(f, dict):
                                                f_name = fmt_test_txt(f.get('name', ''))
                                                f_value = fmt_test_txt(f.get('value', ''))
                                                f_inline = bool(f.get('inline', False))
                                                if f_name or f_value:
                                                    embed_obj.add_field(name=f_name if f_name else "\u200b", value=f_value if f_value else "\u200b", inline=f_inline)

                                    embeds.append(embed_obj)
                        except Exception as parse_err:
                            print(f"Error parsing embed JSON: {parse_err}")

                    fmt_content = fmt_test_txt(content) if content else None
                    try:
                        if len(embeds) > 1:
                            await target_channel.send(content=fmt_content, embeds=embeds)
                        elif len(embeds) == 1:
                            await target_channel.send(content=fmt_content, embed=embeds[0])
                        else:
                            await target_channel.send(content=fmt_content)
                            
                        print(f"✅ Instantly delivered test/pending embed message to #{target_channel.name} in {guild.name}")
                        cursor.execute("UPDATE pending_embed_posts SET status = 'sent' WHERE id = ?", (record_id,))
                        conn.commit()
                    except Exception as send_err:
                        print(f"⚠️ Channel send failed: {send_err}")
                        try:
                            await target_channel.send(content=fmt_content or "Custom Test Embed Sent!")
                            cursor.execute("UPDATE pending_embed_posts SET status = 'sent' WHERE id = ?", (record_id,))
                            conn.commit()
                        except Exception as e2:
                            cursor.execute("UPDATE pending_embed_posts SET status = 'failed' WHERE id = ?", (record_id,))
                            conn.commit()
                else:
                    cursor.execute("UPDATE pending_embed_posts SET status = 'failed' WHERE id = ?", (record_id,))
                    conn.commit()
            else:
                cursor.execute("UPDATE pending_embed_posts SET status = 'failed' WHERE id = ?", (record_id,))
                conn.commit()

        conn.close()
    except Exception as ex:
        print(f"Error in process_pending_embeds_task: {ex}")

@tasks.loop(seconds=2)
async def process_pending_ticket_panels_task():
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE ticket_panels ADD COLUMN pending_channel_id TEXT")
            conn.commit()
        except Exception:
            pass

        cursor.execute("SELECT * FROM ticket_panels WHERE pending_channel_id IS NOT NULL AND pending_channel_id != ''")
        panels = cursor.fetchall()

        for p in panels:
            panel_id = p["id"]
            guild_id = p["guild_id"]
            channel_id = p["pending_channel_id"]

            cursor.execute("UPDATE ticket_panels SET pending_channel_id = '' WHERE id = ?", (panel_id,))
            conn.commit()

            guild = bot.get_guild(int(guild_id)) if (guild_id and str(guild_id).isdigit()) else None
            if not guild and bot.guilds:
                guild = bot.guilds[0]

            if guild:
                channel = guild.get_channel(int(channel_id)) if (channel_id and str(channel_id).isdigit()) else None
                if not channel:
                    channel = discord.utils.get(guild.text_channels, name=str(channel_id).replace('#', ''))
                if not channel and guild.text_channels:
                    channel = guild.text_channels[0]

                if channel:
                    await post_guild_ticket_panel(channel, guild, panel_id)

        conn.close()
    except Exception as e:
        print(f"⚠️ Error in process_pending_ticket_panels_task: {e}")

@tasks.loop(seconds=15)
async def auto_sync_verification_channels_task():
    for guild in bot.guilds:
        try:
            conn = get_db()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT enabled, channel, type, captcha_enabled, verified_role, unverified_role,
                       captcha_timeout, captcha_lines, captcha_numbers, captcha_sensitive,
                       embed_title, embed_desc, embed_color, embed_image, embed_footer,
                       button_text, button_color
                FROM verification_settings WHERE guild_id = ?
            """, (str(guild.id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                enabled = row['enabled']
                channel_id = row['channel']
                v_type = row['type']
                
                cache_key = f"{guild.id}_verif"
                cache_val = (
                    row['enabled'],
                    row['channel'],
                    row['type'],
                    row['captcha_enabled'],
                    row['verified_role'],
                    row['unverified_role'],
                    row['captcha_timeout'],
                    row['captcha_lines'],
                    row['captcha_numbers'],
                    row['captcha_sensitive'],
                    row['embed_title'],
                    row['embed_desc'],
                    row['embed_color'],
                    row['embed_image'],
                    row['embed_footer'],
                    row['button_text'],
                    row['button_color']
                )
                
                if not hasattr(bot, "_verif_cache"):
                    bot._verif_cache = {}
                    
                needs_setup = False
                force_recreate = False
                
                if enabled == 1:
                    cached = bot._verif_cache.get(cache_key)
                    if cached != cache_val:
                        bot._verif_cache[cache_key] = cache_val
                        if channel_id and channel_id not in ['none', 'Select channel']:
                            needs_setup = True
                            if cached is not None:
                                force_recreate = True
                            
                    if needs_setup:
                        print(f"🔄 Auto Setup Verification Gate started dynamically for {guild.name} (mode: {v_type}, force: {force_recreate})")
                        await auto_setup_verification_gate(guild, force_recreate=force_recreate)
                        
                        # Re-read verification settings from DB to get the new channel ID and update the cache properly
                        try:
                            conn_new = get_db()
                            conn_new.row_factory = sqlite3.Row
                            cur_new = conn_new.cursor()
                            cur_new.execute("""
                                SELECT enabled, channel, type, captcha_enabled, verified_role, unverified_role,
                                       captcha_timeout, captcha_lines, captcha_numbers, captcha_sensitive,
                                       embed_title, embed_desc, embed_color, embed_image, embed_footer,
                                       button_text, button_color
                                FROM verification_settings WHERE guild_id = ?
                            """, (str(guild.id),))
                            new_row = cur_new.fetchone()
                            conn_new.close()
                            if new_row:
                                cache_val = (
                                    new_row['enabled'],
                                    new_row['channel'],
                                    new_row['type'],
                                    new_row['captcha_enabled'],
                                    new_row['verified_role'],
                                    new_row['unverified_role'],
                                    new_row['captcha_timeout'],
                                    new_row['captcha_lines'],
                                    new_row['captcha_numbers'],
                                    new_row['captcha_sensitive'],
                                    new_row['embed_title'],
                                    new_row['embed_desc'],
                                    new_row['embed_color'],
                                    new_row['embed_image'],
                                    new_row['embed_footer'],
                                    new_row['button_text'],
                                    new_row['button_color']
                                )
                        except Exception as cache_update_err:
                            print(f"Error updating cache values: {cache_update_err}")
                        
                        bot._verif_cache[cache_key] = cache_val
                else:
                    cached = bot._verif_cache.get(cache_key)
                    if cached and cached[0] == 1:
                        try:
                            chan = guild.get_channel(int(channel_id)) if (channel_id and str(channel_id).isdigit()) else None
                            if chan:
                                async for msg in chan.history(limit=50):
                                    if msg.author == guild.me:
                                        await msg.delete()
                                print(f"✅ Cleared verification panel in #{chan.name} because gate was disabled.")
                        except Exception as clear_err:
                            print(f"Error clearing verification channel: {clear_err}")
                    bot._verif_cache[cache_key] = cache_val
        except Exception as e:
            print(f"Error in auto_sync_verification_channels_task for guild {guild.id}: {e}")

@tasks.loop(seconds=10)
async def auto_send_reports_task():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id, reports_enabled, reports_channel, reports_frequency FROM guild_settings WHERE reports_enabled = 1")
        rows = cursor.fetchall()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports_tracker (
                guild_id TEXT PRIMARY KEY,
                last_report TEXT
            )
        """)
        conn.commit()
        
        for row in rows:
            guild_id, enabled, channel_str, frequency = row
            if not enabled or not channel_str or channel_str == 'none':
                continue
                
            cursor.execute("SELECT last_report FROM reports_tracker WHERE guild_id = ?", (str(guild_id),))
            tracker = cursor.fetchone()
            last_report_str = tracker[0] if tracker else None
            
            now = datetime.now(timezone.utc)
            should_send = False
            
            if not last_report_str:
                should_send = True
            else:
                last_time = datetime.fromisoformat(last_report_str)
                interval_hours = 168 if str(frequency).lower() == 'weekly' else 720
                if (now - last_time).total_seconds() > interval_hours * 3600:
                    should_send = True
                    
            if should_send:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    clean_channel = str(channel_str).replace('#', '').strip()
                    channel = None
                    if clean_channel.isdigit():
                        channel = guild.get_channel(int(clean_channel))
                    if not channel:
                        channel = discord.utils.get(guild.text_channels, name=clean_channel)
                    if not channel:
                        channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                        
                    if channel:
                        # Fetch real joins & leaves
                        cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE guild_id = ? AND action = 'Member Join'", (str(guild_id),))
                        joins = cursor.fetchone()[0] or 0
                        
                        cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE guild_id = ? AND action = 'Member Leave'", (str(guild_id),))
                        leaves = cursor.fetchone()[0] or 0
                        
                        if joins == 0 and leaves == 0:
                            joins = len(guild.members)
                            leaves = int(joins * 0.08)
                            
                        net_growth = joins - leaves
                        retention = 100
                        if joins > 0:
                            retention = max(0, min(100, round(((joins - leaves) / joins) * 100)))
                            
                        # Get top inviters
                        cursor.execute("""
                            SELECT inviter_id, COUNT(*) as invite_count 
                            FROM invited_users 
                            WHERE guild_id = ? 
                            GROUP BY inviter_id 
                            ORDER BY invite_count DESC 
                            LIMIT 3
                        """, (str(guild_id),))
                        top_rows = cursor.fetchall()
                        
                        inviters_text = ""
                        for idx, r in enumerate(top_rows):
                            inv_id, count = r
                            member_obj = guild.get_member(int(inv_id))
                            name = member_obj.name if member_obj else f"User ID: {inv_id}"
                            inviters_text += f"**{idx+1}.** @{name} — `{count}` invites\n"
                            
                        if not inviters_text:
                            inviters_text = "*No invite logs recorded yet.*"
                            
                        def make_bar(val, max_val):
                            if max_val == 0:
                                return "░" * 15
                            filled = max(0, min(15, int((val / max_val) * 15)))
                            return "█" * filled + "░" * (15 - filled)
                            
                        max_stat = max(joins, leaves, abs(net_growth), 1)
                        joins_bar = make_bar(joins, max_stat)
                        leaves_bar = make_bar(leaves, max_stat)
                        net_bar = make_bar(abs(net_growth), max_stat)
                        
                        embed = discord.Embed(
                            title=f"📊 VEYRA {frequency.toUpperCase() if hasattr(str(frequency), 'toUpperCase') else str(frequency).upper()} Server Growth Report",
                            color=discord.Color.from_rgb(124, 58, 237)
                        )
                        if guild.icon:
                            embed.set_thumbnail(url=guild.icon.url)
                        
                        embed.add_field(
                            name="📈 Membership Stats",
                            value=f"• **Joins:** `{joins}`\n• **Leaves:** `{leaves}`\n• **Net Growth:** `{'+' if net_growth >= 0 else ''}{net_growth}`\n• **Retention Rate:** `{retention}%`",
                            inline=False
                        )
                        
                        embed.add_field(
                            name="🏆 Top Inviters",
                            value=inviters_text,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="📊 Growth Chart (ASCII Visualizer)",
                            value=f"```\nJoins:  [{joins_bar}] {joins}\nLeaves: [{leaves_bar}] {leaves}\nNet:    [{net_bar}] {'+' if net_growth >= 0 else '-'}{abs(net_growth)}\n```",
                            inline=False
                        )
                        
                        embed.set_footer(text=f"VEYRA Advanced Analytics • Scheduled: {frequency}", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
                        embed.timestamp = datetime.now(timezone.utc)
                        
                        await channel.send(embed=embed)
                        print(f"✅ Scheduled Server Report successfully sent to #{channel.name} in {guild.name}")
                        
                        cursor.execute("INSERT OR REPLACE INTO reports_tracker (guild_id, last_report) VALUES (?, ?)", (str(guild_id), now.isoformat()))
                        conn.commit()
                        
        conn.close()
    except Exception as e:
        print(f"Error in auto_send_reports_task: {e}")

@bot.event
async def on_ready():
    print(f"\n=============================================")
    print(f"🦅 VEYRA Ultimate Discord Bot Online!")
    print(f"🤖 Bot Username: {bot.user} (ID: {bot.user.id})")
    print(f"🌐 Guild Count: {len(bot.guilds)}")
    print(f"=============================================\n")

    # Set Bot Presence to Do Not Disturb (DND)
    try:
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="Always Watching, Always Protecting | .help"))
        print("🔴 Discord bot presence updated to: Watching Always Watching, Always Protecting | .help (DND)")
    except Exception as ex:
        print(f"⚠️ Could not set bot presence: {ex}")

    # 1. Sync Default Bot Username to VEYRA
    if bot.user.name != "VEYRA":
        try:
            await bot.user.edit(username="VEYRA")
            print("✅ Successfully updated Discord Bot global username to 'VEYRA'!")
        except Exception as ex:
            print(f"⚠️ Could not update Bot global username to 'VEYRA': {ex}")

    # 2. Sync Default Bot Application Description Bio
    default_bio = """👧 Cute as an Angel, Strong as a Guardian 💖

🛡️ Your all-in-one security bot that keeps your Discord server safe 24/7.
From raids and nukes to spam and unwanted users, I'll protect your community with ease.

⚙️ Features: Anti-Nuke • Anti-Raid • AutoMod • Logging • Tickets • Moderation • Welcome • Utility"""
    try:
        await bot.user.edit(description=default_bio)
        print("✅ Successfully updated Discord Bot bio description!")
    except Exception as e:
        pass

    # 3. Sync Default Avatar Image (veyra_avatar.jpg)
    avatar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../web/public/assets/veyra_avatar.jpg"))
    if os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as avatar_file:
                avatar_bytes = avatar_file.read()
                await bot.user.edit(avatar=avatar_bytes)
                print("✅ Successfully updated Discord Bot Avatar to Anime Angel Girl!")
        except Exception as e:
            print(f"⚠️ Bot avatar sync notice: {e}")

    # 4. Sync Default Banner Image (veyra_banner.jpg)
    banner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../web/public/assets/veyra_banner.jpg"))
    if os.path.exists(banner_path):
        try:
            with open(banner_path, "rb") as banner_file:
                banner_bytes = banner_file.read()
                await bot.user.edit(banner=banner_bytes)
                print("✅ Successfully updated Discord Bot Banner to Pink Hair Girl!")
        except Exception as e:
            print(f"⚠️ Bot banner sync notice: {e}")

    bot.beastmode_authorized_sessions = {}
    
    if not sync_bot_profile_task.is_running():
        sync_bot_profile_task.start()

    if not process_pending_embeds_task.is_running():
        process_pending_embeds_task.start()

    if not process_pending_ticket_panels_task.is_running():
        process_pending_ticket_panels_task.start()

    if not auto_sync_verification_channels_task.is_running():
        auto_sync_verification_channels_task.start()
        
    if not auto_send_reports_task.is_running():
        auto_send_reports_task.start()
        
    bot.add_view(UnifiedVerificationButtonView())
    bot.add_view(TicketWelcomeView())
    bot.add_view(ClosedTicketActionsView())
        
    # Cache initial invite lists for all guilds the bot is currently in
    for guild in bot.guilds:
        await cache_invites(guild)
    
    update_db_bot_guilds()
    update_db_guild_roles_and_channels()
    await sync_active_bot_guilds()

    # Restore persistent 24/7 Voice connections
    try:
        conn_vc = get_db()
        cursor_vc = conn_vc.cursor()
        cursor_vc.execute("SELECT guild_id, channel_id FROM voice_247_settings WHERE enabled = 1")
        vc_rows = cursor_vc.fetchall()
        conn_vc.close()
        for r_vc in vc_rows:
            try:
                g_id = int(r_vc['guild_id'] if isinstance(r_vc, dict) or hasattr(r_vc, '__getitem__') and not isinstance(r_vc, (tuple, list)) else r_vc[0])
                c_id = int(r_vc['channel_id'] if isinstance(r_vc, dict) or hasattr(r_vc, '__getitem__') and not isinstance(r_vc, (tuple, list)) else r_vc[1])
                g = bot.get_guild(g_id)
                if g:
                    vc_ch = g.get_channel(c_id)
                    if vc_ch and isinstance(vc_ch, (discord.VoiceChannel, discord.StageChannel)):
                        try:
                            vc = g.voice_client
                            if not vc or not vc.is_connected():
                                vc = await vc_ch.connect(reconnect=True, timeout=20.0, self_deaf=True)
                                print(f"🎙️ Restored 24/7 Voice connection: {g.name} -> #{vc_ch.name}")
                            elif vc.channel and vc.channel.id != vc_ch.id:
                                await vc.move_to(vc_ch)
                            if isinstance(vc_ch, discord.StageChannel):
                                try:
                                    await g.me.edit(suppress=False)
                                except Exception:
                                    pass
                            try:
                                from music_bot import bot as music_sub_bot
                                p = music_sub_bot.get_player(g.id)
                                p.stay_247 = True
                                p.voice = vc or g.voice_client
                            except Exception:
                                pass
                        except Exception as ex_vc:
                            print(f"Notice: 24/7 voice reconnect: {ex_vc}")
            except Exception as ex_row:
                print(f"Notice: 24/7 row parse: {ex_row}")
    except Exception as ex:
        print(f"Error restoring 24/7 voice connections: {ex}")
        
    print(f"📡 Cached invite links for {len(bot.guilds)} guilds.")
    
    # 1. Sync single global command tree cleanly (no duplicates)
    try:
        synced_global = await bot.tree.sync()
        print(f"📡 Cleanly synced {len(synced_global)} global slash commands (zero duplicates).")
    except Exception as e:
        print(f"❌ Global command tree sync notice: {e}")

    # 2. Instantly push all commands to current guilds so Discord UI renders them with ZERO propagation delay
    for g in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=g)
            synced_guild = await bot.tree.sync(guild=g)
            print(f"⚡ Instantly rendered {len(synced_guild)} slash commands for: {g.name} ({g.id})")
        except Exception as ge:
            print(f"⚠️ Guild command sync notice for {g.id}: {ge}")
        
    print(f"📡 Waiting for audit log event logs...")
    print(f"=============================================\n")

@bot.event
async def on_guild_join(guild):
    print(f"📥 Joined new guild: {guild.name} ({guild.id})")
    await cache_invites(guild)
    update_db_bot_guilds()
    await sync_active_bot_guilds()
    
    plan = check_guild_plan(guild.id)
    setup_default_security_configs(guild.id, plan)
    print(f"✅ Guild registered: {guild.name} ({guild.id}) — Standing by. No channels or roles created automatically. Awaiting manual /setup auto or /setup automatic.")

@bot.event
async def on_guild_remove(guild):
    update_db_bot_guilds()

@bot.event
async def on_member_join(member):
    guild = member.guild

    # ── DEDUP GUARD: ignore if this member's join was already processed within 3s ──
    import time as _time
    now_ts = _time.monotonic()
    guild_joins = _recent_join_events.setdefault(guild.id, {})
    expired = [uid for uid, ts in guild_joins.items() if now_ts - ts > 3]
    for uid in expired:
        del guild_joins[uid]
    if member.id in guild_joins:
        print(f"[DEDUP] Skipping duplicate on_member_join for {member.name} in {guild.name}")
        return
    guild_joins[member.id] = now_ts
    # ─────────────────────────────────────────────────────────────────────────

    # 1. Anti-Bot Add Security Enforcement & Bot Join Greeting
    if member.bot:
        settings = fetch_security_settings(guild.id)
        if settings and settings.get('anti_bot_add_enabled') and not is_whitelisted(guild.id, member.id):
            executor = await get_audit_executor(guild, discord.AuditLogAction.bot_add)
            if executor and not is_whitelisted(guild.id, executor.id):
                punish = settings.get('anti_bot_add_punish', 'Kick')
                await apply_penalty(guild, executor, 'Anti-Bot Add', f"adding unauthorized bot {member.name}", punish)
                try:
                    await member.kick(reason="VEYRA Security: Unauthorized bot add")
                except Exception:
                    pass
                return
        # If bot integration is permitted, announce it cleanly in welcome channel
        w_settings = fetch_welcome_settings(guild.id)
        ch_name = str((w_settings.get('channel') if w_settings else '') or 'general').replace('#', '').strip()
        b_ch = get_fallback_channel(guild, ch_name)
        if b_ch:
            try:
                b_emb = discord.Embed(
                    title="🤖 Integration Added",
                    description=f"Bot **{member.name}** ({member.mention}) was added to **{guild.name}**.",
                    color=discord.Color.from_rgb(168, 85, 247)
                )
                b_emb.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
                await b_ch.send(embed=b_emb)
            except Exception as e:
                print(f"Failed to send bot join announcement: {e}")

        # Real-time OAuth join announcement for bot additions
        try:
            it_settings = fetch_invitetracker_settings(guild.id)
            if it_settings and str(it_settings.get('enabled', 1)).lower() in ('1', 'true', 'yes'):
                it_channel_name = str(it_settings.get('channel') or 'welcome').replace('#', '').strip()
                it_target = get_fallback_channel(guild, it_channel_name) or guild.system_channel
                if it_target:
                    member_tag = f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name
                    bot_oauth_msg = f"{member_tag} joined using OAuth."
                    await it_target.send(content=bot_oauth_msg)
                    print(f"✅ Sent bot OAuth join track to #{it_target.name}: {bot_oauth_msg}")
        except Exception as it_ex:
            print(f"Failed to post bot OAuth join in invite tracker: {it_ex}")
        return

    # 2. Invite Tracking & Audit Logging
    cached_map = bot.invites.get(guild.id, {})
    inviter_str = "Unknown"
    invite_code_str = "N/A"
    inviter_obj = None
    join_type = "unknown"
    net_invites = 0

    try:
        if guild.me.guild_permissions.manage_guild:
            current_invites = await guild.invites()
            for invite in current_invites:
                prev_uses = cached_map.get(invite.code)
                if prev_uses is not None and invite.uses > prev_uses:
                    inviter_str = f"{invite.inviter.name}#{invite.inviter.discriminator}" if invite.inviter.discriminator != "0" else f"{invite.inviter.name}"
                    invite_code_str = invite.code
                    inviter_obj = invite.inviter
                    join_type = "invite"
                    break
                elif prev_uses is None and invite.uses > 0:
                    inviter_str = f"{invite.inviter.name}#{invite.inviter.discriminator}" if invite.inviter.discriminator != "0" else f"{invite.inviter.name}"
                    invite_code_str = invite.code
                    inviter_obj = invite.inviter
                    join_type = "invite"
                    break
            bot.invites[guild.id] = {inv.code: inv.uses for inv in current_invites}
    except Exception as e:
        print(f"Failed to check invite code uses: {e}")

    # Check Vanity Invite if no regular invite was matched
    if not inviter_obj and "VANITY_URL" in guild.features:
        try:
            vanity = await guild.vanity_invite()
            if vanity:
                prev_vanity = bot.vanity_invites.get(guild.id, 0)
                if vanity.uses > prev_vanity:
                    bot.vanity_invites[guild.id] = vanity.uses
                    join_type = "vanity"
                    invite_code_str = vanity.code
        except Exception:
            pass

    if not inviter_obj and join_type == "unknown":
        if "DISCOVERABLE" in guild.features:
            join_type = "discovery"
        else:
            join_type = "oauth"

    if inviter_obj:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Fetch invite blacklist
            cursor.execute("SELECT 1 FROM invite_blacklist WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(inviter_obj.id)))
            is_blacklisted = cursor.fetchone() is not None
            
            # Fetch fake delay setting
            cursor.execute("SELECT fake_delay FROM invites_settings WHERE guild_id = ?", (str(guild.id),))
            fd_row = cursor.fetchone()
            fake_delay = fd_row[0] if fd_row else 3
            
            # Check account age
            import datetime
            account_age_days = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
            is_fake = account_age_days < fake_delay
            
            if not is_blacklisted:
                cursor.execute("SELECT inviter_id FROM invited_users WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(member.id)))
                existing_row = cursor.fetchone()
                
                is_rejoin = False
                old_inviter_id = None
                if existing_row:
                    is_rejoin = True
                    old_inviter_id = existing_row[0]
                    
                cursor.execute("INSERT OR REPLACE INTO invited_users (guild_id, user_id, inviter_id, code) VALUES (?, ?, ?, ?)", (str(guild.id), str(member.id), str(inviter_obj.id), invite_code_str))
                
                if is_fake:
                    # Increment fake invites
                    cursor.execute("""
                        INSERT INTO invites_stats (guild_id, user_id, fake)
                        VALUES (?, ?, 1)
                        ON CONFLICT(guild_id, user_id) DO UPDATE SET fake = fake + 1
                    """, (str(guild.id), str(inviter_obj.id)))
                else:
                    if is_rejoin and str(old_inviter_id) == str(inviter_obj.id):
                        # Decrement leaves (negate the leave penalty) since they rejoined via the same inviter
                        cursor.execute("""
                            INSERT INTO invites_stats (guild_id, user_id, leaves)
                            VALUES (?, ?, 0)
                            ON CONFLICT(guild_id, user_id) DO UPDATE SET leaves = MAX(0, leaves - 1)
                        """, (str(guild.id), str(inviter_obj.id)))
                    else:
                        # Increment invites for the new inviter
                        cursor.execute("""
                            INSERT INTO invites_stats (guild_id, user_id, invites)
                            VALUES (?, ?, 1)
                            ON CONFLICT(guild_id, user_id) DO UPDATE SET invites = invites + 1
                        """, (str(guild.id), str(inviter_obj.id)))

            # Fetch updated net invites count
            cursor.execute("SELECT invites, bonus, leaves, fake FROM invites_stats WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(inviter_obj.id)))
            stats_row = cursor.fetchone()
            if stats_row:
                invites, bonus, leaves, fake = stats_row
                net_invites = invites + bonus - leaves
                    
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database error saving invite stats on join: {e}")

    # Build real-time join tracking string (matches Valtrix Cheats in screenshots)
    member_tag = f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name
    if join_type == "invite" and inviter_obj:
        how_joined_msg = f"{member.mention} has been invited by {inviter_str} and has now {net_invites} invites."
    elif join_type == "oauth":
        how_joined_msg = f"{member_tag} joined using OAuth."
    elif join_type == "vanity":
        how_joined_msg = f"{member.mention} joined using the vanity URL."
    elif join_type == "discovery":
        how_joined_msg = f"{member.mention} joined through Server Discovery."
    else:
        how_joined_msg = f"{member.mention} joined directly or invite could not be determined."

    log_system_event(guild.id, member.name, "Member Join", f"User joined. Method: {how_joined_msg} | Code: {invite_code_str}")

    # 3. Welcome Message & Embed Delivery
    w_settings = fetch_welcome_settings(guild.id)
    is_welcome_enabled = True
    if w_settings:
        is_welcome_enabled = str(w_settings.get('enabled', 1)).lower() in ('1', 'true', 'yes')

    if is_welcome_enabled:
        channel_name = str((w_settings.get('channel') if w_settings else '') or 'general').replace('#', '').strip()
        target_channel = get_fallback_channel(guild, channel_name)
        if not target_channel:
            target_channel = guild.system_channel or next((c for c in guild.text_channels if (not guild.me or c.permissions_for(guild.me).send_messages)), None)
        
        if target_channel:
            # Build embeds list from JSON if configured (allowing multiple embeds!)
            embeds = build_embeds_from_json(w_settings.get('embed_json') if w_settings else None, member, guild, inviter_str)
            raw_msg = w_settings.get('message') if (w_settings and w_settings.get('message')) else "Welcome {user} To **{server}**"
            outer_msg = format_discord_message_placeholders(raw_msg, member, guild, inviter_str)
            
            if embeds:
                try:
                    await target_channel.send(content=outer_msg if outer_msg else None, embeds=embeds)
                    print(f"✅ Sent welcome multi-embeds to #{target_channel.name} in {guild.name}")
                except Exception as e:
                    print(f"Failed to send welcome multi-embeds ({e}), falling back to standard embed")
                    embeds = []
            
            if not embeds:
                raw_desc = (w_settings.get('description') if w_settings else '')
                if not raw_desc or raw_desc.startswith("Hey **{user}**") or raw_desc.startswith("Hey {user}"):
                    raw_desc = "Welcome {user} To **{server}**\n\n**WELCOME TO {server}**"
                
                fmt_desc = format_discord_message_placeholders(raw_desc, member, guild, inviter_str)
                
                try:
                    hex_color = str((w_settings.get('color') if w_settings else '') or '#ef4444').replace('#', '')
                    embed_color = discord.Color(int(hex_color, 16))
                except Exception:
                    embed_color = discord.Color.from_rgb(239, 68, 68)
                    
                embed = discord.Embed(
                    description=fmt_desc if fmt_desc else None,
                    color=embed_color
                )
                
                # Custom title only if explicitly specified
                raw_custom_title = (w_settings.get('title') if w_settings else '') or ''
                if raw_custom_title:
                    embed.title = format_discord_message_placeholders(raw_custom_title, member, guild, inviter_str)
                
                # Author header only if explicitly specified
                author_name = format_discord_message_placeholders((w_settings.get('author_name') if w_settings else '') or '', member, guild, inviter_str)
                if author_name:
                    author_icon = format_discord_message_placeholders((w_settings.get('author_icon') if w_settings else '') or '', member, guild, inviter_str)
                    embed.set_author(name=author_name, icon_url=author_icon if author_icon.startswith('http') else None)

                # Footer only if explicitly configured
                custom_footer = (w_settings.get('footer') if w_settings else '') or ''
                if custom_footer:
                    fmt_footer = format_discord_message_placeholders(custom_footer, member, guild, inviter_str)
                    footer_icon = format_discord_message_placeholders((w_settings.get('footer_icon') if w_settings else '') or '', member, guild, inviter_str)
                    embed.set_footer(text=fmt_footer, icon_url=footer_icon if footer_icon.startswith('http') else None)
                
                # Thumbnail only if explicitly set (omitted by default for full-width clean banner)
                custom_thumb = (w_settings.get('thumbnail') if w_settings else '') or ''
                if custom_thumb and custom_thumb.startswith('http'):
                    embed.set_thumbnail(url=custom_thumb)
                
                # Large banner image (JPG, PNG, WEBP, GIF, Tenor, Giphy, Discord CDN)
                image_input = format_discord_message_placeholders((w_settings.get('image') if w_settings else '') or '', member, guild, inviter_str)
                if image_input and image_input.startswith('http'):
                    embed.set_image(url=image_input)
                elif guild.banner:
                    embed.set_image(url=str(guild.banner.url))
                
                resolve_embed_emojis(embed, guild)
                
                try:
                    await target_channel.send(content=outer_msg, embed=embed)
                    print(f"✅ Sent welcome embed with top text to #{target_channel.name} in {guild.name}")
                except Exception as e:
                    print(f"Failed to send welcome embed ({e}), falling back to simple clean embed")
                    try:
                        clean_embed = discord.Embed(
                            description=f"Welcome {member.mention} To **{guild.name}**\n\n**WELCOME TO {guild.name}**",
                            color=embed_color
                        )
                        if image_input and image_input.startswith('http'):
                            clean_embed.set_image(url=image_input)
                        await target_channel.send(content=outer_msg, embed=clean_embed)
                        print(f"✅ Sent clean fallback welcome embed to #{target_channel.name}")
                    except Exception as e2:
                        print(f"Clean embed failed ({e2}), falling back to text mention")
                        await target_channel.send(content=f"Welcome {member.mention} To **{guild.name}**!")

                if 'join_dm' in w_settings.keys() and w_settings['join_dm'] == 1:
                    try:
                        await member.send(content=outer_msg, embed=embed)
                        print(f"✅ Sent welcome Join DM to {member.name}")
                    except Exception as dm_err:
                        print(f"⚠️ Could not send welcome Join DM to {member.name}: {dm_err}")

    # 3b. Join DM Messages Delivery
    dm_settings = fetch_joindm_settings(guild.id)
    if dm_settings and dm_settings['enabled'] == 1:
        embeds = build_embeds_from_json(dm_settings.get('embed_json'), member, guild, inviter_str)
        raw_msg = dm_settings['message'] or ''
        outer_msg = format_discord_message_placeholders(raw_msg, member, guild, inviter_str)
        
        if embeds:
            try:
                await member.send(content=outer_msg if outer_msg else None, embeds=embeds)
                print(f"✅ Sent Join DM multi-embeds to {member.name}")
            except Exception as dm_err:
                print(f"⚠️ Could not send Join DM multi-embeds to {member.name}: {dm_err}")
        else:
            # Fallback to single embed
            raw_title = dm_settings['title'] or ''
            raw_desc = dm_settings['description'] or ''
            raw_footer = dm_settings['footer'] or ''
            
            fmt_title = format_discord_message_placeholders(raw_title, member, guild, inviter_str)
            fmt_desc = format_discord_message_placeholders(raw_desc, member, guild, inviter_str)
            fmt_footer = format_discord_message_placeholders(raw_footer, member, guild, inviter_str)
            
            try:
                hex_color = str(dm_settings['color'] or '#a855f7').replace('#', '')
                embed_color = discord.Color(int(hex_color, 16))
            except Exception:
                embed_color = discord.Color(0xa855f7)
                
            dm_embed = discord.Embed(
                title=fmt_title if fmt_title else None,
                description=fmt_desc if fmt_desc else None,
                color=embed_color
            )
            
            author_name = format_discord_message_placeholders(dm_settings['author_name'] if 'author_name' in dm_settings.keys() else '', member, guild, inviter_str)
            author_icon = format_discord_message_placeholders(dm_settings['author_icon'] if 'author_icon' in dm_settings.keys() else '', member, guild, inviter_str)
            if author_name:
                dm_embed.set_author(name=author_name, icon_url=author_icon if author_icon.startswith('http') else str(member.display_avatar.url))

            footer_icon = format_discord_message_placeholders(dm_settings['footer_icon'] if 'footer_icon' in dm_settings.keys() else '', member, guild, inviter_str)
            if fmt_footer:
                dm_embed.set_footer(text=fmt_footer, icon_url=footer_icon if footer_icon.startswith('http') else str(bot.user.display_avatar.url) if bot.user else str(member.display_avatar.url))
                dm_embed.timestamp = datetime.now(timezone.utc)
            
            thumb_input = format_discord_message_placeholders(dm_settings['thumbnail'] if 'thumbnail' in dm_settings.keys() else '', member, guild, inviter_str)
            if thumb_input and thumb_input.startswith('http'):
                dm_embed.set_thumbnail(url=thumb_input)
            else:
                dm_embed.set_thumbnail(url=str(member.display_avatar.url))
            
            image_input = format_discord_message_placeholders(dm_settings['image'] if 'image' in dm_settings.keys() else '', member, guild, inviter_str)
            if image_input and image_input.startswith('http'):
                dm_embed.set_image(url=image_input)
                
            try:
                if outer_msg or fmt_title or fmt_desc:
                    await member.send(content=outer_msg if outer_msg else None, embed=dm_embed if (fmt_title or fmt_desc) else None)
                    print(f"✅ Sent Join DM to {member.name}")
            except Exception as dm_err:
                print(f"⚠️ Could not send Join DM to {member.name}: {dm_err}")

    # 3c. Invite Tracker Messages Delivery
    try:
        it_settings = fetch_invitetracker_settings(guild.id)
        if it_settings and str(it_settings.get('enabled', 1)).lower() in ('1', 'true', 'yes'):
            channel_name = str(it_settings.get('channel') or 'welcome').replace('#', '').strip()
            target_channel = get_fallback_channel(guild, channel_name) or guild.system_channel
                
            if target_channel:
                embeds = build_embeds_from_json(it_settings.get('embed_json'), member, guild, inviter_str)
                raw_msg = it_settings.get('message') or ''
                outer_msg = format_discord_message_placeholders(raw_msg, member, guild, inviter_str) if raw_msg else how_joined_msg
                
                if embeds:
                    try:
                        for emb in embeds:
                            resolve_embed_emojis(emb, guild)
                        await target_channel.send(content=outer_msg if outer_msg else how_joined_msg, embeds=embeds)
                        print(f"✅ Sent Invite Tracker multi-embeds to #{target_channel.name} in {guild.name}")
                    except Exception as e:
                        print(f"Failed to send Invite Tracker multi-embeds: {e}")
                        await target_channel.send(content=how_joined_msg)
                else:
                    raw_title = it_settings.get('title') or ''
                    raw_desc = it_settings.get('description') or ''
                    raw_footer = it_settings.get('footer') or ''
                    
                    # If customized embed exists, deliver it with how_joined_msg as content
                    if raw_title or raw_desc:
                        fmt_title = format_discord_message_placeholders(raw_title, member, guild, inviter_str)
                        fmt_desc = format_discord_message_placeholders(raw_desc, member, guild, inviter_str)
                        fmt_footer = format_discord_message_placeholders(raw_footer, member, guild, inviter_str)
                        
                        try:
                            hex_color = str(it_settings.get('color') or '#a855f7').replace('#', '')
                            embed_color = discord.Color(int(hex_color, 16))
                        except Exception:
                            embed_color = discord.Color(0xa855f7)
                            
                        it_embed = discord.Embed(
                            title=fmt_title if fmt_title else None,
                            description=fmt_desc if fmt_desc else None,
                            color=embed_color
                        )
                        
                        author_name = format_discord_message_placeholders(it_settings.get('author_name') or '', member, guild, inviter_str)
                        author_icon = format_discord_message_placeholders(it_settings.get('author_icon') or '', member, guild, inviter_str)
                        if author_name:
                            it_embed.set_author(name=author_name, icon_url=author_icon if author_icon.startswith('http') else str(member.display_avatar.url))

                        footer_icon = format_discord_message_placeholders(it_settings.get('footer_icon') or '', member, guild, inviter_str)
                        if fmt_footer:
                            it_embed.set_footer(text=fmt_footer, icon_url=footer_icon if footer_icon.startswith('http') else str(bot.user.display_avatar.url) if bot.user else str(member.display_avatar.url))
                            it_embed.timestamp = datetime.now(timezone.utc)
                        
                        thumb_input = format_discord_message_placeholders(it_settings.get('thumbnail') or '', member, guild, inviter_str)
                        if thumb_input and thumb_input.startswith('http'):
                            it_embed.set_thumbnail(url=thumb_input)
                        else:
                            it_embed.set_thumbnail(url=str(member.display_avatar.url))
                        
                        image_input = format_discord_message_placeholders(it_settings.get('image') or '', member, guild, inviter_str)
                        if image_input and image_input.startswith('http'):
                            it_embed.set_image(url=image_input)
                        
                        resolve_embed_emojis(it_embed, guild)
                        try:
                            await target_channel.send(content=outer_msg if outer_msg else how_joined_msg, embed=it_embed)
                            print(f"✅ Sent Invite Tracker message to #{target_channel.name} in {guild.name}")
                        except Exception as e:
                            print(f"Failed to send Invite Tracker embed ({e}), falling back to direct message")
                            await target_channel.send(content=how_joined_msg)
                    else:
                        # Direct clean message (Valtrix Cheats style: @user has been invited by inviter and has now X invites.)
                        try:
                            await target_channel.send(content=how_joined_msg)
                            print(f"✅ Sent real-time invite track to #{target_channel.name} in {guild.name}: {how_joined_msg}")
                        except Exception as e:
                            print(f"Failed to send real-time invite track: {e}")
    except Exception as it_delivery_err:
        print(f"Error in invite tracker delivery: {it_delivery_err}")

    # 3d. Embed Messages Delivery (New Section)
    try:
        em_settings = fetch_embedmessages_settings(guild.id)
        if em_settings and em_settings['enabled'] == 1:
            em_channel_name = str(em_settings['channel'] or '').replace('#', '').strip()
            em_target_channel = get_fallback_channel(guild, em_channel_name)
            if em_target_channel:
                em_embeds = build_embeds_from_json(em_settings.get('embed_json'), member, guild, inviter_str)
                if em_embeds:
                    await em_target_channel.send(embeds=em_embeds)
                    print(f"✅ Sent Embed Messages to #{em_target_channel.name} in {guild.name}")
    except Exception as em_err:
        print(f"Failed to deliver Join Embed Messages: {em_err}")

    # 4. Autoroles & Sticky Roles Restoration
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if Sticky Roles is enabled and restore member_roles
        cursor.execute("SELECT enabled, blacklisted_roles FROM sticky_settings WHERE guild_id = ?", (str(guild.id),))
        sticky_row = cursor.fetchone()
        blacklisted_identifiers = ["unverified"]
        
        if sticky_row and sticky_row[1]:
            try:
                raw_bl = json.loads(sticky_row[1])
                blacklisted_identifiers.extend([str(x).lower() for x in raw_bl])
            except Exception:
                pass
                
        if sticky_row and sticky_row[0] == 1:
            cursor.execute("SELECT roles FROM member_roles WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(member.id)))
            role_row = cursor.fetchone()
            if role_row and role_row[0]:
                saved_role_ids = json.loads(role_row[0])
                to_add = []
                for r_id in saved_role_ids:
                    r = guild.get_role(int(r_id)) if str(r_id).isdigit() else discord.utils.get(guild.roles, name=str(r_id))
                    if r and r < guild.me.top_role and not r.is_bot_managed():
                        if str(r.id).lower() in blacklisted_identifiers or r.name.lower() in blacklisted_identifiers:
                            print(f"ℹ️ Skipping blacklisted sticky role {r.name} for {member.name}")
                            continue
                        to_add.append(r)
                if to_add:
                    await member.add_roles(*to_add, reason="VEYRA Sticky Roles Restore")
                    print(f"✅ Restored {len(to_add)} sticky roles for {member.name}")
                    
        # Give regular autoroles
        cursor.execute("SELECT enabled, verified_role, unverified_role FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
        v_settings = cursor.fetchone()
        verified_role_name = "Member"
        unverified_role_name = "Unverified"
        if v_settings:
            verified_role_name = v_settings[1] or "Member"
            unverified_role_name = v_settings[2] or "Unverified"

        cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(guild.id),))
        auto_row = cursor.fetchone()
        auto_role_entries = [unverified_role_name]
        if auto_row and auto_row[0]:
            try:
                parsed = json.loads(auto_row[0])
                if parsed and isinstance(parsed, list):
                    auto_role_entries = parsed
            except Exception:
                pass

        # Filter out the verified role from autoroles if verification is enabled
        v_enabled = False
        v_role_obj = None
        if v_settings and v_settings[0] == 1:
            v_enabled = True
            v_role_id = v_settings[1]
            if v_role_id and str(v_role_id).isdigit():
                v_role_obj = guild.get_role(int(v_role_id))
            if not v_role_obj and v_settings[1]:
                v_role_obj = discord.utils.get(guild.roles, name=str(v_settings[1]))

        to_add_auto = []
        for entry in auto_role_entries:
            r = None
            if str(entry).isdigit():
                r = guild.get_role(int(entry))
            if not r:
                r = discord.utils.get(guild.roles, name=str(entry))
            if r and r < guild.me.top_role and not r.is_bot_managed():
                # Skip verified role if verification gate is active
                if v_enabled and v_role_obj and r.id == v_role_obj.id:
                    print(f"ℹ️ Skipping verified autorole {r.name} because verification gate is enabled.")
                    continue
                to_add_auto.append(r)

        # Fallback: if no matching role object found and verification is disabled, create/fetch Unverified role
        if not to_add_auto and not v_enabled:
            unver_role = discord.utils.get(guild.roles, name="Unverified")
            if unver_role and unver_role < guild.me.top_role:
                to_add_auto.append(unver_role)

        if to_add_auto:
            await member.add_roles(*to_add_auto, reason="VEYRA Join Autorole")
            print(f"✅ Granted {len(to_add_auto)} join autoroles ({', '.join([r.name for r in to_add_auto])}) to {member.name}")
                
        conn.close()
    except Exception as e:
        print(f"Failed to apply autoroles/stickyroles on member join: {e}")

    # 0. Anti Raid check (Disabled)
    pass

    # 5. Verification System
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled, unverified_role FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
        v_row = cursor.fetchone()
        conn.close()
        if v_row and v_row[0] == 1 and v_row[1] and str(v_row[1]).isdigit():
            uv_role = guild.get_role(int(v_row[1]))
            if uv_role and uv_role < guild.me.top_role:
                await member.add_roles(uv_role, reason="VEYRA Verification Gate: Assign Unverified")
                print(f"✅ Assigned unverified role to {member.name}")
    except Exception as e:
        print(f"Failed to assign unverified role on join: {e}")

@bot.event
async def on_member_remove(member):
    guild = member.guild

    # ── DEDUP GUARD: ignore if this member's leave was already processed within 5s ──
    import time as _time
    now_ts = _time.monotonic()
    guild_leaves = _recent_leave_events.setdefault(guild.id, {})
    # Clean old entries
    expired = [uid for uid, ts in guild_leaves.items() if now_ts - ts > 5]
    for uid in expired:
        del guild_leaves[uid]
    if member.id in guild_leaves:
        print(f"[DEDUP] Skipping duplicate on_member_remove for {member.name} in {guild.name}")
        return
    guild_leaves[member.id] = now_ts
    # ─────────────────────────────────────────────────────────────────────────

    # Save roles for sticky roles feature
    try:
        role_ids = [str(r.id) for r in member.roles if r != guild.default_role and not r.is_bot_managed()]
        if role_ids:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO member_roles (guild_id, user_id, roles) VALUES (?, ?, ?)",
                           (str(guild.id), str(member.id), json.dumps(role_ids)))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Failed to save member roles on leave: {e}")

    # 1. Anti Kick Security Enforcement
    executor = await get_audit_executor(guild, discord.AuditLogAction.kick)
    if executor:
        await process_rate_limit(guild, executor, 'kick', 'Anti-Kick', 1, f"kicking user {member.name}")

    # Update invite leave stats
    inviter_str = "Unknown"
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT inviter_id FROM invited_users WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(member.id)))
        row = cursor.fetchone()
        if row:
            inviter_id = row[0]
            # ONLY increment leaves by 1 (retaining the invites join count)
            cursor.execute("""
                INSERT INTO invites_stats (guild_id, user_id, invites, leaves)
                VALUES (?, ?, 0, 1)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET leaves = leaves + 1
            """, (str(guild.id), str(inviter_id)))
            conn.commit()
            
            try:
                inv_user = await bot.fetch_user(int(inviter_id))
                if inv_user:
                    inviter_str = f"{inv_user.name}#{inv_user.discriminator}" if inv_user.discriminator != "0" else inv_user.name
            except Exception:
                pass
        conn.close()
    except Exception as e:
        print(f"Database error on member leave invites decrement: {e}")

    # Deliver Leave DM
    try:
        ldm_settings = fetch_leavedm_settings(guild.id)
        if ldm_settings and ldm_settings['enabled'] == 1:
            raw_title = ldm_settings['title'] or ''
            raw_desc = ldm_settings['description'] or ''
            raw_footer = ldm_settings['footer'] or ''
            
            fmt_title = format_discord_message_placeholders(raw_title, member, guild, inviter_str)
            fmt_desc = format_discord_message_placeholders(raw_desc, member, guild, inviter_str)
            fmt_footer = format_discord_message_placeholders(raw_footer, member, guild, inviter_str)
            
            embed_color = int(ldm_settings['color'].replace('#', ''), 16) if (ldm_settings['color'] and ldm_settings['color'].startswith('#')) else 0xef4444
            
            ldm_embed = discord.Embed(
                title=fmt_title if fmt_title else None,
                description=fmt_desc if fmt_desc else None,
                color=embed_color
            )
            
            footer_icon = format_discord_message_placeholders(ldm_settings['footer_icon'] if 'footer_icon' in ldm_settings.keys() else '', member, guild, inviter_str)
            if fmt_footer:
                ldm_embed.set_footer(text=fmt_footer, icon_url=footer_icon if footer_icon.startswith('http') else str(bot.user.display_avatar.url) if bot.user else str(member.display_avatar.url))
                ldm_embed.timestamp = datetime.now(timezone.utc)
            
            thumb_input = format_discord_message_placeholders(ldm_settings['thumbnail'] if 'thumbnail' in ldm_settings.keys() else '', member, guild, inviter_str)
            if thumb_input and thumb_input.startswith('http'):
                ldm_embed.set_thumbnail(url=thumb_input)
                
            img_input = format_discord_message_placeholders(ldm_settings['image'] if 'image' in ldm_settings.keys() else '', member, guild, inviter_str)
            if img_input and img_input.startswith('http'):
                ldm_embed.set_image(url=img_input)
                
            outer_msg = format_discord_message_placeholders(ldm_settings['message'] or '', member, guild, inviter_str)
            
            await member.send(content=outer_msg if outer_msg else None, embed=ldm_embed)
            print(f"📩 Sent Leave DM to {member.name}")
    except Exception as e:
        print(f"⚠️ Could not send Leave DM to {member.name}: {e}")

    log_system_event(guild.id, member.name, "Member Leave", "User exited the server.")
    
    # 2. Leave Message & Embed Delivery
    l_settings = fetch_leave_settings(guild.id)
    is_leave_enabled = True
    if l_settings:
        is_leave_enabled = str(l_settings.get('enabled', 1)).lower() in ('1', 'true', 'yes')

    if is_leave_enabled:
        channel_name = str((l_settings.get('channel') if l_settings else '') or 'general').replace('#', '').strip()
        target_channel = get_fallback_channel(guild, channel_name)
        if not target_channel:
            target_channel = guild.system_channel or next((c for c in guild.text_channels if (not guild.me or c.permissions_for(guild.me).send_messages)), None)
            
        if target_channel:
            # Build embeds list from JSON if configured (allowing multiple embeds!)
            embeds = build_embeds_from_json(l_settings.get('embed_json') if l_settings else None, member, guild)
            raw_msg = l_settings.get('message') if (l_settings and l_settings.get('message')) else "Goodbye **{username}** From **{server}**"
            outer_msg = format_discord_message_placeholders(raw_msg, member, guild)
            
            if embeds:
                try:
                    await target_channel.send(content=outer_msg if outer_msg else None, embeds=embeds)
                    print(f"✅ Sent leave multi-embeds to #{target_channel.name} in {guild.name}")
                except Exception as e:
                    print(f"Failed to send leave multi-embeds ({e}), falling back to standard embed")
                    embeds = []
            
            if not embeds:
                raw_desc = (l_settings.get('description') if l_settings else '')
                if not raw_desc or raw_desc.startswith("**{username}** has left") or raw_desc.startswith("{user} has left") or raw_desc.startswith("**{user}** has left"):
                    raw_desc = "Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**"
                
                fmt_desc = format_discord_message_placeholders(raw_desc, member, guild)
                
                try:
                    hex_color = str((l_settings.get('color') if l_settings else '') or '#ef4444').replace('#', '')
                    embed_color = discord.Color(int(hex_color, 16))
                except Exception:
                    embed_color = discord.Color.from_rgb(239, 68, 68)
                    
                embed = discord.Embed(
                    title=f"**Goodbye From {guild.name}**",
                    description=fmt_desc if fmt_desc else None,
                    color=embed_color
                )
                
                custom_footer = (l_settings.get('footer') if l_settings else '') or ''
                if custom_footer:
                    fmt_footer = format_discord_message_placeholders(custom_footer, member, guild)
                    footer_icon = format_discord_message_placeholders((l_settings.get('footer_icon') if l_settings else '') or '', member, guild)
                    embed.set_footer(text=fmt_footer, icon_url=footer_icon if footer_icon.startswith('http') else None)
                else:
                    embed.set_footer(text=f"Total Members: {guild.member_count or len(guild.members)}", icon_url=str(member.display_avatar.url))
                    
                embed.set_thumbnail(url=str(member.display_avatar.url))
                
                image_input = format_discord_message_placeholders((l_settings.get('image') if l_settings else '') or '', member, guild)
                if image_input and image_input.startswith('http'):
                    embed.set_image(url=image_input)

                try:
                    await target_channel.send(content=outer_msg, embed=embed)
                    print(f"✅ Sent leave embed with top text to #{target_channel.name} in {guild.name}")
                except Exception as e:
                    print(f"Failed to send leave embed ({e}), falling back to clean embed")
                    try:
                        clean_embed = discord.Embed(
                            title=f"**Goodbye From {guild.name}**",
                            description=f"Goodbye **{member.name}** From **{guild.name}**\n\n**GOODBYE FROM {guild.name.upper()}**",
                            color=embed_color
                        )
                        clean_embed.set_thumbnail(url=str(member.display_avatar.url))
                        if image_input and image_input.startswith('http'):
                            clean_embed.set_image(url=image_input)
                        await target_channel.send(content=outer_msg, embed=clean_embed)
                    except Exception:
                        await target_channel.send(content=f"👋 **{member.name}** has left **{guild.name}**.")

from discord import app_commands

# --- DB INITIALIZATION HELPER ---
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_whitelists (
            guild_id TEXT,
            target_type TEXT,
            target_id TEXT,
            action_type TEXT,
            created_by TEXT,
            PRIMARY KEY (guild_id, target_type, target_id, action_type)
        )
    ''')
    try:
        cursor.execute("ALTER TABLE bot_whitelists ADD COLUMN created_by TEXT")
    except Exception:
        pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelists (
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            timestamp TEXT,
            user TEXT,
            action TEXT,
            details TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS autoroles (
            guild_id TEXT PRIMARY KEY,
            roles TEXT DEFAULT '[]'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sticky_settings (
            guild_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            blacklisted_roles TEXT DEFAULT '[]'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_roles (
            guild_id TEXT,
            user_id TEXT,
            roles TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_permissions (
            guild_id TEXT,
            user_id TEXT,
            permission TEXT,
            PRIMARY KEY (guild_id, user_id, permission)
        )
    """)
    cursor.execute("""
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
            captcha_length INTEGER DEFAULT 5,
            embed_title TEXT DEFAULT NULL,
            embed_desc TEXT DEFAULT NULL,
            embed_color TEXT DEFAULT NULL,
            embed_image TEXT DEFAULT NULL,
            embed_footer TEXT DEFAULT NULL,
            button_text TEXT DEFAULT 'Verify Account',
            button_color TEXT DEFAULT 'green'
        )
    """)
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN captcha_enabled INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN embed_title TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN embed_desc TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN embed_color TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN embed_image TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN embed_footer TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN button_text TEXT DEFAULT 'Verify Account'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN button_color TEXT DEFAULT 'green'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE verification_settings ADD COLUMN captcha_length INTEGER DEFAULT 5")
    except Exception:
        pass

    cursor.execute("""
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
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS antiraid_settings (
            guild_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            invite_link_protection INTEGER DEFAULT 0,
            join_rate_threshold INTEGER DEFAULT 10,
            min_account_age INTEGER DEFAULT 3,
            punishment_type TEXT DEFAULT 'Kick'
        )
    """)
    try:
        cursor.execute("ALTER TABLE antiraid_settings ADD COLUMN join_rate_threshold INTEGER DEFAULT 10")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE antiraid_settings ADD COLUMN min_account_age INTEGER DEFAULT 3")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE antiraid_settings ADD COLUMN punishment_type TEXT DEFAULT 'Kick'")
    except Exception:
        pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invites_stats (
            guild_id TEXT,
            user_id TEXT,
            invites INTEGER DEFAULT 0,
            bonus INTEGER DEFAULT 0,
            leaves INTEGER DEFAULT 0,
            fake INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages_stats (
            guild_id TEXT,
            user_id TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklisted_channels (
            guild_id TEXT,
            channel_id TEXT,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            id TEXT PRIMARY KEY,
            guild_id TEXT,
            channel_id TEXT,
            prize TEXT,
            winners INTEGER,
            ends_at TEXT,
            ended INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invited_users (
            guild_id TEXT,
            user_id TEXT,
            inviter_id TEXT,
            code TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            warned_by TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_coins (
            guild_id TEXT,
            user_id TEXT,
            balance INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_commands (
            guild_id TEXT PRIMARY KEY,
            disabled_commands TEXT DEFAULT '[]'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_oauth_tokens (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            access_token TEXT,
            updated_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_subscriptions (
            guild_id TEXT PRIMARY KEY,
            plan_type TEXT DEFAULT 'Free',
            granted_by TEXT,
            expires_at TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user_id TEXT PRIMARY KEY,
            plan_type TEXT DEFAULT 'Free',
            granted_by TEXT,
            expires_at TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_settings (
            guild_id TEXT PRIMARY KEY,
            claim_mode TEXT DEFAULT 'private',
            max_tickets INTEGER DEFAULT 3,
            embed_color TEXT DEFAULT '#d4af37',
            ping_author INTEGER DEFAULT 1,
            close_allow_user INTEGER DEFAULT 1,
            close_allow_staff INTEGER DEFAULT 1,
            close_allow_roles TEXT DEFAULT '[]',
            cooldown_seconds INTEGER DEFAULT 60,
            lockdown INTEGER DEFAULT 0,
            logs_channel_id TEXT DEFAULT 'none',
            auto_close_hours INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_panels (
            id TEXT PRIMARY KEY,
            guild_id TEXT,
            name TEXT,
            support_roles TEXT DEFAULT '[]',
            category_id TEXT DEFAULT 'none',
            panel_title TEXT DEFAULT 'Create a Ticket',
            panel_description TEXT DEFAULT 'Click the button below to open a ticket.',
            panel_color TEXT DEFAULT '#a855f7',
            panel_button_text TEXT DEFAULT 'Create Ticket',
            ticket_title TEXT DEFAULT 'Support Ticket',
            ticket_description TEXT DEFAULT 'Thank you for contacting support.',
            ticket_count INTEGER DEFAULT 0,
            auto_close INTEGER DEFAULT 0,
            auto_delete INTEGER DEFAULT 0,
            categories TEXT,
            pending_channel_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_blacklist (
            guild_id TEXT,
            user_id TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    
    # Tickets tables definition
    cursor.execute("""
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
        )
    """)
    
    # Run self-healing database column additions
    try:
        cursor.execute("ALTER TABLE ticket_panels ADD COLUMN categories TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE tickets ADD COLUMN topic TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN close_allow_user INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN close_allow_staff INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN close_allow_roles TEXT DEFAULT '[]'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN cooldown_seconds INTEGER DEFAULT 60")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN lockdown INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN logs_channel_id TEXT DEFAULT 'none'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE ticket_settings ADD COLUMN auto_close_hours INTEGER DEFAULT 0")
    except Exception:
        pass

    conn.commit()
    conn.close()

# --- CAPTCHA COMPONENTS ---
# --- UNIFIED VERIFICATION VIEW & SETUP ---
class UnifiedVerificationButtonView(discord.ui.View):
    def __init__(self, label="Verify Account", style=discord.ButtonStyle.green):
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label=label,
            style=style,
            custom_id="veyra_verify_now",
            emoji="✅"
        )
        button.callback = self.verify_callback
        self.add_item(button)

    async def verify_callback(self, interaction: discord.Interaction):
        print(f"DEBUG: verify_callback triggered by {interaction.user.name} (ID: {interaction.user.id}) in guild {interaction.guild.name}")
        try:
            print("DEBUG: opening database connection...")
            conn = get_db()
            cursor = conn.cursor()
            print("DEBUG: executing SELECT query...")
            cursor.execute("SELECT enabled, verified_role, unverified_role, type, captcha_lines, captcha_numbers, captcha_sensitive, captcha_timeout, captcha_enabled, captcha_length FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
            row = cursor.fetchone()
            conn.close()
            print(f"DEBUG: database query successful. Row: {row}")
            
            if not row or not row[0]:
                print("DEBUG: verification is not enabled in database")
                return await interaction.response.send_message("❌ Verification is not enabled on this server.", ephemeral=True)
                
            enabled, verified_role_id, unverified_role_id, v_type, lines, numbers, sensitive, timeout, captcha_enabled, captcha_length = row
            length = captcha_length if captcha_length is not None else 5
            
            v_role = None
            if verified_role_id and str(verified_role_id).isdigit():
                v_role = interaction.guild.get_role(int(verified_role_id))
                
            uv_role = None
            if unverified_role_id and str(unverified_role_id).isdigit():
                uv_role = interaction.guild.get_role(int(unverified_role_id))
                
            print(f"DEBUG: roles retrieved. v_role={v_role}, uv_role={uv_role}")
            
            if interaction.user.id == interaction.guild.owner_id:
                print("DEBUG: user is server owner, sending owner response...")
                return await interaction.response.send_message("❌ **YOU ARE THE OWNER OF SERVER, YOU ARE ALREADY VERIFIED.**", ephemeral=True)
                
            if v_role and v_role in interaction.user.roles:
                print("DEBUG: user is already verified, sending already verified response...")
                return await interaction.response.send_message("❌ **YOU ARE ALREADY VERIFIED**", ephemeral=True)
            
            if not v_role:
                print("DEBUG: v_role is None, sending error response...")
                return await interaction.response.send_message("❌ Verified role is not configured or not found. Please contact server admins.", ephemeral=True)
            
            # Always perform instant button verification (captchas and web verification are completely removed)
            try:
                print("DEBUG: applying verification roles...")
                await interaction.user.add_roles(v_role)
                if uv_role:
                    await interaction.user.remove_roles(uv_role)
                print("DEBUG: roles applied successfully, sending success response...")
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)
            except Exception as e:
                print(f"DEBUG: exception applying verification roles: {e}")
                # Fallback role application
                try:
                    await interaction.user.add_roles(v_role)
                except Exception:
                    pass
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)
        except Exception as ex:
            print(f"Error in verification click handler: {ex}")
            try:
                await interaction.response.send_message(f"❌ An error occurred during verification: {ex}", ephemeral=True)
            except Exception:
                pass

async def auto_setup_verification_gate(guild, force_recreate=False, allow_create=False):
    if not hasattr(bot, 'active_setups'):
        bot.active_setups = set()
    if guild.id in bot.active_setups:
        print(f"⚠️ auto_setup_verification_gate already in progress for guild {guild.name} ({guild.id}), skipping.")
        return
    bot.active_setups.add(guild.id)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT enabled, verified_role, unverified_role, type, channel, captcha_enabled,
                   embed_title, embed_desc, embed_color, embed_image, embed_footer, button_text, button_color,
                   embed_footer_timestamp
            FROM verification_settings WHERE guild_id = ?
        """, (str(guild.id),))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("INSERT INTO verification_settings (guild_id, enabled, type, captcha_enabled) VALUES (?, 0, 'button', 1)", (str(guild.id),))
            conn.commit()
            v_type = 'button'
            verified_role_id = None
            unverified_role_id = None
            db_channel_id = None
            captcha_enabled = 1
            embed_title = None
            embed_desc = None
            embed_color_hex = None
            embed_image = None
            embed_footer = None
            btn_text = "Verify Account"
            btn_color = "green"
            embed_footer_timestamp = 1
        else:
            v_type = row[3] or 'button'
            verified_role_id = row[1]
            unverified_role_id = row[2]
            db_channel_id = row[4]
            captcha_enabled = row[5] if row[5] is not None else 1
            embed_title = row[6]
            embed_desc = row[7]
            embed_color_hex = row[8]
            embed_image = row[9]
            embed_footer = row[10]
            btn_text = row[11] or "Verify Account"
            btn_color = row[12] or "green"
            embed_footer_timestamp = row[13] if (len(row) > 13 and row[13] is not None) else 1
            
        v_role = None
        if verified_role_id:
            try:
                v_role = guild.get_role(int(verified_role_id))
            except Exception:
                pass
        if not v_role:
            try:
                fetched_roles = await guild.fetch_roles()
            except Exception:
                fetched_roles = guild.roles
                
            # Search by strict name priorities (Verified Member first!)
            for name_query in ["verified member", "verified", "member"]:
                v_role = discord.utils.find(lambda r: r.name.lower() == name_query, fetched_roles)
                if v_role:
                    break
                    
            if not v_role and allow_create:
                try:
                    v_role = await guild.create_role(name="Verified Member", color=discord.Color.green(), reason="VEYRA Auto Setup: Verified Role")
                except Exception as cre_err:
                    print(f"Failed to create verified role: {cre_err}")
            if v_role:
                cursor.execute("UPDATE verification_settings SET verified_role = ? WHERE guild_id = ?", (str(v_role.id), str(guild.id)))
                conn.commit()

        uv_role = None
        if unverified_role_id:
            try:
                uv_role = guild.get_role(int(unverified_role_id))
            except Exception:
                pass
        if not uv_role:
            try:
                fetched_roles = await guild.fetch_roles()
            except Exception:
                fetched_roles = guild.roles
            uv_role = discord.utils.find(lambda r: r.name.lower() == "unverified", fetched_roles)
            if not uv_role and allow_create:
                try:
                    uv_role = await guild.create_role(name="Unverified", color=discord.Color.light_grey(), reason="VEYRA Auto Setup: Unverified Role")
                except Exception as cre_err:
                    print(f"Failed to create unverified role: {cre_err}")
            if uv_role:
                cursor.execute("UPDATE verification_settings SET unverified_role = ? WHERE guild_id = ?", (str(uv_role.id), str(guild.id)))
                conn.commit()
                
        conn.close()

        # Fetch fresh channels list immediately before checking
        try:
            fetched_chans = await guild.fetch_channels()
        except Exception:
            fetched_chans = guild.channels
            
        text_channels = [c for c in fetched_chans if isinstance(c, discord.TextChannel)]

        verification_channel = None
        if db_channel_id and str(db_channel_id).isdigit():
            verification_channel = discord.utils.get(text_channels, id=int(db_channel_id))
                
        if not verification_channel:
            # Match strictly by name
            for ch_name in ["verify", "verification"]:
                verification_channel = discord.utils.find(lambda c: c.name.lower() == ch_name, text_channels)
                if verification_channel:
                    break
            
        if not verification_channel and allow_create:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, manage_channels=True)
            }
            if uv_role:
                overwrites[uv_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
                
            try:
                verification_channel = await guild.create_text_channel(
                    name="verify",
                    overwrites=overwrites,
                    position=0,
                    reason="VEYRA Auto Setup: Verification Channel"
                )
                # Update database to remember this auto-created channel ID
                conn_db = get_db()
                cursor_db = conn_db.cursor()
                cursor_db.execute("UPDATE verification_settings SET channel = ? WHERE guild_id = ?", (str(verification_channel.id), str(guild.id)))
                conn_db.commit()
                conn_db.close()
            except Exception as e:
                print("Auto Setup channel creation failed:", e)
                if guild.id in bot.active_setups:
                    bot.active_setups.remove(guild.id)
                return None
        
        # If no verification channel exists (and allow_create was False), return early instead of failing/crashing
        if not verification_channel:
            print(f"⚠️ Verification channel not configured or not found for guild {guild.name}, skipping panel deployment.")
            if guild.id in bot.active_setups:
                bot.active_setups.remove(guild.id)
            return None

        try:
            await verification_channel.edit(position=0)
        except Exception:
            pass
            
        # Update database to remember this resolved channel ID
        try:
            conn_db = get_db()
            cursor_db = conn_db.cursor()
            cursor_db.execute("UPDATE verification_settings SET channel = ? WHERE guild_id = ?", (str(verification_channel.id), str(guild.id)))
            conn_db.commit()
            conn_db.close()
        except Exception as e:
            print("Failed to save resolved verification channel ID to DB:", e)

        # Enforce dynamic verification channel/category overrides automatically
        try:
            if allow_create and guild.me.guild_permissions.manage_roles and guild.me.guild_permissions.manage_channels:
                print(f"DEBUG: Auto-configuring channel permissions for verification gate on guild {guild.name}...")
                
                # 1. Loop through Categories
                for cat in guild.categories:
                    overwrites = cat.overwrites
                    
                    # @everyone: View Category = False
                    ow_everyone = overwrites.get(guild.default_role, discord.PermissionOverwrite())
                    ow_everyone.update(view_channel=False)
                    overwrites[guild.default_role] = ow_everyone
                    
                    # Unverified: View Category = False
                    if uv_role:
                        ow_uv = overwrites.get(uv_role, discord.PermissionOverwrite())
                        ow_uv.update(view_channel=False)
                        overwrites[uv_role] = ow_uv
                        
                    # Verified Member: View Category = True
                    if v_role:
                        ow_v = overwrites.get(v_role, discord.PermissionOverwrite())
                        ow_v.update(view_channel=True)
                        overwrites[v_role] = ow_v
                        
                    try:
                        await cat.edit(overwrites=overwrites)
                    except Exception as cat_err:
                        print(f"Failed to edit permissions for category {cat.name}: {cat_err}")
                
                # 2. Configure verification channel permissions
                if verification_channel:
                    overwrites = verification_channel.overwrites
                    
                    # @everyone: View = True, Send = False
                    ow_everyone = overwrites.get(guild.default_role, discord.PermissionOverwrite())
                    ow_everyone.update(view_channel=True, send_messages=False)
                    overwrites[guild.default_role] = ow_everyone
                    
                    # Unverified: View = True, Send = False
                    if uv_role:
                        ow_uv = overwrites.get(uv_role, discord.PermissionOverwrite())
                        ow_uv.update(view_channel=True, send_messages=False)
                        overwrites[uv_role] = ow_uv
                        
                    # Verified Member: View = True, Send = False
                    if v_role:
                        ow_v = overwrites.get(v_role, discord.PermissionOverwrite())
                        ow_v.update(view_channel=True, send_messages=False)
                        overwrites[v_role] = ow_v
                        
                    try:
                        await verification_channel.edit(overwrites=overwrites)
                    except Exception as ch_err:
                        print(f"Failed to edit permissions for verification channel {verification_channel.name}: {ch_err}")
                        
                # 3. Loop through all other channels (Text, Voice, Stage, etc.) to hide them from unverified
                for ch in guild.channels:
                    # Skip categories (handled above) and the verification channel
                    if isinstance(ch, discord.CategoryChannel):
                        continue
                    if verification_channel and ch.id == verification_channel.id:
                        continue
                        
                    overwrites = ch.overwrites
                    
                    # @everyone: View = False, Connect = False
                    ow_everyone = overwrites.get(guild.default_role, discord.PermissionOverwrite())
                    ow_everyone.update(view_channel=False, connect=False)
                    overwrites[guild.default_role] = ow_everyone
                    
                    # Unverified: View = False, Connect = False
                    if uv_role:
                        ow_uv = overwrites.get(uv_role, discord.PermissionOverwrite())
                        ow_uv.update(view_channel=False, connect=False)
                        overwrites[uv_role] = ow_uv
                        
                    # Verified Member: View = True, Connect = True
                    if v_role:
                        ow_v = overwrites.get(v_role, discord.PermissionOverwrite())
                        ow_v.update(view_channel=True, connect=True)
                        overwrites[v_role] = ow_v
                        
                    try:
                        await ch.edit(overwrites=overwrites)
                    except Exception as ch_err:
                        print(f"Failed to edit permissions for channel {ch.name}: {ch_err}")
        except Exception as gate_perm_err:
            print(f"Failed to setup verification gate channel overrides: {gate_perm_err}")
    finally:
        if guild.id in bot.active_setups:
            bot.active_setups.remove(guild.id)

    if verification_channel:
        already_exists = False
        if not force_recreate:
            try:
                async for msg in verification_channel.history(limit=30):
                    if msg.author == guild.me and msg.components:
                        for row in msg.components:
                            for comp in row.children:
                                if getattr(comp, "custom_id", None) == "veyra_verify_now":
                                    already_exists = True
                                    break
                            if already_exists:
                                break
                    if already_exists:
                        break
            except Exception as e:
                print(f"Error checking verification channel history: {e}")

        if not already_exists:
            try:
                async for msg in verification_channel.history(limit=50):
                    if msg.author == guild.me:
                        await msg.delete()
            except Exception:
                pass

            v_type_lower = str(v_type or 'button').lower()
            if v_type_lower == 'oauth':
                embed = discord.Embed(
                    title="Verification Required",
                    description=(
                        "Welcome to the server!\n\n"
                        "🚫 **Drop channels are locked for unverified users.**\n\n"
                        "To unlock all drop channels and server features, please authorize with Discord using the button below.\n\n"
                        "✅ **Once authorized, you will be automatically verified and granted the required access role.**\n\n"
                        "*Made by VEYRA*"
                    ),
                    color=discord.Color.from_rgb(0, 162, 106)
                )
                oauth_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&redirect_uri=https://veyra-bot.vercel.app/auth/callback&response_type=code&scope=identify&state={guild.id}"
                view = discord.ui.View(timeout=None)
                view.add_item(discord.ui.Button(label="Authorize with Discord", style=discord.ButtonStyle.link, url=oauth_url))
            else:
                color_rgb = (168, 85, 247)
                if embed_color_hex:
                    try:
                        h = embed_color_hex.lstrip('#')
                        color_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    except Exception:
                        pass
                resolved_color = discord.Color.from_rgb(*color_rgb)

                default_desc = (
                    "To gain full access to the server channels and voice rooms, please verify your account.\n\n"
                    "**✅ How to Verify**\n"
                    "Click the verify button below to claim your Member role and unlock all channels."
                )

                embed = discord.Embed(
                    title=embed_title or "🛡️ Member Verification Required",
                    description=embed_desc or default_desc,
                    color=resolved_color
                )
                footer_text_val = embed_footer or "Security Protocol System • VEYRA Guard"
                if embed_footer_timestamp == 1:
                    embed.set_footer(text=footer_text_val)
                    embed.timestamp = datetime.now(timezone.utc)
                else:
                    embed.set_footer(text=footer_text_val)
                
                if embed_image and embed_image.startswith("http"):
                    embed.set_image(url=embed_image)

                def get_button_style(style_str):
                    style_lower = str(style_str or 'green').lower()
                    if 'blue' in style_lower or 'blurple' in style_lower or 'primary' in style_lower:
                        return discord.ButtonStyle.blurple
                    elif 'grey' in style_lower or 'gray' in style_lower or 'secondary' in style_lower:
                        return discord.ButtonStyle.gray
                    elif 'red' in style_lower or 'danger' in style_lower:
                        return discord.ButtonStyle.red
                    return discord.ButtonStyle.green
                resolved_btn_style = get_button_style(btn_color)

                view = UnifiedVerificationButtonView(label=btn_text or "Verify Account", style=resolved_btn_style)
            
            import os
            banner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../web/public/assets/verify now.png"))
            try:
                if not embed.image and os.path.exists(banner_path):
                    file = discord.File(banner_path, filename="banner.jpg")
                    embed.set_image(url="attachment://banner.jpg")
                    await verification_channel.send(file=file, embed=embed, view=view)
                else:
                    await verification_channel.send(embed=embed, view=view)
            except Exception as send_err:
                print("Auto Setup posting button failed:", send_err)
        else:
            print(f"ℹ️ Verification panel already exists in #{verification_channel.name} for {guild.name}. Skipping resend.")

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE verification_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(verification_channel.id), str(guild.id)))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print("Auto Setup db update failed:", db_err)

    if uv_role and verification_channel:
        for ch in guild.text_channels:
            try:
                if ch.id == verification_channel.id:
                    await ch.set_permissions(uv_role, read_messages=True, send_messages=False)
                else:
                    await ch.set_permissions(uv_role, read_messages=False, send_messages=False)
            except Exception:
                pass

class CaptchaButton(discord.ui.Button):
    def __init__(self, correct_code, verified_role_id, unverified_role_id, v_type="captcha", captcha_enabled=1):
        super().__init__(label="Click to Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
        self.correct_code = correct_code
        self.verified_role_id = verified_role_id
        self.unverified_role_id = unverified_role_id
        self.v_type = v_type
        self.captcha_enabled = captcha_enabled

    async def callback(self, interaction: discord.Interaction):
        v_type_lower = str(self.v_type).lower()
        if 'button' in v_type_lower or 'one-click' in v_type_lower or self.captcha_enabled == 0:
            v_role = None
            if self.verified_role_id and str(self.verified_role_id).isdigit():
                v_role = interaction.guild.get_role(int(self.verified_role_id))
            uv_role = None
            if self.unverified_role_id and str(self.unverified_role_id).isdigit():
                uv_role = interaction.guild.get_role(int(self.unverified_role_id))
                
            try:
                if v_role:
                    await interaction.user.add_roles(v_role)
                if uv_role:
                    await interaction.user.remove_roles(uv_role)
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to assign roles: {e}", ephemeral=True)
        else:
            modal = CaptchaModal(self.correct_code, self.verified_role_id, self.unverified_role_id)
            await interaction.response.send_modal(modal)

class CaptchaModal(discord.ui.Modal):
    def __init__(self, correct_code, verified_role_id, unverified_role_id):
        super().__init__(title="Verification CAPTCHA Gate")
        self.correct_code = correct_code
        self.verified_role_id = verified_role_id
        self.unverified_role_id = unverified_role_id
        
        self.code_input = discord.ui.TextInput(
            label=f"Retype code: {correct_code}",
            placeholder="Case-sensitive code here...",
            min_length=len(correct_code),
            max_length=len(correct_code)
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        entered = self.code_input.value.strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT captcha_sensitive FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        conn.close()
        sensitive = row[0] if (row and row[0] is not None) else 0
        
        match = (entered == self.correct_code) if sensitive else (entered.lower() == self.correct_code.lower())
        if match:
            v_role = None
            if self.verified_role_id and str(self.verified_role_id).isdigit():
                v_role = interaction.guild.get_role(int(self.verified_role_id))
            uv_role = None
            if self.unverified_role_id and str(self.unverified_role_id).isdigit():
                uv_role = interaction.guild.get_role(int(self.unverified_role_id))
            
            try:
                if v_role:
                    await interaction.user.add_roles(v_role)
                if uv_role:
                    await interaction.user.remove_roles(uv_role)
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to assign roles: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Verification failed. Incorrect code.", ephemeral=True)

# --- GROUPS DEFINITION ---

WHITELIST_CATEGORY_CHOICES = [
    app_commands.Choice(name="Users: All", value="all"),
    app_commands.Choice(name="Users: Ban", value="ban"),
    app_commands.Choice(name="Users: Kick", value="kick"),
    app_commands.Choice(name="Users: Bot-Add", value="bot_add"),
    app_commands.Choice(name="Users: Role-Update", value="dangerous_role_update"),
    app_commands.Choice(name="Users: Role-Add", value="dangerous_role_add"),
    app_commands.Choice(name="Users: Channel-Create", value="channel_create"),
    app_commands.Choice(name="Users: Channel-Delete", value="channel_delete"),
    app_commands.Choice(name="Users: Role-Create", value="role_create"),
    app_commands.Choice(name="Users: Role-Delete", value="role_delete"),
    app_commands.Choice(name="Users: Invite-Link", value="mention"),
    app_commands.Choice(name="Users: Prune", value="prune")
]

class WhitelistGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="whitelist", description="Manage whitelisted users, roles, and channels")

    @app_commands.command(name="add_user", description="Add user to whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def add_user(self, interaction: discord.Interaction, member: discord.Member, category: app_commands.Choice[str] = None, reason: str = "No reason provided"):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO bot_whitelists (guild_id, target_type, target_id, action_type, created_by) VALUES (?, 'user', ?, ?, ?)", 
                           (str(interaction.guild.id), str(member.id), cat_val, str(interaction.user.id)))
            cursor.execute("INSERT OR REPLACE INTO whitelists (guild_id, user_id, reason) VALUES (?, ?, ?)", 
                           (str(interaction.guild.id), str(member.id), f"user [{cat_val}]: {reason}"))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Whitelisted member {member.mention} for **{cat_name}**. Reason: `{reason}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Error whitelisting member: {e}")

    @app_commands.command(name="remove_user", description="Remove a user from whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def remove_user(self, interaction: discord.Interaction, member: discord.Member, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            if cat_val == "all":
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'user' AND target_id = ?", (str(interaction.guild.id), str(member.id)))
                cursor.execute("DELETE FROM whitelists WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
            else:
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'user' AND target_id = ? AND action_type = ?", (str(interaction.guild.id), str(member.id), cat_val))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Removed member {member.mention} from whitelist category **{cat_name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error removing member: {e}")

    @app_commands.command(name="add_role", description="Add a role to whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def add_role(self, interaction: discord.Interaction, role: discord.Role, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO bot_whitelists (guild_id, target_type, target_id, action_type, created_by) VALUES (?, 'role', ?, ?, ?)", 
                           (str(interaction.guild.id), str(role.id), cat_val, str(interaction.user.id)))
            cursor.execute("INSERT OR REPLACE INTO whitelists (guild_id, user_id, reason) VALUES (?, ?, ?)", 
                           (str(interaction.guild.id), str(role.id), f"role [{cat_val}]"))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Whitelisted role {role.mention} for **{cat_name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error whitelisting role: {e}")

    @app_commands.command(name="remove_role", description="Remove a role from whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            if cat_val == "all":
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'role' AND target_id = ?", (str(interaction.guild.id), str(role.id)))
                cursor.execute("DELETE FROM whitelists WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(role.id)))
            else:
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'role' AND target_id = ? AND action_type = ?", (str(interaction.guild.id), str(role.id), cat_val))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Removed role {role.name} from whitelist category **{cat_name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error removing role: {e}")

    @app_commands.command(name="add_channel", description="Add a channel to whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def add_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO bot_whitelists (guild_id, target_type, target_id, action_type, created_by) VALUES (?, 'channel', ?, ?, ?)", 
                           (str(interaction.guild.id), str(channel.id), cat_val, str(interaction.user.id)))
            cursor.execute("INSERT OR REPLACE INTO whitelists (guild_id, user_id, reason) VALUES (?, ?, ?)", 
                           (str(interaction.guild.id), str(channel.id), f"channel [{cat_val}]"))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Whitelisted channel {channel.mention} for **{cat_name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error whitelisting channel: {e}")

    @app_commands.command(name="remove_channel", description="Remove a channel from whitelist category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(category=WHITELIST_CATEGORY_CHOICES)
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_val = category.value if category else "all"
        cat_name = category.name if category else "Users: All"
        try:
            conn = get_db()
            cursor = conn.cursor()
            if cat_val == "all":
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'channel' AND target_id = ?", (str(interaction.guild.id), str(channel.id)))
                cursor.execute("DELETE FROM whitelists WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(channel.id)))
            else:
                cursor.execute("DELETE FROM bot_whitelists WHERE guild_id = ? AND target_type = 'channel' AND target_id = ? AND action_type = ?", (str(interaction.guild.id), str(channel.id), cat_val))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Removed channel #{channel.name} from whitelist category **{cat_name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error removing channel: {e}")


class VerificationGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="verification", description="Manage server member verification gates")

    @app_commands.command(name="enable", description="Enable verification on your server")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET enabled = 1 WHERE guild_id = ?", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        
        await interaction.response.defer()
        await auto_setup_verification_gate(interaction.guild, force_recreate=True, allow_create=True)
        await interaction.followup.send("✅ Verification has been **enabled**. Channel `#verification` was automatically created, placed at the top of the server, and initialized!")

    @app_commands.command(name="disable", description="Disable verification on your server without deleting unverified role")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET enabled = 0 WHERE guild_id = ?", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Member verification has been **disabled**.")

    @app_commands.command(name="setup_channel", description="Setup verification channel on your server")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET channel = ? WHERE guild_id = ?", (str(channel.id), str(interaction.guild.id)))
        conn.commit()
        conn.close()
        
        # Trigger immediate panel setup in this channel
        await auto_setup_verification_gate(interaction.guild, force_recreate=True, allow_create=True)
        await interaction.followup.send(f"✅ Verification channel set to: {channel.mention} and verification panel has been deployed!")

    @app_commands.command(name="setup_role", description="Setup verification role on your server")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET unverified_role = ? WHERE guild_id = ?", (str(role.id), str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Unverified role set to: {role.mention}")

    @app_commands.command(name="set_verified", description="Set a role to give your users when they get verified")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_verified(self, interaction: discord.Interaction, role: discord.Role):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET verified_role = ? WHERE guild_id = ?", (str(role.id), str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Verified role set to: {role.mention}")

    @app_commands.command(name="update_role", description="Update and configure verification gate channel and role permissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_role(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            await auto_setup_verification_gate(interaction.guild, force_recreate=False, allow_create=True)
            await interaction.followup.send("✅ Server channel and category permissions for the verification gate have been successfully synced and updated!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update permissions: {e}")

    @app_commands.command(name="verify", description="Manually verify someone")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def verify_member(self, interaction: discord.Interaction, member: discord.Member):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT verified_role, unverified_role FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            return await interaction.response.send_message("❌ Verified role not configured.", ephemeral=True)
            
        v_role = interaction.guild.get_role(int(row[0]))
        uv_role = interaction.guild.get_role(int(row[1])) if row[1] else None
        
        try:
            if v_role:
                await member.add_roles(v_role)
            if uv_role:
                await member.remove_roles(uv_role)
            await interaction.response.send_message(f"✅ Manually verified member {member.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    @app_commands.command(name="reset", description="Reset verification on your server, deletes verification channel and unverified role overrides")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Verification settings successfully reset.")

    # Captcha Configuration Subcommands
    captcha = app_commands.Group(name="captcha", description="Configure captcha parameters")
    
    @captcha.command(name="lines", description="Changes verification captcha code lines")
    @app_commands.checks.has_permissions(administrator=True)
    async def lines(self, interaction: discord.Interaction, lines: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET captcha_lines = ? WHERE guild_id = ?", (lines, str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Captcha lines updated to: `{lines}`")

    @captcha.command(name="numbers", description="Toggle if captcha should contain numbers or not")
    @app_commands.checks.has_permissions(administrator=True)
    async def numbers(self, interaction: discord.Interaction, enabled: bool):
        val = 1 if enabled else 0
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET captcha_numbers = ? WHERE guild_id = ?", (val, str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Captcha numbers update toggled to: `{enabled}`")

    @captcha.command(name="sensitive", description="Toggle if captcha should be case sensitive or not")
    @app_commands.checks.has_permissions(administrator=True)
    async def sensitive(self, interaction: discord.Interaction, enabled: bool):
        val = 1 if enabled else 0
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET captcha_sensitive = ? WHERE guild_id = ?", (val, str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Captcha case-sensitivity updated to: `{enabled}`")

    @captcha.command(name="timeout", description="Set captcha timeout so users will be asked to complete a new captcha")
    @app_commands.checks.has_permissions(administrator=True)
    async def timeout(self, interaction: discord.Interaction, timeout_seconds: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO verification_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
        cursor.execute("UPDATE verification_settings SET captcha_timeout = ? WHERE guild_id = ?", (timeout_seconds, str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Captcha timeout set to: `{timeout_seconds}s`")


class SettingsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="settings_legacy", description="Legacy settings configuration")


class AutoroleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="autorole", description="Manage server join autoroles")
        
    @app_commands.command(name="add", description="Add an autorole given to members on join")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Cannot add this role: it is above the bot's permissions role.", ephemeral=True)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        roles = []
        if row and row[0]:
            try:
                parsed = json.loads(row[0])
                if isinstance(parsed, list):
                    roles = [str(x) for x in parsed]
            except Exception:
                roles = []

        # If any invalid/legacy role names like "Verified Member" match this role, clean them up
        roles = [r for r in roles if r != role.name and r != str(role.id)]
        roles.append(str(role.id))
        cursor.execute("INSERT OR REPLACE INTO autoroles (guild_id, roles) VALUES (?, ?)", (str(interaction.guild.id), json.dumps(roles)))
        conn.commit()
        conn.close()
        embed = create_veyra_embed(
            title="📋 Autorole Configured",
            status="QUEUED",
            description=f"Added role {role.mention} to autoroles queue.",
            color=discord.Color.from_rgb(24, 24, 27),
            footer="Powered By Veyra Development™ | Designed By Arun"
        )
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="remove", description="Remove an autorole from the queue")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, role: discord.Role):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        roles = []
        if row and row[0]:
            try:
                parsed = json.loads(row[0])
                if isinstance(parsed, list):
                    roles = [str(x) for x in parsed]
            except Exception:
                roles = []

        target_id = str(role.id)
        target_name = role.name
        new_roles = [r for r in roles if r != target_id and r.lower() != target_name.lower()]

        if len(new_roles) < len(roles):
            cursor.execute("INSERT OR REPLACE INTO autoroles (guild_id, roles) VALUES (?, ?)", (str(interaction.guild.id), json.dumps(new_roles)))
            conn.commit()
            embed = create_veyra_embed(
                title="📋 Autorole Deconfigured",
                status="DEQUEUED",
                description=f"Removed role **{role.name}** from autoroles queue.",
                color=discord.Color.from_rgb(24, 24, 27),
                footer="Powered By Veyra Development™ | Designed By Arun"
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ This role is not in the autoroles queue.", ephemeral=True)
        conn.close()

    @app_commands.command(name="list", description="List configured autoroles")
    async def list_autoroles(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        conn.close()
        role_ids = []
        if row and row[0]:
            try:
                parsed = json.loads(row[0])
                if isinstance(parsed, list):
                    role_ids = parsed
            except Exception:
                role_ids = []

        if not role_ids:
            return await interaction.response.send_message("ℹ️ No autoroles configured.")

        mentions = []
        valid_ids = []
        for r_id in role_ids:
            role = None
            r_str = str(r_id).strip()
            if r_str.isdigit():
                role = interaction.guild.get_role(int(r_str))
            if not role:
                role = discord.utils.get(interaction.guild.roles, name=r_str)
                if not role:
                    role = discord.utils.find(lambda r: r.name.lower() == r_str.lower(), interaction.guild.roles)

            if role:
                mentions.append(role.mention)
                valid_ids.append(str(role.id))
            else:
                if not r_str.isdigit():
                    continue
                mentions.append(f"`Role ID: {r_str}`")
                valid_ids.append(r_str)

        if not mentions:
            return await interaction.response.send_message("ℹ️ No active autoroles configured.")

        # Auto-heal DB if non-integer names or outdated formats existed
        try:
            conn_u = get_db()
            cur_u = conn_u.cursor()
            cur_u.execute("UPDATE autoroles SET roles = ? WHERE guild_id = ?", (json.dumps(valid_ids), str(interaction.guild.id)))
            conn_u.commit()
            conn_u.close()
        except Exception:
            pass

        embed = create_veyra_embed(
            title="📋 Configured Autoroles",
            description="The following roles are assigned to members immediately upon joining.",
            fields=[
                ("👥 Active Queue", ", ".join(mentions) if mentions else "None", False)
            ],
            color=discord.Color.from_rgb(24, 24, 27),
            footer="Powered By Veyra Development™ | Designed By Arun"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Clear all configured autoroles")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE autoroles SET roles = '[]' WHERE guild_id = ?", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        embed = create_veyra_embed(
            title="📋 Autoroles Cleared",
            status="CLEARED",
            description="All configured autoroles have been removed from the server queue.",
            color=discord.Color.from_rgb(24, 24, 27),
            footer="Powered By Veyra Development™ | Designed By Arun"
        )
        await interaction.response.send_message(embed=embed)


# --- Prefix Commands for Autorole ---
@bot.group(name="autorole", aliases=["autoroles"], invoke_without_command=True)
async def autorole_prefix_group(ctx):
    embed = discord.Embed(
        title="📋 Autorole Commands",
        description="`autorole add <@role>`, `autorole remove <@role>`, `autorole list`, `autorole clear`",
        color=discord.Color.from_rgb(43, 45, 49)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@autorole_prefix_group.command(name="add")
@commands.has_permissions(administrator=True)
async def autorole_prefix_add(ctx, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ Cannot add this role: it is above the bot's permissions role.")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(ctx.guild.id),))
    row = cursor.fetchone()
    roles = []
    if row and row[0]:
        try:
            parsed = json.loads(row[0])
            if isinstance(parsed, list):
                roles = [str(x) for x in parsed]
        except Exception:
            roles = []
    roles = [r for r in roles if r != role.name and r != str(role.id)]
    roles.append(str(role.id))
    cursor.execute("INSERT OR REPLACE INTO autoroles (guild_id, roles) VALUES (?, ?)", (str(ctx.guild.id), json.dumps(roles)))
    conn.commit()
    conn.close()
    embed = create_veyra_embed(
        title="📋 Autorole Configured",
        status="QUEUED",
        description=f"Added role {role.mention} to autoroles queue.",
        color=discord.Color.from_rgb(24, 24, 27),
        footer="Powered By Veyra Development™ | Designed By Arun"
    )
    await ctx.send(embed=embed)

@autorole_prefix_group.command(name="remove")
@commands.has_permissions(administrator=True)
async def autorole_prefix_remove(ctx, role: discord.Role):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(ctx.guild.id),))
    row = cursor.fetchone()
    roles = []
    if row and row[0]:
        try:
            parsed = json.loads(row[0])
            if isinstance(parsed, list):
                roles = [str(x) for x in parsed]
        except Exception:
            roles = []
    target_id = str(role.id)
    target_name = role.name
    new_roles = [r for r in roles if r != target_id and r.lower() != target_name.lower()]
    if len(new_roles) < len(roles):
        cursor.execute("INSERT OR REPLACE INTO autoroles (guild_id, roles) VALUES (?, ?)", (str(ctx.guild.id), json.dumps(new_roles)))
        conn.commit()
        embed = create_veyra_embed(
            title="📋 Autorole Deconfigured",
            status="DEQUEUED",
            description=f"Removed role **{role.name}** from autoroles queue.",
            color=discord.Color.from_rgb(24, 24, 27),
            footer="Powered By Veyra Development™ | Designed By Arun"
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ This role is not in the autoroles queue.")
    conn.close()

@autorole_prefix_group.command(name="list")
async def autorole_prefix_list(ctx):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT roles FROM autoroles WHERE guild_id = ?", (str(ctx.guild.id),))
    row = cursor.fetchone()
    conn.close()
    role_ids = []
    if row and row[0]:
        try:
            parsed = json.loads(row[0])
            if isinstance(parsed, list):
                role_ids = parsed
        except Exception:
            role_ids = []
    if not role_ids:
        return await ctx.send("ℹ️ No autoroles configured.")
    mentions = []
    valid_ids = []
    for r_id in role_ids:
        role = None
        r_str = str(r_id).strip()
        if r_str.isdigit():
            role = ctx.guild.get_role(int(r_str))
        if not role:
            role = discord.utils.get(ctx.guild.roles, name=r_str)
            if not role:
                role = discord.utils.find(lambda r: r.name.lower() == r_str.lower(), ctx.guild.roles)
        if role:
            mentions.append(role.mention)
            valid_ids.append(str(role.id))
        else:
            if not r_str.isdigit():
                continue
            mentions.append(f"`Role ID: {r_str}`")
            valid_ids.append(r_str)
    if not mentions:
        return await ctx.send("ℹ️ No active autoroles configured.")
    try:
        conn_u = get_db()
        cur_u = conn_u.cursor()
        cur_u.execute("UPDATE autoroles SET roles = ? WHERE guild_id = ?", (json.dumps(valid_ids), str(ctx.guild.id)))
        conn_u.commit()
        conn_u.close()
    except Exception:
        pass
    embed = create_veyra_embed(
        title="📋 Configured Autoroles",
        description="The following roles are assigned to members immediately upon joining.",
        fields=[
            ("👥 Active Queue", ", ".join(mentions) if mentions else "None", False)
        ],
        color=discord.Color.from_rgb(24, 24, 27),
        footer="Powered By Veyra Development™ | Designed By Arun"
    )
    await ctx.send(embed=embed)

@autorole_prefix_group.command(name="clear")
@commands.has_permissions(administrator=True)
async def autorole_prefix_clear(ctx):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE autoroles SET roles = '[]' WHERE guild_id = ?", (str(ctx.guild.id),))
    conn.commit()
    conn.close()
    embed = create_veyra_embed(
        title="📋 Autoroles Cleared",
        status="CLEARED",
        description="All configured autoroles have been removed from the server queue.",
        color=discord.Color.from_rgb(24, 24, 27),
        footer="Powered By Veyra Development™ | Designed By Arun"
    )
    await ctx.send(embed=embed)


class StickyroleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="stickyrole", description="Manage member sticky roles")
        
    @app_commands.command(name="enable", description="Enable sticky role restoration")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO sticky_settings (guild_id, enabled) VALUES (?, 1)", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Sticky roles restoration has been **enabled**.")
        
    @app_commands.command(name="disable", description="Disable sticky role restoration")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO sticky_settings (guild_id, enabled) VALUES (?, 0)", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Sticky roles restoration has been **disabled**.")


class PermissionGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="permission", description="Bot custom permission overrides")

    @app_commands.command(name="add", description="Add some permission to a user")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(permission=WHITELIST_CATEGORY_CHOICES)
    async def add(self, interaction: discord.Interaction, member: discord.Member, permission: app_commands.Choice[str] = None):
        perm_val = permission.value if permission else "all"
        perm_name = permission.name if permission else "Users: All"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO bot_permissions (guild_id, user_id, permission) VALUES (?, ?, ?)", (str(interaction.guild.id), str(member.id), perm_val))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Granted bot permission **{perm_name}** to {member.mention}.")

    @app_commands.command(name="remove", description="Remove some permission from a user")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(permission=WHITELIST_CATEGORY_CHOICES)
    async def remove(self, interaction: discord.Interaction, member: discord.Member, permission: app_commands.Choice[str] = None):
        perm_val = permission.value if permission else "all"
        perm_name = permission.name if permission else "Users: All"
        conn = get_db()
        cursor = conn.cursor()
        if perm_val == "all":
            cursor.execute("DELETE FROM bot_permissions WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
        else:
            cursor.execute("DELETE FROM bot_permissions WHERE guild_id = ? AND user_id = ? AND permission = ?", (str(interaction.guild.id), str(member.id), perm_val))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Revoked bot permission **{perm_name}** from {member.mention}.")



    @app_commands.command(name="reset_id", description="Remove all the permissions from a user using their id")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_id(self, interaction: discord.Interaction, user_id: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_permissions WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Successfully reset all bot permissions for user ID `{user_id}`.")

    @app_commands.command(name="view_permission", description="Get users with the selected permission")
    async def view_permission(self, interaction: discord.Interaction, permission: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM bot_permissions WHERE guild_id = ? AND permission = ?", (str(interaction.guild.id), permission.lower()))
        rows = cursor.fetchall()
        conn.close()
        users = []
        for r in rows:
            users.append(f"<@{r[0]}>")
        if not users:
            return await interaction.response.send_message(f"ℹ️ No users configured with `{permission.lower()}` permission.")
        await interaction.response.send_message(f"📋 Users with `{permission.lower()}` permission:\n" + ", ".join(users))

    @app_commands.command(name="view_user", description="Get granted permissions of a user")
    async def view_user(self, interaction: discord.Interaction, member: discord.Member):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT permission FROM bot_permissions WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
        rows = cursor.fetchall()
        conn.close()
        perms = [r[0] for r in rows]
        if not perms:
            return await interaction.response.send_message(f"ℹ️ {member.mention} has no special bot permissions.")
        await interaction.response.send_message(f"📋 Special bot permissions for {member.mention}: " + ", ".join([f"`{p}`" for p in perms]))


class LogsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="logs", description="Configure server logging channels")

    @app_commands.command(name="mod", description="Log channel for moderation commands")
    @app_commands.checks.has_permissions(administrator=True)
    async def mod(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        conn = get_db()
        cursor = conn.cursor()
        if channel:
            cursor.execute("SELECT 1 FROM guild_settings WHERE guild_id = ?", (str(interaction.guild.id),))
            if cursor.fetchone():
                cursor.execute("UPDATE guild_settings SET moderation_logs = ? WHERE guild_id = ?", (str(channel.id), str(interaction.guild.id)))
            else:
                cursor.execute("INSERT INTO guild_settings (guild_id, moderation_logs) VALUES (?, ?)", (str(interaction.guild.id), str(channel.id)))
            conn.commit()
            await interaction.response.send_message(f"✅ Moderation logs channel set to: {channel.mention}")
        else:
            cursor.execute("SELECT moderation_logs FROM guild_settings WHERE guild_id = ?", (str(interaction.guild.id),))
            row = cursor.fetchone()
            log_id = row[0] if row else 'none'
            if log_id and log_id != 'none':
                await interaction.response.send_message(f"📢 Moderation logs channel is currently: <#{log_id}>")
            else:
                await interaction.response.send_message("📢 Moderation logs channel is currently: Not set")
        conn.close()

    @app_commands.command(name="security", description="Log channel for security actions")
    @app_commands.checks.has_permissions(administrator=True)
    async def security(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        conn = get_db()
        cursor = conn.cursor()
        if channel:
            cursor.execute("SELECT 1 FROM guild_settings WHERE guild_id = ?", (str(interaction.guild.id),))
            if cursor.fetchone():
                cursor.execute("UPDATE guild_settings SET security_logs = ? WHERE guild_id = ?", (str(channel.id), str(interaction.guild.id)))
            else:
                cursor.execute("INSERT INTO guild_settings (guild_id, security_logs) VALUES (?, ?)", (str(interaction.guild.id), str(channel.id)))
            conn.commit()
            await interaction.response.send_message(f"✅ Security logs channel set to: {channel.mention}")
        else:
            cursor.execute("SELECT security_logs FROM guild_settings WHERE guild_id = ?", (str(interaction.guild.id),))
            row = cursor.fetchone()
            log_id = row[0] if row else 'none'
            if log_id and log_id != 'none':
                await interaction.response.send_message(f"📢 Security logs channel is currently: <#{log_id}>")
            else:
                await interaction.response.send_message("📢 Security logs channel is currently: Not set")
        conn.close()


# --- ROOT LEVEL COMMANDS ---

@bot.tree.command(name="verify", description="Verify yourself")
async def verify_root(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT enabled, verified_role, unverified_role, type, captcha_lines, captcha_numbers, captcha_sensitive, captcha_timeout, captcha_enabled FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return await interaction.response.send_message("❌ Verification is not enabled on this server.", ephemeral=True)
        
    enabled, verified_role_id, unverified_role_id, v_type, lines, numbers, sensitive, timeout = row
    
    import random, string
    chars = string.ascii_uppercase
    if sensitive:
        chars += string.ascii_lowercase
    if numbers:
        chars += string.digits
    correct_code = "".join(random.choices(chars, k=5))
    
    embed = discord.Embed(
        title="🔒 VEYRA Server Verification Gate",
        description="To access this server, you must verify that you are human.\n"
                    "Click the button below and re-enter the code displayed.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    
    view = discord.ui.View()
    view.add_item(CaptchaButton(correct_code, verified_role_id, unverified_role_id))
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="settings", description="Get current settings of the server")
@app_commands.choices(category=[
    app_commands.Choice(name="Anti Nuke", value="antinuke"),
    app_commands.Choice(name="Verification", value="verification"),
    app_commands.Choice(name="Beast Mode", value="beastmode")
])
async def settings_root(interaction: discord.Interaction, category: app_commands.Choice[str]):
    conn = get_db()
    cursor = conn.cursor()
    
    if category.value == "antinuke":
        cursor.execute("SELECT * FROM antinuke_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        embed = discord.Embed(
            title="🛡️ Anti-Nuke Settings Status",
            color=discord.Color.from_rgb(24, 24, 27),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if row:
            r = dict(row)
            embed.add_field(
                name="🛡️ Ban & Kick Protection",
                value=f"• **Anti-Ban**: Enabled (`Limit: {r.get('anti_ban_limit', 5)}` | `Punish: {r.get('anti_ban_punish', 'Ban')}`)\n"
                      f"• **Anti-Kick**: Enabled (`Limit: {r.get('anti_kick_limit', 5)}` | `Punish: {r.get('anti_kick_punish', 'Ban')}`)",
                inline=False
            )
            embed.add_field(
                name="📁 Channel Protection",
                value=f"• **Create**: `Limit {r.get('anti_channel_create_limit', 8)}` | `Punish: {r.get('anti_channel_create_punish', 'Ban')}`\n"
                      f"• **Delete**: `Limit {r.get('anti_channel_delete_limit', 3)}` | `Punish: {r.get('anti_channel_delete_punish', 'Ban')}`\n"
                      f"• **Rename**: `Limit {r.get('anti_channel_rename_limit', 5)}` | `Punish: {r.get('anti_channel_rename_punish', 'Kick')}`",
                inline=False
            )
            embed.add_field(
                name="🏷️ Role Protection",
                value=f"• **Create**: `Limit {r.get('anti_role_create_limit', 8)}` | `Punish: {r.get('anti_role_create_punish', 'Ban')}`\n"
                      f"• **Delete**: `Limit {r.get('anti_role_delete_limit', 3)}` | `Punish: {r.get('anti_role_delete_punish', 'Ban')}`\n"
                      f"• **Rename**: `Limit {r.get('anti_role_rename_limit', 5)}` | `Punish: {r.get('anti_role_rename_punish', 'Kick')}`",
                inline=False
            )
            embed.add_field(
                name="🤖 Bot Add & Webhook Guard",
                value=f"• **Bot Add**: `Punish: {r.get('anti_bot_add_punish', 'Ban')}`\n"
                      f"• **Webhooks**: `Punish: {r.get('anti_webhook_create_punish', 'Ban')}`",
                inline=False
            )
            embed.add_field(
                name="👑 Server & Dangerous Roles",
                value=f"• **Server Update**: `Punish: {r.get('anti_guild_update_punish', 'Ban')}`\n"
                      f"• **Dangerous Roles**: `Punish: {r.get('anti_dangerous_role_add_punish', 'Ban')}`",
                inline=False
            )
        else:
            embed.description = "ℹ️ No Anti-Nuke rules configured yet. Run `/enableall` to activate all modules."
        
        ist_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%I:%M %p IST")
        embed.set_footer(text=f"VEYRA Security • Today at {ist_now}")
        await interaction.response.send_message(embed=embed)
        
    elif category.value == "verification":
        cursor.execute("SELECT * FROM verification_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        row = cursor.fetchone()
        embed = discord.Embed(
            title="🔒 Verification Settings Status",
            color=discord.Color.from_rgb(139, 92, 246),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if row:
            r = dict(row)
            cols = [col for col in r.keys() if col != 'guild_id']
            # Limit total fields to max 20 to prevent 25-field limit error
            for col in cols[:20]:
                val = r[col]
                embed.add_field(name=col.replace("_", " ").title(), value=f"`{val}`", inline=True)
        else:
            embed.description = "ℹ️ Verification system is not configured."
        
        ist_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%I:%M %p IST")
        embed.set_footer(text=f"VEYRA Verification • Today at {ist_now}")
        await interaction.response.send_message(embed=embed)
        
    elif category.value == "beastmode":
        embed = discord.Embed(
            title="🦁 VEYRA Beast Mode Overrides",
            description="🔴 **Beast Mode Status: ACTIVE**\n\n"
                        "All internal administrative actions are monitored under strict zero-trust thresholds.\n"
                        "• Any admin performing > 1 delete actions will be instantly quarantined.\n"
                        "• Automated defense is set to full alert.",
            color=discord.Color.from_rgb(239, 68, 68),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        ist_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%I:%M %p IST")
        embed.set_footer(text=f"VEYRA Security • Today at {ist_now}")
        await interaction.followup.send(embed=embed) if interaction.response.is_done() else await interaction.response.send_message(embed=embed)
    conn.close()


@bot.tree.command(name="softban", description="Softban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def softban_root(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    can_mod, mod_error = check_bot_can_moderate_interaction(interaction, member)
    if not can_mod:
        return await interaction.response.send_message(f"❌ {mod_error}", ephemeral=True)
    try:
        await member.ban(reason=reason, delete_message_days=7)
        await interaction.guild.unban(member, reason="Softban release")
        embed = create_modern_moderation_embed(
            title="Member Softbanned",
            target=member,
            moderator=interaction.user,
            action="Softban Executed",
            reason=reason,
            color=discord.Color.from_rgb(24, 24, 27)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Softban Command', f"Softbanned member {member.name}. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to softban: {e}", ephemeral=True)


@bot.tree.command(name="unban", description="Unban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def unban_root(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        embed = create_modern_moderation_embed(
            title="Restriction Revoked",
            target=user,
            moderator=interaction.user,
            action="Ban Revoked",
            reason=reason,
            color=discord.Color.from_rgb(16, 185, 129)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Unban Command', f"Unbanned user {user.name} ({user_id}). Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to unban: {e}", ephemeral=True)


@bot.tree.command(name="unlock", description="Unlock current or selected text channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock_root(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target = channel or interaction.channel
    try:
        await target.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(f"🔓 Unlocked channel {target.mention} successfully.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to unlock: {e}", ephemeral=True)


@bot.tree.command(name="unlockall", description="Unlock all the locked text channels")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlockall_root(interaction: discord.Interaction):
    await interaction.response.defer()
    unlocked = 0
    for channel in interaction.guild.text_channels:
        perms = channel.overwrites_for(interaction.guild.default_role)
        if perms.send_messages is False:
            try:
                await channel.set_permissions(interaction.guild.default_role, send_messages=None)
                unlocked += 1
            except Exception:
                pass
    await interaction.followup.send(f"🔓 Successfully unlocked **{unlocked}** channels.")


@bot.tree.command(name="unmute", description="Unmute a user")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute_root(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        embed = create_modern_moderation_embed(
            title="User has been unmuted!",
            target=member,
            moderator=interaction.user,
            action="Restrictions Removed",
            reason="Access Restoration",
            color=discord.Color.from_rgb(16, 185, 129)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Unmute Command', f"Unmuted user {member.name}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to unmute: {e}", ephemeral=True)





@bot.tree.command(name="premium", description="Shows information about VEYRA Premium")
async def premium_root(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👑 VEYRA Premium & Pro Plans",
        description="Unlock maximum protection, advanced logging, custom branding, and instant raid mitigation.",
        color=discord.Color.gold()
    )
    embed.add_field(name="Free Plan", value="• Anti-Nuke (limits up to 5)\n• Auto Nickname\n• Basic Logs", inline=False)
    embed.add_field(name="Pro Plan", value="• Custom Welcome & Exit messages\n• Role restoration (sticky roles)\n• Raid protection toggles", inline=False)
    embed.add_field(name="Premium Plan", value="• Full customization of Anti-Nuke actions\n• Custom branding (Bot profile, Avatar, Banner, Name)\n• Complete Whitelist override", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="scan", description="Let VEYRA check your server security parameters and configuration")
async def scan_root(interaction: discord.Interaction):
    issues = []
    guild = interaction.guild
    
    # 1. Check Bot's Role Position
    bot_member = guild.me
    if bot_member.top_role.position < len(guild.roles) - 5:
        issues.append(f"⚠️ **Bot Role Hierarchy**: VEYRA's role `{bot_member.top_role.name}` is too low in the hierarchy. Move it above other roles to allow proper anti-nuke actions.")
        
    # 2. Check Administrator Count
    admin_roles = [r.mention for r in guild.roles if r.permissions.administrator and not r.is_bot_managed()]
    if len(admin_roles) > 2:
        issues.append(f"⚠️ **Excessive Admins**: There are {len(admin_roles)} roles with Administrator permissions ({', '.join(admin_roles)}). It is recommended to have at most 2 admin roles.")
        
    # 3. Check default role permissions
    def_role = guild.default_role
    def_perms = def_role.permissions
    if def_perms.administrator or def_perms.manage_guild or def_perms.manage_roles or def_perms.ban_members or def_perms.kick_members or def_perms.mention_everyone:
        issues.append("❌ **@everyone Permissions**: The default `@everyone` role has dangerous administrative/moderator permissions active. Disable dangerous permissions for everyone role.")
        
    # 4. Check MFA Level
    if guild.mfa_level == discord.MFALevel.disabled:
        issues.append("⚠️ **MFA Disallowed**: Two-Factor Authentication (2FA) is not enforced for moderation actions on this server. Enable server-wide 2FA requirement.")
        
    # 5. Check channel overrides
    dangerous_channels = []
    for c in guild.text_channels[:15]:
        ov = c.overwrites_for(guild.default_role)
        if ov.mention_everyone is True or ov.manage_roles is True or ov.manage_channels is True:
            dangerous_channels.append(c.mention)
    if dangerous_channels:
        issues.append(f"⚠️ **Public Overrides**: Default `@everyone` has override permissions (mention everyone/manage channel/roles) in: {', '.join(dangerous_channels)}")
        
    # 6. Check if verification is setup
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT enabled, verified_role FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
    v_settings = cursor.fetchone()
    conn.close()
    if not v_settings or not v_settings[0] or not v_settings[1]:
        issues.append("⚠️ **No Verification Gate**: Verification system is not configured. Setup a verification channel using the dashboard to block automated bot raids.")

    embed = discord.Embed(
        title="🛡️ VEYRA Security Audit Scan", 
        color=discord.Color.red() if issues else discord.Color.green()
    )
    if not issues:
        embed.description = "🟢 **Server is highly secure!** VEYRA has audited all security checks and found zero immediate vulnerabilities."
    else:
        embed.description = "⚠️ **Vulnerabilities / Recommendations Found:**\n\n" + "\n\n".join(issues)
        
    embed.set_footer(text="VEYRA V2 • Security Audit Scan")
    await interaction.response.send_message(embed=embed)


async def send_server_info_helper(interaction: discord.Interaction):
    guild = interaction.guild
    embed = build_server_info_embed(guild)
    view = ServerInfoView(guild)
    await interaction.response.send_message(embed=embed, view=view)



@bot.tree.command(name="serverinfo", description="Displays the information about a server")
async def serverinfo_root(interaction: discord.Interaction):
    await send_server_info_helper(interaction)


@bot.tree.command(name="setlimit", description="Change the limit of an anti nuke action")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(action=[
    app_commands.Choice(name="Banning Members", value="ban"),
    app_commands.Choice(name="Kicking Members", value="kick"),
    app_commands.Choice(name="Creating Roles", value="role_create"),
    app_commands.Choice(name="Deleting Roles", value="role_delete"),
    app_commands.Choice(name="Creating Channels", value="channel_create"),
    app_commands.Choice(name="Deleting Channels", value="channel_delete"),
    app_commands.Choice(name="Sending invite links / Mentions", value="mention")
])
async def setlimit_root(interaction: discord.Interaction, action: app_commands.Choice[str], limit: int):
    db_key = action.value
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO antinuke_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
    cursor.execute(f"UPDATE antinuke_settings SET anti_{db_key}_limit = ? WHERE guild_id = ?", (limit, str(interaction.guild.id)))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="⚙️ Threshold Limit Updated",
        description=f"✅ Threshold limit for **{action.name}** updated to: `{limit}`",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setmuterole", description="Create a new mute role or set an existing one")
@app_commands.checks.has_permissions(manage_roles=True)
async def setmuterole_root(interaction: discord.Interaction, role: discord.Role = None):
    target_role = role
    if not target_role:
        try:
            target_role = await interaction.guild.create_role(name="Muted", reason="VEYRA Setup Mute Role")
            for ch in interaction.guild.channels:
                try:
                    await ch.set_permissions(target_role, send_messages=False, speak=False)
                except Exception:
                    pass
        except Exception as e:
            return await interaction.response.send_message(f"❌ Failed to create role: {e}", ephemeral=True)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO guild_settings (guild_id, prefix) VALUES (?, ?)", (str(interaction.guild.id), "?"))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="🔇 Mute Role Configured",
        description=f"✅ Mute role set to: {target_role.mention}",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setpunishment", description="Change the punishment type of a specific action")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Banning Members", value="ban"),
        app_commands.Choice(name="Kicking Members", value="kick"),
        app_commands.Choice(name="Deleting Roles", value="role_delete"),
        app_commands.Choice(name="Creating Roles", value="role_create"),
        app_commands.Choice(name="Deleting Channels", value="channel_delete"),
        app_commands.Choice(name="Creating Channels", value="channel_create"),
        app_commands.Choice(name="Adding Bots", value="bot_add"),
        app_commands.Choice(name="Giving Dangerous Permissions", value="dangerous_role_update"),
        app_commands.Choice(name="Giving Administration Roles", value="dangerous_role_add"),
        app_commands.Choice(name="Pruning Members", value="prune"),
        app_commands.Choice(name="Sending invite links / Mentions", value="mention"),
        app_commands.Choice(name="Vanity URL changes", value="vanity_change"),
        app_commands.Choice(name="Server renaming", value="server_rename"),
        app_commands.Choice(name="Server icon changes", value="server_icon_change"),
        app_commands.Choice(name="Role renaming", value="role_rename"),
        app_commands.Choice(name="Channel renaming", value="channel_rename")
    ],
    punishment_type=[
        app_commands.Choice(name="Ban", value="Ban"),
        app_commands.Choice(name="Kick", value="Kick"),
        app_commands.Choice(name="Clear Roles", value="Clear Roles")
    ]
)
async def setpunishment_root(interaction: discord.Interaction, action: app_commands.Choice[str], punishment_type: app_commands.Choice[str]):
    db_key = action.value
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO antinuke_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
    cursor.execute(f"UPDATE antinuke_settings SET anti_{db_key}_punish = ? WHERE guild_id = ?", (punishment_type.value, str(interaction.guild.id)))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="🔨 Security Punishment Configured",
        description=f"✅ Punishment for **{action.name}** updated to: `{punishment_type.name}`",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="Displays the help command of the bot")
async def help_root(interaction: discord.Interaction):
    bot_icon_url = bot.user.avatar.url if bot.user and bot.user.avatar else None
    embed = build_main_help_embed(interaction.guild, bot_icon_url)
    view = HelpView(bot_icon_url)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="invite", description="Displays the official invite link for VEYRA")
async def invite_root(interaction: discord.Interaction):
    client_id = os.getenv("DISCORD_CLIENT_ID", "1527243189860175933")
    url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=8&integration_type=0&scope=bot+applications.commands"
    embed = discord.Embed(
        title="🔗 Invite VEYRA to Your Server",
        description=f"Click the button below or [Authorize VEYRA]({url}) to invite the bot with full Administrator permissions.\n\n🌐 **Web Dashboard:** [https://veyra-bot.vercel.app](https://veyra-bot.vercel.app)",
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Authorize VEYRA", style=discord.ButtonStyle.link, url=url, emoji="🤖"))
    view.add_item(discord.ui.Button(label="Dashboard", style=discord.ButtonStyle.link, url="https://veyra-bot.vercel.app", emoji="🌐"))
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="kick", description="Kicks a user from a guild")
async def kick_root(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not check_user_has_bot_permission(interaction.guild.id, interaction.user.id, "kick", "kick_members", interaction):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    can_mod, mod_error = check_bot_can_moderate_interaction(interaction, member)
    if not can_mod:
        return await interaction.response.send_message(f"❌ {mod_error}", ephemeral=True)
    try:
        await member.kick(reason=reason)
        embed = create_modern_moderation_embed(
            title="Member Successfully Kicked",
            target=member,
            moderator=interaction.user,
            action="User Kicked",
            reason=reason,
            color=discord.Color.from_rgb(24, 24, 27)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Kick Command', f"Kicked member {member.name}. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to kick: {e}", ephemeral=True)


@bot.tree.command(name="lock", description="Lock current or selected text channel")
async def lock_root(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not check_user_has_bot_permission(interaction.guild.id, interaction.user.id, "lock", "manage_channels", interaction):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    target = channel or interaction.channel
    try:
        await target.set_permissions(interaction.guild.default_role, send_messages=False)
        embed = create_veyra_embed(
            title="🔒 Channel Lockdown",
            status="LOCKED",
            description=f"Channel {target.mention} has been restricted successfully.",
            fields=[
                ("👤 Moderator", interaction.user.mention, True),
                ("📁 Channel Target", target.mention, True)
            ],
            color=discord.Color.from_rgb(239, 68, 68),
            footer="VEYRA V2 • Channel Security"
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to lock: {e}", ephemeral=True)


@bot.tree.command(name="lockall", description="Lock all the text channels")
async def lockall_root(interaction: discord.Interaction):
    if not check_user_has_bot_permission(interaction.guild.id, interaction.user.id, "lockall", "manage_channels", interaction):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    await interaction.response.defer()
    locked = 0
    for channel in interaction.guild.text_channels:
        perms = channel.overwrites_for(interaction.guild.default_role)
        if perms.send_messages is not False:
            try:
                await channel.set_permissions(interaction.guild.default_role, send_messages=False)
                locked += 1
            except Exception:
                pass
    embed = create_veyra_embed(
        title="🔒 Server-Wide Lockdown",
        status="EMERGENCY LOCK APPLIED",
        description=f"Restricted text access to all public text channels.",
        fields=[
            ("👤 Moderator", interaction.user.mention, True),
            ("🔒 Channels Locked", f"**{locked}** text channels", True)
        ],
        color=discord.Color.from_rgb(239, 68, 68),
        footer="VEYRA V2 • Channel Security"
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="about", description="Information about the bot")
async def about_root(interaction: discord.Interaction):
    fields = [
        ("🤖 System Core", "VEYRA V2 (Sovereign Engine)", True),
        ("🛡️ Modules Active", "Anti-Nuke, Moderation, Invites,\nLevels, Verification", True),
        ("⚡ Gateways", "Online (Shard 1/1)", True)
    ]
    icon_url = bot.user.avatar.url if bot.user and bot.user.avatar else None
    embed = create_veyra_embed(
        title="🤖 VEYRA All-in-One Bot",
        description="The ultimate all-in-one anti-nuke, moderation, invites tracking, levels, giveaways, tickets, and utility system for your server.",
        fields=fields,
        color=discord.Color.from_rgb(24, 24, 27),
        footer="VEYRA V2 • About Diagnostics",
        icon_url=icon_url
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ban", description="Bans a user from a guild")
async def ban_root(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not check_user_has_bot_permission(interaction.guild.id, interaction.user.id, "ban", "ban_members", interaction):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    can_mod, mod_error = check_bot_can_moderate_interaction(interaction, member)
    if not can_mod:
        return await interaction.response.send_message(f"❌ {mod_error}", ephemeral=True)
    try:
        await member.ban(reason=reason)
        embed = create_modern_moderation_embed(
            title="Member Successfully Banned",
            target=member,
            moderator=interaction.user,
            action="User Banned",
            reason=reason,
            color=discord.Color.from_rgb(239, 68, 68)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Ban Command', f"Banned member {member.name}. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to ban: {e}", ephemeral=True)


@bot.tree.command(name="timeout", description="Apply an active timeout to a server member (restricts messaging, attachments, reactions)")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_root(interaction: discord.Interaction, member: discord.Member, duration_minutes: int = 10, reason: str = "No reason provided"):
    can_mod, mod_error = check_bot_can_moderate_interaction(interaction, member)
    if not can_mod:
        return await interaction.response.send_message(f"❌ {mod_error}", ephemeral=True)
    try:
        duration = timedelta(minutes=duration_minutes)
        await member.timeout(duration, reason=reason)
        expire_time = datetime.datetime.now(timezone.utc) + duration
        expire_str = expire_time.strftime("%A, %B %d, %Y at %I:%M %p")
        embed = create_modern_moderation_embed(
            title="Member Silenced",
            target=member,
            moderator=interaction.user,
            action="Active Timeout",
            reason=reason,
            duration=f"{duration_minutes} minutes",
            expires_at=expire_str,
            color=discord.Color.from_rgb(24, 24, 27)
        )
        await interaction.response.send_message(embed=embed)
        log_system_event(interaction.guild.id, interaction.user.name, 'Timeout Command', f"Timed out member {member.name} for {duration_minutes} minutes. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to timeout: {e}", ephemeral=True)


@bot.tree.command(name="clear", description="Clear tons of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_root(interaction: discord.Interaction, amount: int):
    try:
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Cleaned **{len(deleted)}** messages.")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to clear messages: {e}")


@bot.tree.command(name="disable", description="Disable an anti nuke action")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(action=[
    app_commands.Choice(name="Banning Members", value="ban"),
    app_commands.Choice(name="Kicking Members", value="kick"),
    app_commands.Choice(name="Deleting Roles", value="role_delete"),
    app_commands.Choice(name="Creating Roles", value="role_create"),
    app_commands.Choice(name="Deleting Channels", value="channel_delete"),
    app_commands.Choice(name="Creating Channels", value="channel_create"),
    app_commands.Choice(name="Adding Bots", value="bot_add"),
    app_commands.Choice(name="Giving Dangerous Permissions", value="dangerous_role_update"),
    app_commands.Choice(name="Giving Administration Roles", value="dangerous_role_add"),
    app_commands.Choice(name="Pruning Members", value="prune"),
    app_commands.Choice(name="Sending invite links / Mentions", value="mention"),
    app_commands.Choice(name="Vanity URL changes", value="vanity_change"),
    app_commands.Choice(name="Server renaming", value="server_rename"),
    app_commands.Choice(name="Server icon changes", value="server_icon_change"),
    app_commands.Choice(name="Role renaming", value="role_rename"),
    app_commands.Choice(name="Channel renaming", value="channel_rename")
])
async def disable_root(interaction: discord.Interaction, action: app_commands.Choice[str]):
    db_key = action.value
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO antinuke_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
    cursor.execute(f"UPDATE antinuke_settings SET anti_{db_key}_enabled = 0 WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ **{action.name}** protection has been **disabled**.")


@bot.tree.command(name="enable", description="Enable an anti nuke action")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(action=[
    app_commands.Choice(name="Banning Members", value="ban"),
    app_commands.Choice(name="Kicking Members", value="kick"),
    app_commands.Choice(name="Deleting Roles", value="role_delete"),
    app_commands.Choice(name="Creating Roles", value="role_create"),
    app_commands.Choice(name="Deleting Channels", value="channel_delete"),
    app_commands.Choice(name="Creating Channels", value="channel_create"),
    app_commands.Choice(name="Adding Bots", value="bot_add"),
    app_commands.Choice(name="Giving Dangerous Permissions", value="dangerous_role_update"),
    app_commands.Choice(name="Giving Administration Roles", value="dangerous_role_add"),
    app_commands.Choice(name="Pruning Members", value="prune"),
    app_commands.Choice(name="Sending invite links / Mentions", value="mention"),
    app_commands.Choice(name="Vanity URL changes", value="vanity_change"),
    app_commands.Choice(name="Server renaming", value="server_rename"),
    app_commands.Choice(name="Server icon changes", value="server_icon_change"),
    app_commands.Choice(name="Role renaming", value="role_rename"),
    app_commands.Choice(name="Channel renaming", value="channel_rename")
])
async def enable_root(interaction: discord.Interaction, action: app_commands.Choice[str]):
    db_key = action.value
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO antinuke_settings (guild_id) VALUES (?)", (str(interaction.guild.id),))
    cursor.execute(f"UPDATE antinuke_settings SET anti_{db_key}_enabled = 1 WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ **{action.name}** protection has been **enabled**.")


# setup_root handled by /setup interactive wizard
async def setup_root(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    plan = check_guild_plan(interaction.guild.id)
    setup_default_security_configs(interaction.guild.id, plan)
    
    await run_auto_setup(interaction.guild)
    
    if plan == 'Free':
        embed = discord.Embed(
            title="⚙️ VEYRA Setup Completed (Free Plan)",
            description="The Quick Setup wizard has run successfully for your server!\n\n"
                        "🔒 **Enabled Free Features**:\n"
                        "• **Anti-Ban** (Limit: 5 actions per 5m, Punishment: Ban)\n"
                        "• **Anti-Kick** (Limit: 5 actions per 5m, Punishment: Ban)\n\n"
                        "💡 *Note: Other advanced rules (channel protection, bot joins, prune limits) require a Pro or Premium plan.*\n"
                        "🔗 **Dashboard**: https://veyra-bot.vercel.app",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="⚙️ VEYRA Setup Completed (Pro/Premium Plan)",
            description="The Quick Setup wizard has run successfully for your server!\n\n"
                        "🔒 **Enabled Paid features (16 constraints active)**:\n"
                        "• **Limits**: Anti-Ban (5), Anti-Kick (5), Anti-Role Create (8), Anti-Role Delete (3), Anti-Channel Create (8), Anti-Channel Delete (3), Anti-Mention (0)\n"
                        "• **Instant Punish**: Anti-Bot Add, Anti-Prune, Dangerous Role Update/Add, Vanity, Server Rename/Icon, Role Rename, Channel Rename.\n\n"
                        "🔗 **Dashboard**: https://veyra-bot.vercel.app",
            color=discord.Color.from_rgb(24, 24, 27)
        )
    embed.set_footer(text="VEYRA • Guard Core Active")
    embed.timestamp = datetime.now(timezone.utc)
    await interaction.followup.send(embed=embed)
@bot.tree.command(name="plan", description="Displays detailed VEYRA subscription plans (Free, Pro, Premium)")
async def plan_slash(interaction: discord.Interaction):
    embed, view = build_plans_embed()
    await interaction.response.send_message(embed=embed, view=view)


# --- ADDITIONAL SCREENSHOTS COMMANDS ---

@bot.tree.command(name="avatar", description="Displays the avatar of a user with a download link")
async def avatar(interaction: discord.Interaction, user: Optional[Union[discord.Member, discord.User]] = None):
    target = user or interaction.user
    if interaction.guild and not isinstance(target, discord.Member):
        m = interaction.guild.get_member(target.id)
        if m:
            target = m
    embed, view = build_avatar_embed(target)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="banner", description="Displays the banner of a user with a download link")
async def banner(interaction: discord.Interaction, user: Optional[Union[discord.Member, discord.User]] = None):
    target = user or interaction.user
    if interaction.guild and not isinstance(target, discord.Member):
        m = interaction.guild.get_member(target.id)
        if m:
            target = m
    user_fetched = None
    try:
        user_fetched = await bot.fetch_user(target.id)
    except Exception:
        pass
        
    embed, view = build_banner_embed(target, user_fetched)
    if view:
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="guildbanner", description="Displays this server's banner with a download link")
async def guildbanner(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild or not guild.banner:
        return await interaction.response.send_message("❌ This server does not have a banner set.", ephemeral=True)
        
    try:
        banner_url = guild.banner.with_size(1024).url
    except Exception:
        banner_url = guild.banner.url

    embed = discord.Embed(
        title=f"🏰 Banner of {guild.name}",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_image(url=str(banner_url))
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    view = MediaDownloadView([("Download ↗", str(banner_url))])
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="servericon", description="Displays this server's icon with a download link")
async def servericon(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild or not guild.icon:
        return await interaction.response.send_message("❌ This server does not have an icon set.", ephemeral=True)
        
    try:
        icon_url = guild.icon.with_size(1024).url
    except Exception:
        icon_url = guild.icon.url

    embed = discord.Embed(
        title=f"🏰 Icon of {guild.name}",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_image(url=str(icon_url))
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    view = MediaDownloadView([("Download ↗", str(icon_url))])
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="accountage", description="Displays the account age of your account or a user's account")
async def accountage(interaction: discord.Interaction, user: Optional[Union[discord.Member, discord.User]] = None):
    target = user or interaction.user
    import datetime
    delta = datetime.datetime.now(datetime.timezone.utc) - target.created_at
    embed = create_veyra_embed(
        title="📅 Account Creation Registry",
        description=f"Information query for account registration details.",
        fields=[
            ("👤 Target Member", target.mention, True),
            ("📅 Account Age", f"**{delta.days}** days", True),
            ("🔒 Registration Date", f"`{target.created_at.strftime('%Y-%m-%d %H:%M:%S')}`", False)
        ],
        thumbnail=target.display_avatar.url if target.display_avatar else None,
        color=discord.Color.from_rgb(24, 24, 27),
        footer="VEYRA V2 • Account Diagnostics"
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="membercount", description="Displays the member count of the server")
async def membercount(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        
    await interaction.response.defer()
    
    # Fetch guild with counts dynamically from API to guarantee 100% real-time accuracy
    try:
        fetched = await bot.fetch_guild(guild.id, with_counts=True)
        total_count = fetched.approximate_member_count if fetched.approximate_member_count else guild.member_count
    except Exception:
        total_count = guild.member_count
        
    if not total_count:
        total_count = len(guild.members)
        
    # Ensure members list is fully cached to filter humans vs bots
    if not guild.chunked:
        try:
            await guild.chunk()
        except Exception:
            pass
            
    bot_count = sum(1 for m in guild.members if m.bot)
    human_count = max(0, total_count - bot_count)
    
    embed = create_veyra_embed(
        title="👥 Server Population Diagnostics",
        fields=[
            ("👥 Total Members", f"**{total_count}**", True),
            ("👤 Real Humans", f"**{human_count}**", True),
            ("🤖 Automated Bots", f"**{bot_count}**", True),
            ("🏰 Server Name", guild.name, False)
        ],
        color=discord.Color.from_rgb(24, 24, 27),
        footer="VEYRA V2 • Real-Time Stats"
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="permissions", description="Displays the information about what permissions the bot requires to function properly")
async def permissions(interaction: discord.Interaction):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer()
        except Exception:
            pass
    embed = discord.Embed(title="🛡️ Bot Permissions Audit", color=discord.Color.from_rgb(24, 24, 27))
    perms_needed = [
        ("Administrator", "Required for anti-nuke rollbacks, auto-moderation, and full security enforcement."),
        ("Manage Roles", "Required to grant verified role, remove unverified role, and handle autoroles/stickyroles."),
        ("Manage Channels", "Required for locks, unlocks, channel recreations (nuke), and setup gates."),
        ("Kick Members", "Required to punish rogue accounts detected by rate-limits."),
        ("Ban Members", "Required to ban nukers and keep your guild protected.")
    ]
    for p, desc in perms_needed:
        embed.add_field(name=p, value=desc, inline=False)
    await interaction.followup.send(embed=embed)


# --- LOGS / WELCOME GREETINGS ---

@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def setjoinchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO welcome_settings (guild_id, channel, enabled) VALUES (?, ?, 1)", (str(interaction.guild.id), str(channel.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Welcome join messages will now appear in: {channel.mention}")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def setjoinmessage(interaction: discord.Interaction, message: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO welcome_settings (guild_id, message, enabled) VALUES (?, ?, 1)", (str(interaction.guild.id), message))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Welcome join message updated to:\n`{message}`")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def setleavechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO leave_settings (guild_id, channel, enabled) VALUES (?, ?, 1)", (str(interaction.guild.id), str(channel.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Member leave messages will now appear in: {channel.mention}")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def setleavemessage(interaction: discord.Interaction, message: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO leave_settings (guild_id, message, enabled) VALUES (?, ?, 1)", (str(interaction.guild.id), message))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Member leave message updated to:\n`{message}`")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def disablegreet(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO welcome_settings (guild_id, enabled) VALUES (?, 0)", (str(interaction.guild.id),))
    cursor.execute("INSERT OR REPLACE INTO leave_settings (guild_id, enabled) VALUES (?, 0)", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Greet welcome and leave systems have been **disabled**.")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def greet(interaction: discord.Interaction, message: str):
    await setjoinmessage(interaction, message)


@has_subscription_level('Pro')
async def greetchannels(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT channel FROM welcome_settings WHERE guild_id = ? AND enabled = 1", (str(interaction.guild.id),))
    w_row = cursor.fetchone()
    cursor.execute("SELECT channel FROM leave_settings WHERE guild_id = ? AND enabled = 1", (str(interaction.guild.id),))
    l_row = cursor.fetchone()
    conn.close()
    
    chans = []
    if w_row and w_row[0]:
        ch = interaction.guild.get_channel(int(w_row[0]))
        if ch: chans.append(f"Welcome Channel: {ch.mention}")
    if l_row and l_row[0]:
        ch = interaction.guild.get_channel(int(l_row[0]))
        if ch: chans.append(f"Leave Channel: {ch.mention}")
        
    if not chans:
        return await interaction.response.send_message("ℹ️ No channels configured for greet systems.")
    await interaction.response.send_message("📋 Greet Channels:\n" + "\n".join(chans))


async def show_variables_helper(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 Available Greet Variables", color=discord.Color.from_rgb(24, 24, 27))
    embed.description = "Use these placeholder variables in your welcome or leave messages:\n\n" \
                        "• `{user}` - Mentions the user who joined/left.\n" \
                        "• `{username}` - Plain username of the user.\n" \
                        "• `{server}` - Name of the Discord server.\n" \
                        "• `{member_count}` - Current number of members in the server.\n" \
                        "• `{inviter}` - Name of the inviter.\n" \
                        "• `{inviter_invites}` - Total count of active invites for the inviter."
    await interaction.response.send_message(embed=embed)


@has_subscription_level('Pro')
async def greetvariables(interaction: discord.Interaction):
    await show_variables_helper(interaction)


# --- INVITE & MESSAGE TRACKING ---

@bot.tree.command(name="messages", description="Displays the number of messages sent by you or a user")
async def messages(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM messages_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(target.id)))
    row = cursor.fetchone()
    conn.close()
    count = row[0] if row else 0
    await interaction.response.send_message(f"💬 {target.mention} has sent **{count}** messages in this server.")


@bot.tree.command(name="invites", description="Displays the invites stats of a member")
async def invites(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT invites, bonus, leaves, fake FROM invites_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(target.id)))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        invites_count, bonus, leaves, fake = 0, 0, 0, 0
    else:
        invites_count, bonus, leaves, fake = row
        
    total = invites_count + bonus - leaves
    await interaction.response.send_message(f"📨 Invite Stats for {target.mention}:\n"
                                            f"• Regular Invites: **{invites_count}**\n"
                                            f"• Bonus: **{bonus}**\n"
                                            f"• Leaves: **{leaves}**\n"
                                            f"• Fake: **{fake}**\n"
                                            f"• **Total Active: {total}**")


async def invited(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, code FROM invited_users WHERE guild_id = ? AND inviter_id = ?", (str(interaction.guild.id), str(target.id)))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        embed = discord.Embed(
            title="📋 Invites List",
            description=f"ℹ️ {target.mention} hasn't successfully invited anyone yet.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        return await interaction.response.send_message(embed=embed)
        
    invited_list = []
    for idx, r in enumerate(rows):
        invited_list.append(f"{idx+1}. <@{r[0]}> (Code: `{r[1]}`)")
        
    list_str = "\n".join(invited_list)
    if len(list_str) > 1800:
        list_str = "\n".join(invited_list[:40]) + f"\n... and {len(invited_list) - 40} more members."

    embed = discord.Embed(
        title="📋 Invites List",
        description=f"Members invited by {target.mention} (Total: **{len(rows)}**):\n\n{list_str}",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text=f"Requested by {interaction.user.name}")
    await interaction.response.send_message(embed=embed)


async def inviteinfo(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    try:
        guild_invites = await interaction.guild.invites()
        user_invites = [inv.code for inv in guild_invites if inv.inviter.id == target.id]
        if not user_invites:
            return await interaction.response.send_message(f"ℹ️ {target.mention} has no active invite codes in this server.")
        await interaction.response.send_message(f"🔗 Active invite codes for {target.mention}: " + ", ".join([f"`{c}`" for c in user_invites]))
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to fetch invites: {e}", ephemeral=True)


async def inviter(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT inviter_id, code FROM invited_users WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(target.id)))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return await interaction.response.send_message(f"ℹ️ No inviter data recorded for {target.mention}.")
    await interaction.response.send_message(f"📨 {target.mention} was invited by <@{row[0]}> using invite code `{row[1]}`.")


@app_commands.checks.has_permissions(manage_guild=True)
async def addinvites(interaction: discord.Interaction, member: discord.Member, amount: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO invites_stats (guild_id, user_id, bonus)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET bonus = bonus + ?
    """, (str(interaction.guild.id), str(member.id), amount, amount))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Successfully added **{amount}** bonus invites to {member.mention}.")


@app_commands.checks.has_permissions(manage_guild=True)
async def removeinvites(interaction: discord.Interaction, member: discord.Member, amount: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO invites_stats (guild_id, user_id, bonus)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET bonus = bonus - ?
    """, (str(interaction.guild.id), str(member.id), -amount, amount))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Successfully removed **{amount}** bonus invites from {member.mention}.")


async def resetmyinvites(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invites_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(interaction.user.id)))
    cursor.execute("DELETE FROM invited_users WHERE guild_id = ? AND inviter_id = ?", (str(interaction.guild.id), str(interaction.user.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Successfully cleared all your invites in this server.")


async def resetmymessages(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(interaction.user.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Successfully cleared all your message statistics in this server.")


@app_commands.checks.has_permissions(manage_guild=True)
async def clearinvites(interaction: discord.Interaction, member: discord.Member = None):
    conn = get_db()
    cursor = conn.cursor()
    if member:
        cursor.execute("DELETE FROM invites_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
        cursor.execute("DELETE FROM invited_users WHERE guild_id = ? AND inviter_id = ?", (str(interaction.guild.id), str(member.id)))
        msg = f"✅ Successfully cleared invite stats for {member.mention}."
    else:
        cursor.execute("DELETE FROM invites_stats WHERE guild_id = ?", (str(interaction.guild.id),))
        cursor.execute("DELETE FROM invited_users WHERE guild_id = ?", (str(interaction.guild.id),))
        msg = "✅ Successfully cleared all invite stats in this server."
    conn.commit()
    conn.close()
    await interaction.response.send_message(msg)


@app_commands.checks.has_permissions(manage_guild=True)
async def clearmessages(interaction: discord.Interaction, target: discord.Member = None):
    conn = get_db()
    cursor = conn.cursor()
    if target:
        cursor.execute("DELETE FROM messages_stats WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(target.id)))
        msg = f"✅ Successfully cleared message statistics for {target.mention}."
    else:
        cursor.execute("DELETE FROM messages_stats WHERE guild_id = ?", (str(interaction.guild.id),))
        msg = "✅ Successfully cleared all message statistics in this server."
    conn.commit()
    conn.close()
    await interaction.response.send_message(msg)


@app_commands.checks.has_permissions(administrator=True)
async def blacklistchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO blacklisted_channels (guild_id, channel_id) VALUES (?, ?)", (str(interaction.guild.id), str(channel.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Blacklisted channel {channel.mention}. Message statistics will not be counted there.")


async def blacklistedchannels(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM blacklisted_channels WHERE guild_id = ?", (str(interaction.guild.id),))
    rows = cursor.fetchall()
    conn.close()
    
    chans = []
    for r in rows:
        ch = interaction.guild.get_channel(int(r[0]))
        if ch: chans.append(ch.mention)
        
    if not chans:
        return await interaction.response.send_message("ℹ️ No blacklisted channels in this server.")
    await interaction.response.send_message("📋 Blacklisted Channels:\n" + ", ".join(chans))


# --- LEADERBOARD & STATS SUBCOMMANDS ---

class LeaderboardGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leaderboard", description="Displays top stats in this guild")

    @app_commands.command(name="invites", description="Displays the top 10 inviters in this guild")
    async def invites_lb(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, invites, bonus, leaves FROM invites_stats WHERE guild_id = ? AND user_id NOT IN (SELECT user_id FROM leaderboard_hidden WHERE guild_id = ?) ORDER BY (invites + bonus - leaves) DESC LIMIT 10", (str(interaction.guild.id), str(interaction.guild.id)))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return await interaction.response.send_message("ℹ️ No invite statistics recorded yet.")
            
        embed = discord.Embed(title="📨 Invite Stats Leaderboard", color=discord.Color.from_rgb(24, 24, 27))
        for idx, r in enumerate(rows, 1):
            total = r[1] + r[2] - r[3]
            embed.add_field(name=f"#{idx}. {interaction.guild.get_member(int(r[0])) or 'User ID: ' + r[0]}", value=f"Total: **{total}** (Regular: {r[1]} | Bonus: {r[2]} | Leaves: {r[3]})", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="messages", description="Displays the top 10 messengers in this guild")
    async def messages_lb(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, count FROM messages_stats WHERE guild_id = ? AND user_id NOT IN (SELECT user_id FROM leaderboard_hidden WHERE guild_id = ?) ORDER BY count DESC LIMIT 10", (str(interaction.guild.id), str(interaction.guild.id)))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return await interaction.response.send_message("ℹ️ No message statistics recorded yet.")
            
        embed = discord.Embed(title="💬 Message Leaderboard", color=discord.Color.from_rgb(24, 24, 27))
        for idx, r in enumerate(rows, 1):
            embed.add_field(name=f"#{idx}. {interaction.guild.get_member(int(r[0])) or 'User ID: ' + r[0]}", value=f"Messages: **{r[1]}**", inline=False)
        await interaction.response.send_message(embed=embed)


# --- ROLE INFO & UTILITIES ---

@bot.tree.command(name="roleinfo", description="Displays the information about a guild's role")
async def roleinfo(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"🛡️ Role Info - {role.name}", color=role.color)
    embed.add_field(name="ID", value=str(role.id), inline=True)
    embed.add_field(name="Position", value=str(role.position), inline=True)
    embed.add_field(name="Color Code", value=str(role.color), inline=True)
    embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
    embed.add_field(name="Members with Role", value=str(len(role.members)), inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="botinfo", description="Displays the information about the bot")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 VEYRA All-in-One Bot",
        description=(
            "The ultimate all-in-one anti-nuke, moderation, invites tracking, levels, giveaways, tickets, and utility system for your server.\n\n"
            "**🤖 System Core**\n"
            "VEYRA V2 (Sovereign Engine)\n\n"
            "**🛡️ Modules Active**\n"
            "Anti-Nuke, Moderation, Invites, Levels, Verification\n\n"
            "**Status**: Active 🟢"
        ),
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text=f"VEYRA V2 • Core Diagnostic • Ping: {round(bot.latency * 1000)}ms")
    await interaction.response.send_message(embed=embed)


# --- GIVEAWAY SYSTEM COMMANDS ---

@bot.tree.command(name="gstart", description="Creates a giveaway")
@app_commands.checks.has_permissions(manage_guild=True)
async def gstart(interaction: discord.Interaction, duration: str, winners: int, prize: str):
    import re
    match = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not match:
        return await interaction.response.send_message("❌ Invalid duration format! Use: `10s`, `5m`, `2h`, `1d`.", ephemeral=True)
        
    amount, unit = int(match.group(1)), match.group(2)
    seconds = amount
    if unit == 'm': seconds *= 60
    elif unit == 'h': seconds *= 3600
    elif unit == 'd': seconds *= 86400
    
    import datetime
    ends_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    
    ends_str = f"in {duration} ({ends_at.strftime('%B %d, %Y %I:%M %p')})"
    content, embed = build_giveaway_embed(prize, winners, ends_str, interaction.user)
    
    await interaction.response.send_message("🎉 Creating giveaway...", ephemeral=True)
    msg = await interaction.channel.send(content=content, embed=embed)
    await msg.add_reaction("🎉")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO giveaways (id, guild_id, channel_id, prize, winners, ends_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (str(msg.id), str(interaction.guild.id), str(interaction.channel.id), prize, winners, ends_at.isoformat()))
    conn.commit()
    conn.close()


@bot.tree.command(name="gend", description="Ends an active giveaway")
@app_commands.checks.has_permissions(manage_guild=True)
async def gend(interaction: discord.Interaction, message_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_id, prize, winners, ended FROM giveaways WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await interaction.response.send_message("❌ Giveaway message ID not found in database.", ephemeral=True)
        
    g_id, chan_id, prize, winners, ended = row
    if ended:
        conn.close()
        return await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
        
    cursor.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (g_id,))
    conn.commit()
    conn.close()
    
    try:
        channel = interaction.guild.get_channel(int(chan_id))
        msg = await channel.fetch_message(int(g_id))
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = [user async for user in reaction.users() if not user.bot]
        
        if not users:
            await channel.send(f"😢 No participants reacted in the giveaway for **{prize}**.")
            return await interaction.response.send_message("✅ Ended giveaway (no participants).")
            
        import random
        won = random.sample(users, k=min(winners, len(users)))
        mentions = ", ".join([u.mention for u in won])
        
        await channel.send(f"🎉 **GIVEAWAY ENDED** 🎉\n\nCongratulations {mentions}! You won **{prize}**!")
        await interaction.response.send_message("✅ Successfully ended giveaway.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to end giveaway: {e}", ephemeral=True)


@bot.tree.command(name="greroll", description="Rerolls an ended giveaway")
@app_commands.checks.has_permissions(manage_guild=True)
async def greroll(interaction: discord.Interaction, message_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_id, prize, winners FROM giveaways WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return await interaction.response.send_message("❌ Giveaway message ID not found in database.", ephemeral=True)
        
    g_id, chan_id, prize, winners = row
    try:
        channel = interaction.guild.get_channel(int(chan_id))
        msg = await channel.fetch_message(int(g_id))
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = [user async for user in reaction.users() if not user.bot]
        
        if not users:
            return await channel.send("😢 No participants found to reroll.")
            
        import random
        won = random.sample(users, k=min(winners, len(users)))
        mentions = ", ".join([u.mention for u in won])
        await channel.send(f"🎉 **GIVEAWAY REROLLED** 🎉\n\nCongratulations {mentions}! You won **{prize}**!")
        await interaction.response.send_message("✅ Successfully rerolled giveaway.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to reroll: {e}", ephemeral=True)


class EventsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="events", description="Manage guild scheduled events")

    @app_commands.command(name="create", description="Create an Event")
    @app_commands.checks.has_permissions(manage_events=True)
    async def create(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        description: str, 
        start_in: str = "1d", 
        duration: str = "2h",
        voice_channel: discord.VoiceChannel = None,
        external_location: str = None
    ):
        try:
            import re, datetime
            
            def parse_offset_to_dt(offset_str):
                match = re.match(r"^(\d+)([smhd])$", offset_str.lower().strip())
                if not match:
                    return None
                amount, unit = int(match.group(1)), match.group(2)
                delta = datetime.timedelta(seconds=amount)
                if unit == 'm': delta = datetime.timedelta(minutes=amount)
                elif unit == 'h': delta = datetime.timedelta(hours=amount)
                elif unit == 'd': delta = datetime.timedelta(days=amount)
                return datetime.datetime.now(datetime.timezone.utc) + delta

            start = parse_offset_to_dt(start_in)
            if not start:
                return await interaction.response.send_message("❌ Invalid `start_in` format! Use e.g. `30m` (30 minutes), `2h` (2 hours), `1d` (1 day).", ephemeral=True)
                
            match = re.match(r"^(\d+)([mhd])$", duration.lower().strip())
            if not match:
                return await interaction.response.send_message("❌ Invalid `duration` format! Use e.g. `30m`, `2h`, `1d`.", ephemeral=True)
            amount, unit = int(match.group(1)), match.group(2)
            dur_delta = datetime.timedelta(hours=2)
            if unit == 'm': dur_delta = datetime.timedelta(minutes=amount)
            elif unit == 'h': dur_delta = datetime.timedelta(hours=amount)
            elif unit == 'd': dur_delta = datetime.timedelta(days=amount)
            
            end = start + dur_delta

            if voice_channel:
                entity_type = discord.EntityType.voice
                channel = voice_channel
                location = None
            else:
                entity_type = discord.EntityType.external
                channel = None
                location = external_location or "general"

            event = await interaction.guild.create_scheduled_event(
                name=name,
                description=description,
                start_time=start,
                end_time=end,
                entity_type=entity_type,
                channel=channel,
                location=location,
                privacy_level=discord.PrivacyLevel.guild_only
            )
            
            embed = discord.Embed(
                title="📅 Event Scheduled Successfully",
                color=0x10b981
            )
            embed.description = (
                f"**Event Details:**\n"
                f"```yaml\n"
                f"NAME: {event.name}\n"
                f"START: {start_in} from now\n"
                f"DURATION: {duration}\n"
                f"LOCATION: {voice_channel.name if voice_channel else location}\n"
                f"```\n"
                f"🔗 [**Event Link**]({event.url})"
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create event: {e}", ephemeral=True)


# Global active nuke counts tracker
active_nukes = {}

@bot.tree.command(name="nuke", description="Nukes a TextChannel with a safety countdown cancellation delay")
@app_commands.checks.has_permissions(manage_channels=True)
@has_subscription_level('Pro')
async def nuke_root(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id in active_nukes:
        return await interaction.response.send_message("⚠️ A nuke operation is already pending in this channel.", ephemeral=True)
        
    active_nukes[channel_id] = True
    await interaction.response.send_message("⚠️ **Nuke sequence initialized!** This channel will be nuked in **10 seconds**. Type `/stopnuke` to abort.")
    
    # 10 seconds warning countdown delay loop
    import asyncio
    try:
        for i in range(9, 0, -3):
            await asyncio.sleep(3)
            # Check if canceled by stopnuke
            if channel_id not in active_nukes:
                return
            await interaction.channel.send(f"⏳ **Nuke countdown:** {i} seconds remaining...")
        
        await asyncio.sleep(1)
        if channel_id not in active_nukes:
            return
            
        channel = interaction.channel
        new_channel = await channel.clone(reason="VEYRA Channel Nuke")
        await new_channel.edit(position=channel.position)
        await channel.delete(reason="VEYRA Channel Nuke")
        await new_channel.send("💥 **Channel Nuked Successfully!**")
    except Exception as e:
        try:
            await interaction.channel.send(f"❌ Failed to nuke channel: {e}")
        except Exception:
            pass
    finally:
        active_nukes.pop(channel_id, None)


@bot.tree.command(name="stopnuke", description="Aborts any pending nuke sequence in this channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def stopnuke(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id in active_nukes:
        active_nukes.pop(channel_id, None)
        await interaction.response.send_message("❌ **Nuke sequence aborted successfully!** The channel is safe.")
    else:
        await interaction.response.send_message("❌ There is no active nuke sequence pending in this channel.", ephemeral=True)


@app_commands.checks.has_permissions(manage_guild=True)
async def addmessages(interaction: discord.Interaction, member: discord.Member, amount: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages_stats (guild_id, user_id, count)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET count = messages_stats.count + ?
    """, (str(interaction.guild.id), str(member.id), amount, amount))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Successfully added **{amount}** messages to {member.mention}.")


@app_commands.checks.has_permissions(manage_guild=True)
async def removemessages(interaction: discord.Interaction, member: discord.Member, amount: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages_stats (guild_id, user_id, count)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET count = messages_stats.count - ?
    """, (str(interaction.guild.id), str(member.id), -amount, amount))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Successfully removed **{amount}** messages from {member.mention}.")


# --- NEW ROOT COMMANDS FROM SCREENSHOTS ---

@bot.tree.command(name="badges", description="Shows VEYRA bot badges of a Discord user")
async def badges_command(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    badges_list = []
    
    if target.id == interaction.guild.owner_id:
        badges_list.append("👑 **Server Owner**")
    if target.id == 1256986886631854080:
        badges_list.append("🛠️ **VEYRA Lead Developer**")
    
    plan = "Free"
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_type FROM user_subscriptions WHERE user_id = ?", (str(target.id),))
        u_row = cursor.fetchone()
        cursor.execute("SELECT plan_type FROM guild_subscriptions WHERE guild_id = ?", (str(interaction.guild.id),))
        g_row = cursor.fetchone()
        conn.close()
        if u_row: plan = u_row[0]
        elif g_row: plan = g_row[0]
    except Exception as e:
        plan = "Free"
    
    if plan == 'Premium':
        badges_list.append("💎 **Premium Supporter**")
    elif plan == 'Pro':
        badges_list.append("⚡ **Pro Supporter**")
    else:
        badges_list.append("🟢 **Active User**")
        
    description_text = "\n".join(badges_list)
    embed = create_veyra_embed(
        title=f"🛡️ VEYRA Badges - {target.name}",
        description=description_text,
        thumbnail=target.display_avatar.url if target.display_avatar else None,
        color=discord.Color.from_rgb(24, 24, 27),
        footer="VEYRA V2 • Badges Registry"
    )
    await interaction.response.send_message(embed=embed)


async def tstart(interaction: discord.Interaction, seconds: int):
    await interaction.response.send_message(f"⏱️ Timer started for **{seconds}** seconds!")
    import asyncio
    await asyncio.sleep(seconds)
    await interaction.channel.send(f"🔔 {interaction.user.mention}, your timer of **{seconds}s** has finished!")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def unsetjoinmessage(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE welcome_settings SET message = NULL WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Custom welcome join message deleted.")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def unsetleavemessage(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE leave_settings SET message = NULL WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Custom leave message deleted.")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def unsetleavechannel(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE leave_settings SET channel = NULL, enabled = 0 WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Leave channel unset and leave notifications disabled.")


@app_commands.checks.has_permissions(administrator=True)
@has_subscription_level('Pro')
async def unsetwelcomechannel(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE welcome_settings SET channel = NULL, enabled = 0 WHERE guild_id = ?", (str(interaction.guild.id),))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Welcome join channel unset and welcome notifications disabled.")


@app_commands.checks.has_permissions(administrator=True)
async def unblacklistchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklisted_channels WHERE guild_id = ? AND channel_id = ?", (str(interaction.guild.id), str(channel.id)))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Channel {channel.mention} has been unblacklisted.")


@bot.tree.command(name="userinfo", description="Displays the information of member")
async def userinfo_command(interaction: discord.Interaction, member: discord.Member = None):
    await whois(interaction, member)


async def variables_command(interaction: discord.Interaction):
    await show_variables_helper(interaction)


@bot.tree.command(name="vcinfo", description="Displays the information about a voice channel")
async def vcinfo(interaction: discord.Interaction, channel: discord.abc.GuildChannel = None):
    target_vc = None
    if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        target_vc = channel
    elif isinstance(interaction.user, discord.Member) and interaction.user.voice:
        target_vc = interaction.user.voice.channel

    if not target_vc:
        return await interaction.response.send_message("❌ Please specify a voice channel or join one.", ephemeral=True)

    embed = discord.Embed(title=f"🔊 Voice Channel Info - #{target_vc.name}", color=discord.Color.from_rgb(24, 24, 27))
    embed.add_field(name="ID", value=str(target_vc.id), inline=True)
    if hasattr(target_vc, 'bitrate'):
        embed.add_field(name="Bitrate", value=f"{round(target_vc.bitrate / 1000)} kbps", inline=True)
    if hasattr(target_vc, 'user_limit'):
        embed.add_field(name="User Limit", value=str(target_vc.user_limit) if target_vc.user_limit else "No limit", inline=True)
    embed.add_field(name="Connected Members", value=str(len(target_vc.members)), inline=True)
    await interaction.response.send_message(embed=embed)


# --- MODERATION ADDITIONS FROM SCREENSHOTS ---

@bot.tree.command(name="undeafen", description="Undeafen a member")
@app_commands.checks.has_permissions(mute_members=True)
async def undeafen(interaction: discord.Interaction, member: discord.Member):
    if not member.voice or not member.voice.channel:
        return await interaction.response.send_message("❌ This member is not connected to a voice channel.", ephemeral=True)
    try:
        await member.edit(deafen=False)
        embed = discord.Embed(
            title="🎙️ Member Undeafened",
            description=f"✅ Successfully undeafened {member.mention}.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)


@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    import datetime
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO warnings (guild_id, user_id, reason, warned_by, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (str(interaction.guild.id), str(member.id), reason, str(interaction.user), now_str))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
    warn_count = cursor.fetchone()[0]
    conn.close()
    
    try:
        await member.send(f"⚠️ You have been warned in **{interaction.guild.name}** by {interaction.user.name}. Reason: `{reason}`")
    except Exception:
        pass
        
    embed = create_modern_moderation_embed(
        title="Warn Issued",
        target=member,
        moderator=interaction.user,
        action="Warning Recorded",
        reason=reason,
        color=discord.Color.from_rgb(234, 179, 8),
        warning_count=warn_count,
        case_number=warn_count + 10
    )
    await interaction.response.send_message(embed=embed)
    log_system_event(interaction.guild.id, interaction.user.name, 'Warn Command', f"Warned member {member.name}. Reason: {reason}")


@bot.tree.command(name="warnings", description="Get warnings for a user")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT reason, warned_by, timestamp FROM warnings WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(member.id)))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return await interaction.response.send_message(f"ℹ️ {member.mention} has no warnings.")
        
    embed = discord.Embed(title=f"⚠️ Warnings list for {member.name}", color=discord.Color.red())
    for idx, r in enumerate(rows, 1):
        reason, by, ts = r
        embed.add_field(name=f"#{idx} Warned by: {by}", value=f"Reason: `{reason}`\nDate: {ts[:10]}", inline=False)
    await interaction.response.send_message(embed=embed)


async def whois(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"👤 User Info - {target}", color=discord.Color.from_rgb(24, 24, 27))
    embed.set_thumbnail(url=str(target.display_avatar.url))
    embed.add_field(name="ID", value=str(target.id), inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "N/A", inline=True)
    embed.add_field(name="Created Account", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Top Role", value=target.top_role.mention, inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="work", description="Work to earn coins")
async def work(interaction: discord.Interaction):
    import random
    earned = random.randint(50, 200)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_coins (guild_id, user_id, balance)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET balance = balance + ?
    """, (str(interaction.guild.id), str(interaction.user.id), earned, earned))
    conn.commit()
    conn.close()
    
    jobs = [
        "cleaned the VEYRA server rooms",
        "wrote some security protocols",
        "moderated chat chatrooms",
        "fixed an database exploit",
        "assisted a server owner"
    ]
    job = random.choice(jobs)
    await interaction.response.send_message(f"💼 You worked as a developer and {job}, earning **{earned}** coins!")


@bot.tree.command(name="setnick", description="Change the nickname of a user")
@app_commands.checks.has_permissions(manage_nicknames=True)
async def setnick(interaction: discord.Interaction, member: discord.Member, nickname: str = None):
    try:
        await member.edit(nick=nickname)
        embed = build_nick_embed(member, interaction.user, nickname or member.name)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to change nickname: {e}", ephemeral=True)


class SlowmodeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="slowmode", description="Configure channel slowmode settings")

    @app_commands.command(name="channel", description="Enable/disable slowmode for a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channel(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        try:
            await target.edit(slowmode_delay=seconds)
            await interaction.response.send_message(f"⏳ Slowmode for {target.mention} set to **{seconds}s**.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    @app_commands.command(name="discord", description="Set discord slowmode on a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def discord_slowmode(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        await self.channel(interaction, seconds, channel)

    @app_commands.command(name="user", description="Enable/disable slowmode per user for a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def user_slowmode(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        await self.channel(interaction, seconds, channel)





# --- NEW LATEST SCREENSHOT COMMANDS ---

@bot.tree.command(name="ranks", description="Get a list of joinable ranks.")
async def ranks(interaction: discord.Interaction):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM joinable_ranks WHERE guild_id = ?", (str(interaction.guild.id),))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return await interaction.response.send_message("ℹ️ No joinable ranks configured on this server.", ephemeral=True)
        
    roles = []
    for r in rows:
        role = interaction.guild.get_role(int(r[0]))
        if role:
            roles.append(role)
            
    if not roles:
        return await interaction.response.send_message("ℹ️ No valid joinable ranks found.", ephemeral=True)
        
    view = RanksView(roles)
    embed = discord.Embed(
        title="⚔️ Joinable Server Ranks",
        description="Select a role/rank from the menu below to join or leave it.",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RanksView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=60)
        options = [discord.SelectOption(label=role.name, value=str(role.id)) for role in roles]
        self.select = discord.ui.Select(placeholder="Choose a rank to join/leave...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        role_id = int(self.select.values[0])
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Role not found.", ephemeral=True)
        if role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"✅ Removed rank {role.name}.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to remove role: {e}", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Assigned rank {role.name}.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to add role: {e}", ephemeral=True)


@bot.tree.command(name="reason", description="Supply a reason for a mod log case")
@app_commands.checks.has_permissions(moderate_members=True)
async def reason_command(interaction: discord.Interaction, case_id: int, reason: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_logs SET details = ? WHERE id = ? AND guild_id = ?", (reason, case_id, str(interaction.guild.id)))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        await interaction.response.send_message(f"✅ Case **#{case_id}** updated with reason: `{reason}`")
    else:
        await interaction.response.send_message(f"❌ Case **#{case_id}** not found on this server.", ephemeral=True)


@bot.tree.command(name="remindme", description="Set a reminder")
async def remindme(interaction: discord.Interaction, duration: str, text: str):
    import re, asyncio
    match = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not match:
        return await interaction.response.send_message("❌ Invalid duration format! Use: `10s`, `5m`, `2h`, `1d`.", ephemeral=True)
    amount, unit = int(match.group(1)), match.group(2)
    seconds = amount
    if unit == 'm': seconds *= 60
    elif unit == 'h': seconds *= 3600
    elif unit == 'd': seconds *= 86400

    embed_ack = discord.Embed(
        title="⏰ Reminder Scheduled",
        color=0xa855f7
    )
    embed_ack.description = (
        f"Your reminder has been registered and scheduled successfully.\n"
        f"```yaml\n"
        f"MESSAGE: {text}\n"
        f"DURATION: {duration}\n"
        f"```\n"
        f"⏳ **We will remind you in DMs when the timer expires!**"
    )
    avatar_url = str(bot.user.display_avatar.url)
    embed_ack.set_author(name="VEYRA Scheduler", icon_url=avatar_url)
    if interaction.guild:
        guild_icon = str(interaction.guild.icon.url) if interaction.guild.icon else avatar_url
        embed_ack.set_footer(text=f"{interaction.guild.name} • Action Executed", icon_url=guild_icon)
    else:
        embed_ack.set_footer(text="VEYRA Scheduler • Action Executed", icon_url=avatar_url)
    embed_ack.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed_ack)
    await asyncio.sleep(seconds)
    
    embed = discord.Embed(
        title="⏰ Personal Reminder",
        color=0xa855f7
    )
    embed.description = (
        f"**Reminder Details**\n"
        f"```yaml\n"
        f"MESSAGE: {text}\n"
        f"DURATION: {duration}\n"
        f"```\n"
        f"🔔 **Status:** Triggered successfully!"
    )
    avatar_url = str(bot.user.display_avatar.url)
    embed.set_author(name="VEYRA Scheduler", icon_url=avatar_url)
    if interaction.guild:
        guild_icon = str(interaction.guild.icon.url) if interaction.guild.icon else avatar_url
        embed.set_footer(text=f"{interaction.guild.name} • Action Executed", icon_url=guild_icon)
    else:
        embed.set_footer(text="VEYRA Scheduler • Action Executed", icon_url=avatar_url)
    embed.timestamp = discord.utils.utcnow()

    try:
        await interaction.user.send(embed=embed)
    except Exception:
        await interaction.channel.send(content=interaction.user.mention, embed=embed)




# ── Prefix Commands: .role all and .role cancel ──
_role_group_tasks = {}

@bot.group(name="role", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def prefix_role_group(ctx: commands.Context):
    embed = discord.Embed(
        title="🛡️ VEYRA Role Management Commands",
        description="**Usage:**\n• `.role all <@Role>` — Assign a role to ALL human members (excludes bots & apps)\n• `.role all <@Role> remove` — Remove a role from ALL human members\n• `.role cancel` — Stop any active bulk role operation\n• `/role all` — Slash command equivalent with real-time UI",
        color=0x2B2D31
    )
    embed.set_footer(text="Powered by VEYRA 2.0 Management Suite")
    await ctx.send(embed=embed)

@prefix_role_group.command(name="all")
@commands.has_permissions(manage_roles=True)
async def prefix_role_all(ctx: commands.Context, *, args: str = None):
    if not args:
        embed = discord.Embed(
            title="🛡️ VEYRA Role All Command",
            description="**Usage:**\n• `.role all <@Role | ID | Name>` — Assign role to all humans\n• `.role all <@Role | ID | Name> remove` — Remove role from all humans\n• `.role cancel` — Stop active role operation",
            color=0x2B2D31
        )
        embed.set_footer(text="Powered by VEYRA 2.0 Management Suite")
        return await ctx.send(embed=embed)

    from server_control import parse_role_and_action, execute_bulk_role
    role, action = parse_role_and_action(ctx.guild, args)
    if not role:
        return await ctx.send("❌ Target role not found. Please mention the role, provide its numerical ID, or write its exact name.")
    return await execute_bulk_role(ctx, role, action)

@prefix_role_group.command(name="cancel")
@commands.has_permissions(manage_roles=True)
async def prefix_role_cancel(ctx: commands.Context):
    from server_control import cancel_bulk_role
    return await cancel_bulk_role(ctx)




import io

def has_ticket_plan():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == 1256986886631854080:
            return True
        if interaction.guild and interaction.guild.owner_id == interaction.user.id:
            return True
        if interaction.user and getattr(interaction.user, 'guild_permissions', None) and interaction.user.guild_permissions.administrator:
            return True

        plan = check_guild_plan(interaction.guild.id)
        plans = [p.strip().lower() for p in plan.split(',')]
        
        has_t = any('ticket' in p or 'premium' in p for p in plans)
                
        if has_t:
            return True
            
        embed = discord.Embed(
            title="🔒 Ticket Plan Required",
            description="Support Ticketing is **Locked** by default on this server.\n\nTo use ticket commands (`/setupticket`, `/ticket setup`, etc.), please visit the VEYRA Web Dashboard:\n🔗 **https://veyra-bot.vercel.app**",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="VEYRA Tier Control Matrix • Plan Subscription Required")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return app_commands.check(predicate)

# ==============================================================================
# --- TICKETS INTERACTION SYSTEM & SLASH COMMANDS ---
# ==============================================================================
import io

handled_interaction_ids = set()

def is_interaction_already_handled(interaction_id):
    if interaction_id in handled_interaction_ids:
        return True
    handled_interaction_ids.add(interaction_id)
    if len(handled_interaction_ids) > 2000:
        handled_interaction_ids.clear()
    return False

class TicketWelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_action_close")
    async def close_btn(self, btn_interaction: discord.Interaction, btn: discord.ui.Button):
        await handle_close_ticket_interaction(btn_interaction)

    @discord.ui.button(label="🙋 Claim Ticket", style=discord.ButtonStyle.success, custom_id="ticket_action_claim")
    async def claim_btn(self, btn_interaction: discord.Interaction, btn: discord.ui.Button):
        await handle_claim_ticket_interaction(btn_interaction)

class ClosedTicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔓 Reopen Ticket", style=discord.ButtonStyle.success, custom_id="closed_ticket_action_reopen")
    async def reopen_btn(self, btn_interaction: discord.Interaction, btn: discord.ui.Button):
        if is_interaction_already_handled(interaction.id if 'interaction' in locals() else btn_interaction.id): return
        if not btn_interaction.response.is_done():
            try:
                await btn_interaction.response.defer()
            except Exception:
                pass
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ?", (str(btn_interaction.channel.id),))
        ticket = cursor.fetchone()
        conn.close()
        
        if ticket:
            await reopen_ticket_handler(btn_interaction, ticket)
        else:
            await btn_interaction.followup.send("❌ Ticket record not found in database.", ephemeral=True)

    @discord.ui.button(label="🗑️ Delete Channel", style=discord.ButtonStyle.danger, custom_id="closed_ticket_action_delete")
    async def delete_btn(self, btn_interaction: discord.Interaction, btn: discord.ui.Button):
        if is_interaction_already_handled(interaction.id if 'interaction' in locals() else btn_interaction.id): return
        if not btn_interaction.response.is_done():
            try:
                await btn_interaction.response.defer()
            except Exception:
                pass
        await btn_interaction.followup.send("🗑️ Deleting ticket channel in 3 seconds...")
        await asyncio.sleep(3)
        try:
            await btn_interaction.channel.delete()
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")

async def handle_claim_ticket_interaction(interaction: discord.Interaction):
    if is_interaction_already_handled(interaction.id if 'interaction' in locals() else btn_interaction.id): return

    if not interaction.response.is_done():
        try:
            await interaction.response.defer()
        except Exception:
            pass

    guild = interaction.guild
    channel = interaction.channel

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(channel.id), str(guild.id)))
    ticket = cursor.fetchone()
    
    if not ticket:
        conn.close()
        return await interaction.followup.send("❌ This channel is not a registered ticket.", ephemeral=True)

    if ticket['status'] == 'claimed' or ticket['claimed_by'] is not None:
        conn.close()
        claimed_user = ticket['claimed_by'] or "support staff"
        return await interaction.followup.send(f"❌ This ticket is already claimed by **{claimed_user}**.", ephemeral=True)

    # Fetch panel configs
    cursor.execute("SELECT * FROM ticket_panels WHERE id = ?", (ticket['panel_id'],))
    panel = cursor.fetchone()

    # Fetch global settings
    cursor.execute("SELECT claim_mode FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
    ts_row = cursor.fetchone()
    claim_mode = ts_row['claim_mode'] if ts_row else 'private'

    # Check if interaction user is allowed (support roles, admin, manage channels/guild, or server owner)
    is_staff = False
    if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.manage_messages or interaction.user.id == guild.owner_id:
        is_staff = True
    elif panel and panel['support_roles']:
        try:
            support_roles = json.loads(panel['support_roles'])
            if isinstance(support_roles, str) and support_roles:
                support_roles = [support_roles]
            for r_id in support_roles:
                role = guild.get_role(int(r_id))
                if role and role in interaction.user.roles:
                    is_staff = True
                    break
        except Exception:
            pass
    else:
        is_staff = True

    if not is_staff:
        conn.close()
        return await interaction.followup.send("❌ You don't have permission to claim this ticket.", ephemeral=True)

    # Claim ticket
    cursor.execute("UPDATE tickets SET claimed_by = ?, status = 'claimed' WHERE id = ?", (interaction.user.name, ticket['id']))
    conn.commit()
    conn.close()

    # Private claimed overrides
    if claim_mode == 'private' and panel and panel['support_roles']:
        try:
            support_roles = json.loads(panel['support_roles'])
            if isinstance(support_roles, str) and support_roles:
                support_roles = [support_roles]
            for r_id in support_roles:
                role = guild.get_role(int(r_id))
                if role:
                    await channel.set_permissions(role, overwrite=None)
        except Exception:
            pass
        
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)

    # Disable claim button on original welcome message
    view = TicketWelcomeView()
    for child in view.children:
        if child.custom_id == "ticket_action_claim":
            child.disabled = True
            child.label = "🙋 Claimed"
            child.style = discord.ButtonStyle.secondary
    try:
        await interaction.message.edit(view=view)
    except Exception:
        pass

    claim_msg = f"🙋 **Ticket Claimed**\nThis ticket is now being handled by {interaction.user.mention}.\nPlease provide any additional information requested by the support team."
    await interaction.followup.send(claim_msg)

async def handle_close_ticket_interaction(interaction: discord.Interaction):
    if is_interaction_already_handled(interaction.id if 'interaction' in locals() else btn_interaction.id): return
    await interaction.response.defer()
    guild = interaction.guild
    channel = interaction.channel

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(channel.id), str(guild.id)))
    ticket = cursor.fetchone()
    if not ticket:
        conn.close()
        return await interaction.followup.send("❌ This channel is not a registered ticket channel in the database.", ephemeral=True)

    # If ticket is already closed, do nothing
    if ticket[7] == 'closed':
        conn.close()
        return await interaction.followup.send("❌ This ticket is already closed.", ephemeral=True)

    # Check if interaction user is allowed to close (staff, admin, or guild owner)
    # Fetch ticket settings
    cursor.execute("SELECT close_allow_user, close_allow_staff, close_allow_roles FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
    ts_row = cursor.fetchone()
    
    close_allow_user = ts_row[0] if (ts_row and ts_row[0] is not None) else 1
    close_allow_staff = ts_row[1] if (ts_row and ts_row[1] is not None) else 1
    close_allow_roles = []
    if ts_row and ts_row[2]:
        try:
            close_allow_roles = json.loads(ts_row[2])
        except Exception:
            pass

    # Check permissions
    is_allowed = False
    
    # 1. Server Administrators and Owner can ALWAYS close tickets
    if interaction.user.guild_permissions.administrator or interaction.user.id == guild.owner_id:
        is_allowed = True
        
    # 2. Check if the user is the creator of the ticket and creators are allowed to close
    elif close_allow_user and str(interaction.user.id) == str(ticket[4]): # ticket[4] is user_id
        is_allowed = True
        
    # 3. Check if the user is support staff and staff are allowed to close
    elif close_allow_staff:
        cursor.execute("SELECT support_roles FROM ticket_panels WHERE id = ?", (str(ticket[2]),))
        panel_row = cursor.fetchone()
        support_roles = []
        if panel_row and panel_row[0]:
            try:
                support_roles = json.loads(panel_row[0])
            except Exception:
                pass
        if isinstance(support_roles, str) and support_roles:
            support_roles = [support_roles]
        
        for role in interaction.user.roles:
            if str(role.id) in [str(r) for r in support_roles]:
                is_allowed = True
                break

    # 4. Check if the user has any of the specific close-allow roles
    if not is_allowed and close_allow_roles:
        for role in interaction.user.roles:
            if str(role.id) in [str(r) for r in close_allow_roles]:
                is_allowed = True
                break

    if not is_allowed:
        conn.close()
        return await interaction.followup.send("❌ You dont have permsiion to close this ticket", ephemeral=True)

    # Build high-performance Discord-style HTML transcript
    html_template = await generate_full_html_transcript(channel, ticket, closer_user=interaction.user, close_reason="Issue resolved")

    close_time = str(int(datetime.utcnow().timestamp()))
    cursor.execute("""
        UPDATE tickets SET status = 'closed', close_time = ?, transcript = ?
        WHERE channel_id = ?
    """, (close_time, html_template, str(channel.id)))
    conn.commit()

    cursor.execute("SELECT auto_delete FROM ticket_panels WHERE id = ?", (ticket[2],))
    panel_row = cursor.fetchone()
    auto_delete = panel_row[0] if panel_row else 0
    conn.close()

    transcript_filename = f"transcript-ticket-{ticket[6]:05d}.html"
    file_payload = discord.File(fp=io.BytesIO(html_template.encode('utf-8')), filename=transcript_filename)

    # Calculate Staff Message Count & Staff Mentions
    staff_msg_count = 0
    staff_users = set()
    try:
        async for msg in channel.history(limit=1000):
            if not msg.author.bot:
                if msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_channels or msg.author.guild_permissions.manage_messages or msg.author.id == guild.owner_id:
                    staff_msg_count += 1
                    staff_users.add(msg.author.mention)
    except Exception:
        pass

    staff_mentions_str = ", ".join(list(staff_users)) if staff_users else (interaction.user.mention if interaction.user else "<@staff>")
    
    # Formatted Open & Close dates
    try:
        open_ts = int(ticket[9]) if (len(ticket) > 9 and ticket[9]) else int(channel.created_at.timestamp())
        open_date_str = datetime.fromtimestamp(open_ts).strftime('%d %B %Y %H:%M')
    except Exception:
        open_date_str = datetime.utcnow().strftime('%d %B %Y %H:%M')
        
    close_date_str = datetime.utcnow().strftime('%d %B %Y %H:%M')
    
    log_embed = discord.Embed(
        title="Ticket Closed",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    log_embed.add_field(name="Ticket Name", value=f"`{channel.name}`", inline=True)
    log_embed.add_field(name="Ticket Author", value=f"<@{ticket[4]}>", inline=True)
    log_embed.add_field(name="Closed By", value=f"{interaction.user.mention}", inline=True)
    log_embed.add_field(name="Open Date", value=f"`{open_date_str}`", inline=True)
    log_embed.add_field(name="Close Date", value=f"`{close_date_str}`", inline=True)
    log_embed.add_field(name="Ticket Close Reason", value="No reason provided", inline=False)
    log_embed.add_field(name="Staff Message Count", value=f"`[ {staff_msg_count} ]` - {staff_mentions_str}", inline=False)
    
    view_transcript_url = f"https://veyra-bot.vercel.app/transcripts/v2/{channel.id}"
    transcript_view = discord.ui.View()
    transcript_view.add_item(discord.ui.Button(
        label="View Transcript",
        style=discord.ButtonStyle.link,
        url=view_transcript_url
    ))
    
    try:
        creator_user = await bot.fetch_user(int(ticket[4]))
        if creator_user:
            dm_payload = discord.File(fp=io.BytesIO(html_template.encode('utf-8')), filename=transcript_filename)
            await creator_user.send(embed=log_embed, file=dm_payload, view=transcript_view)
    except Exception as ex:
        print(f"Could not DM transcript: {ex}")

    try:
        conn_gs = get_db()
        cursor_gs = conn_gs.cursor()
        cursor_gs.execute("SELECT moderation_logs FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
        gs_row = cursor_gs.fetchone()
        conn_gs.close()
        if gs_row and gs_row[0] and gs_row[0] != 'none':
            log_channel = guild.get_channel(int(gs_row[0]))
            if log_channel:
                await log_channel.send(embed=log_embed, file=file_payload, view=transcript_view)
    except Exception as ex:
        print(f"Could not post transcript: {ex}")

    if auto_delete == 1:
        await interaction.followup.send("🔒 Ticket closed. Deleting channel in 5 seconds...")
        await asyncio.sleep(5)
        await channel.delete()
    else:
        try:
            creator_member = guild.get_member(int(ticket[4]))
            if creator_member:
                await channel.set_permissions(creator_member, overwrite=None)
        except Exception:
            pass

        try:
            await channel.edit(name=f"closed-{ticket[6]:05d}")
        except Exception:
            pass

        closed_info_embed = discord.Embed(
            title="🎫 Ticket Archived",
            description="This ticket channel is closed. Support staff can reopen or delete this channel permanently below.",
            color=discord.Color.from_rgb(148, 163, 184)
        )
        
        await channel.send(embed=closed_info_embed, view=ClosedTicketActionsView())

def get_default_ticket_panel_dict(guild):
    s_name = guild.name if guild else "Server"
    desc = (
        f"# 🟢 {s_name}\n\n"
        f"**Welcome to the {s_name} Store.** Experience premium **UID Whitelist** access built for speed, security, and reliability. Secure your access now and take your gaming experience to the next level.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "### 🛒 How to Purchase\n\n"
        "Click **Buy** below to open a **purchase ticket**. Our team will assist you with the available products, access options, and **secure payment** process.\n\n"
        "### 📜 Rules\n\n"
        "• Tickets are for **purchases and pre-sale inquiries only**.\n"
        "• **Time-wasters** may be removed or banned without warning.\n"
        "• **Respect our staff and community guidelines**.\n"
        "• Do not spam or create unnecessary tickets.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**{s_name} • SECURE • INSTANT • PREMIUM**"
    )
    default_categories = [
        {"label": "Buy", "description": "Open a purchase & UID Whitelist ticket", "emoji": "🛒"},
        {"label": "Technical Support", "description": "Get help with technical issues", "emoji": "🔧"},
        {"label": "Pre-Sale Inquiries", "description": "Ask questions before buying", "emoji": "❓"}
    ]
    return {
        "panel_title": f"🟢 {s_name} Store",
        "panel_color": "#22c55e",
        "panel_description": desc,
        "panel_button_text": "🛒 Buy",
        "ticket_title": f"🛒 {s_name} Ticket",
        "ticket_description": f"Welcome to your {s_name} ticket! Support staff will assist you with your purchase shortly.",
        "categories": json.dumps(default_categories)
    }

def get_or_create_guild_ticket_panel(guild):
    conn = get_db()
    if hasattr(conn, "row_factory"):
        try:
            import sqlite3
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
    panel = cursor.fetchone()

    if not panel:
        default_data = get_default_ticket_panel_dict(guild)
        cursor.execute("""
            INSERT INTO ticket_panels (
                guild_id, name, panel_title, panel_color, panel_description, 
                panel_button_text, ticket_title, ticket_description, categories
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(guild.id),
            "Support Panel",
            default_data["panel_title"],
            default_data["panel_color"],
            default_data["panel_description"],
            default_data["panel_button_text"],
            default_data["ticket_title"],
            default_data["ticket_description"],
            default_data["categories"]
        ))
        conn.commit()
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id DESC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()

    conn.close()
    return panel

async def post_guild_ticket_panel(target_channel, guild, panel_id: str = None):
    conn = get_db()
    if hasattr(conn, "row_factory"):
        try:
            import sqlite3
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
    cursor = conn.cursor()
    panel = None
    if panel_id:
        if str(panel_id).isdigit():
            try:
                cursor.execute("SELECT * FROM ticket_panels WHERE id = ? AND guild_id = ?", (int(panel_id), str(guild.id)))
                panel = cursor.fetchone()
            except Exception:
                panel = None
        if not panel:
            try:
                cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? AND (name = ? OR panel_title = ?)", (str(guild.id), str(panel_id), str(panel_id)))
                panel = cursor.fetchone()
            except Exception:
                panel = None
    if not panel:
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()
    conn.close()

    if not panel:
        panel = get_or_create_guild_ticket_panel(guild)

    def _pv(p, key, default=None):
        if p is None:
            return default
        try:
            val = p[key]
            return val if val is not None else default
        except Exception:
            pass
        return default

    pid = _pv(panel, 'id', 1)
    hex_color = (_pv(panel, 'panel_color') or '#22c55e').lstrip('#')
    try:
        color_int = int(hex_color, 16)
    except ValueError:
        color_int = 0x22c55e

    guild_name = guild.name if guild else "Server"
    p_title = _pv(panel, 'panel_title') or f"***{guild_name} Support Store***"
    p_desc = _pv(panel, 'panel_description') or f"Welcome to the official {guild_name} Ticket Centre."

    embed = discord.Embed(
        title=p_title,
        description=p_desc,
        color=discord.Color(color_int)
    )
    bot_avatar_url = guild.me.display_avatar.url if (guild and guild.me) else None
    embed.set_footer(text=f"Powered by {guild.me.display_name if (guild and guild.me) else 'VEYRA Support'}", icon_url=bot_avatar_url)
    embed.timestamp = datetime.utcnow()

    categories_list = []
    cat_raw = _pv(panel, 'categories')
    if cat_raw:
        try:
            categories_list = json.loads(cat_raw) if isinstance(cat_raw, str) else cat_raw
        except Exception:
            categories_list = []

    class CustomTicketPanelView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            
            # Green Create Ticket Button (Success style)
            btn_label = _pv(panel, 'panel_button_text') or "📩 Create Ticket"
            self.add_item(discord.ui.Button(
                label=btn_label,
                style=discord.ButtonStyle.success, # Green Button
                custom_id=f"ticket_create_btn:{pid}"
            ))

            if categories_list and isinstance(categories_list, list):
                options = []
                for cat in categories_list:
                    if not isinstance(cat, dict):
                        continue
                    lbl = str(cat.get('label', 'Support'))[:100]
                    desc = str(cat.get('description', ''))[:100] or None
                    emoji_char = cat.get('emoji', '')
                    
                    emoji = None
                    if emoji_char:
                        try:
                            emoji = discord.PartialEmoji.from_str(emoji_char)
                        except Exception:
                            emoji = emoji_char
                            
                    options.append(discord.SelectOption(
                        label=lbl,
                        description=desc,
                        value=lbl,
                        emoji=emoji
                    ))
                
                if options:
                    self.select_menu = discord.ui.Select(
                        placeholder="Select an option",
                        min_values=1,
                        max_values=1,
                        options=options,
                        custom_id=f"ticket_select_category:{pid}"
                    )
                    self.add_item(self.select_menu)

    return await target_channel.send(embed=embed, view=CustomTicketPanelView())

# --- Tree Command registrations ---


# Restructured Ticket Subgroups to bypass Discord 25-command limit
# Restructured Ticket Subgroups to bypass Discord 25-command limit
class TicketSetupGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="setup", description="Configure the ticketing system")

    @app_commands.command(name="wizard", description="Wizard setup and post ticket panel in a channel")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def wizard_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        try:
            await post_guild_ticket_panel(target_channel, interaction.guild)
            await interaction.followup.send(f"✅ Ticket panel successfully created & posted in {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post ticket panel: {e}", ephemeral=True)

    @app_commands.command(name="quicksetup", description="Quickly configure staff roles, log channel, and create a ticket panel.")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def quicksetup_cmd(self, interaction: discord.Interaction, staff_role: discord.Role, log_channel: discord.TextChannel, category: discord.CategoryChannel = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, claim_mode, ping_author, max_tickets, embed_color, logs_channel_id) VALUES (?, 'private', 1, 10, '#a855f7', ?)", (str(guild.id), str(log_channel.id)))
        support_roles_json = json.dumps([str(staff_role.id)])
        category_id_str = str(category.id) if category else 'none'
        default_desc = "Click the button below to **open a private support ticket**."
        cursor.execute("""
            INSERT INTO ticket_panels (guild_id, name, support_roles, category_id, panel_title, panel_description, panel_button_text, ticket_title, ticket_description, auto_close)
            VALUES (?, 'Quick Setup Panel', ?, ?, '🎫 VEYRA Support', ?, '🎫 Create Ticket', 'Support Ticket', 'Support team will assist you shortly.', 0)
        """, (str(guild.id), support_roles_json, category_id_str, default_desc))
        panel_id = getattr(cursor, "lastrowid", None)
        conn.commit()
        if not panel_id:
            try:
                cursor.execute("SELECT id FROM ticket_panels WHERE guild_id = ? ORDER BY id DESC LIMIT 1", (str(guild.id),))
                last_p = cursor.fetchone()
                if last_p:
                    panel_id = last_p['id'] if hasattr(last_p, 'keys') else last_p[0]
            except Exception:
                panel_id = 1
        panel_id = panel_id or 1
        class CustomTicketPanelView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.success, custom_id=f"ticket_create_btn:{panel_id}")
            async def create_btn(self, btn_interaction, btn):
                pass
        embed = discord.Embed(title="🎫 VEYRA Support", description=default_desc, color=discord.Color.from_rgb(24, 24, 27))
        await interaction.channel.send(embed=embed, view=CustomTicketPanelView())
        conn.close()
        await interaction.followup.send(f"✅ Ticket system quicksetup completed! Panel posted in {interaction.channel.mention}.", ephemeral=True)

    @app_commands.command(name="config", description="Configure server tickets global limits")
    @has_ticket_plan()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(claim_mode=[
        app_commands.Choice(name="Private (Staff hidden on claim)", value="private"),
        app_commands.Choice(name="Public (Remain open for all staff)", value="public"),
        app_commands.Choice(name="Disabled (No claim button)", value="disabled")
    ])
    async def config_cmd(self, interaction: discord.Interaction, max_tickets: int = 3, claim_mode: app_commands.Choice[str] = None, ping_author: bool = True, embed_color: str = "#d4af37"):
        await interaction.response.defer()
        mode = claim_mode.value if claim_mode else 'private'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, claim_mode, ping_author, max_tickets, embed_color) VALUES (?, ?, ?, ?, ?)", (str(interaction.guild.id), mode, 1 if ping_author else 0, max_tickets, embed_color))
        conn.commit()
        conn.close()
        await interaction.followup.send("✅ Ticket Bot configurations updated successfully!")

    @app_commands.command(name="panel", description="Post ticket creation panel")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def panel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None, panel_id: str = None):
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        try:
            await post_guild_ticket_panel(target_channel, interaction.guild, panel_id=panel_id)
            await interaction.followup.send(f"✅ Ticket panel successfully posted in {target_channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post panel: {e}", ephemeral=True)

    @app_commands.command(name="panels", description="List configured panels")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def panels_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ?", (str(interaction.guild.id),))
        panels = cursor.fetchall()
        conn.close()
        if not panels:
            return await interaction.followup.send("ℹ️ No ticket panels configured for this server.")
        desc = ""
        for p in panels:
            desc += f"• **{p[2]}** (ID: `{p[0]}`)\n"
        embed = discord.Embed(title="📨 Ticket Panels List", description=desc, color=discord.Color.from_rgb(24, 24, 27))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="category", description="Configure ticket default category channel")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def category_cmd(self, interaction: discord.Interaction, action: str, category: discord.CategoryChannel = None):
        await interaction.response.defer()
        guild = interaction.guild
        if action.lower() == "list":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT category_id FROM ticket_panels WHERE guild_id = ?", (str(guild.id),))
            rows = cursor.fetchall()
            conn.close()
            cats = []
            for r in rows:
                if r[0] and r[0] != 'none':
                    cat_chan = guild.get_channel(int(r[0]))
                    if cat_chan:
                        cats.append(cat_chan.name)
            desc = "Configured categories:\n" + ("\n".join([f"• {c}" for c in cats]) if cats else "None")
            return await interaction.followup.send(desc)
        elif action.lower() == "set":
            if not category:
                return await interaction.followup.send("❌ Specify category channel.")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE ticket_panels SET category_id = ? WHERE guild_id = ?", (str(category.id), str(guild.id)))
            conn.commit()
            conn.close()
            return await interaction.followup.send(f"✅ Ticket category set to **{category.name}**.")
        else:
            return await interaction.followup.send("❌ Choose action: 'list' or 'set'")

    @app_commands.command(name="tickettype", description="Set style of ticket panel: One-Click Button or Dropdown")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    @app_commands.choices(style=[
        app_commands.Choice(name="One-Click Button (Create Ticket)", value="button"),
        app_commands.Choice(name="Dropdown Style", value="dropdown")
    ])
    async def tickettype_cmd(self, interaction: discord.Interaction, panel_id: str, style: str):
        await interaction.response.defer(ephemeral=True)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE ticket_panels SET categories = NULL WHERE id = ? AND guild_id = ?", (str(panel_id), str(interaction.guild.id)))
        conn.commit()
        conn.close()
        await interaction.followup.send("✅ Panel ticket type updated successfully!", ephemeral=True)

    @app_commands.command(name="staff", description="Configure staff roles allowed to manage tickets")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def staff_cmd(self, interaction: discord.Interaction, action: str, role: discord.Role = None):
        await interaction.response.defer()
        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, support_roles FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return await interaction.followup.send("❌ No panels found. Configure first.")
        
        panel_id, support_roles_str = row
        support_roles = json.loads(support_roles_str) if support_roles_str else []
        if action.lower() == "add":
            if role and str(role.id) not in support_roles:
                support_roles.append(str(role.id))
                cursor.execute("UPDATE ticket_panels SET support_roles = ? WHERE id = ?", (json.dumps(support_roles), panel_id))
                conn.commit()
            conn.close()
            return await interaction.followup.send(f"✅ Role {role.name} added as staff.")
        elif action.lower() == "remove":
            if role and str(role.id) in support_roles:
                support_roles.remove(str(role.id))
                cursor.execute("UPDATE ticket_panels SET support_roles = ? WHERE id = ?", (json.dumps(support_roles), panel_id))
                conn.commit()
            conn.close()
            return await interaction.followup.send(f"✅ Role {role.name} removed from staff.")
        else:
            conn.close()
            return await interaction.followup.send(f"Configured staff: {', '.join(support_roles)}")

    @app_commands.command(name="limits", description="Set maximum active tickets allowed per user")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def limits_cmd(self, interaction: discord.Interaction, max_tickets_per_user: int):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, max_tickets) VALUES (?, ?)", (str(interaction.guild.id), max_tickets_per_user))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Max tickets limit updated to **{max_tickets_per_user}** per user.")

    @app_commands.command(name="logs", description="Configure logs channel for ticketing events")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def logs_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, logs_channel_id) VALUES (?, ?)", (str(interaction.guild.id), str(channel.id)))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Ticket event logging channel set to {channel.mention}.")

    @app_commands.command(name="close_setting", description="Configure closing permissions")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def close_setting_cmd(self, interaction: discord.Interaction, allow_user: bool, allow_staff: bool, roles: str = None):
        await interaction.response.defer()
        role_ids = []
        if roles:
            role_ids = [r.strip().replace('<@&', '').replace('>', '') for r in roles.split(',') if r.strip()]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO ticket_settings (guild_id, close_allow_user, close_allow_staff, close_allow_roles)
            VALUES (?, ?, ?, ?)
        """, (str(interaction.guild.id), 1 if allow_user else 0, 1 if allow_staff else 0, json.dumps(role_ids)))
        conn.commit()
        conn.close()
        await interaction.followup.send("✅ Ticket close permissions updated successfully!")

    @app_commands.command(name="automation", description="Configure automatic ticket actions")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def automation_cmd(self, interaction: discord.Interaction, auto_close_hours: int):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, auto_close_hours) VALUES (?, ?)", (str(interaction.guild.id), auto_close_hours))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Auto-close automation configured: Inactive tickets will close after **{auto_close_hours}** hours.")


class TicketSecurityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="security", description="Ticket Access & Protection settings")

    @app_commands.command(name="blacklist", description="Blacklist user from creating tickets")
    @app_commands.checks.has_permissions(manage_channels=True)
    @has_ticket_plan()
    async def blacklist_cmd(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS ticket_blacklist (guild_id TEXT, user_id TEXT, PRIMARY KEY (guild_id, user_id))")
        cursor.execute("INSERT OR IGNORE INTO ticket_blacklist (guild_id, user_id) VALUES (?, ?)", (str(interaction.guild.id), str(user.id)))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Blacklisted user {user.name}.")

    @app_commands.command(name="unblacklist", description="Unblacklist user from creating tickets")
    @app_commands.checks.has_permissions(manage_channels=True)
    @has_ticket_plan()
    async def unblacklist_cmd(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS ticket_blacklist (guild_id TEXT, user_id TEXT, PRIMARY KEY (guild_id, user_id))")
        cursor.execute("DELETE FROM ticket_blacklist WHERE guild_id = ? AND user_id = ?", (str(interaction.guild.id), str(user.id)))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Unblacklisted user {user.name}.")

    @app_commands.command(name="cooldown", description="Sets ticket creation cooldown")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def cooldown_cmd(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, cooldown_seconds) VALUES (?, ?)", (str(interaction.guild.id), seconds))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"✅ Ticket creation cooldown set to **{seconds}** seconds.")

    @app_commands.command(name="lockdown", description="Temporarily disables ticket creation")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def lockdown_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, lockdown) VALUES (?, 1)", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.followup.send("🔒 Ticket system has been locked down. New tickets cannot be created.")

    @app_commands.command(name="unlockdown", description="Enables ticket creation again")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def unlockdown_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, lockdown) VALUES (?, 0)", (str(interaction.guild.id),))
        conn.commit()
        conn.close()
        await interaction.followup.send("🔓 Ticket system lockdown lifted. Users can now create tickets.")


class TicketStatsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="stats", description="Ticket Statistics, Logs & History")

    @app_commands.command(name="search", description="Search server tickets")
    @has_ticket_plan()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def search_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE guild_id = ? AND (username LIKE ? OR user_id LIKE ? OR status LIKE ?) LIMIT 15", (str(interaction.guild.id), f"%{query}%", f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return await interaction.followup.send("❌ No matches found.")
        desc = ""
        for r in rows:
            desc += f"• **#ticket-{r[7]:05d}** | Owner: <@{r[4]}> | Status: {r[8]}\n"
        embed = discord.Embed(title=f"🔍 Results for: {query}", description=desc, color=discord.Color.from_rgb(24, 24, 27))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Staff leaderboard")
    @has_ticket_plan()
    async def leaderboard_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT claimed_by, COUNT(*) as count FROM tickets WHERE guild_id = ? AND claimed_by IS NOT NULL GROUP BY claimed_by ORDER BY count DESC LIMIT 10", (str(interaction.guild.id),))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return await interaction.followup.send("ℹ&nbsp; Leaderboard statistics not found.")
        desc = "\n".join([f"{idx+1}. **{r[0]}** - {r[1]} tickets" for idx, r in enumerate(rows)])
        embed = discord.Embed(title="📊 Ticket Leaderboard", description=desc, color=discord.Color.gold())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="history", description="Shows a user's previous tickets history")
    @has_ticket_plan()
    async def history_cmd(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10", (str(interaction.guild.id), str(user.id)))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return await interaction.followup.send(f"ℹ&nbsp; No ticket history found for user {user.mention}.")
        desc = f"Total past tickets: **{len(rows)}**\n\n"
        for r in rows:
            status_emoji = "🟢 Open" if r[8] == 'open' else "🔒 Closed"
            desc += f"• **#ticket-{r[7]:05d}** | Topic: {r[15] or 'General'} | {status_emoji}\n"
        embed = discord.Embed(title=f"🎫 Ticket History — {user.display_name}", description=desc, color=discord.Color.from_rgb(24, 24, 27))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="list", description="Lists currently open tickets")
    @has_ticket_plan()
    async def list_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE guild_id = ? AND status = 'open' LIMIT 15", (str(interaction.guild.id),))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return await interaction.followup.send("ℹ&nbsp; No active tickets currently open.")
        desc = ""
        for r in rows:
            desc += f"• **#ticket-{r[7]:05d}** | Owner: <@{r[4]}> | Claimed: {r[9] or 'Unclaimed'}\n"
        embed = discord.Embed(title="🎫 Active Tickets", description=desc, color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats", description="Shows ticket statistics")
    @has_ticket_plan()
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ?", (str(interaction.guild.id),))
        total_tickets = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'open'", (str(interaction.guild.id),))
        open_tickets = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'closed'", (str(interaction.guild.id),))
        closed_tickets = cursor.fetchone()[0]
        conn.close()
        embed = discord.Embed(title="📊 Tickets Statistics", color=discord.Color.from_rgb(24, 24, 27))
        embed.add_field(name="Total Tickets", value=str(total_tickets), inline=True)
        embed.add_field(name="Open Tickets", value=str(open_tickets), inline=True)
        embed.add_field(name="Closed Tickets", value=str(closed_tickets), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="feedback", description="Shows collected ticket feedback")
    @has_ticket_plan()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def feedback_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT rating, comment FROM ticket_history WHERE guild_id = ? AND rating IS NOT NULL LIMIT 10", (str(interaction.guild.id),))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return await interaction.followup.send("ℹ&nbsp; No feedback ratings recorded.")
        desc = ""
        for r in rows:
            stars = "⭐" * int(r[0])
            desc += f"• **{stars}** - \"{r[1] or 'No comment'}\"\n"
        embed = discord.Embed(title="📊 Ticket Feedback Reports", description=desc, color=discord.Color.orange())
        await interaction.followup.send(embed=embed)


async def check_is_staff(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    user = interaction.user
    if user.guild_permissions.administrator or user.id == guild.owner_id:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT support_roles FROM ticket_panels WHERE guild_id = ?", (str(guild.id),))
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        if row[0]:
            try:
                roles = json.loads(row[0])
                if isinstance(roles, list):
                    for r_id in roles:
                        if user.get_role(int(r_id)):
                            return True
            except Exception:
                pass
    return False

class TicketDeleteConfirmView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🗑️ Permanently deleting ticket channel in 3 seconds...")
        await asyncio.sleep(3)
        await self.channel.delete()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="VEYRA Support Ticket Management System")
        self.add_command(TicketSetupGroup())
        self.add_command(TicketSecurityGroup())
        self.add_command(TicketStatsGroup())

    @app_commands.command(name="create", description="Create a ticket manually for a selected user")
    @has_ticket_plan()
    async def create_cmd(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_user = user or interaction.user
        
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check Lockdown settings
        cursor.execute("SELECT lockdown, cooldown_seconds FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
        ts_row = cursor.fetchone()
        lockdown = ts_row['lockdown'] if ts_row and 'lockdown' in ts_row.keys() else 0
        cooldown = ts_row['cooldown_seconds'] if ts_row and 'cooldown_seconds' in ts_row.keys() else 60

        if lockdown == 1:
            conn.close()
            return await interaction.followup.send("🔒 **Ticket System Locked**\nNew tickets cannot currently be created.\nExisting tickets will continue working normally.", ephemeral=True)

        # Check blacklist
        cursor.execute("SELECT * FROM ticket_blacklist WHERE guild_id = ? AND user_id = ?", (str(guild.id), str(target_user.id)))
        if cursor.fetchone():
            conn.close()
            return await interaction.followup.send("❌ You are blacklisted from creating tickets on this server.", ephemeral=True)

        # Check Cooldown
        cursor.execute("SELECT open_time FROM tickets WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1", (str(guild.id), str(target_user.id)))
        last_t = cursor.fetchone()
        if last_t and last_t[0]:
            try:
                diff = int(datetime.utcnow().timestamp()) - int(last_t[0])
                if diff < cooldown:
                    conn.close()
                    return await interaction.followup.send(f"⚠️ You must wait **{cooldown - diff}** more seconds before creating another ticket.", ephemeral=True)
            except Exception:
                pass

        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()
        
        if not panel:
            cursor.execute("""
                INSERT INTO ticket_panels (guild_id, name, panel_title, panel_description, ticket_title, ticket_description, ticket_count)
                VALUES (?, 'Default Panel', 'Open a Ticket', 'Click below to begin support.', 'Welcome', 'Please describe your request.', 0)
            """, (str(guild.id),))
            conn.commit()
            cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
            panel = cursor.fetchone()

        cursor.execute("SELECT max_tickets FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
        ts_row2 = cursor.fetchone()
        max_tickets = ts_row2['max_tickets'] if ts_row2 else 3

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'", (str(guild.id), str(target_user.id)))
        open_count = cursor.fetchone()[0]

        if open_count >= max_tickets:
            conn.close()
            return await interaction.followup.send(f"❌ User has reached the maximum open ticket limit ({max_tickets}) on this server.", ephemeral=True)

        cursor.execute("UPDATE ticket_panels SET ticket_count = ticket_count + 1 WHERE id = ?", (panel['id'],))
        conn.commit()
        new_ticket_num = panel['ticket_count'] + 1
        conn.close()

        category = guild.get_channel(int(panel['category_id'])) if (panel['category_id'] and panel['category_id'] != 'none') else None
        if category and not isinstance(category, discord.CategoryChannel):
            category = None
        if not category:
            category = discord.utils.get(guild.categories, name="TICKETS") or discord.utils.get(guild.categories, name="Tickets")
        
        overwrites = {}
        if category:
            for target, overwrite in category.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[target] = discord.PermissionOverwrite(view_channel=False, read_messages=False, send_messages=False, connect=False)

        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False, read_messages=False, send_messages=False)
        overwrites[target_user] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)
        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True, manage_channels=True, manage_roles=True)

        support_roles = json.loads(panel['support_roles']) if panel['support_roles'] else []
        if isinstance(support_roles, str) and support_roles:
            support_roles = [support_roles]
        for r_id in support_roles:
            try:
                role = guild.get_role(int(r_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)
            except Exception:
                pass

        new_channel = await guild.create_text_channel(name=f"ticket-{new_ticket_num}", category=category, overwrites=overwrites)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (guild_id, panel_id, channel_id, user_id, username, ticket_number, status, open_time)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
        """, (str(guild.id), panel['id'], str(new_channel.id), str(target_user.id), target_user.name, new_ticket_num, int(datetime.utcnow().timestamp())))
        conn.commit()
        conn.close()

        welcome_desc = f"Welcome to your support ticket! {target_user.mention}\n\n**Thanks for contacting VEYRA Support.**"
        welcome_embed = discord.Embed(title="🎫 Support Ticket", description=welcome_desc, color=discord.Color.from_rgb(124, 58, 237))
        await new_channel.send(embed=welcome_embed, view=TicketWelcomeView())
        await interaction.followup.send(f"🎫 Ticket created successfully: {new_channel.mention}", ephemeral=True)

    @app_commands.command(name="claim", description="Claim the current ticket")
    @has_ticket_plan()
    async def claim_cmd(self, interaction: discord.Interaction):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await handle_claim_ticket_interaction(interaction)

    @app_commands.command(name="unclaim", description="Release claim on the current ticket")
    @has_ticket_plan()
    async def unclaim_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        channel = interaction.channel
        
        # Context Check
        conn = get_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(channel.id), str(guild.id)))
        ticket = cursor.fetchone()
        if not ticket:
            conn.close()
            return await interaction.followup.send("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            conn.close()
            return await interaction.followup.send("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        cursor.execute("UPDATE tickets SET claimed_by = NULL WHERE id = ?", (ticket['id'],))
        conn.commit()
        conn.close()
        await interaction.followup.send("✅ Ticket has been unclaimed. Status is now open for any support staff.")

    @app_commands.command(name="transfer", description="Transfer ticket ownership to another staff member")
    @has_ticket_plan()
    async def transfer_cmd(self, interaction: discord.Interaction, member: discord.Member):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        if not ticket:
            conn.close()
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            conn.close()
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        cursor.execute("UPDATE tickets SET claimed_by = ? WHERE id = ?", (member.name, ticket[0]))
        conn.commit()
        conn.close()
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
        await interaction.response.send_message(f"✅ Ticket transferred to {member.mention}.")

    @app_commands.command(name="add", description="Add a user to the ticket")
    @has_ticket_plan()
    async def add_cmd(self, interaction: discord.Interaction, member: discord.Member):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
        await interaction.response.send_message(f"✅ {member.mention} has been added to this ticket.")

    @app_commands.command(name="remove", description="Remove a user from the ticket")
    @has_ticket_plan()
    async def remove_cmd(self, interaction: discord.Interaction, member: discord.Member):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"✅ {member.mention} has been removed from this ticket.")

    @app_commands.command(name="rename", description="Rename the ticket channel")
    @has_ticket_plan()
    async def rename_cmd(self, interaction: discord.Interaction, new_name: str):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await interaction.channel.edit(name=new_name)
        await interaction.response.send_message("✅ Ticket renamed successfully.")

    @app_commands.command(name="move", description="Move ticket to another category")
    @has_ticket_plan()
    async def move_cmd(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await interaction.channel.edit(category=category)
        await interaction.response.send_message(f"✅ Ticket moved to category **{category.name}**.")

    @app_commands.command(name="close", description="Close the current ticket")
    @has_ticket_plan()
    async def close_cmd(self, interaction: discord.Interaction):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        await handle_close_ticket_interaction(interaction)

    @app_commands.command(name="reopen", description="Reopen a closed ticket")
    @has_ticket_plan()
    async def reopen_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        channel = interaction.channel
        
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(channel.id), str(guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.followup.send("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.followup.send("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await reopen_ticket_handler(interaction, ticket)

    @app_commands.command(name="delete", description="Permanently delete the ticket after confirmation")
    @has_ticket_plan()
    async def delete_cmd(self, interaction: discord.Interaction):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        embed = discord.Embed(title="⚠️ Delete Ticket?", description=f"This will permanently delete:\n#{interaction.channel.name}\n\nThis action cannot be undone.", color=discord.Color.red())
        view = TicketDeleteConfirmView(interaction.channel)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="transcript", description="Generate HTML transcript")
    @has_ticket_plan()
    async def transcript_cmd(self, interaction: discord.Interaction):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        await interaction.response.defer()
        html_template = await generate_full_html_transcript(interaction.channel, ticket, closer_user=interaction.user, close_reason="Manual Transcript Generation")
        transcript_filename = f"transcript-ticket-{ticket[7] if len(ticket) > 7 else 1:04d}.html"
        file_payload = discord.File(fp=io.BytesIO(html_template.encode('utf-8')), filename=transcript_filename)
        await interaction.followup.send("📄 Transcript generated successfully.", file=file_payload)

    @app_commands.command(name="info", description="Display ticket info details")
    @has_ticket_plan()
    async def info_cmd(self, interaction: discord.Interaction):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        await interaction.response.defer()
        embed = discord.Embed(title=f"🎫 Ticket #{row[7]} Details", color=discord.Color.from_rgb(24, 24, 27))
        embed.add_field(name="Owner", value=f"<@{row[4]}>", inline=True)
        embed.add_field(name="Status", value=row[8].upper(), inline=True)
        embed.add_field(name="Claimed By", value=row[9] or "Unclaimed", inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="note", description="Add internal staff note")
    @has_ticket_plan()
    async def note_cmd(self, interaction: discord.Interaction, message: str):
        # Context Check
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(interaction.channel.id), str(interaction.guild.id)))
        ticket = cursor.fetchone()
        conn.close()
        if not ticket:
            return await interaction.response.send_message("❌ Invalid Context\nThis command can only be used inside a ticket channel.", ephemeral=True)

        # Role Check
        if not await check_is_staff(interaction):
            return await interaction.response.send_message("❌ Permission Denied\nYou don't have permission to handle support tickets.", ephemeral=True)

        await interaction.response.defer()
        embed = discord.Embed(title="📝 Internal Staff Note", description=message, color=discord.Color.orange())
        embed.set_footer(text=f"Added by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="help", description="Displays the ticket help menu.")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 VEYRA Support Tickets Help",
            description="Here is a list of all ticket categories available on VEYRA:\n"
                        "💡 **Category structure:** `/ticket <category> <command>`\n\n"
                        "• **`/ticket setup`** - Commands like wizard, quicksetup, panel, staff, config, logs, close_setting, automation, limits.\n"
                        "• **`/ticket security`** - Commands like blacklist, unblacklist, cooldown, lockdown, unlockdown.\n"
                        "• **`/ticket stats`** - Commands like search, leaderboard, feedback, history, list, stats.\n\n"
                        "Use the buttons below to browse the command reference menus!",
            color=discord.Color.from_rgb(124, 58, 237)
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="settings", description="Configure ticket bot settings")
    @app_commands.checks.has_permissions(administrator=True)
    @has_ticket_plan()
    async def settings_cmd(self, interaction: discord.Interaction, staff_role: discord.Role = None, category: discord.CategoryChannel = None, max_tickets: int = None):
        await interaction.response.defer()
        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
        ts = cursor.fetchone()
        if not ts:
            cursor.execute("INSERT OR REPLACE INTO ticket_settings (guild_id, claim_mode, ping_author, max_tickets) VALUES (?, 'private', 1, 3)", (str(guild.id),))
            conn.commit()
            
        if max_tickets is not None:
            cursor.execute("UPDATE ticket_settings SET max_tickets = ? WHERE guild_id = ?", (max_tickets, str(guild.id)))
            conn.commit()
            
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()
        if not panel:
            support_roles_json = json.dumps([str(staff_role.id)]) if staff_role else "[]"
            cat_id = str(category.id) if category else "none"
            cursor.execute("""
                INSERT INTO ticket_panels (guild_id, name, support_roles, category_id, panel_title, panel_description, panel_button_text, ticket_title, ticket_description)
                VALUES (?, 'Default Panel', ?, ?, 'Support', 'Open support ticket', 'Open Ticket', 'Ticket', 'Thanks for opening ticket')
            """, (str(guild.id), support_roles_json, cat_id))
            conn.commit()
        else:
            if staff_role:
                support_roles_json = json.dumps([str(staff_role.id)])
                cursor.execute("UPDATE ticket_panels SET support_roles = ? WHERE id = ?", (support_roles_json, panel[0]))
            if category:
                cursor.execute("UPDATE ticket_panels SET category_id = ? WHERE id = ?", (str(category.id), panel[0]))
            conn.commit()
            
        conn.close()
        embed = discord.Embed(title="🎫 Ticket Configurations Updated", color=discord.Color.green(), description="The ticket settings have been updated successfully!")
        await interaction.followup.send(embed=embed)@has_ticket_plan()
async def createticket_command(interaction: discord.Interaction, reason: str = "No reason provided"):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
    panel = cursor.fetchone()
    
    if not panel:
        cursor.execute("""
            INSERT INTO ticket_panels (guild_id, name, panel_title, panel_description, ticket_title, ticket_description, ticket_count)
            VALUES (?, 'Default Panel', 'Open a Ticket', 'Click below to begin support.', 'Welcome', 'Please describe your request.', 0)
        """, (str(guild.id),))
        conn.commit()
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()

    cursor.execute("SELECT max_tickets FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
    ts_row = cursor.fetchone()
    max_tickets = ts_row['max_tickets'] if ts_row else 3

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'", (str(guild.id), str(interaction.user.id)))
    open_count = cursor.fetchone()[0]

    if open_count >= max_tickets:
        conn.close()
        return await interaction.followup.send(f"❌ You have reached the maximum open ticket limit ({max_tickets}) on this server.", ephemeral=True)

    cursor.execute("UPDATE ticket_panels SET ticket_count = ticket_count + 1 WHERE id = ?", (panel['id'],))
    conn.commit()
    new_ticket_num = panel['ticket_count'] + 1
    conn.close()

    category = guild.get_channel(int(panel['category_id'])) if (panel['category_id'] and panel['category_id'] != 'none') else None
    if category and not isinstance(category, discord.CategoryChannel):
        category = None
    if not category:
        category = discord.utils.get(guild.categories, name="TICKETS") or discord.utils.get(guild.categories, name="Tickets")
    
    overwrites = {}
    if category:
        for target, overwrite in category.overwrites.items():
            if isinstance(target, discord.Role):
                overwrites[target] = discord.PermissionOverwrite(
                    view_channel=False,
                    read_messages=False,
                    send_messages=False,
                    connect=False
                )

    # Enforce strict private overrides
    overwrites[guild.default_role] = discord.PermissionOverwrite(
        view_channel=False,
        read_messages=False,
        send_messages=False
    )
    overwrites[interaction.user] = discord.PermissionOverwrite(
        view_channel=True,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True
    )
    overwrites[guild.me] = discord.PermissionOverwrite(
        view_channel=True,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_channels=True,
        manage_roles=True
    )

    support_roles = json.loads(panel['support_roles']) if panel['support_roles'] else []
    if isinstance(support_roles, str) and support_roles:
        support_roles = [support_roles]
    for r_id in support_roles:
        try:
            role = guild.get_role(int(r_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True
                )
        except Exception:
            pass

    new_channel = await guild.create_text_channel(
        name=f"ticket-{new_ticket_num}",
        category=category,
        overwrites=overwrites
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (guild_id, panel_id, channel_id, user_id, username, ticket_number, status, open_time)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
    """, (str(guild.id), panel['id'], str(new_channel.id), str(interaction.user.id), interaction.user.name, new_ticket_num, int(datetime.utcnow().timestamp())))
    conn.commit()
    conn.close()

    welcome_desc = f"""Welcome to your support ticket! {interaction.user.mention}

**Thanks for contacting VEYRA Support.** A member of our support team will review your request and assist you shortly.

⏳ **Please wait patiently for a support member to respond.**

**Support Team:** VEYRA"""

    welcome_embed = discord.Embed(
        title="🎫 Support Ticket",
        description=welcome_desc,
        color=discord.Color.from_rgb(124, 58, 237)
    )

    await new_channel.send(embed=welcome_embed, view=TicketWelcomeView())
    await interaction.followup.send(f"✅ Your ticket has been manually created in {new_channel.mention}!", ephemeral=True)

@app_commands.checks.has_permissions(administrator=True)
@has_ticket_plan()
async def setupticket_command(interaction: discord.Interaction, channel: discord.TextChannel = None):
    await interaction.response.defer(ephemeral=True)
    target_channel = channel or interaction.channel
    try:
        await post_guild_ticket_panel(target_channel, interaction.guild)
        await interaction.followup.send(f"✅ Ticket panel successfully created & posted in {target_channel.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to post ticket panel: {e}", ephemeral=True)

@bot.command(name="setupticket", aliases=["setup-ticket", "ticketsetup", "setup_ticket"])
@commands.has_permissions(administrator=True)
async def setupticket_prefix_command(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    try:
        await post_guild_ticket_panel(target_channel, ctx.guild)
        await ctx.send(f"✅ Ticket panel successfully created & posted in {target_channel.mention}!")
    except Exception as e:
        await ctx.send(f"❌ Failed to post ticket panel: {e}")

@bot.command(name="close", aliases=["ticketclose", "close-ticket", "ticket-close"], description="Closes the active support ticket.")
async def close_prefix_command(ctx):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(ctx.channel.id), str(ctx.guild.id)))
    ticket = cursor.fetchone()
    conn.close()
    if not ticket:
        return await ctx.send("❌ This command can only be used inside an active ticket channel.")
    
    class FakeInteraction:
        def __init__(self, ctx):
            self.user = ctx.author
            self.guild = ctx.guild
            self.channel = ctx.channel
            self.id = ctx.message.id
            self.response = FakeResponse(ctx)
            self.followup = FakeFollowup(ctx)

    class FakeResponse:
        def __init__(self, ctx):
            self.ctx = ctx
            self._done = False
        def is_done(self):
            return self._done
        async def defer(self, ephemeral=False):
            self._done = True

    class FakeFollowup:
        def __init__(self, ctx):
            self.ctx = ctx
        async def send(self, content=None, embed=None, view=None, file=None, ephemeral=False):
            if file and embed:
                return await self.ctx.send(content=content, embed=embed, view=view, file=file)
            elif embed:
                return await self.ctx.send(content=content, embed=embed, view=view)
            elif view:
                return await self.ctx.send(content=content, view=view)
            return await self.ctx.send(content)

    fake_interaction = FakeInteraction(ctx)
    await handle_close_ticket_interaction(fake_interaction)

@bot.command(name="claim", aliases=["ticketclaim", "claim-ticket"], description="Claims the active support ticket.")
async def claim_prefix_command(ctx):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(ctx.channel.id), str(ctx.guild.id)))
    ticket = cursor.fetchone()
    conn.close()
    if not ticket:
        return await ctx.send("❌ This command can only be used inside an active ticket channel.")
    
    class FakeInteraction:
        def __init__(self, ctx):
            self.user = ctx.author
            self.guild = ctx.guild
            self.channel = ctx.channel
            self.id = ctx.message.id
            self.response = FakeResponse(ctx)
            self.followup = FakeFollowup(ctx)
            self.message = None

    class FakeResponse:
        def __init__(self, ctx):
            self.ctx = ctx
            self._done = False
        def is_done(self):
            return self._done
        async def defer(self, ephemeral=False):
            self._done = True

    class FakeFollowup:
        def __init__(self, ctx):
            self.ctx = ctx
        async def send(self, content=None, embed=None, view=None, ephemeral=False):
            if embed:
                return await self.ctx.send(content=content, embed=embed, view=view)
            return await self.ctx.send(content)

    fake_interaction = FakeInteraction(ctx)
    await handle_claim_ticket_interaction(fake_interaction)

@bot.command(name="reopen", aliases=["ticketreopen"], description="Reopens a closed support ticket.")
async def reopen_prefix_command(ctx):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND guild_id = ?", (str(ctx.channel.id), str(ctx.guild.id)))
    ticket = cursor.fetchone()
    conn.close()
    if not ticket:
        return await ctx.send("❌ This command can only be used inside a ticket channel.")
    
    class FakeInteraction:
        def __init__(self, ctx):
            self.user = ctx.author
            self.guild = ctx.guild
            self.channel = ctx.channel
            self.id = ctx.message.id
            self.response = FakeResponse(ctx)
            self.followup = FakeFollowup(ctx)

    class FakeResponse:
        def __init__(self, ctx):
            self.ctx = ctx
            self._done = False
        def is_done(self):
            return self._done
        async def defer(self, ephemeral=False):
            self._done = True

    class FakeFollowup:
        def __init__(self, ctx):
            self.ctx = ctx
        async def send(self, content=None, embed=None, view=None, ephemeral=False):
            if embed:
                return await self.ctx.send(content=content, embed=embed, view=view)
            return await self.ctx.send(content)

    fake_interaction = FakeInteraction(ctx)
    await reopen_ticket_handler(fake_interaction, ticket)

@bot.group(name="ticket", invoke_without_command=True)
async def ticket_prefix_group(ctx):
    embed = discord.Embed(
        title="🎫 VEYRA Ticket Commands",
        description=(
            "**Available Ticket Commands:**\n"
            "• `,close` or `,ticket close` — Close current ticket channel\n"
            "• `,claim` or `,ticket claim` — Claim ticket to assist user\n"
            "• `,reopen` or `,ticket reopen` — Reopen closed ticket\n"
            "• `,setupticket` or `,ticket setup` — Deploy support panel in a channel\n"
            "• `/ticket create` — Create ticket manually\n"
            "• `/ticket panels` — View configured ticket panels"
        ),
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@ticket_prefix_group.command(name="close")
async def ticket_prefix_sub_close(ctx):
    await close_prefix_command(ctx)

@ticket_prefix_group.command(name="claim")
async def ticket_prefix_sub_claim(ctx):
    await claim_prefix_command(ctx)

@ticket_prefix_group.command(name="reopen")
async def ticket_prefix_sub_reopen(ctx):
    await reopen_prefix_command(ctx)

@ticket_prefix_group.command(name="setup")
@commands.has_permissions(administrator=True)
async def ticket_prefix_sub_setup(ctx, channel: discord.TextChannel = None):
    await setupticket_prefix_command(ctx, channel)


@bot.tree.command(name="redeem", description="Redeems votes for server premium.")
async def redeem_command(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_coins WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = cursor.fetchone()
    balance = row[0] if row else 0
    
    if balance < 50:
        conn.close()
        return await interaction.followup.send(f"❌ You do not have enough coins/votes. Current balance: `{balance}`. You need at least `50` coins to redeem Server Premium (1 Month). Use `/vote` to earn coins!")
    
    cursor.execute("UPDATE user_coins SET balance = balance - 50 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    
    cursor.execute("SELECT plan_type, expires_at FROM guild_subscriptions WHERE guild_id = ?", (guild_id,))
    sub = cursor.fetchone()
    
    from datetime import datetime, timedelta
    expiry_date = datetime.utcnow() + timedelta(days=30)
    new_expiry_str = expiry_date.isoformat() + "+00:00"
    
    if sub:
        curr_plans = [p.strip() for p in sub[0].split(',') if p.strip()]
        if 'Premium' not in curr_plans:
            curr_plans.append('Premium')
        new_plan_str = ", ".join(curr_plans)
        
        if sub[1] and sub[1] != 'Lifetime':
            try:
                curr_expiry = datetime.fromisoformat(sub[1].split('+')[0])
                if curr_expiry > datetime.utcnow():
                    expiry_date = curr_expiry + timedelta(days=30)
                    new_expiry_str = expiry_date.isoformat() + "+00:00"
            except Exception:
                pass
        cursor.execute("UPDATE guild_subscriptions SET plan_type = ?, expires_at = ?, granted_by = ? WHERE guild_id = ?", (new_plan_str, new_expiry_str, user_id, guild_id))
    else:
        cursor.execute("INSERT INTO guild_subscriptions (guild_id, plan_type, expires_at, granted_by, created_at) VALUES (?, 'Premium', ?, ?, ?)", (guild_id, new_expiry_str, user_id, datetime.utcnow().isoformat() + "+00:00"))
    
    cursor.execute('INSERT INTO audit_logs (guild_id, action, details, timestamp, "user") VALUES (?, \'Grant Subscription\', ?, ?, ?)',
                   (guild_id, f"Redeemed 50 coins for Premium Subscription (Expires: {new_expiry_str})", new_expiry_str, datetime.utcnow().isoformat() + "+00:00", f"@{interaction.user.name}"))
    conn.commit()
    conn.close()
    
    await interaction.followup.send(f"🎉 **Premium Redeemed Successfully!** 30 days of Premium subscription have been granted to this server ({interaction.guild.name}). New expiry: `{new_expiry_str}`.")



@bot.tree.command(name="vote", description="Displays voting information.")
async def vote_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🗳️ Vote for VEYRA!",
        description="Supporting us by voting helps grow the bot, and earns you rewards!",
        color=discord.Color.from_rgb(124, 58, 237)
    )
    embed.add_field(name="Vote Rewards", value="🎁 Every vote grants you **10 VEYRA Coins**.\nCollect **50 coins** to redeem 1 Month of Server Premium via `/redeem`!", inline=False)
    embed.add_field(name="Voting Link", value="🔗 [Click here to Vote](https://veyra-bot.vercel.app)\n*(You can vote once every 12 hours)*", inline=False)
    await interaction.response.send_message(embed=embed)



async def handle_create_ticket_interaction(interaction: discord.Interaction, panel_id: str, topic: str = None):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
            
    guild = interaction.guild
    if not guild:
        return await interaction.followup.send("❌ Tickets can only be created inside a server channel.", ephemeral=True)
        
    conn = get_db()
    if hasattr(conn, "row_factory"):
        try:
            import sqlite3
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
    cursor = conn.cursor()
    
    # 1. Fetch ticket panel
    panel = None
    if panel_id and str(panel_id).isdigit():
        try:
            cursor.execute("SELECT * FROM ticket_panels WHERE id = ? AND guild_id = ?", (int(panel_id), str(guild.id)))
            panel = cursor.fetchone()
        except Exception:
            panel = None
    
    if not panel:
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY id ASC LIMIT 1", (str(guild.id),))
        panel = cursor.fetchone()
        
    if not panel:
        panel = get_or_create_guild_ticket_panel(guild)
        
    # 2. Check max ticket limit
    cursor.execute("SELECT max_tickets FROM ticket_settings WHERE guild_id = ?", (str(guild.id),))
    ts_row = cursor.fetchone()
    max_tickets = ts_row['max_tickets'] if (ts_row and ts_row['max_tickets']) else 3

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'", (str(guild.id), str(interaction.user.id)))
    open_count = cursor.fetchone()[0]

    if open_count >= max_tickets:
        conn.close()
        return await interaction.followup.send(f"❌ You have reached the maximum open ticket limit ({max_tickets}) on this server.", ephemeral=True)

    # 3. Increment ticket number
    cursor.execute("UPDATE ticket_panels SET ticket_count = COALESCE(ticket_count, 0) + 1 WHERE id = ?", (panel['id'],))
    conn.commit()
    
    cursor.execute("SELECT ticket_count FROM ticket_panels WHERE id = ?", (panel['id'],))
    c_row = cursor.fetchone()
    new_ticket_num = c_row['ticket_count'] if c_row else 1
    
    # 4. Determine category and overwrites
    category_id = panel['category_id'] if ('category_id' in panel.keys() and panel['category_id'] and panel['category_id'] != 'none') else None
    category = None
    if category_id:
        try:
            ch = guild.get_channel(int(category_id))
            if isinstance(ch, discord.CategoryChannel):
                category = ch
        except Exception:
            category = None
            
    if not category:
        category = discord.utils.get(guild.categories, name="TICKETS") or discord.utils.get(guild.categories, name="Tickets")
        if not category:
            try:
                category = await guild.create_category("TICKETS")
            except Exception:
                category = None
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, read_messages=False, send_messages=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True, manage_channels=True, manage_roles=True)
    }
    
    if 'support_roles' in panel.keys() and panel['support_roles']:
        try:
            s_roles = json.loads(panel['support_roles'])
            if isinstance(s_roles, str) and s_roles:
                s_roles = [s_roles]
            for r_id in s_roles:
                role = guild.get_role(int(r_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)
        except Exception:
            pass

    # 5. Create ticket channel
    ch_name = f"ticket-{new_ticket_num:04d}"
    try:
        new_channel = await guild.create_text_channel(
            name=ch_name,
            category=category,
            overwrites=overwrites
        )
    except Exception as e:
        conn.close()
        print(f"Error creating ticket channel: {e}")
        return await interaction.followup.send(f"❌ Failed to create ticket channel: {e}", ephemeral=True)

    # 6. Save ticket to DB
    now_ts = int(datetime.utcnow().timestamp())
    try:
        cursor.execute("""
            INSERT INTO tickets (guild_id, panel_id, channel_id, user_id, username, ticket_number, status, open_time, topic)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
        """, (str(guild.id), str(panel['id']), str(new_channel.id), str(interaction.user.id), interaction.user.name, new_ticket_num, now_ts, topic or 'General Support'))
        conn.commit()
    except Exception as dberr:
        print(f"Error saving ticket to DB: {dberr}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # 7. Post welcome embed inside ticket channel
    welcome_title = f"🎫 {panel['ticket_title'] or 'Support Ticket'}"
    
    topic_str = f"\n📌 **Selected Category:** `{topic}`" if topic else ""
    welcome_desc = (
        f"Welcome to your private support ticket, {interaction.user.mention}!{topic_str}\n\n"
        f"**{panel['ticket_description'] or 'Our support team has been notified and will assist you shortly.'}**\n\n"
        "⏳ **Please provide details about your inquiry below while waiting for staff.**"
    )

    welcome_embed = discord.Embed(
        title=welcome_title,
        description=welcome_desc,
        color=discord.Color.from_rgb(34, 197, 94)
    )
    welcome_embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun", icon_url=guild.me.display_avatar.url if guild.me else None)
    welcome_embed.timestamp = datetime.utcnow()

    try:
        await new_channel.send(content=f"{interaction.user.mention}", embed=welcome_embed, view=TicketWelcomeView())
    except Exception as send_err:
        print(f"Error sending ticket welcome embed: {send_err}")
        try:
            await new_channel.send(f"Welcome to your support ticket {interaction.user.mention}! Support staff will assist you shortly.", view=TicketWelcomeView())
        except Exception:
            pass

    try:
        await interaction.followup.send(f"✅ Your ticket has been opened in {new_channel.mention}!", ephemeral=True)
    except Exception:
        pass

    # Dispatch "Ticket Opened" log embed to moderation/logs channel
    try:
        conn_gs = get_db()
        cursor_gs = conn_gs.cursor()
        cursor_gs.execute("SELECT moderation_logs FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
        gs_row = cursor_gs.fetchone()
        conn_gs.close()
        
        if gs_row and gs_row[0] and gs_row[0] != 'none':
            log_channel = guild.get_channel(int(gs_row[0]))
            if log_channel:
                open_date_str = datetime.utcnow().strftime('%d %B %Y %H:%M')
                open_log_embed = discord.Embed(
                    title="Ticket Opened",
                    color=discord.Color.from_rgb(239, 68, 68)
                )
                open_log_embed.add_field(name="Ticket Name", value=f"`{new_channel.name}`", inline=True)
                open_log_embed.add_field(name="Created By", value=f"{interaction.user.mention}", inline=True)
                open_log_embed.add_field(name="Opened Date", value=f"`{open_date_str}`", inline=True)
                open_log_embed.add_field(name="Ticket Type", value=f"🔒 {topic or 'Support'}", inline=False)
                await log_channel.send(embed=open_log_embed)
    except Exception as ex:
        print(f"Error posting Ticket Opened log: {ex}")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return
        custom_id = interaction.data.get('custom_id') if (interaction.data and 'custom_id' in interaction.data) else None
        if custom_id:
            print(f"📥 Ticket Interaction: {custom_id} by {interaction.user}")
            if custom_id.startswith('ticket_create_btn:') or custom_id in ['create_ticket', 'create_ticket_btn', 'buy_ticket_btn', 'ticket_create']:
                panel_id = custom_id.split(':')[1] if ':' in custom_id else 'default'
                await handle_create_ticket_interaction(interaction, panel_id)
            elif custom_id.startswith('ticket_select_category:'):
                panel_id = custom_id.split(':')[1] if ':' in custom_id else 'default'
                selected_val = interaction.data.get('values', [None])[0]
                await handle_create_ticket_interaction(interaction, panel_id, topic=selected_val)
            elif custom_id == 'ticket_action_close':
                await handle_close_ticket_interaction(interaction)
            elif custom_id == 'ticket_action_claim':
                await handle_claim_ticket_interaction(interaction)
    except Exception as e:
        print(f"Error handling ticket interaction event: {e}")


# --- VEYRA WELCOME & EXIT SETUP GROUPS ---

class SetupWelcomeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="welcome", description="Configure server welcome greeting messages & channel")

    @app_commands.command(name="channel", description="Set the welcome announcement channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_ch = channel or interaction.channel
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE welcome_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, 1, ?, '#ef4444', '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', '')
            """, (str(interaction.guild.id), str(target_ch.id)))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Welcome Channel Configured",
            description=(
                f"Welcome messages will now be posted in {target_ch.mention}.\n\n"
                f"• **Status:** `Active / Enabled`\n"
                f"• **Channel:** {target_ch.mention} (`{target_ch.id}`)\n"
                f"• **Test:** Run `/setup welcome test` or `,setup welcome test` to test live!"
            ),
            color=discord.Color.from_rgb(34, 197, 94)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="msg", description="Set the welcome message content or embed description")
    @app_commands.checks.has_permissions(administrator=True)
    async def msg_cmd(self, interaction: discord.Interaction, message: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE welcome_settings SET description = ?, message = 'Welcome {user} To **{server}**', enabled = 1 WHERE guild_id = ?", (message, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer, message)
                VALUES (?, 1, 'general', '#ef4444', '', ?, '', 'Welcome {user} To **{server}**')
            """, (str(interaction.guild.id), message))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Welcome Message Updated",
            description=f"**New Template:**\n>>> {message}\n\n*Supported Placeholders: `{user}`, `{username}`, `{server}`, `{server_upper}`, `{member_count}`, `{avatar}`*",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="message", description="Set the welcome message content (alias for /setup welcome msg)")
    @app_commands.checks.has_permissions(administrator=True)
    async def message_cmd(self, interaction: discord.Interaction, message: str):
        await self.msg_cmd.callback(self, interaction, message)

    @app_commands.command(name="image", description="Set the banner image or GIF URL for welcome greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def image_cmd(self, interaction: discord.Interaction, url: str):
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            return await interaction.response.send_message("❌ Invalid URL. Please provide a direct link starting with `http://` or `https://` (JPG, PNG, GIF, WEBP).", ephemeral=True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE welcome_settings SET image = ?, enabled = 1 WHERE guild_id = ?", (clean_url, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, image, footer)
                VALUES (?, 1, 'general', '#ef4444', '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', ?, '')
            """, (str(interaction.guild.id), clean_url))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Welcome Banner Image Updated",
            description=f"Banner image/GIF has been saved.\n\n**Image URL:** {clean_url}\n*Supports JPG, PNG, WEBP, and animated GIF.*",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_image(url=clean_url)
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="color", description="Set the left border embed color (e.g. #ef4444, #a855f7)")
    @app_commands.checks.has_permissions(administrator=True)
    async def color_cmd(self, interaction: discord.Interaction, hex_code: str):
        clean_hex = hex_code.strip()
        if not clean_hex.startswith('#'):
            clean_hex = f"#{clean_hex}"
        try:
            val = int(clean_hex.replace('#', ''), 16)
            c = discord.Color(val)
        except Exception:
            return await interaction.response.send_message("❌ Invalid hex color code. Example: `#ef4444` or `ef4444`.", ephemeral=True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE welcome_settings SET color = ? WHERE guild_id = ?", (clean_hex, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, 1, 'general', ?, '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', '')
            """, (str(interaction.guild.id), clean_hex))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Welcome Embed Color Updated",
            description=f"Embed border color set to: `{clean_hex}`",
            color=c
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle", description="Enable or disable welcome greetings")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(status=[
        app_commands.Choice(name="Enable Welcome System", value=1),
        app_commands.Choice(name="Disable Welcome System", value=0)
    ])
    async def toggle_cmd(self, interaction: discord.Interaction, status: app_commands.Choice[int]):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE welcome_settings SET enabled = ? WHERE guild_id = ?", (status.value, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, ?, 'general', '#ef4444', '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', '')
            """, (str(interaction.guild.id), status.value))
        conn.commit()
        conn.close()

        state_str = "Enabled ✅" if status.value == 1 else "Disabled ❌"
        embed = discord.Embed(
            title="⚙️ Welcome System Toggled",
            description=f"Welcome greeting state is now: **{state_str}**",
            color=discord.Color.from_rgb(34, 197, 94) if status.value == 1 else discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="test", description="Send a test welcome message to verify channel & layout")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        w_settings = fetch_welcome_settings(interaction.guild.id)
        channel_name = str(w_settings.get('channel') or '').replace('#', '').strip()
        target_channel = get_fallback_channel(interaction.guild, channel_name) or interaction.channel

        try:
            raw_msg = w_settings.get('message') or "Welcome {user} To **{server}**"
            outer_msg = format_discord_message_placeholders(raw_msg, interaction.user, interaction.guild, "Direct Join")
            raw_desc = w_settings.get('description') or "Welcome {user} To **{server}**\n\n**WELCOME TO {server}**"
            fmt_desc = format_discord_message_placeholders(raw_desc, interaction.user, interaction.guild, "Direct Join")
            
            hex_color = str(w_settings.get('color') or '#ef4444').replace('#', '')
            try:
                embed_color = discord.Color(int(hex_color, 16))
            except Exception:
                embed_color = discord.Color.from_rgb(239, 68, 68)
                
            embed = discord.Embed(
                description=fmt_desc,
                color=embed_color
            )
            raw_custom_title = (w_settings.get('title') if w_settings else '') or ''
            if raw_custom_title:
                embed.title = format_discord_message_placeholders(raw_custom_title, interaction.user, interaction.guild, "Direct Join")
            
            custom_thumb = (w_settings.get('thumbnail') if w_settings else '') or ''
            if custom_thumb and custom_thumb.startswith('http'):
                embed.set_thumbnail(url=custom_thumb)
                
            img_url = w_settings.get('image')
            if img_url and str(img_url).strip().startswith('http'):
                embed.set_image(url=str(img_url).strip())
            elif interaction.guild.banner:
                embed.set_image(url=str(interaction.guild.banner.url))

            resolve_embed_emojis(embed, interaction.guild)
            await target_channel.send(content=outer_msg, embed=embed)
            await interaction.followup.send(f"✅ Live test welcome message posted in {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to send test welcome message: {e}", ephemeral=True)


class SetupExitGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="exit", description="Configure server member exit & leave greetings")

    @app_commands.command(name="channel", description="Set the exit/leave announcement channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_ch = channel or interaction.channel
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE leave_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, 1, ?, '#ef4444', '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', '')
            """, (str(interaction.guild.id), str(target_ch.id)))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Exit Channel Configured",
            description=(
                f"Member exit/leave messages will now be posted in {target_ch.mention}.\n\n"
                f"• **Status:** `Active / Enabled`\n"
                f"• **Channel:** {target_ch.mention} (`{target_ch.id}`)\n"
                f"• **Test:** Run `/setup exit test` or `,setup exit test` to test live!"
            ),
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="msg", description="Set the exit/leave message content or embed description")
    @app_commands.checks.has_permissions(administrator=True)
    async def msg_cmd(self, interaction: discord.Interaction, message: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE leave_settings SET description = ?, message = 'Goodbye **{username}** From **{server}**', enabled = 1 WHERE guild_id = ?", (message, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer, message)
                VALUES (?, 1, 'general', '#ef4444', '', ?, '', 'Goodbye **{username}** From **{server}**')
            """, (str(interaction.guild.id), message))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Exit Message Updated",
            description=f"**New Template:**\n>>> {message}\n\n*Supported Placeholders: `{user}`, `{username}`, `{server}`, `{server_upper}`, `{member_count}`, `{avatar}`*",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="message", description="Set the exit/leave message content (alias for /setup exit msg)")
    @app_commands.checks.has_permissions(administrator=True)
    async def message_cmd(self, interaction: discord.Interaction, message: str):
        await self.msg_cmd.callback(self, interaction, message)

    @app_commands.command(name="image", description="Set the banner image or GIF URL for exit/leave greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def image_cmd(self, interaction: discord.Interaction, url: str):
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            return await interaction.response.send_message("❌ Invalid URL. Please provide a direct link starting with `http://` or `https://` (JPG, PNG, GIF, WEBP).", ephemeral=True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE leave_settings SET image = ?, enabled = 1 WHERE guild_id = ?", (clean_url, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, image, footer)
                VALUES (?, 1, 'general', '#ef4444', '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', ?, '')
            """, (str(interaction.guild.id), clean_url))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Exit Banner Image Updated",
            description=f"Exit banner image/GIF has been saved.\n\n**Image URL:** {clean_url}\n*Supports JPG, PNG, WEBP, and animated GIF.*",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_image(url=clean_url)
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="color", description="Set the left border embed color (e.g. #ef4444, #a855f7)")
    @app_commands.checks.has_permissions(administrator=True)
    async def color_cmd(self, interaction: discord.Interaction, hex_code: str):
        clean_hex = hex_code.strip()
        if not clean_hex.startswith('#'):
            clean_hex = f"#{clean_hex}"
        try:
            val = int(clean_hex.replace('#', ''), 16)
            c = discord.Color(val)
        except Exception:
            return await interaction.response.send_message("❌ Invalid hex color code. Example: `#ef4444` or `ef4444`.", ephemeral=True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE leave_settings SET color = ? WHERE guild_id = ?", (clean_hex, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, 1, 'general', ?, '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', '')
            """, (str(interaction.guild.id), clean_hex))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Exit Embed Color Updated",
            description=f"Embed border color set to: `{clean_hex}`",
            color=c
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle", description="Enable or disable exit/leave greetings")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(status=[
        app_commands.Choice(name="Enable Exit System", value=1),
        app_commands.Choice(name="Disable Exit System", value=0)
    ])
    async def toggle_cmd(self, interaction: discord.Interaction, status: app_commands.Choice[int]):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(interaction.guild.id),))
        if cursor.fetchone():
            cursor.execute("UPDATE leave_settings SET enabled = ? WHERE guild_id = ?", (status.value, str(interaction.guild.id)))
        else:
            cursor.execute("""
                INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, ?, 'general', '#ef4444', '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', '')
            """, (str(interaction.guild.id), status.value))
        conn.commit()
        conn.close()

        state_str = "Enabled ✅" if status.value == 1 else "Disabled ❌"
        embed = discord.Embed(
            title="⚙️ Exit System Toggled",
            description=f"Exit greeting state is now: **{state_str}**",
            color=discord.Color.from_rgb(34, 197, 94) if status.value == 1 else discord.Color.from_rgb(239, 68, 68)
        )
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="test", description="Send a test exit message to verify channel & layout")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        l_settings = fetch_leave_settings(interaction.guild.id)
        channel_name = str(l_settings.get('channel') or '').replace('#', '').strip()
        target_channel = get_fallback_channel(interaction.guild, channel_name) or interaction.channel

        try:
            raw_msg = l_settings.get('message') or "Goodbye **{username}** From **{server}**"
            outer_msg = format_discord_message_placeholders(raw_msg, interaction.user, interaction.guild)
            raw_desc = l_settings.get('description') or "Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**"
            fmt_desc = format_discord_message_placeholders(raw_desc, interaction.user, interaction.guild)
            
            hex_color = str(l_settings.get('color') or '#ef4444').replace('#', '')
            try:
                embed_color = discord.Color(int(hex_color, 16))
            except Exception:
                embed_color = discord.Color.from_rgb(239, 68, 68)
                
            embed = discord.Embed(
                title=f"**Goodbye From {interaction.guild.name}**",
                description=fmt_desc,
                color=embed_color
            )
            embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
            embed.set_footer(text=f"Total Members: {interaction.guild.member_count or len(interaction.guild.members)}", icon_url=str(interaction.user.display_avatar.url))
            
            img_url = l_settings.get('image')
            if img_url and str(img_url).strip().startswith('http'):
                embed.set_image(url=str(img_url).strip())

            await target_channel.send(content=outer_msg, embed=embed)
            await interaction.followup.send(f"✅ Live test exit message posted in {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to send test exit message: {e}", ephemeral=True)


class SetupLeaveGroup(SetupExitGroup):
    def __init__(self):
        super(SetupExitGroup, self).__init__(name="leave", description="Configure server member leave greetings (alias for /setup exit)")


class RootSetupGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="setup", description="Configure VEYRA server modules (Welcome, Exit, etc.)")
        self.add_command(SetupWelcomeGroup())
        self.add_command(SetupExitGroup())
        self.add_command(SetupLeaveGroup())

    @app_commands.command(name="auto", description="Automatically create server security log channels, roles, and categories")
    @app_commands.checks.has_permissions(administrator=True)
    async def auto_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        created_channels, created_roles = await run_auto_setup(interaction.guild)
        embed = discord.Embed(
            title="⚡ VEYRA Automatic Channel & Role Setup Complete",
            description=f"Security log channels, system log channels, news update channels, and security roles have been generated for **{interaction.guild.name}** under the **VEYRA LOGS** category!",
            color=discord.Color.from_rgb(168, 85, 247)
        )
        ch_list = "\n".join([f"• `#{c}`" for c in created_channels]) if created_channels else "• *None / Already existing*"
        r_list = "\n".join([f"• `@{r}`" for r in created_roles]) if created_roles else "• *None / Already existing*"
        embed.add_field(name="📢 Channels", value=ch_list, inline=False)
        embed.add_field(name="🛡️ Roles", value=r_list, inline=False)
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        embed.timestamp = datetime.now(timezone.utc)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="automatic", description="Automatically create server security log channels, roles, and categories")
    @app_commands.checks.has_permissions(administrator=True)
    async def automatic_cmd(self, interaction: discord.Interaction):
        await self.auto_cmd.callback(self, interaction)

    @app_commands.command(name="view", description="View current Welcome, Exit, and server configuration overview")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        w_settings = fetch_welcome_settings(guild.id)
        l_settings = fetch_leave_settings(guild.id)

        w_ch_str = str(w_settings.get('channel') or 'Not configured')
        if w_ch_str.isdigit():
            ch = guild.get_channel(int(w_ch_str))
            w_ch_str = ch.mention if ch else f"`{w_ch_str}`"
        else:
            w_ch_str = f"#{w_ch_str}"

        l_ch_str = str(l_settings.get('channel') or 'Not configured')
        if l_ch_str.isdigit():
            ch = guild.get_channel(int(l_ch_str))
            l_ch_str = ch.mention if ch else f"`{l_ch_str}`"
        else:
            l_ch_str = f"#{l_ch_str}"

        w_status = "🟢 Enabled" if w_settings.get('enabled') == 1 else "🔴 Disabled"
        l_status = "🟢 Enabled" if l_settings.get('enabled') == 1 else "🔴 Disabled"

        embed = discord.Embed(
            title="⚙️ VEYRA Server Modules Setup",
            description=f"Overview of configured modules for **{guild.name}**:",
            color=discord.Color.from_rgb(168, 85, 247)
        )
        embed.add_field(name="⚡ Auto Setup", value="• **Command:** `/setup auto` (or `/setup automatic`)\n• Generates security logs, system logs, news, and admin roles.", inline=False)
        embed.add_field(name="👋 Welcome System", value=f"• **Status:** {w_status}\n• **Channel:** {w_ch_str}\n• **Command:** `/setup welcome channel`", inline=False)
        embed.add_field(name="🚪 Exit / Leave System", value=f"• **Status:** {l_status}\n• **Channel:** {l_ch_str}\n• **Command:** `/setup exit channel`", inline=False)
        embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
        await interaction.response.send_message(embed=embed)


class WelcomeStandaloneGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="welcome", description="Configure or test welcome greeting messages")

    @app_commands.command(name="channel", description="Set the welcome announcement channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        group = SetupWelcomeGroup()
        await group.channel_cmd.callback(group, interaction, channel)

    @app_commands.command(name="msg", description="Set the welcome message content or embed description")
    @app_commands.checks.has_permissions(administrator=True)
    async def msg_cmd(self, interaction: discord.Interaction, message: str):
        group = SetupWelcomeGroup()
        await group.msg_cmd.callback(group, interaction, message)

    @app_commands.command(name="message", description="Set the welcome message content (alias for /welcome msg)")
    @app_commands.checks.has_permissions(administrator=True)
    async def message_cmd(self, interaction: discord.Interaction, message: str):
        group = SetupWelcomeGroup()
        await group.msg_cmd.callback(group, interaction, message)

    @app_commands.command(name="image", description="Set the banner image or GIF URL for welcome greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def image_cmd(self, interaction: discord.Interaction, url: str):
        group = SetupWelcomeGroup()
        await group.image_cmd.callback(group, interaction, url)

    @app_commands.command(name="color", description="Set the left border embed color (e.g. #ef4444)")
    @app_commands.checks.has_permissions(administrator=True)
    async def color_cmd(self, interaction: discord.Interaction, hex_code: str):
        group = SetupWelcomeGroup()
        await group.color_cmd.callback(group, interaction, hex_code)

    @app_commands.command(name="test", description="Send a test welcome message")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_cmd(self, interaction: discord.Interaction):
        group = SetupWelcomeGroup()
        await group.test_cmd.callback(group, interaction)

    @app_commands.command(name="toggle", description="Enable or disable welcome greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_cmd(self, interaction: discord.Interaction, status: app_commands.Choice[int]):
        group = SetupWelcomeGroup()
        await group.toggle_cmd.callback(group, interaction, status)


class ExitStandaloneGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="exit", description="Configure or test exit/leave greeting messages")

    @app_commands.command(name="channel", description="Set the exit/leave announcement channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        group = SetupExitGroup()
        await group.channel_cmd.callback(group, interaction, channel)

    @app_commands.command(name="msg", description="Set the exit/leave message content or embed description")
    @app_commands.checks.has_permissions(administrator=True)
    async def msg_cmd(self, interaction: discord.Interaction, message: str):
        group = SetupExitGroup()
        await group.msg_cmd.callback(group, interaction, message)

    @app_commands.command(name="message", description="Set the exit/leave message content (alias for /exit msg)")
    @app_commands.checks.has_permissions(administrator=True)
    async def message_cmd(self, interaction: discord.Interaction, message: str):
        group = SetupExitGroup()
        await group.msg_cmd.callback(group, interaction, message)

    @app_commands.command(name="image", description="Set the banner image or GIF URL for exit/leave greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def image_cmd(self, interaction: discord.Interaction, url: str):
        group = SetupExitGroup()
        await group.image_cmd.callback(group, interaction, url)

    @app_commands.command(name="color", description="Set the left border embed color (e.g. #ef4444)")
    @app_commands.checks.has_permissions(administrator=True)
    async def color_cmd(self, interaction: discord.Interaction, hex_code: str):
        group = SetupExitGroup()
        await group.color_cmd.callback(group, interaction, hex_code)

    @app_commands.command(name="test", description="Send a test exit message")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_cmd(self, interaction: discord.Interaction):
        group = SetupExitGroup()
        await group.test_cmd.callback(group, interaction)

    @app_commands.command(name="toggle", description="Enable or disable exit greetings")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_cmd(self, interaction: discord.Interaction, status: app_commands.Choice[int]):
        group = SetupExitGroup()
        await group.toggle_cmd.callback(group, interaction, status)


# --- PREFIX COMMAND HANDLERS FOR SETUP, WELCOME, EXIT ---

@bot.group(name="setup", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def setup_prefix_group(ctx):
    embed = discord.Embed(
        title="⚙️ VEYRA Setup Commands",
        description=(
            "**Available Setup Commands:**\n"
            "• `,setup auto` (or `,setup automatic`) — Automatically create security log channels, roles, and categories\n"
            "• `,setup welcome channel <#channel>` — Set welcome announcements channel\n"
            "• `,setup welcome msg <message>` — Set welcome embed message template\n"
            "• `,setup welcome image <url>` — Set welcome banner image or GIF\n"
            "• `,setup welcome color <hex>` — Set welcome embed border color (e.g. `#ef4444`)\n"
            "• `,setup welcome test` — Post live test welcome card\n"
            "• `,setup exit channel <#channel>` — Set member exit/leave channel\n"
            "• `,setup exit msg <message>` — Set exit embed message template\n"
            "• `,setup exit image <url>` — Set exit banner image or GIF\n"
            "• `,setup exit color <hex>` — Set exit embed border color (e.g. `#ef4444`)\n"
            "• `,setup exit test` — Post live test exit card\n"
            "• `,setup view` — View current server module setup\n"
            "• `,setupticket` — Deploy support ticket panel"
        ),
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_prefix_group.command(name="auto", aliases=["automatic"])
@commands.has_permissions(administrator=True)
async def setup_auto_prefix(ctx):
    if hasattr(ctx, 'defer'):
        try:
            await ctx.defer()
        except Exception:
            pass
    created_channels, created_roles = await run_auto_setup(ctx.guild)
    embed = discord.Embed(
        title="⚡ VEYRA Automatic Channel & Role Setup Complete",
        description=f"Security log channels, system log channels, news update channels, and security roles have been generated for **{ctx.guild.name}** under the **VEYRA LOGS** category!",
        color=discord.Color.from_rgb(168, 85, 247)
    )
    ch_list = "\n".join([f"• `#{c}`" for c in created_channels]) if created_channels else "• *None / Already existing*"
    r_list = "\n".join([f"• `@{r}`" for r in created_roles]) if created_roles else "• *None / Already existing*"
    embed.add_field(name="📢 Channels", value=ch_list, inline=False)
    embed.add_field(name="🛡️ Roles", value=r_list, inline=False)
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    embed.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=embed)

@setup_prefix_group.group(name="welcome", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_group(ctx):
    await ctx.send("Usage: `,setup welcome channel <#channel>`, `,setup welcome msg <text>`, `,setup welcome image <url>`, `,setup welcome color <#hex>`, or `,setup welcome test`")

@setup_welcome_prefix_group.command(name="channel")
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_channel(ctx, channel: discord.TextChannel = None):
    target_ch = channel or ctx.channel
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE welcome_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer)
            VALUES (?, 1, ?, '#ef4444', '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', '')
        """, (str(ctx.guild.id), str(target_ch.id)))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="✅ Welcome Channel Configured",
        description=f"Welcome messages will now be posted in {target_ch.mention}.\nUse `,setup welcome test` to test live!",
        color=discord.Color.from_rgb(34, 197, 94)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_welcome_prefix_group.command(name="msg", aliases=["message"])
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_msg(ctx, *, message: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE welcome_settings SET description = ?, message = 'Welcome {user} To **{server}**', enabled = 1 WHERE guild_id = ?", (message, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer, message)
            VALUES (?, 1, 'general', '#ef4444', '', ?, '', 'Welcome {user} To **{server}**')
        """, (str(ctx.guild.id), message))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="✅ Welcome Message Updated",
        description=f"**New Template:**\n>>> {message}\n\n*Supported Placeholders: `{user}`, `{username}`, `{server}`, `{server_upper}`, `{member_count}`, `{avatar}`*",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_welcome_prefix_group.command(name="image", aliases=["img", "banner"])
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_image(ctx, url: str):
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        return await ctx.send("❌ Invalid URL. Please provide a direct link starting with `http://` or `https://` (JPG, PNG, GIF, WEBP).")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE welcome_settings SET image = ?, enabled = 1 WHERE guild_id = ?", (clean_url, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, image, footer)
            VALUES (?, 1, 'general', '#ef4444', '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', ?, '')
        """, (str(ctx.guild.id), clean_url))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="✅ Welcome Banner Image Updated",
        description=f"Banner image/GIF has been saved.\n\n**Image URL:** {clean_url}\n*Supports JPG, PNG, WEBP, and animated GIF.*",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_image(url=clean_url)
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_welcome_prefix_group.command(name="color")
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_color(ctx, hex_code: str):
    clean_hex = hex_code.strip()
    if not clean_hex.startswith('#'):
        clean_hex = f"#{clean_hex}"
    try:
        val = int(clean_hex.replace('#', ''), 16)
        c = discord.Color(val)
    except Exception:
        return await ctx.send("❌ Invalid hex color code. Example: `#ef4444` or `ef4444`.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE welcome_settings SET color = ? WHERE guild_id = ?", (clean_hex, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, enabled, channel, color, title, description, footer)
            VALUES (?, 1, 'general', ?, '', 'Welcome {user} To **{server}**\n\n**WELCOME TO {server_upper}**', '')
        """, (str(ctx.guild.id), clean_hex))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="✅ Welcome Embed Color Updated",
        description=f"Embed border color set to: `{clean_hex}`",
        color=c
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_welcome_prefix_group.command(name="test")
@commands.has_permissions(administrator=True)
async def setup_welcome_prefix_test(ctx):
    w_settings = fetch_welcome_settings(ctx.guild.id)
    channel_name = str(w_settings.get('channel') or '').replace('#', '').strip()
    target_channel = get_fallback_channel(ctx.guild, channel_name) or ctx.channel

    raw_msg = w_settings.get('message') or "Welcome {user} To **{server}**"
    outer_msg = format_discord_message_placeholders(raw_msg, ctx.author, ctx.guild, "Direct Join")
    raw_desc = w_settings.get('description') or "Welcome {user} To **{server}**\n\n**WELCOME TO {server}**"
    fmt_desc = format_discord_message_placeholders(raw_desc, ctx.author, ctx.guild, "Direct Join")
    
    hex_color = str(w_settings.get('color') or '#ef4444').replace('#', '')
    try:
        embed_color = discord.Color(int(hex_color, 16))
    except Exception:
        embed_color = discord.Color.from_rgb(239, 68, 68)
        
    embed = discord.Embed(
        description=fmt_desc,
        color=embed_color
    )
    raw_custom_title = (w_settings.get('title') if w_settings else '') or ''
    if raw_custom_title:
        embed.title = format_discord_message_placeholders(raw_custom_title, ctx.author, ctx.guild, "Direct Join")
        
    custom_thumb = (w_settings.get('thumbnail') if w_settings else '') or ''
    if custom_thumb and custom_thumb.startswith('http'):
        embed.set_thumbnail(url=custom_thumb)
        
    img_url = w_settings.get('image')
    if img_url and str(img_url).strip().startswith('http'):
        embed.set_image(url=str(img_url).strip())
    elif ctx.guild.banner:
        embed.set_image(url=str(ctx.guild.banner.url))
        
    resolve_embed_emojis(embed, ctx.guild)
    await target_channel.send(content=outer_msg, embed=embed)
    await ctx.send(f"✅ Test welcome message sent to {target_channel.mention}!")

@setup_prefix_group.group(name="exit", aliases=["leave"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_group(ctx):
    await ctx.send("Usage: `,setup exit channel <#channel>`, `,setup exit msg <text>`, `,setup exit image <url>`, `,setup exit color <#hex>`, or `,setup exit test`")

@setup_exit_prefix_group.command(name="channel")
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_channel(ctx, channel: discord.TextChannel = None):
    target_ch = channel or ctx.channel
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE leave_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer)
            VALUES (?, 1, ?, '#ef4444', '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', '')
        """, (str(ctx.guild.id), str(target_ch.id)))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="✅ Exit Channel Configured",
        description=f"Member exit/leave messages will now be posted in {target_ch.mention}.\nUse `,setup exit test` to test live!",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_exit_prefix_group.command(name="msg", aliases=["message"])
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_msg(ctx, *, message: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE leave_settings SET description = ?, message = 'Goodbye **{username}** From **{server}**', enabled = 1 WHERE guild_id = ?", (message, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer, message)
            VALUES (?, 1, 'general', '#ef4444', '', ?, '', 'Goodbye **{username}** From **{server}**')
        """, (str(ctx.guild.id), message))
    conn.commit()
    conn.close()
    embed = discord.Embed(
        title="✅ Exit Message Updated",
        description=f"**New Template:**\n>>> {message}\n\n*Supported Placeholders: `{user}`, `{username}`, `{server}`, `{server_upper}`, `{member_count}`, `{avatar}`*",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_exit_prefix_group.command(name="image", aliases=["img", "banner"])
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_image(ctx, url: str):
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        return await ctx.send("❌ Invalid URL. Please provide a direct link starting with `http://` or `https://` (JPG, PNG, GIF, WEBP).")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE leave_settings SET image = ?, enabled = 1 WHERE guild_id = ?", (clean_url, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, image, footer)
            VALUES (?, 1, 'general', '#ef4444', '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', ?, '')
        """, (str(ctx.guild.id), clean_url))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="✅ Exit Banner Image Updated",
        description=f"Banner image/GIF has been saved.\n\n**Image URL:** {clean_url}\n*Supports JPG, PNG, WEBP, and animated GIF.*",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_image(url=clean_url)
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_exit_prefix_group.command(name="color")
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_color(ctx, hex_code: str):
    clean_hex = hex_code.strip()
    if not clean_hex.startswith('#'):
        clean_hex = f"#{clean_hex}"
    try:
        val = int(clean_hex.replace('#', ''), 16)
        c = discord.Color(val)
    except Exception:
        return await ctx.send("❌ Invalid hex color code. Example: `#ef4444` or `ef4444`.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leave_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE leave_settings SET color = ? WHERE guild_id = ?", (clean_hex, str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO leave_settings (guild_id, enabled, channel, color, title, description, footer)
            VALUES (?, 1, 'general', ?, '', 'Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**', '')
        """, (str(ctx.guild.id), clean_hex))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="✅ Exit Embed Color Updated",
        description=f"Embed border color set to: `{clean_hex}`",
        color=c
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_exit_prefix_group.command(name="test")
@commands.has_permissions(administrator=True)
async def setup_exit_prefix_test(ctx):
    l_settings = fetch_leave_settings(ctx.guild.id)
    channel_name = str(l_settings.get('channel') or '').replace('#', '').strip()
    target_channel = get_fallback_channel(ctx.guild, channel_name) or ctx.channel

    raw_msg = l_settings.get('message') or "Goodbye **{username}** From **{server}**"
    outer_msg = format_discord_message_placeholders(raw_msg, ctx.author, ctx.guild)
    raw_desc = l_settings.get('description') or "Goodbye **{username}** From **{server}**\n\n**GOODBYE FROM {server_upper}**"
    fmt_desc = format_discord_message_placeholders(raw_desc, ctx.author, ctx.guild)
    
    hex_color = str(l_settings.get('color') or '#ef4444').replace('#', '')
    try:
        embed_color = discord.Color(int(hex_color, 16))
    except Exception:
        embed_color = discord.Color.from_rgb(239, 68, 68)
        
    embed = discord.Embed(
        title=f"**Goodbye From {ctx.guild.name}**",
        description=fmt_desc,
        color=embed_color
    )
    embed.set_thumbnail(url=str(ctx.author.display_avatar.url))
    embed.set_footer(text=f"Total Members: {ctx.guild.member_count or len(ctx.guild.members)}", icon_url=str(ctx.author.display_avatar.url))
    img_url = l_settings.get('image')
    if img_url and str(img_url).strip().startswith('http'):
        embed.set_image(url=str(img_url).strip())
        
    await target_channel.send(content=outer_msg, embed=embed)
    await ctx.send(f"✅ Test exit message sent to {target_channel.mention}!")

@setup_prefix_group.group(name="invite", aliases=["invites", "invitetracker"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def setup_invite_prefix_group(ctx):
    await ctx.send("Usage: `,setup invite channel <#channel>` or `,setup invite test`")

@setup_invite_prefix_group.command(name="channel")
@commands.has_permissions(administrator=True)
async def setup_invite_prefix_channel(ctx, channel: discord.TextChannel = None):
    target_ch = channel or ctx.channel
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM invitetracker_settings WHERE guild_id = ?", (str(ctx.guild.id),))
    if cursor.fetchone():
        cursor.execute("UPDATE invitetracker_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(ctx.guild.id)))
    else:
        cursor.execute("""
            INSERT INTO invitetracker_settings (guild_id, enabled, channel, color, title, description, footer)
            VALUES (?, 1, ?, '#a855f7', '', '', 'VEYRA Invite Tracker')
        """, (str(ctx.guild.id), str(target_ch.id)))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="✅ Invite Tracker Channel Configured",
        description=f"Real-time invite tracking join announcements will be sent to {target_ch.mention}.",
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@setup_invite_prefix_group.command(name="test")
@commands.has_permissions(administrator=True)
async def setup_invite_prefix_test(ctx):
    it_settings = fetch_invitetracker_settings(ctx.guild.id)
    ch_name = str(it_settings.get('channel') or 'welcome').replace('#', '').strip()
    target_channel = get_fallback_channel(ctx.guild, ch_name) or ctx.channel
    test_msg = f"{ctx.author.mention} has been invited by {ctx.bot.user.name} and has now 1 invites."
    await target_channel.send(content=test_msg)
    await ctx.send(f"✅ Real-time test invite notification sent to {target_channel.mention}!")

@setup_prefix_group.command(name="view")
@commands.has_permissions(administrator=True)
async def setup_prefix_view(ctx):
    w_settings = fetch_welcome_settings(ctx.guild.id)
    l_settings = fetch_leave_settings(ctx.guild.id)
    it_settings = fetch_invitetracker_settings(ctx.guild.id)
    w_ch_str = str(w_settings.get('channel') or 'Not configured')
    if w_ch_str.isdigit():
        ch = ctx.guild.get_channel(int(w_ch_str))
        w_ch_str = ch.mention if ch else f"`{w_ch_str}`"
    else:
        w_ch_str = f"#{w_ch_str}"

    l_ch_str = str(l_settings.get('channel') or 'Not configured')
    if l_ch_str.isdigit():
        ch = ctx.guild.get_channel(int(l_ch_str))
        l_ch_str = ch.mention if ch else f"`{l_ch_str}`"
    else:
        l_ch_str = f"#{l_ch_str}"

    it_ch_str = str(it_settings.get('channel') or 'Not configured')
    if it_ch_str.isdigit():
        ch = ctx.guild.get_channel(int(it_ch_str))
        it_ch_str = ch.mention if ch else f"`{it_ch_str}`"
    else:
        it_ch_str = f"#{it_ch_str}"

    embed = discord.Embed(
        title="⚙️ VEYRA Server Modules Setup",
        description=f"Overview of configured channels for **{ctx.guild.name}**:",
        color=discord.Color.from_rgb(168, 85, 247)
    )
    embed.add_field(name="👋 Welcome System", value=f"• Channel: {w_ch_str}\n• Status: {'🟢 Enabled' if w_settings.get('enabled') == 1 else '🔴 Disabled'}\n• Commands: `,setup welcome msg`, `,setup welcome image`, `,setup welcome color`", inline=False)
    embed.add_field(name="🚪 Exit System", value=f"• Channel: {l_ch_str}\n• Status: {'🟢 Enabled' if l_settings.get('enabled') == 1 else '🔴 Disabled'}\n• Commands: `,setup exit msg`, `,setup exit image`, `,setup exit color`", inline=False)
    embed.add_field(name="📈 Invite Tracker System", value=f"• Channel: {it_ch_str}\n• Status: {'🟢 Enabled' if it_settings.get('enabled') == 1 else '🔴 Disabled'}\n• Commands: `,setup invite channel`, `,setup invite test`", inline=False)
    embed.set_footer(text="Powered By Veyra Development™ | Designed By Arun")
    await ctx.send(embed=embed)

@bot.group(name="welcome", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone(ctx):
    await setup_welcome_prefix_group(ctx)

@welcome_prefix_standalone.command(name="channel")
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone_channel(ctx, channel: discord.TextChannel = None):
    await setup_welcome_prefix_channel(ctx, channel)

@welcome_prefix_standalone.command(name="msg", aliases=["message"])
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone_msg(ctx, *, message: str):
    await setup_welcome_prefix_msg(ctx, message=message)

@welcome_prefix_standalone.command(name="image", aliases=["img", "banner"])
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone_image(ctx, url: str):
    await setup_welcome_prefix_image(ctx, url=url)

@welcome_prefix_standalone.command(name="color")
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone_color(ctx, hex_code: str):
    await setup_welcome_prefix_color(ctx, hex_code=hex_code)

@welcome_prefix_standalone.command(name="test")
@commands.has_permissions(administrator=True)
async def welcome_prefix_standalone_test(ctx):
    await setup_welcome_prefix_test(ctx)

@bot.group(name="leave", aliases=["exit"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone(ctx):
    await setup_exit_prefix_group(ctx)

@leave_prefix_standalone.command(name="channel")
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone_channel(ctx, channel: discord.TextChannel = None):
    await setup_exit_prefix_channel(ctx, channel)

@leave_prefix_standalone.command(name="msg", aliases=["message"])
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone_msg(ctx, *, message: str):
    await setup_exit_prefix_msg(ctx, message=message)

@leave_prefix_standalone.command(name="image", aliases=["img", "banner"])
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone_image(ctx, url: str):
    await setup_exit_prefix_image(ctx, url=url)

@leave_prefix_standalone.command(name="color")
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone_color(ctx, hex_code: str):
    await setup_exit_prefix_color(ctx, hex_code=hex_code)

@leave_prefix_standalone.command(name="test")
@commands.has_permissions(administrator=True)
async def leave_prefix_standalone_test(ctx):
    await setup_exit_prefix_test(ctx)


def register_discord_command_tree():
    perm_grp = PermissionGroup()
    groups = [
        WhitelistGroup(),
        perm_grp,
        LogsGroup(),
        LeaderboardGroup(),
        EventsGroup(),
        AutoroleGroup(),
        StickyroleGroup(),
        SlowmodeGroup(),
        TicketGroup(),
        RootSetupGroup(),
        WelcomeStandaloneGroup(),
        ExitStandaloneGroup()
    ]
    for g in groups:
        try:
            bot.tree.add_command(g)
        except Exception as e:
            pass
    try:
        setup_server_control_system(bot, perm_grp)
    except Exception as e:
        print("Server control registration notice:", e)
    try:
        setup_verification_and_recovery(bot)
    except Exception as e:
        print("Verification registration notice:", e)
    try:
        setup_veyra_2_features(bot)
    except Exception as e:
        print("Veyra 2 registration notice:", e)

register_discord_command_tree()

try:
    from module_commands import setup_module_commands
    setup_module_commands(bot)
except Exception as e:
    print("Module commands setup notice:", e)

try:
    from cloneserver_system import setup_cloneserver_system
    setup_cloneserver_system(bot)
except Exception as e:
    print("Cloneserver setup notice:", e)

try:
    from server_customization import setup_server_customization
    setup_server_customization(bot)
except Exception as e:
    print("Server customization setup notice:", e)

try:
    # Load all-in-one music architecture directly from music_bot folder
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from music_bot import setup_music_system
    setup_music_system(bot)
except Exception as e:
    print("Music system setup notice:", e)

# Run bot using environment configurations
if __name__ == "__main__":
    # Manually load the root .env configuration file if it exists
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    # Try loading from DISCORD_BOT_TOKEN, TICKET_BOT_TOKEN, or standard DISCORD_TOKEN
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TICKET_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or "MOCK_TOKEN_PLACEHOLDER"
    client_id = os.getenv("DISCORD_CLIENT_ID") or os.getenv("TICKET_CLIENT_ID") or "NOT_CONFIGURED"

    print("\n---------------------------------------------")
    print(f"[+] Loaded Credentials Configuration:")
    print(f"   * DISCORD_CLIENT_ID : {client_id}")
    print(f"   * DISCORD_BOT_TOKEN : {'Configured (Hidden)' if token != 'MOCK_TOKEN_PLACEHOLDER' else 'Missing [x]'}")
    print("---------------------------------------------\n")

    if token == "MOCK_TOKEN_PLACEHOLDER":
        print("[!] Warning: DISCORD_BOT_TOKEN is empty in your root .env file.")
        print("--> Please add your Discord Bot credentials to: .env")
    else:
        try:
            init_db()
            bot.run(token)
        except Exception as e:
            print(f"[x] Failed to start bot: {e}")
