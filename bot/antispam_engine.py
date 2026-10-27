# bot/antispam_engine.py - Professional Real-Time Anti-Spam Engine for Veyra
import time
import re
import json
import datetime
from collections import defaultdict

# In-memory sliding window buffers: (guild_id, user_id) -> list of timestamps
_user_message_timestamps = defaultdict(list)
_user_message_contents = defaultdict(list)
_cached_settings = {}
_cached_settings_time = {}

INVITE_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9]+', re.IGNORECASE)
LINK_REGEX = re.compile(r'https?://[^\s]+', re.IGNORECASE)
EMOJI_REGEX = re.compile(r'<a?:[a-zA-Z0-9_]+:[0-9]+>|[\U00010000-\U0010ffff]', re.UNICODE)

def get_antispam_settings(guild_id, get_db_func):
    """Fetch anti-spam settings with 15s in-memory TTL cache for high performance."""
    now = time.time()
    gid_str = str(guild_id)
    if gid_str in _cached_settings and (now - _cached_settings_time.get(gid_str, 0)) < 15:
        return _cached_settings[gid_str]
    
    defaults = {
        'enabled': 1,
        'max_messages': 5,
        'message_seconds': 5,
        'max_duplicates': 3,
        'max_mentions': 4,
        'block_invites': 1,
        'block_links': 0,
        'max_emojis': 8,
        'max_caps_percent': 70,
        'punishment': 'Timeout',
        'timeout_duration': 300,
        'log_channel': '',
        'ignored_roles': [],
        'ignored_channels': []
    }
    
    try:
        conn = get_db_func()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM antispam_settings WHERE guild_id = ?", (gid_str,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Row mapping based on columns
            # Column names: guild_id, enabled, max_messages, message_seconds, max_duplicates, max_mentions, block_invites, block_links, max_emojis, max_caps_percent, punishment, timeout_duration, log_channel, ignored_roles, ignored_channels
            if isinstance(row, dict):
                r = row
            else:
                cols = ['guild_id', 'enabled', 'max_messages', 'message_seconds', 'max_duplicates', 'max_mentions', 'block_invites', 'block_links', 'max_emojis', 'max_caps_percent', 'punishment', 'timeout_duration', 'log_channel', 'ignored_roles', 'ignored_channels']
                r = dict(zip(cols, row))
            
            ignored_roles = []
            ignored_channels = []
            try:
                ignored_roles = json.loads(r.get('ignored_roles') or '[]')
            except Exception:
                pass
            try:
                ignored_channels = json.loads(r.get('ignored_channels') or '[]')
            except Exception:
                pass
                
            defaults.update({
                'enabled': int(r.get('enabled', 1)),
                'max_messages': int(r.get('max_messages', 5)),
                'message_seconds': int(r.get('message_seconds', 5)),
                'max_duplicates': int(r.get('max_duplicates', 3)),
                'max_mentions': int(r.get('max_mentions', 4)),
                'block_invites': int(r.get('block_invites', 1)),
                'block_links': int(r.get('block_links', 0)),
                'max_emojis': int(r.get('max_emojis', 8)),
                'max_caps_percent': int(r.get('max_caps_percent', 70)),
                'punishment': str(r.get('punishment') or 'Timeout'),
                'timeout_duration': int(r.get('timeout_duration', 300)),
                'log_channel': str(r.get('log_channel') or ''),
                'ignored_roles': ignored_roles,
                'ignored_channels': ignored_channels
            })
    except Exception as e:
        print(f"[AntiSpam] Error loading settings for {guild_id}: {e}")
        
    _cached_settings[gid_str] = defaults
    _cached_settings_time[gid_str] = now
    return defaults


