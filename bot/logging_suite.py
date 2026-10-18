import os
import re
import json
import asyncio
import datetime
import typing
import discord
from discord.ext import commands
from discord import app_commands

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db

COLOR_CREATE = discord.Color.from_rgb(34, 197, 94)    # Green 0x22c55e
COLOR_DELETE = discord.Color.from_rgb(239, 68, 68)    # Red 0xef4444
COLOR_UPDATE = discord.Color.from_rgb(59, 130, 246)    # Blue 0x3b82f6
COLOR_EDIT   = discord.Color.from_rgb(245, 158, 11)    # Yellow/Amber 0xf59e0b
COLOR_PURPLE = discord.Color.from_rgb(168, 85, 247)   # Purple 0xa855f7

LOG_CHANNEL_KEYS = {
    "server_logs": ["server-logs", "server-log", "server_logs", "serverlogs"],
    "bot_logs": ["bot-logs", "bot-log", "bot_logs", "botlogs"],
    "channel_logs": ["channel-logs", "channel-log", "channel_logs", "channels-logs", "channellogs"],
    "emoji_logs": ["emoji-logs", "emoji-log", "emojis-logs", "emojilogs"],
    "invites_logs": ["invites-logs", "invite-logs", "invites-log", "invitelogs", "inviteslogs"],
    "invite_tracker_logs": ["invite-tracker-logs", "invite-tracker-log", "invitetracker-logs", "invite-tracker", "invitetracker"],
    "message_logs": ["message-logs", "messages-logs", "message-log", "messagelogs"],
    "moderation_logs": ["moderation-logs", "mod-logs", "modlogs", "moderationlogs"],
    "roles_logs": ["roles-logs", "role-logs", "roles-log", "rolelogs"],
    "voice_logs": ["voice-logs", "vc-logs", "voicelogs", "vclogs"],
    "ticket_opened_logs": ["ticket-opened-logs", "ticket-opened", "tickets-opened-logs", "ticket-create-logs"],
    "ticket_closed_logs": ["ticket-closed-logs", "ticket-closed", "tickets-closed-logs", "ticket-close-logs"],
    "server_reports": ["server-reports", "server-report", "reports"]
}

def normalize_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', str(s or '')).lower()

def get_actor_footer(user: typing.Optional[typing.Union[discord.User, discord.Member]], action_time: typing.Optional[datetime.datetime] = None) -> tuple[str, typing.Optional[str]]:
    now = action_time or datetime.datetime.now(datetime.timezone.utc)
    time_str = now.strftime("%m/%d/%y, %I:%M %p")
    if user:
        tag = f"@{user.name}"
        avatar_url = user.display_avatar.url if user.display_avatar else None
        return f"{tag} • {time_str}", avatar_url
    return f"{time_str}", None

def resolve_guild_log_channel(guild: discord.Guild, log_type: str) -> typing.Optional[discord.TextChannel]:
    if not guild:
        return None
    col = log_type.lower().strip()
    if not col.endswith("_logs") and not col.endswith("_reports"):
        if col in ("invitetracker", "invite_tracker"):
            col = "invite_tracker_logs"
        elif col == "server":
            col = "server_logs"
        elif col == "bot":
            col = "bot_logs"
        elif col == "channel":
            col = "channel_logs"
        elif col == "emoji":
            col = "emoji_logs"
        elif col == "invites":
            col = "invites_logs"
        elif col == "message":
            col = "message_logs"
        elif col == "moderation":
            col = "moderation_logs"
        elif col == "roles":
            col = "roles_logs"
        elif col == "voice":
            col = "voice_logs"
        elif col in ("ticket_opened", "ticketopened"):
            col = "ticket_opened_logs"
        elif col in ("ticket_closed", "ticketclosed"):
            col = "ticket_closed_logs"
        elif col == "reports":
            col = "server_reports"
        else:
            col = f"{col}_logs"

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"SELECT {col} FROM guild_logging_channels WHERE guild_id = ?", (str(guild.id),))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            target_str = str(row[0]).strip()
            if target_str.isdigit():
                target_ch = guild.get_channel(int(target_str))
                if target_ch and isinstance(target_ch, discord.TextChannel):
                    return target_ch
            clean_name = target_str.replace('#', '').strip().lower()
            for ch in guild.text_channels:
                if ch.name.lower() == clean_name:
                    return ch
    except Exception:
        pass

    # Auto-resolve by normalized name matching against existing server channels
    aliases = LOG_CHANNEL_KEYS.get(col, [col.replace('_', '-')])
    for ch in guild.text_channels:
        norm_ch = normalize_name(ch.name)
        for alias in aliases:
            norm_alias = normalize_name(alias)
            if norm_alias == norm_ch or norm_alias in norm_ch or norm_ch in norm_alias:
                return ch

    # Fallback for moderation_logs to guild_settings
    if col == "moderation_logs":
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT moderation_logs, security_logs FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
            row = cur.fetchone()
            conn.close()
            if row:
                for c_id in (row[0], row[1]):
                    if c_id and str(c_id).isdigit():
                        ch = guild.get_channel(int(c_id))
                        if ch:
                            return ch
        except Exception:
            pass

    return None

