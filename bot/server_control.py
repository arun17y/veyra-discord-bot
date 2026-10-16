# server_control.py - Production-Grade Advanced Server Control System for VEYRA Bot
import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import json
import asyncio
import io
import os
import typing
from datetime import datetime, timezone, timedelta

DB_PATH_VEYRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/VEYRA.db"))

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db


# ── 1. AUDIT LOG HELPER ───────────────────────────────────────────────────────
async def dispatch_discord_log(guild, log_type, title, description, color=0xa855f7, fields=None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT mod_log_channel, sec_log_channel, audit_log_channel FROM server_central_settings WHERE guild_id = ?", (str(guild.id),))
        row = cursor.fetchone()
        
        target_ch_id = None
        if row:
            if log_type == 'security' and row['sec_log_channel']:
                target_ch_id = row['sec_log_channel']
            elif log_type == 'audit' and row['audit_log_channel']:
                target_ch_id = row['audit_log_channel']
            elif row['mod_log_channel']:
                target_ch_id = row['mod_log_channel']

        if not target_ch_id:
            cursor.execute("SELECT moderation_logs, security_logs FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
            gs_row = cursor.fetchone()
            if gs_row:
                target_ch_id = gs_row['security_logs'] if log_type == 'security' else gs_row['moderation_logs']

        conn.close()

        if target_ch_id and target_ch_id not in ('none', 'Select option', ''):
            channel = guild.get_channel(int(target_ch_id))
            if channel:
                embed = discord.Embed(
                    title=f"🛡️ {title}",
                    description=description,
                    color=discord.Color(color)
                )
                if fields:
                    for fname, fval, inline in fields:
                        embed.add_field(name=fname, value=fval, inline=inline)
                embed.set_footer(text=f"VEYRA Audit Control • Guild ID: {guild.id}")
                embed.timestamp = datetime.now(timezone.utc)
                await channel.send(embed=embed)
    except Exception as e:
        print(f"[AUDIT LOG ERROR] {e}")

# ── 2. PERMISSION MATRIX AUTHORIZATION CHECK ─────────────────────────────────
async def is_authorized_manager(interaction: discord.Interaction, command_name: str = "general") -> bool:
    guild = interaction.guild
    user = interaction.user
    if not guild or not user:
        return True

    # 1. Server Owner & Devs always allowed
    if user.id == guild.owner_id or user.id in (1256986886631854080, 1538041381132697610):
        return True

    # 2. Server Administrator permission
    if isinstance(user, discord.Member) and user.guild_permissions.administrator:
        return True

    conn = get_db()
    cursor = conn.cursor()

    # 3. Bot Manager Role Check
    cursor.execute("SELECT bot_manager_role_id FROM server_central_settings WHERE guild_id = ?", (str(guild.id),))
    sc_row = cursor.fetchone()
    if sc_row and sc_row['bot_manager_role_id']:
        mgr_role = guild.get_role(int(sc_row['bot_manager_role_id']))
        if mgr_role and mgr_role in user.roles:
            conn.close()
            return True

    # 4. Custom Authorized Bot Roles Check
    cursor.execute("SELECT role_id FROM authorized_bot_roles WHERE guild_id = ?", (str(guild.id),))
    auth_roles = [r['role_id'] for r in cursor.fetchall()]
    for r_id in auth_roles:
        r = guild.get_role(int(r_id))
        if r and r in user.roles:
            conn.close()
            return True

    # 5. Command Specific Access Matrix
    cursor.execute("SELECT allowed_roles FROM command_access_matrix WHERE guild_id = ? AND command_name = ?", (str(guild.id), command_name))
    cm_row = cursor.fetchone()
    conn.close()

    if cm_row and cm_row['allowed_roles']:
        try:
            allowed = json.loads(cm_row['allowed_roles'])
            for r_id in allowed:
                r = guild.get_role(int(r_id))
                if r and r in user.roles:
                    return True
        except Exception:
            pass

    embed = discord.Embed(
        title="❌ Permission Denied",
        description=f"You do not have authorization to use `/ {command_name}`.\nRequired access: **Server Owner, Administrator, or Bot Manager Role**.",
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_footer(text="VEYRA Security Matrix")
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)
    return False


# ── 3. DESTRUCTIVE ACTION CONFIRMATION VIEW ──────────────────────────────────
class DestructiveActionConfirmView(discord.ui.View):
    def __init__(self, author: discord.User, action_type: str, target_name: str, callback_coro):
        super().__init__(timeout=60)
        self.author = author
        self.action_type = action_type
        self.target_name = target_name
        self.callback_coro = callback_coro
        self.confirmed = False

    @discord.ui.button(label="Confirm Action", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Only the command invoker can confirm this action.", ephemeral=True)
        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.callback_coro(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Only the command invoker can cancel this action.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🚫 Action `{self.action_type}` on **{self.target_name}** cancelled.", embed=None, view=self)


# ── 4. 24/7 VOICE SYSTEM ─────────────────────────────────────────────────────
def resolve_member_voice_channel(guild: discord.Guild, user_id: int):
    if not guild:
        return None
    # 1. Guild voice states cache if available
    voice_states = getattr(guild, 'voice_states', getattr(guild, '_voice_states', None))
    if voice_states and isinstance(voice_states, dict):
        vs = voice_states.get(user_id)
        if vs and getattr(vs, 'channel', None):
            return vs.channel
    # 2. Guild get_member voice attribute
    member = guild.get_member(user_id)
    if member and member.voice and member.voice.channel:
        return member.voice.channel
    # 3. Direct inspection across all voice channels
    for vc in getattr(guild, 'voice_channels', []):
        if any(m.id == user_id for m in vc.members):
            return vc
    # 4. Direct inspection across all stage channels
    for sc in getattr(guild, 'stage_channels', []):
        if any(m.id == user_id for m in sc.members):
            return sc
    return None

class Voice247Group(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="247", description="24/7 Persistent Voice Channel System")
        self.bot = bot

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        guild = interaction.guild
        if not guild:
            return
        target_vc = resolve_member_voice_channel(guild, interaction.user.id)
        if target_vc:
            try:
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

                await dispatch_discord_log(guild, "audit", "24/7 Voice Connection Enabled", f"Bot locked 24/7 to voice channel {target_vc.mention}.", 0x22c55e)
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
                print(f"[VOICE247 on_error fallback connect] {ex}")

        embed = discord.Embed(
            title="⚠️ Invalid Parameter",
            description="Please join a voice channel first, or select a valid voice channel from Discord's list!",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="join", description="Connect bot 24/7 to your current voice channel")
    @app_commands.describe(channel="Voice channel to join (optional, defaults to your current voice channel)")
    async def join_cmd(self, interaction: discord.Interaction, channel: typing.Optional[discord.VoiceChannel] = None):
        await interaction.response.defer()
        if not await is_authorized_manager(interaction, "247"):
            return
        guild = interaction.guild

        target_vc = channel or resolve_member_voice_channel(guild, interaction.user.id)

        if not target_vc:
            embed = discord.Embed(
                title="⚠️ Voice Channel Required",
                description="Please join a voice channel first or specify a valid voice channel!",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.set_footer(text="Powered by VEYRA")
            return await interaction.followup.send(embed=embed)

        # Real Discord Voice Connection
        try:
            vc = guild.voice_client
            if vc:
                if vc.channel.id == target_vc.id and vc.is_connected():
                    pass
                else:
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

            await dispatch_discord_log(guild, "audit", "24/7 Voice Connection Enabled", f"Bot locked 24/7 to voice channel {target_vc.mention}.", 0x22c55e)
            embed = discord.Embed(
                title="🟢 24/7 Voice System Active",
                description=f"Connected to {target_vc.mention}.\nConnection saved and will automatically restore on bot restart.",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.set_footer(text="Powered by VEYRA")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to connect to voice channel: `{e}`")

    @app_commands.command(name="leave", description="Disconnect bot and disable 24/7 voice mode")
    async def leave_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await is_authorized_manager(interaction, "247"):
            return
        guild = interaction.guild

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE voice_247_settings SET enabled = 0 WHERE guild_id = ?", (str(guild.id),))
        conn.commit()
        conn.close()

        vc = guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect(force=True)

        await dispatch_discord_log(guild, "audit", "24/7 Voice Connection Disabled", "Bot disconnected from voice channel.", 0xef4444)
        embed = discord.Embed(
            title="🔴 24/7 Voice System Disabled",
            description="Bot disconnected and 24/7 persistence turned off.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set", description="Set default 24/7 voice channel for this server")
    @app_commands.describe(channel="Voice channel to set (optional, defaults to your current voice channel)")
    async def set_cmd(self, interaction: discord.Interaction, channel: typing.Optional[discord.VoiceChannel] = None):
        await interaction.response.defer()
        if not await is_authorized_manager(interaction, "247"):
            return
        guild = interaction.guild

        target_vc = channel or resolve_member_voice_channel(guild, interaction.user.id)

        if not target_vc:
            embed = discord.Embed(
                title="⚠️ Voice Channel Required",
                description="Please join a voice channel first or specify a valid voice channel!",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.set_footer(text="Powered by VEYRA")
            return await interaction.followup.send(embed=embed)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO voice_247_settings (guild_id, channel_id, enabled, last_reconnect, updated_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
        """, (str(guild.id), str(target_vc.id), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        vc = guild.voice_client
        try:
            if vc:
                if vc.channel.id != target_vc.id and vc.is_connected():
                    await vc.move_to(target_vc)
            else:
                await target_vc.connect(reconnect=True, timeout=30.0)
        except Exception as e:
            print(f"Voice connect error: {e}")

        embed = discord.Embed(
            title="✅ 24/7 Voice Channel Configured",
            description=f"Set to {target_vc.mention}.\nBot will auto-reconnect permanently.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="status", description="Show current 24/7 voice connection status")
    async def status_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voice_247_settings WHERE guild_id = ?", (str(guild.id),))
        row = cursor.fetchone()
        conn.close()

        vc = guild.voice_client
        is_connected = vc and vc.is_connected()
        vc_name = vc.channel.name if is_connected else "Not Connected"

        enabled = row['enabled'] if row else 0
        target_ch_id = row['channel_id'] if row else None
        target_ch = guild.get_channel(int(target_ch_id)) if target_ch_id else None

        embed = discord.Embed(
            title="🎙️ 24/7 Voice System Status",
            color=discord.Color.from_rgb(34, 197, 94) if is_connected else discord.Color.from_rgb(239, 68, 68)
        )
        embed.add_field(name="24/7 Enabled", value="🟢 Yes" if enabled == 1 else "🔴 No", inline=True)
        embed.add_field(name="Live Connection", value=f"🟢 `{vc_name}`" if is_connected else "🔴 Offline", inline=True)
        embed.add_field(name="Configured Channel", value=target_ch.mention if target_ch else "`None`", inline=True)
        embed.set_footer(text=f"Server: {guild.name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reconnect", description="Force immediate 24/7 voice channel reconnect")
    async def reconnect_cmd(self, interaction: discord.Interaction):
        if not await is_authorized_manager(interaction, "247"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voice_247_settings WHERE guild_id = ? AND enabled = 1", (str(guild.id),))
        row = cursor.fetchone()
        conn.close()

        if not row or not row['channel_id']:
            return await interaction.followup.send("❌ No 24/7 voice channel enabled for this server. Use `/247 set` first.")

        target_ch = guild.get_channel(int(row['channel_id']))
        if not target_ch:
            return await interaction.followup.send("❌ Saved voice channel no longer exists.")

        try:
            vc = guild.voice_client
            if vc:
                await vc.disconnect(force=True)
                await asyncio.sleep(1)
            await target_ch.connect(reconnect=True, timeout=30.0)
            await interaction.followup.send(f"🔄 Reconnected 24/7 voice client to {target_ch.mention} successfully!")
        except Exception as e:
            await interaction.followup.send(f"❌ Reconnect failed: `{e}`")


# ── 5. INTERACTIVE CHANNEL PERMISSION EDITOR ─────────────────────────────────
class ChannelPermissionEditorView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel, target: discord.abc.Snowflake, author: discord.User):
        super().__init__(timeout=180)
        self.channel = channel
        self.target = target
        self.author = author

        # Fetch current overwrites
        current_ow = channel.overwrites_for(target)
        self.states = {
            "view_channel": current_ow.view_channel,
            "send_messages": current_ow.send_messages if hasattr(current_ow, 'send_messages') else current_ow.connect,
            "read_message_history": current_ow.read_message_history if hasattr(current_ow, 'read_message_history') else current_ow.speak,
            "attach_files": current_ow.attach_files if hasattr(current_ow, 'attach_files') else None,
            "embed_links": current_ow.embed_links if hasattr(current_ow, 'embed_links') else None,
            "add_reactions": current_ow.add_reactions if hasattr(current_ow, 'add_reactions') else None,
            "manage_channels": current_ow.manage_channels
        }

    def _render_state_str(self, val):
        if val is True:
            return "✅ ALLOW"
        elif val is False:
            return "❌ DENY"
        return "⚪ NEUTRAL"

    def build_embed(self):
        target_name = getattr(self.target, 'name', str(self.target))
        embed = discord.Embed(
            title=f"⚙️ Channel Permissions Editor — #{self.channel.name}",
            description=f"Target: **{target_name}** (`{self.target.id}`)\nClick buttons to cycle permissions between `ALLOW`, `DENY`, and `NEUTRAL`.",
            color=discord.Color.from_rgb(124, 58, 237)
        )
        for perm, val in self.states.items():
            if val is not None or perm in ("view_channel", "send_messages"):
                lbl = perm.replace('_', ' ').title()
                embed.add_field(name=lbl, value=self._render_state_str(val), inline=True)
        embed.set_footer(text="Click SAVE to apply real updates to Discord API.")
        return embed

    @discord.ui.button(label="👁 View Channel", style=discord.ButtonStyle.primary, row=0)
    async def toggle_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        cur = self.states["view_channel"]
        self.states["view_channel"] = False if cur is True else (None if cur is False else True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="💬 Send / Connect", style=discord.ButtonStyle.primary, row=0)
    async def toggle_send(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        cur = self.states["send_messages"]
        self.states["send_messages"] = False if cur is True else (None if cur is False else True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="📖 Read History / Speak", style=discord.ButtonStyle.primary, row=0)
    async def toggle_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        cur = self.states["read_message_history"]
        self.states["read_message_history"] = False if cur is True else (None if cur is False else True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="📎 Attach Files", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_attach(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        cur = self.states["attach_files"]
        self.states["attach_files"] = False if cur is True else (None if cur is False else True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔗 Embed Links", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        cur = self.states["embed_links"]
        self.states["embed_links"] = False if cur is True else (None if cur is False else True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="💾 SAVE CHANGES", style=discord.ButtonStyle.success, row=2)
    async def save_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()

        try:
            ow = self.channel.overwrites_for(self.target)
            ow.view_channel = self.states["view_channel"]
            if hasattr(ow, 'send_messages'):
                ow.send_messages = self.states["send_messages"]
                ow.read_message_history = self.states["read_message_history"]
                ow.attach_files = self.states["attach_files"]
                ow.embed_links = self.states["embed_links"]
            elif hasattr(ow, 'connect'):
                ow.connect = self.states["send_messages"]
                ow.speak = self.states["read_message_history"]

            await self.channel.set_permissions(self.target, overwrite=ow)
            await dispatch_discord_log(interaction.guild, "audit", "Channel Permissions Updated", f"Permissions for **{self.target}** in {self.channel.mention} updated by {self.author.mention}.", 0x22c55e)
            
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(content=f"✅ Permissions for **{self.target}** in {self.channel.mention} successfully saved to Discord!", embed=None, view=self)
        except discord.Forbidden:
            await interaction.followup.send("❌ Discord API Error: Bot lacks `Manage Channels` or `Manage Permissions` in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update permissions: `{e}`", ephemeral=True)

    @discord.ui.button(label="🔄 RESET TO NEUTRAL", style=discord.ButtonStyle.danger, row=2)
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()
        try:
            await self.channel.set_permissions(self.target, overwrite=None)
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(content=f"✅ Permission overwrites for **{self.target}** in {self.channel.mention} reset to neutral.", embed=None, view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ Reset failed: `{e}`", ephemeral=True)


# ── 6. ADVANCED CHANNEL MANAGER GROUP ────────────────────────────────────────
class ChannelManagerGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="channel", description="Advanced Server Channel Management Suite")
        self.bot = bot

    @app_commands.command(name="create", description="Create a new channel")
    async def create_cmd(self, interaction: discord.Interaction, name: str, channel_type: str = "text", category: discord.CategoryChannel = None, topic: str = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        try:
            if channel_type.lower() == "voice":
                ch = await guild.create_voice_channel(name=name, category=category)
            elif channel_type.lower() == "category":
                ch = await guild.create_category(name=name)
            else:
                ch = await guild.create_text_channel(name=name, category=category, topic=topic)

            await dispatch_discord_log(guild, "audit", "Channel Created", f"Created {channel_type} channel {ch.mention} (`{ch.id}`) by {interaction.user.mention}.", 0x22c55e)
            await interaction.followup.send(f"✅ Created channel {ch.mention} successfully!")
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot lacks permission to create channels.")
        except Exception as e:
            await interaction.followup.send(f"❌ Channel creation failed: `{e}`")

    @app_commands.command(name="delete", description="Delete an existing channel")
    async def delete_cmd(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        if not await is_authorized_manager(interaction, "channel"):
            return

        async def _do_delete(inter):
            try:
                ch_name = channel.name
                await channel.delete()
                await dispatch_discord_log(inter.guild, "audit", "Channel Deleted", f"Channel `{ch_name}` deleted by {inter.user.mention}.", 0xef4444)
                await inter.followup.send(f"🗑️ Channel `{ch_name}` permanently deleted.")
            except Exception as e:
                await inter.followup.send(f"❌ Failed to delete channel: `{e}`")

        view = DestructiveActionConfirmView(interaction.user, "Delete Channel", channel.name, _do_delete)
        embed = discord.Embed(
            title="⚠️ Confirm Channel Deletion",
            description=f"Are you sure you want to permanently delete **#{channel.name}** (`{channel.id}`)?\nThis action cannot be undone!",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="permissions", description="Open interactive permission overwrites editor")
    async def permissions_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None, member: discord.Member = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        target_ch = channel or interaction.channel
        target = role or member or interaction.guild.default_role

        view = ChannelPermissionEditorView(target_ch, target, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(name="lock", description="Lock a text channel (deny Send Messages for @everyone)")
    async def lock_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        target_ch = channel or interaction.channel
        guild = interaction.guild

        try:
            ow = target_ch.overwrites_for(guild.default_role)
            ow.send_messages = False
            await target_ch.set_permissions(guild.default_role, overwrite=ow)
            await dispatch_discord_log(guild, "audit", "Channel Locked", f"{target_ch.mention} locked by {interaction.user.mention}.", 0xef4444)
            await interaction.followup.send(f"🔒 {target_ch.mention} locked successfully!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to lock channel: `{e}`")

    @app_commands.command(name="unlock", description="Unlock a text channel (allow Send Messages for @everyone)")
    async def unlock_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        target_ch = channel or interaction.channel
        guild = interaction.guild

        try:
            ow = target_ch.overwrites_for(guild.default_role)
            ow.send_messages = None
            await target_ch.set_permissions(guild.default_role, overwrite=ow)
            await dispatch_discord_log(guild, "audit", "Channel Unlocked", f"{target_ch.mention} unlocked by {interaction.user.mention}.", 0x22c55e)
            await interaction.followup.send(f"🔓 {target_ch.mention} unlocked successfully!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unlock channel: `{e}`")

    @app_commands.command(name="slowmode", description="Set slowmode cooldown for a channel")
    async def slowmode_cmd(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        target_ch = channel or interaction.channel
        try:
            await target_ch.edit(slowmode_delay=seconds)
            await interaction.followup.send(f"⏱️ Slowmode for {target_ch.mention} set to `{seconds}` seconds.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set slowmode: `{e}`")

    @app_commands.command(name="rename", description="Rename a channel")
    async def rename_cmd(self, interaction: discord.Interaction, new_name: str, channel: discord.abc.GuildChannel = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        target_ch = channel or interaction.channel
        try:
            old_name = target_ch.name
            await target_ch.edit(name=new_name)
            await interaction.followup.send(f"✏️ Channel `{old_name}` renamed to `{new_name}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Rename failed: `{e}`")

    @app_commands.command(name="topic", description="Set topic of a text channel")
    async def topic_cmd(self, interaction: discord.Interaction, topic: str, channel: discord.TextChannel = None):
        if not await is_authorized_manager(interaction, "channel"):
            return
        await interaction.response.defer()
        target_ch = channel or interaction.channel
        try:
            await target_ch.edit(topic=topic)
            await interaction.followup.send(f"📝 Topic for {target_ch.mention} updated.")
        except Exception as e:
            await interaction.followup.send(f"❌ Topic update failed: `{e}`")

    @app_commands.command(name="view", description="View detailed information about a channel")
    async def view_cmd(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel = None):
        target_ch = channel or interaction.channel
        embed = discord.Embed(
            title=f"📊 Channel Info — #{target_ch.name}",
            color=discord.Color.from_rgb(124, 58, 237)
        )
        embed.add_field(name="Channel ID", value=f"`{target_ch.id}`", inline=True)
        embed.add_field(name="Type", value=f"`{target_ch.type}`", inline=True)
        embed.add_field(name="Category", value=target_ch.category.name if target_ch.category else "`None`", inline=True)
        embed.add_field(name="Position", value=f"`{target_ch.position}`", inline=True)
        embed.set_footer(text=f"Guild: {interaction.guild.name}")
        await interaction.response.send_message(embed=embed)


# ── 7. CATEGORY MANAGER GROUP ────────────────────────────────────────────────
class CategoryManagerGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="category", description="Category Permission & Layout Management Suite")
        self.bot = bot

    @app_commands.command(name="create", description="Create a new category channel")
    async def create_cmd(self, interaction: discord.Interaction, name: str):
        if not await is_authorized_manager(interaction, "category"):
            return
        await interaction.response.defer()
        try:
            cat = await interaction.guild.create_category(name=name)
            await interaction.followup.send(f"📁 Category **{cat.name}** (`{cat.id}`) created!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create category: `{e}`")

    @app_commands.command(name="lock", description="Lock all channels under a category")
    async def lock_cmd(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not await is_authorized_manager(interaction, "category"):
            return
        await interaction.response.defer()
        guild = interaction.guild
        try:
            count = 0
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = False
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    count += 1
            await interaction.followup.send(f"🔒 Locked `{count}` text channels inside category **{category.name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to lock category: `{e}`")

    @app_commands.command(name="unlock", description="Unlock all channels under a category")
    async def unlock_cmd(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not await is_authorized_manager(interaction, "category"):
            return
        await interaction.response.defer()
        guild = interaction.guild
        try:
            count = 0
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    count += 1
            await interaction.followup.send(f"🔓 Unlocked `{count}` text channels inside category **{category.name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unlock category: `{e}`")

    @app_commands.command(name="sync", description="Sync channel permissions with category")
    async def sync_cmd(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not await is_authorized_manager(interaction, "category"):
            return
        await interaction.response.defer()
        try:
            for ch in category.channels:
                await ch.edit(sync_permissions=True)
            await interaction.followup.send(f"🔄 Synced permissions for `{len(category.channels)}` channels with **{category.name}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Permission sync failed: `{e}`")


# ── 8. ROLE MANAGER GROUP ────────────────────────────────────────────────────
class RoleManagerGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="role", description="Advanced Server Role Management Suite")
        self.bot = bot
        self.active_tasks = {}

    @app_commands.command(name="create", description="Create a new server role")
    async def create_cmd(self, interaction: discord.Interaction, name: str, color_hex: str = "#99aab5", hoist: bool = False, mentionable: bool = False):
        if not await is_authorized_manager(interaction, "role"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        try:
            clean_hex = color_hex.lstrip("#")
            color_val = discord.Color(int(clean_hex, 16))
        except ValueError:
            color_val = discord.Color.default()

        try:
            role = await guild.create_role(name=name, color=color_val, hoist=hoist, mentionable=mentionable)
            await dispatch_discord_log(guild, "audit", "Role Created", f"Role {role.mention} (`{role.id}`) created by {interaction.user.mention}.", 0x22c55e)
            await interaction.followup.send(f"🎭 Created role {role.mention} successfully!")
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot lacks permission to manage roles.")
        except Exception as e:
            await interaction.followup.send(f"❌ Role creation failed: `{e}`")

    @app_commands.command(name="delete", description="Delete an existing server role")
    async def delete_cmd(self, interaction: discord.Interaction, role: discord.Role):
        if not await is_authorized_manager(interaction, "role"):
            return

        guild = interaction.guild
        if role >= guild.me.top_role:
            return await interaction.response.send_message("❌ Cannot delete a role equal to or higher than the bot's highest role.", ephemeral=True)
        if role >= interaction.user.top_role and interaction.user.id != guild.owner_id:
            return await interaction.response.send_message("❌ Cannot delete a role equal to or higher than your top role.", ephemeral=True)

        async def _do_delete_role(inter):
            try:
                r_name = role.name
                await role.delete()
                await dispatch_discord_log(inter.guild, "audit", "Role Deleted", f"Role `{r_name}` deleted by {inter.user.mention}.", 0xef4444)
                await inter.followup.send(f"🗑️ Role `{r_name}` permanently deleted.")
            except Exception as e:
                await inter.followup.send(f"❌ Failed to delete role: `{e}`")

        view = DestructiveActionConfirmView(interaction.user, "Delete Role", role.name, _do_delete_role)
        embed = discord.Embed(
            title="⚠️ Confirm Role Deletion",
            description=f"Are you sure you want to delete role **@{role.name}** (`{role.id}`)?",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="add", description="Add a role to a member")
    async def add_cmd(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if not await is_authorized_manager(interaction, "role"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        if role >= guild.me.top_role:
            return await interaction.followup.send("❌ Cannot assign a role equal to or higher than the bot's top role.")
        try:
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Added {role.mention} to {member.mention}.")
        except Exception as e:
            await interaction.followup.send(f"❌ Role assignment failed: `{e}`")

    @app_commands.command(name="remove", description="Remove a role from a member")
    async def remove_cmd(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if not await is_authorized_manager(interaction, "role"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        if role >= guild.me.top_role:
            return await interaction.followup.send("❌ Cannot remove a role equal to or higher than the bot's top role.")
        try:
            await member.remove_roles(role)
            await interaction.followup.send(f"✅ Removed {role.mention} from {member.mention}.")
        except Exception as e:
            await interaction.followup.send(f"❌ Role removal failed: `{e}`")

    @app_commands.command(name="all", description="Assign or remove a role to all human members (excludes bots & apps)")
    @app_commands.describe(role="The role to assign/remove", action="Action to perform (Default: Add)")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add (Assign role to all human members)", value="add"),
        app_commands.Choice(name="Remove (Remove role from all human members)", value="remove")
    ])
    async def all_cmd(self, interaction: discord.Interaction, role: discord.Role, action: app_commands.Choice[str] = None):
        if not await is_authorized_manager(interaction, "role"):
            return
        await interaction.response.defer()
        guild = interaction.guild
        act = action.value if action else "add"
        act_name = "added" if act == "add" else "removed"

        if role >= guild.me.top_role:
            return await interaction.followup.send(f"❌ Role {role.mention} is higher than or equal to my highest role ({guild.me.top_role.mention}). Drag my bot role above {role.name} in Server Settings -> Roles.")

        if not guild.chunked:
            try:
                await guild.chunk()
            except Exception:
                pass

        human_members = [m for m in guild.members if not m.bot]
        total_humans = len(human_members)
        if total_humans == 0:
            return await interaction.followup.send("⚠️ No human members found in this server.")

        self.active_tasks[guild.id] = True
        prog_msg = await interaction.followup.send(f"⏳ **Bulk Role ({act.upper()}):** Processing **{total_humans}** human members for role {role.mention} (excluding bots)...\nUse `/role cancel` or `.role cancel` to stop.")

        count = 0
        failed = 0
        last_edit = asyncio.get_event_loop().time()

        for idx, member in enumerate(human_members, start=1):
            if not self.active_tasks.get(guild.id):
                return await interaction.channel.send("⏹️ Bulk role task was cancelled.")

            try:
                if act == "add" and role not in member.roles:
                    await member.add_roles(role, reason=f"Bulk /role all executed by {interaction.user}")
                    count += 1
                elif act == "remove" and role in member.roles:
                    await member.remove_roles(role, reason=f"Bulk /role all executed by {interaction.user}")
                    count += 1
            except discord.HTTPException as http_ex:
                if http_ex.status == 429:
                    retry_after = getattr(http_ex, 'retry_after', 2.0) or 2.0
                    await asyncio.sleep(float(retry_after) + 0.5)
                    try:
                        if act == "add" and role not in member.roles:
                            await member.add_roles(role)
                            count += 1
                        elif act == "remove" and role in member.roles:
                            await member.remove_roles(role)
                            count += 1
                    except Exception:
                        failed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            now = asyncio.get_event_loop().time()
            if now - last_edit > 4 or idx == total_humans:
                last_edit = now
                try:
                    await prog_msg.edit(content=f"⏳ **Bulk Role ({act.upper()}):** Processing... `{count}/{total_humans}` members updated (Processed: {idx}/{total_humans})")
                except Exception:
                    pass

            await asyncio.sleep(0.35)

        self.active_tasks.pop(guild.id, None)
        embed = discord.Embed(
            title="✅ Bulk Role Operation Completed",
            description=f"Role {role.mention} was successfully **{act_name}** for **{count}** human members.\n(Excluded all bots and applications. Failed: `{failed}`).",
            color=discord.Color.from_rgb(16, 185, 129)
        )
        embed.set_footer(text="Powered by VEYRA 2.0 Management Suite")
        await interaction.channel.send(embed=embed)

    @app_commands.command(name="bots", description="Toggle a role for all bots")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def bots_cmd(self, interaction: discord.Interaction, role: discord.Role, action: app_commands.Choice[str]):
        if not await is_authorized_manager(interaction, "role"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        self.active_tasks[guild.id] = True
        count = 0
        for member in guild.members:
            if not self.active_tasks.get(guild.id):
                return await interaction.followup.send("⏹️ Role bulk task was cancelled.")
            if member.bot:
                try:
                    if action.value == 'add' and role not in member.roles:
                        await member.add_roles(role)
                        count += 1
                    elif action.value == 'remove' and role in member.roles:
                        await member.remove_roles(role)
                        count += 1
                except Exception:
                    pass
        self.active_tasks.pop(guild.id, None)
        await interaction.followup.send(f"✅ Successfully {action.name.lower()}ed role {role.name} for **{count}** bots.")

    @app_commands.command(name="cancel", description="Cancel current role assignment")
    async def cancel_cmd(self, interaction: discord.Interaction):
        if interaction.guild.id in self.active_tasks:
            self.active_tasks[interaction.guild.id] = False
            await interaction.response.send_message("✅ Cancel signal sent for active bulk role tasks.")
        else:
            await interaction.response.send_message("ℹ️ No active bulk role tasks running on this server.", ephemeral=True)


# ── 9. EMERGENCY SERVER LOCKDOWN SYSTEM ─────────────────────────────────────
class ServerControlGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="servermgmt", description="Server Administrative & Lockdown System")
        self.bot = bot

    @app_commands.command(name="lockdown", description="Emergency Lockdown: lock all public channels with state preservation")
    async def lockdown_cmd(self, interaction: discord.Interaction):
        if not await is_authorized_manager(interaction, "lockdown"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        conn = get_db()
        cursor = conn.cursor()

        locked_count = 0
        for ch in guild.text_channels:
            ow = ch.overwrites_for(guild.default_role)
            # Store existing overwrite in DB if not already present
            prev_ow_dict = {"send_messages": ow.send_messages, "view_channel": ow.view_channel}
            cursor.execute("""
                INSERT OR REPLACE INTO lockdown_states (guild_id, channel_id, previous_overwrite_json)
                VALUES (?, ?, ?)
            """, (str(guild.id), str(ch.id), json.dumps(prev_ow_dict)))

            ow.send_messages = False
            try:
                await ch.set_permissions(guild.default_role, overwrite=ow)
                locked_count += 1
            except Exception:
                pass

        conn.commit()
        conn.close()

        await dispatch_discord_log(guild, "security", "EMERGENCY SERVER LOCKDOWN ACTIVATED", f"Locked down `{locked_count}` text channels by {interaction.user.mention}.", 0xef4444)
        await interaction.followup.send(f"🚨 **EMERGENCY SERVER LOCKDOWN ACTIVATED**\nLocked `{locked_count}` text channels. Previous overwrite states saved in VEYRA.db.")

    @app_commands.command(name="unlock", description="Emergency Unlock: restore exact channel overwrites before lockdown")
    async def unlock_cmd(self, interaction: discord.Interaction):
        if not await is_authorized_manager(interaction, "lockdown"):
            return
        await interaction.response.defer()
        guild = interaction.guild

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lockdown_states WHERE guild_id = ?", (str(guild.id),))
        rows = cursor.fetchall()

        unlocked_count = 0
        for r in rows:
            ch = guild.get_channel(int(r['channel_id']))
            if ch and isinstance(ch, discord.TextChannel):
                try:
                    prev_ow = json.loads(r['previous_overwrite_json'])
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = prev_ow.get("send_messages")
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    unlocked_count += 1
                except Exception:
                    pass

        cursor.execute("DELETE FROM lockdown_states WHERE guild_id = ?", (str(guild.id),))
        conn.commit()
        conn.close()

        await dispatch_discord_log(guild, "security", "SERVER LOCKDOWN LIFTED", f"Restored previous channel states across `{unlocked_count}` channels.", 0x22c55e)
        await interaction.followup.send(f"🔓 **SERVER LOCKDOWN LIFTED**\nRestored original permissions across `{unlocked_count}` text channels.")


# ── 10. SERVER BACKUP & CONFIG EXPORT ────────────────────────────────────────
class ServerBackupGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="backup", description="Server Configuration Backup & Restore Engine")
        self.bot = bot

    @app_commands.command(name="create", description="Create a complete backup of server roles and channel structures")
    async def create_cmd(self, interaction: discord.Interaction):
        if not await is_authorized_manager(interaction, "backup"):
            return
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        backup_data = {
            "guild_id": str(guild.id),
            "guild_name": guild.name,
            "roles": [{"name": r.name, "color": r.color.value, "hoist": r.hoist, "mentionable": r.mentionable, "permissions": r.permissions.value} for r in guild.roles if not r.is_default() and not r.managed],
            "categories": [{"name": c.name, "position": c.position} for c in guild.categories],
            "text_channels": [{"name": ch.name, "topic": ch.topic, "category": ch.category.name if ch.category else None} for ch in guild.text_channels],
            "voice_channels": [{"name": ch.name, "category": ch.category.name if ch.category else None} for ch in guild.voice_channels]
        }

        backup_id = f"bak_{guild.id}_{int(datetime.now(timezone.utc).timestamp())}"
        json_str = json.dumps(backup_data)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO server_backups (backup_id, guild_id, created_by, backup_json)
            VALUES (?, ?, ?, ?)
        """, (backup_id, str(guild.id), str(interaction.user.id), json_str))
        conn.commit()
        conn.close()

        await interaction.followup.send(f"💾 **Backup Created Successfully**\nBackup ID: `{backup_id}`\nSaved `{len(backup_data['roles'])}` roles, `{len(backup_data['categories'])}` categories, and `{len(backup_data['text_channels'])}` channels.", ephemeral=True)

    @app_commands.command(name="list", description="List saved server backups")
    async def list_cmd(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT backup_id, created_at FROM server_backups WHERE guild_id = ? ORDER BY rowid DESC LIMIT 10", (str(interaction.guild.id),))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return await interaction.response.send_message("❌ No backups found for this server.", ephemeral=True)

        desc = "\n".join([f"• `{r['backup_id']}` — Created: `{r['created_at']}`" for r in rows])
        embed = discord.Embed(title="📦 Server Backups", description=desc, color=discord.Color.from_rgb(124, 58, 237))
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ── 11. SCHEDULED TASKS ENGINE ───────────────────────────────────────────────
class SchedulerGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="scheduler", description="Schedule Announcements & Delayed Actions")
        self.bot = bot

    @app_commands.command(name="message", description="Schedule a message to be sent after N minutes")
    async def message_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel, delay_minutes: int, content: str):
        if not await is_authorized_manager(interaction, "scheduler"):
            return
        await interaction.response.defer(ephemeral=True)

        exec_time = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        exec_time_ist = exec_time.astimezone(ist_tz)
        payload = json.dumps({"content": content})

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_tasks (guild_id, task_type, channel_id, payload_json, execute_at)
            VALUES (?, 'message', ?, ?, ?)
        """, (str(interaction.guild.id), str(channel.id), payload, exec_time.isoformat()))
        conn.commit()
        conn.close()

        await interaction.followup.send(f"⏰ Message scheduled for {channel.mention} at `{exec_time_ist.strftime('%Y-%m-%d %H:%M IST')}`.", ephemeral=True)


# ── 12. SERVER SETTINGS INTERACTIVE DASHBOARD VIEW ───────────────────────────
class ServerSettingsDashboardView(discord.ui.View):
    def __init__(self, guild: discord.Guild, author: discord.User):
        super().__init__(timeout=300)
        self.guild = guild
        self.author = author

    @discord.ui.select(
        placeholder="Select a Server Settings Category...",
        options=[
            discord.SelectOption(label="General & Moderation Logs", value="logs", emoji="⚙️"),
            discord.SelectOption(label="24/7 Voice Channel System", value="voice", emoji="🎙️"),
            discord.SelectOption(label="Security & Anti-Raid", value="security", emoji="🛡️"),
            discord.SelectOption(label="AutoModeration Rules", value="automod", emoji="🤖"),
            discord.SelectOption(label="Ticketing System", value="tickets", emoji="🎫"),
            discord.SelectOption(label="Welcome & Leave Messages", value="welcome", emoji="👋"),
        ]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)

        cat = select.values[0]
        embed = discord.Embed(
            title=f"🛠️ Server Control Panel — Category: {cat.title()}",
            color=discord.Color.from_rgb(124, 58, 237)
        )

        conn = get_db()
        cursor = conn.cursor()

        if cat == "voice":
            cursor.execute("SELECT * FROM voice_247_settings WHERE guild_id = ?", (str(self.guild.id),))
            v = cursor.fetchone()
            enabled = v['enabled'] if v else 0
            ch_id = v['channel_id'] if v else None
            ch = self.guild.get_channel(int(ch_id)) if ch_id else None
            embed.description = f"**24/7 Status:** {'🟢 Active' if enabled == 1 else '🔴 Disabled'}\n**Configured Voice Channel:** {ch.mention if ch else '`None`'}\nUse `/247 set <vc>` or `/247 join` to configure."
        
        elif cat == "logs":
            cursor.execute("SELECT * FROM server_central_settings WHERE guild_id = ?", (str(self.guild.id),))
            s = cursor.fetchone()
            mod_ch = self.guild.get_channel(int(s['mod_log_channel'])) if (s and s['mod_log_channel']) else None
            sec_ch = self.guild.get_channel(int(s['sec_log_channel'])) if (s and s['sec_log_channel']) else None
            embed.description = f"**Mod Log Channel:** {mod_ch.mention if mod_ch else '`None`'}\n**Security Log Channel:** {sec_ch.mention if sec_ch else '`None`'}"

        else:
            embed.description = f"Active category: `{cat}`. All configuration modules loaded successfully."

        conn.close()
        await interaction.response.edit_message(embed=embed, view=self)


# ── 13. REGISTRATION FUNCTION ────────────────────────────────────────────────
def setup_server_control_system(bot: commands.Bot, perm_group: app_commands.Group = None):
    """
    Registers all Server Control app command groups, Diagnostics Suite, and background loops on bot tree.
    """
    ch_grp = ChannelManagerGroup(bot)
    cat_grp = CategoryManagerGroup(bot)
    role_grp = RoleManagerGroup(bot)
    server_grp = ServerControlGroup(bot)

    try:
        from channel_system import attach_ultimate_channel_commands, attach_ultimate_category_commands, setup_channel_system_prefix_commands
        attach_ultimate_channel_commands(ch_grp, bot)
        attach_ultimate_category_commands(cat_grp, bot)
        setup_channel_system_prefix_commands(bot)
    except Exception as cs_err:
        try:
            from bot.channel_system import attach_ultimate_channel_commands, attach_ultimate_category_commands, setup_channel_system_prefix_commands
            attach_ultimate_channel_commands(ch_grp, bot)
            attach_ultimate_category_commands(cat_grp, bot)
            setup_channel_system_prefix_commands(bot)
        except Exception as cs_err2:
            print(f"⚠️ Channel system registration notice: {cs_err2}")

    try:
        from advanced_customization import register_role_customization
        register_role_customization(role_grp, bot)
    except Exception as r_err:
        try:
            from bot.advanced_customization import register_role_customization
            register_role_customization(role_grp, bot)
        except Exception as r_err2:
            print(f"⚠️ Role customization registration notice: {r_err2}")

    try:
        from diagnostics_suite import setup_diagnostics_suite
        setup_diagnostics_suite(bot, perm_group, server_grp)
    except Exception as d_err:
        try:
            from bot.diagnostics_suite import setup_diagnostics_suite
            setup_diagnostics_suite(bot, perm_group, server_grp)
        except Exception as d_err2:
            print(f"⚠️ Diagnostics suite registration notice: {d_err2}")

    bot.tree.add_command(Voice247Group(bot))
    bot.tree.add_command(ch_grp)
    bot.tree.add_command(cat_grp)
    bot.tree.add_command(role_grp)
    bot.tree.add_command(server_grp)
    bot.tree.add_command(ServerBackupGroup(bot))
    bot.tree.add_command(SchedulerGroup(bot))

    @bot.tree.command(name="roleall", description="Assign or remove a role to all human members (excludes bots & apps)")
    @app_commands.describe(role="The role to assign/remove", action="Action to perform (Default: Add)")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add (Assign role to all human members)", value="add"),
        app_commands.Choice(name="Remove (Remove role from all human members)", value="remove")
    ])
    async def tree_roleall(interaction: discord.Interaction, role: discord.Role, action: app_commands.Choice[str] = None):
        return await role_grp.all_cmd(interaction, role, action)

    @bot.tree.command(name="rolecancel", description="Cancel active bulk role assignment")
    async def tree_rolecancel(interaction: discord.Interaction):
        return await role_grp.cancel_cmd(interaction)

    @bot.command(name="roleall", description="Assign or remove a role to all human members (excludes bots & apps)")
    @commands.has_permissions(manage_roles=True)
    async def prefix_roleall_direct(ctx: commands.Context, role: discord.Role, action: str = "add"):
        cmd = bot.get_command("role all")
        if cmd:
            return await ctx.invoke(cmd, role=role, action=action)

    @bot.command(name="rolecancel", description="Cancel active bulk role assignment")
    @commands.has_permissions(manage_roles=True)
    async def prefix_rolecancel_direct(ctx: commands.Context):
        cmd = bot.get_command("role cancel")
        if cmd:
            return await ctx.invoke(cmd)

    @bot.command(name="set247", aliases=["voice247"], description="Connect bot 24/7 to a voice channel")
    async def prefix_set247(ctx, channel: typing.Optional[typing.Union[discord.VoiceChannel, discord.StageChannel]] = None):
        guild = ctx.guild
        if not guild:
            return
        target_vc = channel or resolve_member_voice_channel(guild, ctx.author.id)
        if not target_vc:
            embed = discord.Embed(
                title="⚠️ Voice Channel Required",
                description="Please join a voice channel first or mention one (`?set247 #channel`)!",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.set_footer(text="Powered by VEYRA")
            return await ctx.send(embed=embed)
        try:
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
                description=f"Connected and locked 24/7 to {target_vc.mention}.\nBot will automatically reconnect on restart.",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.set_footer(text="Powered by VEYRA")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Failed to connect to voice channel: `{e}`")

    print("✅ Registered All-in-One Server Control Command Groups & 24/7 Commands.")