async def check_message_spam(message, bot, get_db_func, is_whitelisted_func):
    """
    Main Anti-Spam evaluator. Returns True if spam was detected and handled, False otherwise.
    """
    if not message.guild or message.author.bot:
        return False
        
    # Never punish server owner or admins
    if message.author.id == message.guild.owner_id or message.author.guild_permissions.administrator:
        return False
        
    guild_id = message.guild.id
    user_id = message.author.id
    channel_id = message.channel.id
    user_roles = [r.id for r in getattr(message.author, 'roles', [])]
    
    # Check Whitelist
    if is_whitelisted_func(guild_id, user_id, action_type="antispam", channel_id=channel_id, roles=user_roles):
        return False
        
    settings = get_antispam_settings(guild_id, get_db_func)
    if not settings.get('enabled', 1):
        return False
        
    # Check ignored channels or roles
    if str(channel_id) in settings.get('ignored_channels', []):
        return False
    if any(str(r_id) in settings.get('ignored_roles', []) for r_id in user_roles):
        return False
        
    now = time.time()
    key = (guild_id, user_id)
    content = message.content or ""
    
    # 1. Update sliding window timestamps
    timestamps = [t for t in _user_message_timestamps[key] if (now - t) < 60]
    timestamps.append(now)
    _user_message_timestamps[key] = timestamps
    
    # Update content history for duplicate detection
    history = [(c, t) for c, t in _user_message_contents[key] if (now - t) < 30]
    history.append((content.strip(), now))
    _user_message_contents[key] = history
    
    spam_reason = None
    
    # 2. Check: Message Flooding (e.g. > max_messages in message_seconds)
    max_msgs = settings.get('max_messages', 5)
    sec_window = settings.get('message_seconds', 5)
    recent_in_window = [t for t in timestamps if (now - t) <= sec_window]
    if len(recent_in_window) > max_msgs:
        spam_reason = f"Chat Flooding ({len(recent_in_window)} messages sent in {sec_window}s)"
        
    # 3. Check: Duplicate Message Spam
    if not spam_reason and len(content.strip()) > 3:
        max_dupes = settings.get('max_duplicates', 3)
        duplicate_count = sum(1 for c, t in history if c.lower() == content.strip().lower())
        if duplicate_count >= max_dupes:
            spam_reason = f"Duplicate Message Spam (Sent identical text {duplicate_count} times)"
            
    # 4. Check: Mass Mentions
    if not spam_reason:
        max_mentions = settings.get('max_mentions', 4)
        total_mentions = len(message.mentions) + len(message.role_mentions) + (1 if message.mention_everyone else 0)
        if total_mentions > max_mentions:
            spam_reason = f"Mass Mention Spam ({total_mentions} mentions exceed limit of {max_mentions})"
            
    # 5. Check: Unauthorized Discord Invites
    if not spam_reason and settings.get('block_invites', 1):
        if INVITE_REGEX.search(content):
            spam_reason = "Unauthorized Discord Invite Link"
            
    # 6. Check: External Links
    if not spam_reason and settings.get('block_links', 0):
        if LINK_REGEX.search(content):
            spam_reason = "Unauthorized External Link / URL"
            
    # 7. Check: Emoji Spam
    if not spam_reason:
        max_emojis = settings.get('max_emojis', 8)
        emojis = EMOJI_REGEX.findall(content)
        if len(emojis) > max_emojis:
            spam_reason = f"Emoji Spam ({len(emojis)} emojis exceed limit of {max_emojis})"
            
    # 8. Check: Excessive Caps Spam
    if not spam_reason and len(content) >= 12:
        caps_limit = settings.get('max_caps_percent', 70)
        alpha_chars = [c for c in content if c.isalpha()]
        if len(alpha_chars) >= 8:
            caps_count = sum(1 for c in alpha_chars if c.isupper())
            caps_percent = int((caps_count / len(alpha_chars)) * 100)
            if caps_percent >= caps_limit:
                spam_reason = f"Excessive Caps ({caps_percent}% uppercase exceeds {caps_limit}% limit)"
                
    if not spam_reason:
        return False
        
    # --- SPAM DETECTED: EXECUTE MITIGATION ---
    try:
        await message.delete()
    except Exception as del_err:
        print(f"[AntiSpam] Failed to delete message: {del_err}")
        
    punishment = settings.get('punishment', 'Timeout')
    timeout_duration = settings.get('timeout_duration', 300)
    action_taken = "Message Deleted"
    
    try:
        member = message.author
        if punishment == 'Timeout':
            until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=timeout_duration)
            await member.timeout(until, reason=f"VEYRA Anti-Spam: {spam_reason}")
            action_taken = f"Muted / Timed Out for {timeout_duration // 60}m"
        elif punishment == 'Kick':
            await member.kick(reason=f"VEYRA Anti-Spam: {spam_reason}")
            action_taken = "Kicked from Server"
        elif punishment == 'Ban':
            await member.ban(reason=f"VEYRA Anti-Spam: {spam_reason}", delete_message_days=1)
            action_taken = "Banned from Server"
        elif punishment == 'Delete':
            action_taken = "Message Deleted"
    except Exception as punish_err:
        print(f"[AntiSpam] Mitigation action error ({punishment}): {punish_err}")
        
    # Send quick ephemeral warning in chat
    try:
        warn_msg = await message.channel.send(
            f"🛡️ **Anti-Spam Triggered** | {message.author.mention} was penalized (`{action_taken}`). Reason: *{spam_reason}*",
            delete_after=6
        )
    except Exception:
        pass
        
    # Send DM to offending user
    try:
        dm_embed = {
            "title": "🛡️ Veyra Anti-Spam Violation",
            "description": f"Your message in **{message.guild.name}** was flagged and removed by Veyra Anti-Spam.\n\n"
                           f"**Violation:** `{spam_reason}`\n"
                           f"**Penalty Applied:** `{action_taken}`\n\n"
                           f"*Please follow server chat rules to maintain good standing.*",
            "color": 0xEF4444
        }
        import discord
        emb = discord.Embed.from_dict(dm_embed)
        await message.author.send(embed=emb)
    except Exception:
        pass
        
    # Dispatch rich embed to configured log channel or security logs
    log_ch_id = settings.get('log_channel')
    target_log_channel = None
    if log_ch_id and str(log_ch_id).isdigit():
        target_log_channel = message.guild.get_channel(int(log_ch_id))
        
    if not target_log_channel:
        # Fallback to guild security logs channel from guild_settings
        try:
            conn = get_db_func()
            c = conn.cursor()
            c.execute("SELECT security_logs FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
            r = c.fetchone()
            conn.close()
            if r and r[0] and str(r[0]).isdigit():
                target_log_channel = message.guild.get_channel(int(r[0]))
        except Exception:
            pass
            
    if target_log_channel:
        try:
            import discord
            log_embed = discord.Embed(
                title="🛡️ Anti-Spam Violation Intercepted",
                description=f"A spam outburst was neutralized in real time in {message.channel.mention}.",
                color=0xEF4444,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
            log_embed.add_field(name="Action Taken", value=f"`{action_taken}`", inline=True)
            log_embed.add_field(name="Trigger Reason", value=f"`{spam_reason}`", inline=False)
            
            preview = (content[:300] + "...") if len(content) > 300 else (content or "*[Embed or Media]*")
            log_embed.add_field(name="Message Preview", value=f"```{preview}```", inline=False)
            log_embed.set_footer(text="Veyra Security Engine", icon_url=bot.user.display_avatar.url if bot.user else None)
            
            await target_log_channel.send(embed=log_embed)
        except Exception as log_err:
            print(f"[AntiSpam] Error dispatching log embed: {log_err}")
            
    # Record to Database audit_logs table
    try:
        conn = get_db_func()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_logs (guild_id, "user", action, details, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            str(guild_id),
            f"{message.author.name}#{message.author.discriminator}" if hasattr(message.author, 'discriminator') and message.author.discriminator != '0' else message.author.name,
            "Anti-Spam Filter",
            f"Action: {action_taken} | Reason: {spam_reason} in #{message.channel.name}"
        ))
        conn.commit()
        conn.close()
    except Exception as db_log_err:
        print(f"[AntiSpam] Error saving audit log: {db_log_err}")
        
    return True