async def dispatch_log_embed(guild: discord.Guild, log_type: str, embed: discord.Embed):
    ch = resolve_guild_log_channel(guild, log_type)
    if ch:
        try:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages and perms.embed_links:
                await ch.send(embed=embed)
                return True
        except Exception as e:
            print(f"[LoggingSuite] Error sending {log_type} to #{ch.name}: {e}")
    return False

async def fetch_audit_actor(guild: discord.Guild, action: discord.AuditLogAction, target_id: typing.Optional[int] = None) -> typing.Optional[discord.User]:
    try:
        if not guild.me.guild_permissions.view_audit_log:
            return None
        async for entry in guild.audit_logs(limit=3, action=action):
            if target_id is None or (entry.target and getattr(entry.target, 'id', None) == target_id):
                return entry.user
    except Exception:
        pass
    return None

def update_db_log_channel(guild_id: int, column_name: str, channel_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO guild_logging_channels (guild_id) VALUES (?)", (str(guild_id),))
    cur.execute(f"UPDATE guild_logging_channels SET {column_name} = ? WHERE guild_id = ?", (str(channel_id), str(guild_id)))
    conn.commit()
    conn.close()


# ── LOGGING SUITE COG ─────────────────────────────────────────────────────────

class LoggingSuiteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. Channel Lifecycle
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.channel_create, channel.id)
        footer_text, footer_icon = get_actor_footer(actor)

        if isinstance(channel, discord.CategoryChannel):
            embed = discord.Embed(title="Category channel created", color=COLOR_CREATE)
            embed.description = (
                f"**Name:** {channel.name} (`# {channel.name}`)\n"
                f"**ID:** `{channel.id}`\n"
                f"**Position:** `{channel.position}`"
            )
        elif isinstance(channel, discord.VoiceChannel):
            embed = discord.Embed(title="Voice channel created", color=COLOR_CREATE)
            cat_name = channel.category.name if channel.category else "None"
            embed.description = (
                f"**Name:** 🔊 {channel.name} ({channel.mention})\n"
                f"**ID:** `{channel.id}`\n"
                f"**Category:** `{cat_name}`\n"
                f"**Bitrate:** `{int(channel.bitrate / 1000)}kbps`"
            )
        else:
            embed = discord.Embed(title="Text channel created", color=COLOR_CREATE)
            cat_name = channel.category.name if channel.category else "None"
            embed.description = (
                f"**Name:** {channel.name} ({channel.mention})\n"
                f"**ID:** `{channel.id}`\n"
                f"**Category:** `{cat_name}`"
            )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "channel_logs", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.channel_delete, channel.id)
        footer_text, footer_icon = get_actor_footer(actor)

        type_name = "Category channel" if isinstance(channel, discord.CategoryChannel) else ("Voice channel" if isinstance(channel, discord.VoiceChannel) else "Text channel")
        embed = discord.Embed(title=f"{type_name} deleted", color=COLOR_DELETE)
        embed.description = (
            f"**Name:** {channel.name}\n"
            f"**ID:** `{channel.id}`"
        )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "channel_logs", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = after.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.channel_update, after.id)
        footer_text, footer_icon = get_actor_footer(actor)
        is_category = isinstance(after, discord.CategoryChannel)
        prefix = "Category channel" if is_category else "Text channel"

        # Name Update
        if before.name != after.name:
            embed = discord.Embed(title=f"{prefix} name updated", color=COLOR_UPDATE)
            mention_str = f"({after.mention})" if hasattr(after, 'mention') else f"(# {after.name})"
            embed.description = (
                f"**Name:** {after.name} {mention_str}\n"
                f"**ID:** `{after.id}`\n"
                f"**Previous name:** `{before.name}`"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "channel_logs", embed)

        # Topic Update
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            embed = discord.Embed(title="Text channel topic updated", color=COLOR_UPDATE)
            embed.description = (
                f"**Name:** {after.name} ({after.mention})\n"
                f"**ID:** `{after.id}`\n"
                f"**Before:** ```\n{before.topic or 'None'}\n```\n"
                f"**After:** ```\n{after.topic or 'None'}\n```"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "channel_logs", embed)

        # Permissions Update
        if before.overwrites != after.overwrites:
            added_lines = []
            removed_lines = []
            all_targets = set(before.overwrites.keys()).union(set(after.overwrites.keys()))
            for t in all_targets:
                target_name = getattr(t, 'name', str(t))
                b_ow = before.overwrites.get(t, discord.PermissionOverwrite())
                a_ow = after.overwrites.get(t, discord.PermissionOverwrite())
                for perm, val in a_ow:
                    b_val = getattr(b_ow, perm)
                    if val != b_val:
                        p_name = perm.replace('_', ' ').title().replace(' ', '')
                        if val is True:
                            added_lines.append(f"{target_name}: {p_name}")
                        elif val is False:
                            removed_lines.append(f"{target_name}: {p_name}")
                        elif val is None:
                            removed_lines.append(f"{target_name}: {p_name} (Neutral)")

            if added_lines or removed_lines:
                embed = discord.Embed(title=f"{prefix} permissions updated", color=COLOR_UPDATE)
                mention_str = f"({after.mention})" if hasattr(after, 'mention') else f"(# {after.name})"
                desc = f"**Name:** {after.name} {mention_str}\n**ID:** `{after.id}`\n"
                if added_lines:
                    desc += f"**Added:** `{', '.join(added_lines[:6])}`\n"
                if removed_lines:
                    desc += f"**Removed:** `{', '.join(removed_lines[:6])}`\n"
                embed.description = desc.strip()
                embed.set_footer(text=footer_text, icon_url=footer_icon)
                await dispatch_log_embed(guild, "channel_logs", embed)

    # 2. Role Lifecycle & Updates
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.role_create, role.id)
        footer_text, footer_icon = get_actor_footer(actor)

        embed = discord.Embed(title="Role created", color=COLOR_CREATE)
        embed.description = (
            f"**Role:** {role.name} ({role.mention})\n"
            f"**ID:** `{role.id}`\n"
            f"**Color:** `#{role.color.value:06x}`\n"
            f"**Hoisted:** `{'Yes' if role.hoist else 'No'}`\n"
            f"**Mentionable:** `{'Yes' if role.mentionable else 'No'}`"
        )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "roles_logs", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.role_delete, role.id)
        footer_text, footer_icon = get_actor_footer(actor)

        embed = discord.Embed(title="Role deleted", color=COLOR_DELETE)
        embed.description = (
            f"**Role:** {role.name}\n"
            f"**ID:** `{role.id}`"
        )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "roles_logs", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = after.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.role_update, after.id)
        footer_text, footer_icon = get_actor_footer(actor)

        if before.hoist != after.hoist:
            embed = discord.Embed(title="Role hoist update", color=COLOR_UPDATE)
            embed.description = (
                f"**Role:** {after.name} ({after.mention})\n"
                f"**ID:** `{after.id}`\n"
                f"**Hoisted:** {'✅' if after.hoist else '❌'}"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "roles_logs", embed)

        if before.mentionable != after.mentionable:
            embed = discord.Embed(title="Role mentionable update", color=COLOR_UPDATE)
            embed.description = (
                f"**Role:** {after.name} ({after.mention})\n"
                f"**ID:** `{after.id}`\n"
                f"**Mentionable:** {'✅' if after.mentionable else '❌'}"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "roles_logs", embed)

        if before.name != after.name:
            embed = discord.Embed(title="Role name update", color=COLOR_UPDATE)
            embed.description = (
                f"**Role:** {after.name} ({after.mention})\n"
                f"**ID:** `{after.id}`\n"
                f"**Previous name:** `{before.name}`"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "roles_logs", embed)

        if before.color != after.color:
            embed = discord.Embed(title="Role color update", color=COLOR_UPDATE)
            embed.description = (
                f"**Role:** {after.name} ({after.mention})\n"
                f"**ID:** `{after.id}`\n"
                f"**Before:** `#{before.color.value:06x}`\n"
                f"**After:** `#{after.color.value:06x}`"
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "roles_logs", embed)

    # 3. Member Updates (Nickname, Roles, Join, Leave)
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        # Nickname Update
        if before.display_name != after.display_name:
            actor = await fetch_audit_actor(guild, discord.AuditLogAction.member_update, after.id)
            footer_text, footer_icon = get_actor_footer(actor or after)
            user_tag = f"{after.name}#{after.discriminator}" if after.discriminator != "0" else after.name
            embed = discord.Embed(title="User nickname update", color=COLOR_EDIT)
            embed.description = (
                f"**User:** {user_tag} ({after.mention})\n"
                f"**Nickname:** {after.display_name}\n"
                f"**Previous nickname:** {before.display_name}"
            )
            if after.display_avatar:
                embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "server_logs", embed)

        # Role Add / Remove
        if before.roles != after.roles:
            actor = await fetch_audit_actor(guild, discord.AuditLogAction.member_role_update, after.id)
            footer_text, footer_icon = get_actor_footer(actor)
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            for r in added:
                embed = discord.Embed(title="Role assigned to member", color=COLOR_CREATE)
                embed.description = (
                    f"**User:** {after.name} ({after.mention})\n"
                    f"**Role:** {r.name} ({r.mention})\n"
                    f"**Role ID:** `{r.id}`"
                )
                embed.set_footer(text=footer_text, icon_url=footer_icon)
                await dispatch_log_embed(guild, "roles_logs", embed)

            for r in removed:
                embed = discord.Embed(title="Role removed from member", color=COLOR_DELETE)
                embed.description = (
                    f"**User:** {after.name} ({after.mention})\n"
                    f"**Role:** {r.name} ({r.mention})\n"
                    f"**Role ID:** `{r.id}`"
                )
                embed.set_footer(text=footer_text, icon_url=footer_icon)
                await dispatch_log_embed(guild, "roles_logs", embed)

    # 4. Message Edit & Delete
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or after.author.bot:
            return
        if before.content == after.content:
            return

        guild = after.guild
        embed = discord.Embed(title="Message edited", color=COLOR_EDIT)
        user_tag = f"{after.author.name}#{after.author.discriminator}" if after.author.discriminator != "0" else after.author.name
        
        embed.description = (
            f"**Channel:** 💬 {after.channel.name} ({after.channel.mention})\n"
            f"**Message ID:** `{after.id}`\n"
            f"**Message author:** {user_tag} ({after.author.mention})\n"
            f"**Message created:** <t:{int(after.created_at.timestamp())}:R>\n\n"
            f"**Before**\n```\n{before.content[:1000] if before.content else 'None'}\n```\n"
            f"**After**\n```\n{after.content[:1000] if after.content else 'None'}\n```"
        )
        footer_text, footer_icon = get_actor_footer(after.author)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "message_logs", embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.message_delete, message.author.id)
        user_tag = f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator != "0" else message.author.name

        embed = discord.Embed(title="Message deleted", color=COLOR_DELETE)
        embed.description = (
            f"**Channel:** 💬 {message.channel.name} ({message.channel.mention})\n"
            f"**Message ID:** `{message.id}`\n"
            f"**Message author:** {user_tag} ({message.author.mention})\n"
            f"**Message created:** <t:{int(message.created_at.timestamp())}:R>\n\n"
            f"**Message**\n```\n{message.content[:1500] if message.content else 'No text content / embed only'}\n```"
        )
        footer_text, footer_icon = get_actor_footer(actor or message.author)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "message_logs", embed)

    # 5. Voice Lifecycle (Join, Leave, Move)
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        user_tag = f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name
        now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%m/%d/%y, %I:%M %p")

        # Joined Voice
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="User joined channel", color=COLOR_CREATE)
            users_count = len(after.channel.members)
            limit_str = str(after.channel.user_limit) if after.channel.user_limit else "∞"
            embed.description = (
                f"**User:** {user_tag} ({member.mention})\n"
                f"**Channel:** 🔊 {after.channel.name}\n"
                f"**Users:** `{users_count}/{limit_str}`"
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"@{member.name} • {now_ts}", icon_url=member.display_avatar.url if member.display_avatar else None)
            await dispatch_log_embed(guild, "voice_logs", embed)

        # Left Voice
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(title="User left channel", color=COLOR_DELETE)
            users_count = len(before.channel.members)
            limit_str = str(before.channel.user_limit) if before.channel.user_limit else "∞"
            embed.description = (
                f"**User:** {user_tag} ({member.mention})\n"
                f"**Channel:** 🔊 {before.channel.name}\n"
                f"**Users:** `{users_count}/{limit_str}`"
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"@{member.name} • {now_ts}", icon_url=member.display_avatar.url if member.display_avatar else None)
            await dispatch_log_embed(guild, "voice_logs", embed)

        # Moved Voice Channel
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed = discord.Embed(title="User moved channel", color=COLOR_UPDATE)
            users_count = len(after.channel.members)
            limit_str = str(after.channel.user_limit) if after.channel.user_limit else "∞"
            embed.description = (
                f"**User:** {user_tag} ({member.mention})\n"
                f"**From:** 🔊 {before.channel.name}\n"
                f"**To:** 🔊 {after.channel.name}\n"
                f"**Users:** `{users_count}/{limit_str}`"
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"@{member.name} • {now_ts}", icon_url=member.display_avatar.url if member.display_avatar else None)
            await dispatch_log_embed(guild, "voice_logs", embed)

    # 6. Discord Invites Lifecycle (Separate from Invite-Tracker!)
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        guild = invite.guild
        if not guild:
            return
        footer_text, footer_icon = get_actor_footer(invite.inviter)

        embed = discord.Embed(title="Invite created", color=COLOR_CREATE)
        channel_str = f"{invite.channel.name} ({invite.channel.mention})" if hasattr(invite.channel, 'mention') else f"{invite.channel.name}"
        max_uses_str = str(invite.max_uses) if invite.max_uses else "∞"
        expires_str = f"in {int(invite.max_age / 86400)} days" if invite.max_age else "Never"

        embed.description = (
            f"**Code:** `{invite.code}`\n"
            f"**Channel:** {channel_str}\n"
            f"**Expires:** `{expires_str}`\n"
            f"**Max uses:** `{max_uses_str}`"
        )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "invites_logs", embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        guild = invite.guild
        if not guild:
            return
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.invite_delete)
        footer_text, footer_icon = get_actor_footer(actor)

        embed = discord.Embed(title="Invite deleted", color=COLOR_DELETE)
        ch_name = getattr(invite.channel, 'name', 'Unknown')
        embed.description = (
            f"**Code:** `{invite.code}`\n"
            f"**Channel:** `{ch_name}`"
        )
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "invites_logs", embed)

    # 7. Emojis & Stickers Lifecycle
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: typing.Sequence[discord.Emoji], after: typing.Sequence[discord.Emoji]):
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]

        for emoji in added:
            actor = await fetch_audit_actor(guild, discord.AuditLogAction.emoji_create, emoji.id)
            footer_text, footer_icon = get_actor_footer(actor)
            embed = discord.Embed(title="Emoji created", color=COLOR_CREATE)
            embed.description = (
                f"**Name:** `{emoji.name}`\n"
                f"**ID:** `{emoji.id}`\n"
                f"**Animated:** {'✅' if emoji.animated else '❌'}"
            )
            embed.set_thumbnail(url=emoji.url)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "emoji_logs", embed)

        for emoji in removed:
            actor = await fetch_audit_actor(guild, discord.AuditLogAction.emoji_delete, emoji.id)
            footer_text, footer_icon = get_actor_footer(actor)
            embed = discord.Embed(title="Emoji deleted", color=COLOR_DELETE)
            embed.description = (
                f"**Name:** `{emoji.name}`\n"
                f"**ID:** `{emoji.id}`\n"
                f"**Animated:** {'✅' if emoji.animated else '❌'}\n"
                f"**Created:** <t:{int(emoji.created_at.timestamp())}:R>"
            )
            embed.set_thumbnail(url=emoji.url)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "emoji_logs", embed)

    # 8. Webhooks & Server Updates
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.webhook_create)
        if actor:
            embed = discord.Embed(title="Webhook created", color=COLOR_CREATE)
            embed.description = (
                f"**Channel:** {channel.name} ({channel.mention})\n"
                f"**Type:** `INCOMING`\n"
                f"**Reason:** Webhook created for logging / integrations."
            )
            footer_text, footer_icon = get_actor_footer(actor)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "server_logs", embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        guild = after
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.guild_update)
        footer_text, footer_icon = get_actor_footer(actor)

        if before.mfa_level != after.mfa_level:
            embed = discord.Embed(title="Multi factor authentication level updated", color=COLOR_UPDATE)
            embed.description = f"**Status:** Level changed from `{before.mfa_level}` to `{after.mfa_level}`."
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "server_logs", embed)

        if before.name != after.name:
            embed = discord.Embed(title="Server name updated", color=COLOR_UPDATE)
            embed.description = f"**Before:** `{before.name}`\n**After:** `{after.name}`"
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "server_logs", embed)

        if before.icon != after.icon:
            embed = discord.Embed(title="Server icon updated", color=COLOR_UPDATE)
            if after.icon:
                embed.set_thumbnail(url=after.icon.url)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            await dispatch_log_embed(guild, "server_logs", embed)

    # 9. Moderation Logs (Ban, Unban)
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: typing.Union[discord.User, discord.Member]):
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.ban, user.id)
        footer_text, footer_icon = get_actor_footer(actor)
        user_tag = f"{user.name}#{user.discriminator}" if getattr(user, 'discriminator', '0') != "0" else user.name

        embed = discord.Embed(title="Member Banned", color=COLOR_DELETE)
        embed.description = (
            f"**Member:** {user_tag} ({user.mention})\n"
            f"**ID:** `{user.id}`\n"
            f"**Banned By:** {actor.mention if actor else 'Unknown'}"
        )
        if hasattr(user, 'display_avatar') and user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "moderation_logs", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        actor = await fetch_audit_actor(guild, discord.AuditLogAction.unban, user.id)
        footer_text, footer_icon = get_actor_footer(actor)
        user_tag = f"{user.name}#{user.discriminator}" if getattr(user, 'discriminator', '0') != "0" else user.name

        embed = discord.Embed(title="Member Unbanned", color=COLOR_CREATE)
        embed.description = (
            f"**Member:** {user_tag} ({user.mention})\n"
            f"**ID:** `{user.id}`\n"
            f"**Revoked By:** {actor.mention if actor else 'Unknown'}"
        )
        if hasattr(user, 'display_avatar') and user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        await dispatch_log_embed(guild, "moderation_logs", embed)


