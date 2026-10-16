# bot/channel_system.py - Production-Grade Ultimate Channel & Category Management System for VEYRA
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import typing
from datetime import datetime, timezone

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db

THEME_PURPLE = 0xa855f7
THEME_SUCCESS = 0x22c55e
THEME_ERROR = 0xef4444
THEME_WARNING = 0xf59e0b
THEME_DARK = 0x18181b
FOOTER_TEXT = "Powered By Veyra Development™ | Designed By Arun"

# ── 1. DATABASE SCHEMA & INITIALIZATION ──────────────────────────────────────
def init_channel_system_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_lock_states (
            channel_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            original_overwrites TEXT NOT NULL,
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_lock_states (
            category_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            channels_overwrites TEXT NOT NULL,
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_perm_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            overwrites_json TEXT NOT NULL,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, template_name)
        )
    """)
    conn.commit()
    conn.close()

init_channel_system_db()


# ── 2. AUDIT LOGGING HELPER ──────────────────────────────────────────────────
async def log_channel_action(guild: discord.Guild, title: str, description: str, actor: discord.User, color: int = THEME_PURPLE, fields: list = None):
    try:
        from server_control import dispatch_discord_log
        await dispatch_discord_log(guild, "audit", title, f"{description}\n**Actor:** {actor.mention} (`{actor.id}`)", color=color, fields=fields)
    except Exception:
        pass


# ── 3. OVERWRITE SERIALIZATION UTILITIES ─────────────────────────────────────
def serialize_channel_overwrites(channel: discord.abc.GuildChannel) -> list[dict]:
    data = []
    for target, ow in channel.overwrites.items():
        allow_val, deny_val = ow.pair()
        data.append({
            "target_id": str(target.id),
            "target_type": "role" if isinstance(target, discord.Role) else "member",
            "target_name": target.name,
            "allow": allow_val.value,
            "deny": deny_val.value
        })
    return data

async def apply_serialized_overwrites(channel: discord.abc.GuildChannel, overwrites_data: list[dict], mode: str = "replace"):
    guild = channel.guild
    if mode == "replace":
        for target in list(channel.overwrites.keys()):
            try:
                await channel.set_permissions(target, overwrite=None)
            except Exception:
                pass

    for entry in overwrites_data:
        t_id = int(entry["target_id"])
        target = guild.get_role(t_id) if entry["target_type"] == "role" else guild.get_member(t_id)
        if not target and entry.get("target_name") == "@everyone":
            target = guild.default_role

        if target:
            allow = discord.Permissions(entry.get("allow", 0))
            deny = discord.Permissions(entry.get("deny", 0))
            ow = discord.PermissionOverwrite.from_pair(allow, deny)
            try:
                await channel.set_permissions(target, overwrite=ow)
            except Exception:
                pass


# ── 4. INTERACTIVE VEYRA CHANNEL CONTROL CENTER UI ───────────────────────────
class ChannelControlCenterView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel, author: discord.User):
        super().__init__(timeout=180)
        self.channel = channel
        self.author = author

    def build_embed(self) -> discord.Embed:
        ch = self.channel
        guild = ch.guild
        everyone_ow = ch.overwrites_for(guild.default_role)
        is_locked = everyone_ow.send_messages is False

        embed = discord.Embed(
            title=f"⚙️ VEYRA Channel Control Center — #{ch.name}",
            description=f"Manage and customize all properties for {ch.mention} (`{ch.id}`) directly from this terminal interface.",
            color=discord.Color(THEME_PURPLE)
        )
        cat_name = ch.category.name if ch.category else "Uncategorized"
        embed.add_field(name="📌 Type & Category", value=f"• Type: `{ch.type}`\n• Category: `{cat_name}`\n• Position: `{ch.position}`", inline=True)
        embed.add_field(
            name="🔒 Security & Lock",
            value=f"• Status: {'🔴 Locked' if is_locked else '🟢 Unlocked'}\n• Overwrites: `{len(ch.overwrites)}` configured\n• Synced: `{'Yes' if ch.permissions_synced else 'No'}`",
            inline=True
        )

        if isinstance(ch, discord.TextChannel):
            embed.add_field(
                name="⏱️ Rate Limit & Content",
                value=f"• Slowmode: `{ch.slowmode_delay}s`\n• NSFW: `{'Yes 🔞' if ch.nsfw else 'No'}`\n• Topic: `{ch.topic or 'No description set'}`",
                inline=False
            )
        elif isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
            embed.add_field(
                name="🔊 Audio Metrics",
                value=f"• Bitrate: `{ch.bitrate // 1000} kbps`\n• User Limit: `{ch.user_limit if ch.user_limit else 'Unlimited'}`\n• Connected: `{len(ch.members)} members`",
                inline=False
            )

        embed.set_footer(text=f"{FOOTER_TEXT} | User: {self.author.name}")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="🔍 Select a different channel to manage...",
        channel_types=[discord.ChannelType.text, discord.ChannelType.voice, discord.ChannelType.stage_voice, discord.ChannelType.news],
        row=0
    )
    async def on_channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized. Open your own `/channel select` session.", ephemeral=True)
        self.channel = select.values[0]
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔒 Toggle Lock", style=discord.ButtonStyle.danger, row=1)
    async def toggle_lock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        ch = self.channel
        ow = ch.overwrites_for(guild.default_role)

        if ow.send_messages is False:
            # Unlock - restore from DB if present
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT original_overwrites FROM channel_lock_states WHERE channel_id = ? AND target_id = ?", (str(ch.id), str(guild.default_role.id)))
            row = cursor.fetchone()
            if row:
                saved_val = row[0]
                ow.send_messages = None if saved_val == "None" else (True if saved_val == "True" else False)
                cursor.execute("DELETE FROM channel_lock_states WHERE channel_id = ? AND target_id = ?", (str(ch.id), str(guild.default_role.id)))
                conn.commit()
            else:
                ow.send_messages = None
            conn.close()

            await ch.set_permissions(guild.default_role, overwrite=ow)
            await log_channel_action(guild, "Channel Unlocked", f"{ch.mention} unlocked via Control Center.", interaction.user, THEME_SUCCESS)
        else:
            # Lock - record previous state
            conn = get_db()
            cursor = conn.cursor()
            prev_val = str(ow.send_messages)
            cursor.execute("INSERT OR REPLACE INTO channel_lock_states (channel_id, guild_id, target_id, original_overwrites) VALUES (?, ?, ?, ?)",
                           (str(ch.id), str(guild.id), str(guild.default_role.id), prev_val))
            conn.commit()
            conn.close()

            ow.send_messages = False
            await ch.set_permissions(guild.default_role, overwrite=ow)
            await log_channel_action(guild, "Channel Locked", f"{ch.mention} locked via Control Center.", interaction.user, THEME_ERROR)

        await interaction.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔄 Sync Category", style=discord.ButtonStyle.secondary, row=1)
    async def sync_category_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        if not self.channel.category:
            return await interaction.response.send_message("⚠️ This channel does not belong to any category.", ephemeral=True)
        await interaction.response.defer()
        try:
            await self.channel.edit(sync_permissions=True)
            await log_channel_action(interaction.guild, "Channel Category Synced", f"{self.channel.mention} synced permissions with **{self.channel.category.name}**.", interaction.user, THEME_SUCCESS)
            await interaction.message.edit(embed=self.build_embed(), view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to sync: `{e}`", ephemeral=True)

    @discord.ui.button(label="👥 Role Access", style=discord.ButtonStyle.primary, row=1)
    async def role_access_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        view = ChannelRoleSelectView(self.channel, self.author, self)
        await interaction.response.send_message("👥 Select a role below to configure view, message, and media access:", view=view, ephemeral=True)

    @discord.ui.button(label="📄 Clone Channel", style=discord.ButtonStyle.secondary, row=2)
    async def clone_channel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            new_ch = await self.channel.clone(name=f"{self.channel.name}-copy")
            await log_channel_action(interaction.guild, "Channel Cloned", f"Cloned {self.channel.mention} into {new_ch.mention}.", interaction.user, THEME_SUCCESS)
            await interaction.followup.send(f"✅ Cloned successfully: {new_ch.mention} (`{new_ch.id}`)", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to clone: `{e}`", ephemeral=True)

    @discord.ui.button(label="🗑️ Delete Channel", style=discord.ButtonStyle.danger, row=2)
    async def delete_channel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        ch_name = self.channel.name
        ch_mention = self.channel.mention
        try:
            await self.channel.delete()
            await log_channel_action(interaction.guild, "Channel Deleted", f"Deleted channel `{ch_name}` via Control Center.", interaction.user, THEME_ERROR)
            await interaction.response.send_message(f"🗑️ Channel `#{ch_name}` permanently deleted.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to delete: `{e}`", ephemeral=True)


# ── 5. ROLE ACCESS SELECTOR VIEW ─────────────────────────────────────────────
class ChannelRoleSelectView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel, author: discord.User, parent_view: ChannelControlCenterView):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.parent_view = parent_view

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select a role to configure permissions...")
    async def on_role_selected(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        view = InteractiveRolePermissionSwitchView(self.channel, role, self.author, self.parent_view)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


class InteractiveRolePermissionSwitchView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel, target: typing.Union[discord.Role, discord.Member], author: discord.User, parent_view: ChannelControlCenterView):
        super().__init__(timeout=180)
        self.channel = channel
        self.target = target
        self.author = author
        self.parent_view = parent_view

        ow = channel.overwrites_for(target)
        self.view_channel = ow.view_channel
        self.send_messages = getattr(ow, "send_messages", getattr(ow, "connect", None))
        self.attach_files = getattr(ow, "attach_files", getattr(ow, "speak", None))
        self.embed_links = getattr(ow, "embed_links", None)

    def _state_badge(self, val):
        if val is True: return "✅ ALLOW"
        if val is False: return "❌ DENY"
        return "⚪ INHERIT"

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🛡️ Role Access Matrix — #{self.channel.name}",
            description=f"Target: **@{self.target.name}** (`{self.target.id}`)\nClick buttons below to cycle permissions between `ALLOW` (✅), `DENY` (❌), and `INHERIT` (⚪).",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="👁️ View Channel", value=self._state_badge(self.view_channel), inline=True)
        embed.add_field(name="💬 Send / Connect", value=self._state_badge(self.send_messages), inline=True)
        embed.add_field(name="📎 Attach / Speak", value=self._state_badge(self.attach_files), inline=True)
        embed.add_field(name="🔗 Embed Links", value=self._state_badge(self.embed_links), inline=True)
        embed.set_footer(text="Changes apply immediately to Discord API.")
        return embed

    async def _update_discord(self):
        ow = self.channel.overwrites_for(self.target)
        ow.view_channel = self.view_channel
        if hasattr(ow, "send_messages"): ow.send_messages = self.send_messages
        if hasattr(ow, "connect"): ow.connect = self.send_messages
        if hasattr(ow, "attach_files"): ow.attach_files = self.attach_files
        if hasattr(ow, "speak"): ow.speak = self.attach_files
        if hasattr(ow, "embed_links"): ow.embed_links = self.embed_links

        if ow.is_empty():
            await self.channel.set_permissions(self.target, overwrite=None)
        else:
            await self.channel.set_permissions(self.target, overwrite=ow)

    def _cycle(self, cur):
        # ALLOW -> DENY -> INHERIT -> ALLOW
        if cur is True: return False
        if cur is False: return None
        return True

    @discord.ui.button(label="👁️ View Channel", style=discord.ButtonStyle.primary, row=0)
    async def toggle_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.view_channel = self._cycle(self.view_channel)
        await self._update_discord()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="💬 Send / Connect", style=discord.ButtonStyle.primary, row=0)
    async def toggle_send(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.send_messages = self._cycle(self.send_messages)
        await self._update_discord()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="📎 Attach / Speak", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_attach(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.attach_files = self._cycle(self.attach_files)
        await self._update_discord()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔗 Embed Links", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_links = self._cycle(self.embed_links)
        await self._update_discord()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⚪ Reset All to Inherit", style=discord.ButtonStyle.danger, row=2)
    async def reset_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.view_channel = None
        self.send_messages = None
        self.attach_files = None
        self.embed_links = None
        await self.channel.set_permissions(self.target, overwrite=None)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ── 6. INTERACTIVE CATEGORY CONTROL CENTER UI ────────────────────────────────
class CategoryControlCenterView(discord.ui.View):
    def __init__(self, category: discord.CategoryChannel, author: discord.User):
        super().__init__(timeout=180)
        self.category = category
        self.author = author

    def build_embed(self) -> discord.Embed:
        cat = self.category
        text_count = sum(1 for c in cat.channels if isinstance(c, discord.TextChannel))
        voice_count = sum(1 for c in cat.channels if isinstance(c, (discord.VoiceChannel, discord.StageChannel)))

        embed = discord.Embed(
            title=f"📁 VEYRA Category Control Center — {cat.name}",
            description=f"Manage child channels, bulk security locks, and permission inheritance for **{cat.name}** (`{cat.id}`).",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="📊 Structure", value=f"• Total Channels: `{len(cat.channels)}`\n• Text Channels: `{text_count}`\n• Voice Channels: `{voice_count}`", inline=True)
        embed.add_field(name="🔒 Permissions", value=f"• Category Overwrites: `{len(cat.overwrites)}`\n• Position: `{cat.position}`", inline=True)
        embed.set_footer(text=f"{FOOTER_TEXT} | Category ID: {cat.id}")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    @discord.ui.button(label="🔒 Lock All Text", style=discord.ButtonStyle.danger, row=0)
    async def lock_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        saved_map = {}
        locked = 0

        for ch in self.category.channels:
            if isinstance(ch, discord.TextChannel):
                ow = ch.overwrites_for(guild.default_role)
                saved_map[str(ch.id)] = str(ow.send_messages)
                ow.send_messages = False
                try:
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    locked += 1
                except Exception:
                    pass

        cursor.execute("INSERT OR REPLACE INTO category_lock_states (category_id, guild_id, channels_overwrites) VALUES (?, ?, ?)",
                       (str(self.category.id), str(guild.id), json.dumps(saved_map)))
        conn.commit()
        conn.close()

        await log_channel_action(guild, "Category Lockdown", f"Locked `{locked}` text channels in **{self.category.name}**.", interaction.user, THEME_ERROR)
        await interaction.followup.send(f"🔒 Locked `{locked}` text channels in **{self.category.name}**.", ephemeral=True)

    @discord.ui.button(label="🔓 Unlock All", style=discord.ButtonStyle.success, row=0)
    async def unlock_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT channels_overwrites FROM category_lock_states WHERE category_id = ?", (str(self.category.id),))
        row = cursor.fetchone()

        restored = 0
        if row:
            saved_map = json.loads(row[0])
            for ch_id_str, prev_val in saved_map.items():
                ch = guild.get_channel(int(ch_id_str))
                if ch:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None if prev_val == "None" else (True if prev_val == "True" else False)
                    try:
                        await ch.set_permissions(guild.default_role, overwrite=ow)
                        restored += 1
                    except Exception:
                        pass
            cursor.execute("DELETE FROM category_lock_states WHERE category_id = ?", (str(self.category.id),))
            conn.commit()
        else:
            for ch in self.category.channels:
                if isinstance(ch, discord.TextChannel):
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    try:
                        await ch.set_permissions(guild.default_role, overwrite=ow)
                        restored += 1
                    except Exception:
                        pass
        conn.close()

        await log_channel_action(guild, "Category Unlocked", f"Restored `{restored}` text channels in **{self.category.name}**.", interaction.user, THEME_SUCCESS)
        await interaction.followup.send(f"🔓 Restored and unlocked `{restored}` channels in **{self.category.name}**.", ephemeral=True)

    @discord.ui.button(label="🔄 Sync All Channels", style=discord.ButtonStyle.secondary, row=0)
    async def sync_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        await interaction.response.defer()
        count = 0
        for ch in self.category.channels:
            try:
                await ch.edit(sync_permissions=True)
                count += 1
            except Exception:
                pass
        await log_channel_action(interaction.guild, "Category Synced", f"Synchronized `{count}` channels in **{self.category.name}**.", interaction.user, THEME_SUCCESS)
        await interaction.followup.send(f"🔄 Synced permissions for `{count}` channels with **{self.category.name}**.", ephemeral=True)


# ── 7. ATTACH ALL 25 SUBCOMMANDS TO CHANNEL GROUP ─────────────────────────────
def attach_ultimate_channel_commands(channel_group: app_commands.Group, bot: commands.Bot):
    """
    Attaches the complete suite of channel commands directly into ChannelManagerGroup.
    """

    # 1. /channel select
    @channel_group.command(name="select", description="Open interactive VEYRA Channel Control Center")
    @app_commands.describe(channel="Channel to open and manage (defaults to current channel)")
    async def slash_channel_select(interaction: discord.Interaction, channel: typing.Optional[discord.abc.GuildChannel] = None):
        target_ch = channel or interaction.channel
        view = ChannelControlCenterView(target_ch, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    # 2. /channel clone
    @channel_group.command(name="clone", description="Clone channel with settings, topic, slowmode, and permissions")
    @app_commands.describe(channel="Channel to clone", name="New channel title")
    async def slash_channel_clone(interaction: discord.Interaction, channel: discord.abc.GuildChannel, name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        target_name = name or f"{channel.name}-copy"
        try:
            new_ch = await channel.clone(name=target_name)
            await log_channel_action(interaction.guild, "Channel Cloned", f"Cloned {channel.mention} into {new_ch.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="✅ Channel Cloned Successfully",
                description=f"Source: {channel.mention} (`{channel.id}`)\nNew Channel: {new_ch.mention} (`{new_ch.id}`)",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Channel clone failed: `{e}`")

    # 3. /channel move
    @channel_group.command(name="move", description="Move channel into another category")
    @app_commands.describe(channel="Channel to move", category="Target category")
    async def slash_channel_move(interaction: discord.Interaction, channel: discord.abc.GuildChannel, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await channel.edit(category=category)
            await log_channel_action(interaction.guild, "Channel Moved", f"Moved {channel.mention} into **{category.name}**.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(title="📦 Channel Relocated", description=f"Moved {channel.mention} into category **{category.name}**.", color=discord.Color(THEME_SUCCESS))
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to move channel: `{e}`")

    # 4. /channel reorder
    @channel_group.command(name="reorder", description="Change channel position inside its category")
    @app_commands.describe(channel="Channel to reorder", position="Integer position number")
    async def slash_channel_reorder(interaction: discord.Interaction, channel: discord.abc.GuildChannel, position: int):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await channel.edit(position=position)
            await log_channel_action(interaction.guild, "Channel Reordered", f"Set position of {channel.mention} to `{position}`.", interaction.user, THEME_SUCCESS)
            await interaction.followup.send(f"✅ Set position of {channel.mention} to `{position}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reorder: `{e}`")

    # 5. /channel allow
    @channel_group.command(name="allow", description="Explicitly allow a specific permission for a role or member")
    @app_commands.describe(
        channel="Target channel",
        target_role="Role to grant permission",
        target_member="Member to grant permission",
        permission="Permission flag to ALLOW"
    )
    @app_commands.choices(permission=[
        app_commands.Choice(name="View Channel (view_channel)", value="view_channel"),
        app_commands.Choice(name="Send Messages / Connect (send_messages)", value="send_messages"),
        app_commands.Choice(name="Attach Files / Speak (attach_files)", value="attach_files"),
        app_commands.Choice(name="Embed Links (embed_links)", value="embed_links"),
        app_commands.Choice(name="Add Reactions (add_reactions)", value="add_reactions"),
        app_commands.Choice(name="Read Message History (read_message_history)", value="read_message_history"),
        app_commands.Choice(name="Manage Channel (manage_channels)", value="manage_channels")
    ])
    async def slash_channel_allow(
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        permission: app_commands.Choice[str],
        target_role: typing.Optional[discord.Role] = None,
        target_member: typing.Optional[discord.Member] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target = target_role or target_member or interaction.guild.default_role
        await interaction.response.defer()

        ow = channel.overwrites_for(target)
        perm_key = permission.value
        setattr(ow, perm_key, True)
        if perm_key == "send_messages" and hasattr(ow, "connect"):
            ow.connect = True
        if perm_key == "attach_files" and hasattr(ow, "speak"):
            ow.speak = True

        try:
            await channel.set_permissions(target, overwrite=ow)
            await log_channel_action(interaction.guild, "Permission Allowed", f"Granted `{perm_key}` to **{target.name}** in {channel.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="✅ Permission Allowed",
                description=f"Explicitly granted **`{perm_key}`** to {target.mention} in {channel.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update permissions: `{e}`")

    # 6. /channel deny
    @channel_group.command(name="deny", description="Explicitly deny a specific permission for a role or member")
    @app_commands.describe(
        channel="Target channel",
        target_role="Role to restrict permission",
        target_member="Member to restrict permission",
        permission="Permission flag to DENY"
    )
    @app_commands.choices(permission=[
        app_commands.Choice(name="View Channel (view_channel)", value="view_channel"),
        app_commands.Choice(name="Send Messages / Connect (send_messages)", value="send_messages"),
        app_commands.Choice(name="Attach Files / Speak (attach_files)", value="attach_files"),
        app_commands.Choice(name="Embed Links (embed_links)", value="embed_links"),
        app_commands.Choice(name="Add Reactions (add_reactions)", value="add_reactions"),
        app_commands.Choice(name="Read Message History (read_message_history)", value="read_message_history"),
        app_commands.Choice(name="Manage Channel (manage_channels)", value="manage_channels")
    ])
    async def slash_channel_deny(
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        permission: app_commands.Choice[str],
        target_role: typing.Optional[discord.Role] = None,
        target_member: typing.Optional[discord.Member] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target = target_role or target_member or interaction.guild.default_role
        await interaction.response.defer()

        ow = channel.overwrites_for(target)
        perm_key = permission.value
        setattr(ow, perm_key, False)
        if perm_key == "send_messages" and hasattr(ow, "connect"):
            ow.connect = False
        if perm_key == "attach_files" and hasattr(ow, "speak"):
            ow.speak = False

        try:
            await channel.set_permissions(target, overwrite=ow)
            await log_channel_action(interaction.guild, "Permission Denied", f"Denied `{perm_key}` for **{target.name}** in {channel.mention}.", interaction.user, THEME_ERROR)
            embed = discord.Embed(
                title="🚫 Permission Denied",
                description=f"Explicitly restricted **`{perm_key}`** for {target.mention} in {channel.mention}.",
                color=discord.Color(THEME_ERROR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update permissions: `{e}`")

    # 7. /channel resetperms
    @channel_group.command(name="resetperms", description="Reset channel permission overrides for a role/member back to inherit")
    @app_commands.describe(channel="Target channel", target_role="Role to reset", target_member="Member to reset")
    async def slash_channel_resetperms(
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        target_role: typing.Optional[discord.Role] = None,
        target_member: typing.Optional[discord.Member] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target = target_role or target_member or interaction.guild.default_role
        await interaction.response.defer()

        try:
            await channel.set_permissions(target, overwrite=None)
            await log_channel_action(interaction.guild, "Permissions Reset", f"Reset all overrides for **{target.name}** in {channel.mention} back to inherit.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="⚪ Permissions Reset",
                description=f"Removed channel-specific overrides for {target.mention} in {channel.mention}. Permissions are now inherited from category/server.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reset: `{e}`")

    # 8. /channel copyperms
    @channel_group.command(name="copyperms", description="Copy all permission overwrites from source to target channel")
    @app_commands.describe(
        source="Source channel",
        target="Target channel",
        mode="replace (wipe target first) or merge (preserve other roles on target)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Replace (Wipe and apply exact copy)", value="replace"),
        app_commands.Choice(name="Merge (Keep unmentioned roles on target)", value="merge")
    ])
    async def slash_channel_copyperms(
        interaction: discord.Interaction,
        source: discord.abc.GuildChannel,
        target: discord.abc.GuildChannel,
        mode: app_commands.Choice[str] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        apply_mode = mode.value if mode else "replace"
        try:
            if apply_mode == "replace":
                for t in list(target.overwrites.keys()):
                    await target.set_permissions(t, overwrite=None)
            for t, ow in source.overwrites.items():
                await target.set_permissions(t, overwrite=ow)

            await log_channel_action(interaction.guild, "Permissions Copied", f"Replicated `{len(source.overwrites)}` overwrites from {source.mention} to {target.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="🛡️ Permissions Replicated",
                description=f"Copied **`{len(source.overwrites)}`** permission entries from {source.mention} into {target.mention} (Mode: `{apply_mode.upper()}`).",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to copy permissions: `{e}`")

    # 9. /channel syncperms
    @channel_group.command(name="syncperms", description="Sync channel permissions with parent category")
    @app_commands.describe(channel="Channel to sync with its category")
    async def slash_channel_syncperms(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        if not channel.category:
            return await interaction.response.send_message("⚠️ This channel does not belong to any category.", ephemeral=True)
        await interaction.response.defer()

        try:
            await channel.edit(sync_permissions=True)
            await log_channel_action(interaction.guild, "Channel Synced", f"{channel.mention} synced with parent category **{channel.category.name}**.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="🔄 Category Synced",
                description=f"{channel.mention} is now completely synchronized with **{channel.category.name}**.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: `{e}`")

    # 10. /channel roleaccess
    @channel_group.command(name="roleaccess", description="1-Click configure view, message, and media access for a role")
    @app_commands.describe(
        channel="Target channel",
        role="Role to configure",
        access_level="Access Preset: Read-Only, Full Member, or Hidden"
    )
    @app_commands.choices(access_level=[
        app_commands.Choice(name="Full Member (View + Send + Attach)", value="full"),
        app_commands.Choice(name="Read-Only (View Only, No Messaging)", value="readonly"),
        app_commands.Choice(name="Hidden (Completely Invisible to Role)", value="hidden"),
        app_commands.Choice(name="Reset to Inherit", value="inherit")
    ])
    async def slash_channel_roleaccess(
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        role: discord.Role,
        access_level: app_commands.Choice[str]
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        lvl = access_level.value
        ow = channel.overwrites_for(role)

        if lvl == "inherit":
            ow = None
        elif lvl == "hidden":
            ow.view_channel = False
        elif lvl == "readonly":
            ow.view_channel = True
            ow.send_messages = False
            ow.add_reactions = True
            ow.read_message_history = True
        elif lvl == "full":
            ow.view_channel = True
            ow.send_messages = True
            ow.attach_files = True
            ow.embed_links = True
            ow.read_message_history = True

        try:
            await channel.set_permissions(role, overwrite=ow)
            await log_channel_action(interaction.guild, "Role Access Configured", f"Set `{lvl.upper()}` access for **@{role.name}** in {channel.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="👥 Role Access Configured",
                description=f"Applied preset **`{lvl.upper()}`** for {role.mention} in {channel.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set role access: `{e}`")

    # 11. /channel memberaccess
    @channel_group.command(name="memberaccess", description="Grant or revoke channel access for a specific member")
    @app_commands.describe(
        channel="Target channel",
        member="Server member",
        access_level="Access Preset: Full, Read-Only, Denied, or Inherit"
    )
    @app_commands.choices(access_level=[
        app_commands.Choice(name="Grant Access (View + Send)", value="grant"),
        app_commands.Choice(name="Read-Only (View Only)", value="readonly"),
        app_commands.Choice(name="Revoke / Deny Access (Invisible)", value="deny"),
        app_commands.Choice(name="Reset (Remove member overwrite)", value="inherit")
    ])
    async def slash_channel_memberaccess(
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        member: discord.Member,
        access_level: app_commands.Choice[str]
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        lvl = access_level.value
        ow = channel.overwrites_for(member)

        if lvl == "inherit":
            ow = None
        elif lvl == "deny":
            ow.view_channel = False
        elif lvl == "readonly":
            ow.view_channel = True
            ow.send_messages = False
            ow.read_message_history = True
        elif lvl == "grant":
            ow.view_channel = True
            ow.send_messages = True
            ow.read_message_history = True

        try:
            await channel.set_permissions(member, overwrite=ow)
            await log_channel_action(interaction.guild, "Member Access Configured", f"Set `{lvl.upper()}` access for **{member.name}** in {channel.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="👤 Member Access Configured",
                description=f"Configured **`{lvl.upper()}`** for {member.mention} in {channel.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set member access: `{e}`")

    # 12. /channel lockrole
    @channel_group.command(name="lockrole", description="Restrict a specific role from sending messages in this channel")
    @app_commands.describe(channel="Target channel", role="Role to restrict")
    async def slash_channel_lockrole(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        ow = channel.overwrites_for(role)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO channel_lock_states (channel_id, guild_id, target_id, original_overwrites) VALUES (?, ?, ?, ?)",
                       (str(channel.id), str(interaction.guild.id), str(role.id), str(ow.send_messages)))
        conn.commit()
        conn.close()

        ow.send_messages = False
        try:
            await channel.set_permissions(role, overwrite=ow)
            await log_channel_action(interaction.guild, "Role Locked in Channel", f"Restricted {role.mention} from messaging in {channel.mention}.", interaction.user, THEME_ERROR)
            embed = discord.Embed(
                title="🔒 Role Restricted",
                description=f"Role {role.mention} is now locked from sending messages in {channel.mention}.",
                color=discord.Color(THEME_ERROR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to lock role: `{e}`")

    # 13. /channel unlockrole
    @channel_group.command(name="unlockrole", description="Restore a previously locked role without destroying other permissions")
    @app_commands.describe(channel="Target channel", role="Role to restore")
    async def slash_channel_unlockrole(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT original_overwrites FROM channel_lock_states WHERE channel_id = ? AND target_id = ?", (str(channel.id), str(role.id)))
        row = cursor.fetchone()

        ow = channel.overwrites_for(role)
        if row:
            saved_val = row[0]
            ow.send_messages = None if saved_val == "None" else (True if saved_val == "True" else False)
            cursor.execute("DELETE FROM channel_lock_states WHERE channel_id = ? AND target_id = ?", (str(channel.id), str(role.id)))
            conn.commit()
        else:
            ow.send_messages = None
        conn.close()

        try:
            await channel.set_permissions(role, overwrite=ow)
            await log_channel_action(interaction.guild, "Role Unlocked in Channel", f"Restored {role.mention} messaging permissions in {channel.mention}.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="🔓 Role Restriction Lifted",
                description=f"Restored messaging access for {role.mention} in {channel.mention} with original settings preserved.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unlock role: `{e}`")

    # 14. /channel nsfw
    @channel_group.command(name="nsfw", description="Enable or disable age-restricted (NSFW) flag for a channel")
    @app_commands.describe(channel="Target text channel", enabled="Enable (True) or Disable (False)")
    async def slash_channel_nsfw(interaction: discord.Interaction, channel: discord.TextChannel, enabled: bool):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await channel.edit(nsfw=enabled)
            await log_channel_action(interaction.guild, "Channel NSFW Toggled", f"Set NSFW to `{enabled}` for {channel.mention}.", interaction.user, THEME_WARNING if enabled else THEME_SUCCESS)
            embed = discord.Embed(
                title="🔞 NSFW Status Updated",
                description=f"{channel.mention} is now marked as **{'Age-Restricted (NSFW)' if enabled else 'Family Friendly / Standard'}**.",
                color=discord.Color(THEME_WARNING if enabled else THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 15. /channel bitrate
    @channel_group.command(name="bitrate", description="Set audio bitrate for a voice channel (e.g. 64, 96, 128 kbps)")
    @app_commands.describe(channel="Target voice channel", kbps="Bitrate in kbps (e.g. 64, 96, 128, 256)")
    async def slash_channel_bitrate(interaction: discord.Interaction, channel: discord.VoiceChannel, kbps: int):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        bitrate_bps = max(8000, min(kbps * 1000, interaction.guild.bitrate_limit))
        try:
            await channel.edit(bitrate=bitrate_bps)
            await log_channel_action(interaction.guild, "Voice Bitrate Updated", f"Set {channel.mention} bitrate to `{bitrate_bps // 1000} kbps`.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="🔊 Voice Bitrate Updated",
                description=f"{channel.mention} audio bitrate configured to **`{bitrate_bps // 1000} kbps`**.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set bitrate: `{e}`")

    # 16. /channel userlimit
    @channel_group.command(name="userlimit", description="Set member capacity limit for a voice channel")
    @app_commands.describe(channel="Target voice channel", limit="Capacity (0 for unlimited, 1-99)")
    async def slash_channel_userlimit(interaction: discord.Interaction, channel: discord.VoiceChannel, limit: int):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        cap = max(0, min(limit, 99))
        try:
            await channel.edit(user_limit=cap)
            await log_channel_action(interaction.guild, "User Limit Updated", f"Set {channel.mention} user limit to `{cap}`.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="👥 Voice Capacity Updated",
                description=f"{channel.mention} capacity limit set to **`{'Unlimited' if cap == 0 else f'{cap} members'}`**.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set user limit: `{e}`")


# ── 8. ATTACH CATEGORY MANAGEMENT COMMANDS ───────────────────────────────────
def attach_ultimate_category_commands(category_group: app_commands.Group, bot: commands.Bot):

    # 1. /category select
    @category_group.command(name="select", description="Open interactive VEYRA Category Control Center")
    @app_commands.describe(category="Category to inspect and manage")
    async def slash_category_select(interaction: discord.Interaction, category: discord.CategoryChannel):
        view = CategoryControlCenterView(category, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    # 2. /category rename
    @category_group.command(name="rename", description="Rename a category channel")
    @app_commands.describe(category="Category to rename", name="New category title")
    async def slash_category_rename(interaction: discord.Interaction, category: discord.CategoryChannel, name: str):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        old_name = category.name
        try:
            await category.edit(name=name)
            await log_channel_action(interaction.guild, "Category Renamed", f"Renamed **{old_name}** to **{name}**.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="✏️ Category Renamed",
                description=f"Updated category title from **{old_name}** to **{name}**.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to rename: `{e}`")

    # 3. /category clone
    @category_group.command(name="clone", description="Clone category and its child channels with full permission structures")
    @app_commands.describe(category="Category to clone", name="New category name")
    async def slash_category_clone(interaction: discord.Interaction, category: discord.CategoryChannel, name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        cat_name = name or f"{category.name}-copy"
        try:
            new_cat = await guild.create_category(name=cat_name, overwrites=category.overwrites)
            created_channels = 0
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    await guild.create_text_channel(
                        name=ch.name,
                        category=new_cat,
                        topic=ch.topic,
                        slowmode_delay=ch.slowmode_delay,
                        nsfw=ch.nsfw,
                        overwrites=ch.overwrites
                    )
                    created_channels += 1
                elif isinstance(ch, discord.VoiceChannel):
                    await guild.create_voice_channel(
                        name=ch.name,
                        category=new_cat,
                        bitrate=ch.bitrate,
                        user_limit=ch.user_limit,
                        overwrites=ch.overwrites
                    )
                    created_channels += 1

            await log_channel_action(guild, "Category Cloned", f"Cloned **{category.name}** into **{new_cat.name}** with `{created_channels}` channels.", interaction.user, THEME_SUCCESS)
            embed = discord.Embed(
                title="📁 Category & Structure Cloned",
                description=f"Cloned **{category.name}** into **{new_cat.name}** (`{new_cat.id}`).\nInstantiated `{created_channels}` child channels with full permission preservation.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to clone category: `{e}`")

    # 4. /category movechannels
    @category_group.command(name="movechannels", description="Move selected channels into a category by keyword filter")
    @app_commands.describe(category="Destination category", keyword="Filter keyword in channel name")
    async def slash_category_movechannels(interaction: discord.Interaction, category: discord.CategoryChannel, keyword: str):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        moved = 0
        kw = keyword.lower()
        for ch in interaction.guild.channels:
            if not isinstance(ch, discord.CategoryChannel) and kw in ch.name.lower() and ch.category_id != category.id:
                try:
                    await ch.edit(category=category)
                    moved += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="📦 Channels Moved to Category",
            description=f"Moved **`{moved}`** channels matching `{keyword}` into **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 5. /category syncall
    @category_group.command(name="syncall", description="Sync all child channels to category permissions")
    @app_commands.describe(category="Category whose channels will be synchronized")
    async def slash_category_syncall(interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        synced = 0
        for ch in category.channels:
            try:
                await ch.edit(sync_permissions=True)
                synced += 1
            except Exception:
                pass

        await log_channel_action(interaction.guild, "Category Synced All", f"Synced `{synced}` channels in **{category.name}**.", interaction.user, THEME_SUCCESS)
        embed = discord.Embed(
            title="🔄 Category Channels Synced",
            description=f"Synchronized permissions for **`{synced}`** channels with **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 6. /category lockall
    @category_group.command(name="lockall", description="Lock all text channels in category, saving original states for clean unlock")
    @app_commands.describe(category="Category to lock down")
    async def slash_category_lockall(interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        saved_map = {}
        locked = 0

        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                ow = ch.overwrites_for(guild.default_role)
                saved_map[str(ch.id)] = str(ow.send_messages)
                ow.send_messages = False
                try:
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    locked += 1
                except Exception:
                    pass

        cursor.execute("INSERT OR REPLACE INTO category_lock_states (category_id, guild_id, channels_overwrites) VALUES (?, ?, ?)",
                       (str(category.id), str(guild.id), json.dumps(saved_map)))
        conn.commit()
        conn.close()

        await log_channel_action(guild, "Category Locked Down", f"Sealed `{locked}` text channels in **{category.name}**.", interaction.user, THEME_ERROR)
        embed = discord.Embed(
            title="🔒 Category Lockdown Active",
            description=f"Sealed **`{locked}`** text channels in **{category.name}**.\nOriginal permissions saved for lossless restoration.",
            color=discord.Color(THEME_ERROR)
        )
        embed.set_footer(text=f"{FOOTER_TEXT} | Use '/category unlockall' to lift")
        await interaction.followup.send(embed=embed)

    # 7. /category unlockall
    @category_group.command(name="unlockall", description="Restore category channels to exact pre-lockdown permissions")
    @app_commands.describe(category="Category to restore")
    async def slash_category_unlockall(interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT channels_overwrites FROM category_lock_states WHERE category_id = ?", (str(category.id),))
        row = cursor.fetchone()

        restored = 0
        if row:
            saved_map = json.loads(row[0])
            for ch_id_str, prev_val in saved_map.items():
                ch = guild.get_channel(int(ch_id_str))
                if ch:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None if prev_val == "None" else (True if prev_val == "True" else False)
                    try:
                        await ch.set_permissions(guild.default_role, overwrite=ow)
                        restored += 1
                    except Exception:
                        pass
            cursor.execute("DELETE FROM category_lock_states WHERE category_id = ?", (str(category.id),))
            conn.commit()
        else:
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    try:
                        await ch.set_permissions(guild.default_role, overwrite=ow)
                        restored += 1
                    except Exception:
                        pass
        conn.close()

        await log_channel_action(guild, "Category Lockdown Lifted", f"Restored `{restored}` text channels in **{category.name}**.", interaction.user, THEME_SUCCESS)
        embed = discord.Embed(
            title="🔓 Category Lockdown Lifted",
            description=f"Restored **`{restored}`** text channels in **{category.name}** to their pre-lockdown permission state.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)


# ── 9. PREFIX COMMANDS FOR CHANNEL & CATEGORY SUITE ──────────────────────────
def setup_channel_system_prefix_commands(bot: commands.Bot):
    """
    Registers high-speed prefix commands with identical UI.
    """

    @bot.group(name="channel", invoke_without_command=True)
    async def p_channel_root(ctx):
        view = ChannelControlCenterView(ctx.channel, ctx.author)
        await ctx.send(embed=view.build_embed(), view=view)

    @p_channel_root.command(name="select")
    async def p_channel_select(ctx, channel: discord.abc.GuildChannel = None):
        target = channel or ctx.channel
        view = ChannelControlCenterView(target, ctx.author)
        await ctx.send(embed=view.build_embed(), view=view)

    @p_channel_root.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def p_channel_lock(ctx, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        ow = target.overwrites_for(ctx.guild.default_role)
        ow.send_messages = False
        await target.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send(f"🔒 {target.mention} locked successfully!")

    @p_channel_root.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def p_channel_unlock(ctx, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        ow = target.overwrites_for(ctx.guild.default_role)
        ow.send_messages = None
        await target.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send(f"🔓 {target.mention} unlocked successfully!")

    @p_channel_root.command(name="copyperms")
    @commands.has_permissions(manage_channels=True)
    async def p_channel_copyperms(ctx, source: discord.abc.GuildChannel, target: discord.abc.GuildChannel, mode: str = "replace"):
        for t in list(target.overwrites.keys()):
            if mode == "replace":
                await target.set_permissions(t, overwrite=None)
        for t, ow in source.overwrites.items():
            await target.set_permissions(t, overwrite=ow)
        await ctx.send(f"✅ Replicated `{len(source.overwrites)}` overwrites from {source.mention} to {target.mention}.")

    @p_channel_root.command(name="syncperms")
    @commands.has_permissions(manage_channels=True)
    async def p_channel_syncperms(ctx, channel: discord.abc.GuildChannel = None):
        target = channel or ctx.channel
        if not target.category:
            return await ctx.send("⚠️ Channel has no parent category.")
        await target.edit(sync_permissions=True)
        await ctx.send(f"🔄 Synced {target.mention} with **{target.category.name}**.")

    @p_channel_root.command(name="clone")
    @commands.has_permissions(manage_channels=True)
    async def p_channel_clone(ctx, channel: discord.abc.GuildChannel = None, name: str = None):
        target = channel or ctx.channel
        new_name = name or f"{target.name}-copy"
        new_ch = await target.clone(name=new_name)
        await ctx.send(f"✅ Cloned {target.mention} -> {new_ch.mention} (`{new_ch.id}`).")

    @bot.group(name="category", invoke_without_command=True)
    async def p_category_root(ctx):
        cats = ctx.guild.categories
        if not cats:
            return await ctx.send("ℹ️ No categories found.")
        view = CategoryControlCenterView(cats[0], ctx.author)
        await ctx.send(embed=view.build_embed(), view=view)

    @p_category_root.command(name="select")
    async def p_category_select(ctx, category: discord.CategoryChannel):
        view = CategoryControlCenterView(category, ctx.author)
        await ctx.send(embed=view.build_embed(), view=view)

    @p_category_root.command(name="lockall")
    @commands.has_permissions(manage_channels=True)
    async def p_category_lockall(ctx, category: discord.CategoryChannel):
        count = 0
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                ow = ch.overwrites_for(ctx.guild.default_role)
                ow.send_messages = False
                try:
                    await ch.set_permissions(ctx.guild.default_role, overwrite=ow)
                    count += 1
                except Exception:
                    pass
        await ctx.send(f"🔒 Locked `{count}` text channels in **{category.name}**.")

    @p_category_root.command(name="unlockall")
    @commands.has_permissions(manage_channels=True)
    async def p_category_unlockall(ctx, category: discord.CategoryChannel):
        count = 0
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                ow = ch.overwrites_for(ctx.guild.default_role)
                ow.send_messages = None
                try:
                    await ch.set_permissions(ctx.guild.default_role, overwrite=ow)
                    count += 1
                except Exception:
                    pass
        await ctx.send(f"🔓 Unlocked `{count}` text channels in **{category.name}**.")

    @p_category_root.command(name="syncall")
    @commands.has_permissions(manage_channels=True)
    async def p_category_syncall(ctx, category: discord.CategoryChannel):
        count = 0
        for ch in category.channels:
            try:
                await ch.edit(sync_permissions=True)
                count += 1
            except Exception:
                pass
        await ctx.send(f"🔄 Synced permissions for `{count}` channels with **{category.name}**.")

    print("✅ Registered Ultimate Channel & Category Management System.")