# ── SETUP LOGS SLASH GROUP WITH ALL SUBCOMMANDS ───────────────────────────────

class SetupLogsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="logs", description="Configure server-wide real-time audit logging suite")

    async def _set_log_channel(self, interaction: discord.Interaction, col_name: str, friendly_name: str, channel: discord.TextChannel):
        update_db_log_channel(interaction.guild_id, col_name, channel.id)
        embed = discord.Embed(
            title=f"✅ Log Channel Mapped: {friendly_name}",
            description=f"All **{friendly_name}** events will now dispatch real-time to {channel.mention} (`{channel.id}`).",
            color=COLOR_CREATE
        )
        embed.set_footer(text="Powered by VEYRA Development™")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="auto", description="Automatically create all [ 🛠️ Server-Logs ] & [ 🛠️ Logs ] channels and categories")
    @app_commands.checks.has_permissions(administrator=True)
    async def auto_setup_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        cat_server = discord.utils.find(lambda c: normalize_name(c.name) in ("serverlogs", "serverlog"), guild.categories)
        if not cat_server:
            cat_server = await guild.create_category(name="『 🛠 』Server-Logs", reason="Auto-created by VEYRA Logs Suite")

        cat_logs = discord.utils.find(lambda c: normalize_name(c.name) in ("logs", "log"), guild.categories)
        if not cat_logs:
            cat_logs = await guild.create_category(name="[ 🛠️ Logs ]", reason="Auto-created by VEYRA Logs Suite")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True)
        }

        server_log_channels = [
            ("Server-Logs", "server_logs"),
            ("Bot-Logs", "bot_logs"),
            ("Channel-Logs", "channel_logs"),
            ("Emoji-Logs", "emoji_logs"),
            ("Invites-Logs", "invites_logs"),
            ("Message-Logs", "message_logs"),
            ("Moderation-Logs", "moderation_logs"),
            ("Roles-Logs", "roles_logs"),
            ("Voice-Logs", "voice_logs"),
        ]

        main_log_channels = [
            ("Invite-Tracker-Logs", "invite_tracker_logs"),
            ("Ticket-Opened-Logs", "ticket_opened_logs"),
            ("Ticket-Closed-Logs", "ticket_closed_logs"),
            ("Server-Reports", "server_reports")
        ]

        mapping = {}

        for ch_base, db_key in server_log_channels:
            existing = discord.utils.find(lambda c: normalize_name(c.name) == normalize_name(ch_base), guild.text_channels)
            if not existing:
                ch_obj = await guild.create_text_channel(name=f"🛠・{ch_base}", category=cat_server, overwrites=overwrites, reason="VEYRA Logging Suite Setup")
            else:
                ch_obj = existing
            mapping[db_key] = str(ch_obj.id)

        for ch_base, db_key in main_log_channels:
            existing = discord.utils.find(lambda c: normalize_name(c.name) == normalize_name(ch_base), guild.text_channels)
            if not existing:
                prefix_icon = "📊・" if "report" in ch_base.lower() else "🛠・"
                ch_obj = await guild.create_text_channel(name=f"{prefix_icon}{ch_base}", category=cat_logs, overwrites=overwrites, reason="VEYRA Logging Suite Setup")
            else:
                ch_obj = existing
            mapping[db_key] = str(ch_obj.id)

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO guild_logging_channels (
                guild_id, server_logs, channel_logs, roles_logs, message_logs, moderation_logs,
                bot_logs, emoji_logs, voice_logs, invites_logs, invite_tracker_logs,
                ticket_opened_logs, ticket_closed_logs, server_reports
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(guild.id),
            mapping.get("server_logs"),
            mapping.get("channel_logs"),
            mapping.get("roles_logs"),
            mapping.get("message_logs"),
            mapping.get("moderation_logs"),
            mapping.get("bot_logs"),
            mapping.get("emoji_logs"),
            mapping.get("voice_logs"),
            mapping.get("invites_logs"),
            mapping.get("invite_tracker_logs"),
            mapping.get("ticket_opened_logs"),
            mapping.get("ticket_closed_logs"),
            mapping.get("server_reports")
        ))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ VEYRA Real-Time Logging Suite Configured",
            description=(
                f"Successfully initialized all dedicated categories and audit channels:\n\n"
                f"**『 🛠 』Server-Logs**\n"
                f"• Server Logs: <#{mapping['server_logs']}>\n"
                f"• Channel Logs: <#{mapping['channel_logs']}>\n"
                f"• Role Logs: <#{mapping['roles_logs']}>\n"
                f"• Message Logs: <#{mapping['message_logs']}>\n"
                f"• Moderation Logs: <#{mapping['moderation_logs']}>\n"
                f"• Bot Logs: <#{mapping['bot_logs']}>\n"
                f"• Emoji Logs: <#{mapping['emoji_logs']}>\n"
                f"• Voice Logs: <#{mapping['voice_logs']}>\n"
                f"• Invites Logs: <#{mapping['invites_logs']}>\n\n"
                f"**[ 🛠️ Logs ]**\n"
                f"• Invite Tracker: <#{mapping['invite_tracker_logs']}>\n"
                f"• Ticket Opened: <#{mapping['ticket_opened_logs']}>\n"
                f"• Ticket Closed: <#{mapping['ticket_closed_logs']}>\n"
                f"• Server Reports: <#{mapping['server_reports']}>"
            ),
            color=COLOR_CREATE
        )
        embed.set_footer(text="Powered by VEYRA Development™ | Real-Time Logging Engine")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="server", description="Set dedicated Server-Logs channel (Nicknames, Webhooks, MFA)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "server_logs", "Server Logs", channel)

    @app_commands.command(name="channel", description="Set dedicated Channel-Logs channel (Create, Delete, Perms)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "channel_logs", "Channel Logs", channel)

    @app_commands.command(name="roles", description="Set dedicated Roles-Logs channel (Create, Delete, Hoist, Perms)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_roles_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "roles_logs", "Roles Logs", channel)

    @app_commands.command(name="message", description="Set dedicated Message-Logs channel (Edit, Delete, Purge)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_message_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "message_logs", "Message Logs", channel)

    @app_commands.command(name="moderation", description="Set dedicated Moderation-Logs channel (Ban, Unban, Kick, Mute)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_moderation_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "moderation_logs", "Moderation Logs", channel)

    @app_commands.command(name="bot", description="Set dedicated Bot-Logs channel (Bot Add, Remove, Permissions)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_bot_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "bot_logs", "Bot Logs", channel)

    @app_commands.command(name="emoji", description="Set dedicated Emoji-Logs channel (Emoji/Sticker Create, Delete)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_emoji_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "emoji_logs", "Emoji Logs", channel)

    @app_commands.command(name="voice", description="Set dedicated Voice-Logs channel (Voice Join, Leave, Move)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_voice_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "voice_logs", "Voice Logs", channel)

    @app_commands.command(name="invites", description="Set dedicated Invites-Logs channel (Discord Invite Create & Delete)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_invites_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "invites_logs", "Invites Logs", channel)

    @app_commands.command(name="invitetracker", description="Set dedicated Invite-Tracker-Logs channel (Real-time Join/Leave)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_invitetracker_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._set_log_channel(interaction, "invite_tracker_logs", "Invite Tracker Logs", channel)

    @app_commands.command(name="view", description="View all currently mapped log channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        lines = []
        for key in LOG_CHANNEL_KEYS.keys():
            ch = resolve_guild_log_channel(guild, key)
            friendly = key.replace('_', ' ').title()
            ch_str = ch.mention if ch else "`Not Mapped`"
            lines.append(f"• **{friendly}:** {ch_str}")

        embed = discord.Embed(
            title="📋 Real-Time Server Logging Channels",
            description="\n".join(lines),
            color=COLOR_PURPLE
        )
        embed.set_footer(text="To configure channels, run /setup logs <type> <#channel> or /setup logs auto")
        await interaction.response.send_message(embed=embed)


class SetupInviteSlashGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="invite", description="Configure real-time member invite tracker")

    @app_commands.command(name="channel", description="Set the real-time invite tracker announcement channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_ch = channel or interaction.channel
        guild = interaction.guild

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM invitetracker_settings WHERE guild_id = ?", (str(guild.id),))
        if cur.fetchone():
            cur.execute("UPDATE invitetracker_settings SET channel = ?, enabled = 1 WHERE guild_id = ?", (str(target_ch.id), str(guild.id)))
        else:
            cur.execute("""
                INSERT INTO invitetracker_settings (guild_id, enabled, channel, color, title, description, footer)
                VALUES (?, 1, ?, '#a855f7', '', '', 'VEYRA Invite Tracker')
            """, (str(guild.id), str(target_ch.id)))

        cur.execute("INSERT OR IGNORE INTO guild_logging_channels (guild_id) VALUES (?)", (str(guild.id),))
        cur.execute("UPDATE guild_logging_channels SET invite_tracker_logs = ? WHERE guild_id = ?", (str(target_ch.id), str(guild.id)))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Invite Tracker Channel Configured",
            description=f"Real-time invite tracking join announcements will now be sent to {target_ch.mention}.",
            color=COLOR_CREATE
        )
        embed.set_footer(text="Powered by VEYRA Development™")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle", description="Enable or disable real-time invite tracking")
    @app_commands.choices(status=[
        app_commands.Choice(name="Enable Real-Time Invite Tracking", value=1),
        app_commands.Choice(name="Disable Real-Time Invite Tracking", value=0)
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_cmd(self, interaction: discord.Interaction, status: int):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE invitetracker_settings SET enabled = ? WHERE guild_id = ?", (status, str(interaction.guild_id)))
        conn.commit()
        conn.close()
        state_str = "Enabled 🟢" if status == 1 else "Disabled 🔴"
        await interaction.response.send_message(f"✅ Real-Time Invite Tracking is now **{state_str}**.")

    @app_commands.command(name="test", description="Send a test invite tracking announcement")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        ch = resolve_guild_log_channel(guild, "invite_tracker_logs") or interaction.channel
        test_msg = f"{interaction.user.mention} has been invited by {interaction.client.user.name} and has now 1 invites."
        await ch.send(content=test_msg)
        await interaction.response.send_message(f"✅ Real-time test invite notification sent to {ch.mention}!", ephemeral=True)


def register_logging_suite(bot: commands.Bot, setup_group: app_commands.Group):
    cog = LoggingSuiteCog(bot)
    bot.add_cog(cog)

    setup_logs = SetupLogsGroup()
    setup_invite = SetupInviteSlashGroup()

    try:
        setup_group.add_command(setup_logs)
    except Exception as e:
        print(f"Notice adding setup logs: {e}")

    try:
        setup_group.add_command(setup_invite)
    except Exception as e:
        print(f"Notice adding setup invite: {e}")

    # Prefix Commands for setup logs
    @bot.group(name="logs", invoke_without_command=True)
    async def logs_prefix_group(ctx):
        await ctx.send("Usage: `,logs auto`, `,logs <server|bot|channel|emoji|invites|message|moderation|roles|voice> <#channel>`, or `,logs view`")

    @logs_prefix_group.command(name="auto")
    @commands.has_permissions(administrator=True)
    async def p_logs_auto(ctx):
        class FakeInter:
            def __init__(self, c):
                self.guild = c.guild
                self.guild_id = c.guild.id
                self.user = c.author
                self.client = c.bot
                self.response = self
            async def defer(self): pass
            async def followup_send(self, *a, **kw): await ctx.send(*a, **kw)
            async def send_message(self, *a, **kw): await ctx.send(*a, **kw)
        fake = FakeInter(ctx)
        fake.followup = fake
        fake.followup.send = fake.send_message
        await setup_logs.auto_setup_cmd.callback(setup_logs, fake)

    def make_log_prefix_handler(col_key, friendly):
        async def handler(ctx, channel: discord.TextChannel = None):
            target_ch = channel or ctx.channel
            update_db_log_channel(ctx.guild.id, col_key, target_ch.id)
            await ctx.send(f"✅ Mapped **{friendly}** to {target_ch.mention} successfully!")
        return handler

    types = [
        ("server", "server_logs", "Server Logs"),
        ("bot", "bot_logs", "Bot Logs"),
        ("channel", "channel_logs", "Channel Logs"),
        ("emoji", "emoji_logs", "Emoji Logs"),
        ("invites", "invites_logs", "Invites Logs"),
        ("message", "message_logs", "Message Logs"),
        ("moderation", "moderation_logs", "Moderation Logs"),
        ("roles", "roles_logs", "Roles Logs"),
        ("voice", "voice_logs", "Voice Logs"),
        ("invitetracker", "invite_tracker_logs", "Invite Tracker Logs"),
    ]

    for sub_name, col_key, friendly in types:
        cmd = commands.Command(make_log_prefix_handler(col_key, friendly), name=sub_name)
        cmd.add_check(commands.has_permissions(administrator=True).predicate)
        logs_prefix_group.add_command(cmd)

    @logs_prefix_group.command(name="view")
    @commands.has_permissions(administrator=True)
    async def p_logs_view(ctx):
        lines = []
        for key in LOG_CHANNEL_KEYS.keys():
            ch = resolve_guild_log_channel(ctx.guild, key)
            friendly = key.replace('_', ' ').title()
            ch_str = ch.mention if ch else "`Not Mapped`"
            lines.append(f"• **{friendly}:** {ch_str}")

        embed = discord.Embed(
            title="📋 Real-Time Server Logging Channels",
            description="\n".join(lines),
            color=COLOR_PURPLE
        )
        embed.set_footer(text="To configure channels, run ,logs <type> <#channel> or ,logs auto")
        await ctx.send(embed=embed)

    print("✅ VEYRA Real-Time Logging Suite & Invite Tracking Engine registered.")
