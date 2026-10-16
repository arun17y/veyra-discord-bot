# bot/advanced_customization.py - Advanced Channel, Category & Role Customization Suite
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import uuid
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

# ── 1. DATABASE SCHEMA & INITIALIZATION ──────────────────────────────────────
def init_customization_db():
    conn = get_db()
    cursor = conn.cursor()
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, template_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            permissions_value INTEGER NOT NULL,
            color_hex TEXT,
            hoist INTEGER DEFAULT 0,
            mentionable INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, template_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customization_undo_log (
            action_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_id TEXT,
            target_name TEXT,
            before_state TEXT NOT NULL,
            after_state TEXT,
            actor_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_lock_states (
            channel_id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            original_overwrites TEXT NOT NULL,
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_customization_db()


# ── 2. SERIALIZATION & HELPER UTILITIES ──────────────────────────────────────
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

def log_undo_action(guild_id: int, action_type: str, target_id: int, target_name: str, before_state: dict, after_state: dict, actor_id: int) -> str:
    action_id = f"act_{uuid.uuid4().hex[:10]}"
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customization_undo_log (action_id, guild_id, action_type, target_id, target_name, before_state, after_state, actor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (action_id, str(guild_id), action_type, str(target_id), target_name, json.dumps(before_state), json.dumps(after_state), str(actor_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ [Undo Log Error] {e}")
    return action_id


# ── 3. CHANNEL CUSTOMIZATION COMMANDS (12 COMMANDS) ──────────────────────────
def register_channel_customization(channel_group: app_commands.Group, bot: commands.Bot):

    # 1. /channel clone
    @channel_group.command(name="clone", description="Clone existing channel with settings, topic, slowmode, and permissions")
    @app_commands.describe(channel="Channel to clone", name="New channel name (defaults to source name)")
    async def channel_clone(interaction: discord.Interaction, channel: discord.abc.GuildChannel, name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        clone_name = name or f"{channel.name}-copy"
        try:
            overwrites = channel.overwrites
            category = channel.category
            topic = getattr(channel, "topic", None)
            slowmode = getattr(channel, "slowmode_delay", 0)
            nsfw = getattr(channel, "nsfw", False)

            if isinstance(channel, discord.TextChannel):
                new_ch = await guild.create_text_channel(
                    name=clone_name,
                    category=category,
                    topic=topic,
                    slowmode_delay=slowmode,
                    nsfw=nsfw,
                    overwrites=overwrites
                )
            elif isinstance(channel, discord.VoiceChannel):
                new_ch = await guild.create_voice_channel(
                    name=clone_name,
                    category=category,
                    bitrate=channel.bitrate,
                    user_limit=channel.user_limit,
                    overwrites=overwrites
                )
            elif isinstance(channel, discord.StageChannel):
                new_ch = await guild.create_stage_channel(
                    name=clone_name,
                    category=category,
                    overwrites=overwrites
                )
            else:
                return await interaction.followup.send("❌ Unsupported channel type for cloning.")

            log_undo_action(guild.id, "channel_create", new_ch.id, new_ch.name, {}, {"id": str(new_ch.id)}, interaction.user.id)

            embed = discord.Embed(
                title="✅ Channel Cloned Successfully",
                description=f"Source: {channel.mention} (`{channel.id}`)\nNew Channel: {new_ch.mention} (`{new_ch.id}`)",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.add_field(name="Category", value=category.name if category else "`None`", inline=True)
            embed.add_field(name="Overwrites Cloned", value=f"`{len(overwrites)}` roles/members", inline=True)
            embed.set_footer(text=f"Action Actor: {interaction.user.name}")
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot lacks permission to manage/create channels.")
        except Exception as e:
            await interaction.followup.send(f"❌ Channel clone failed: `{e}`")

    # 2. /channel copysettings
    @channel_group.command(name="copysettings", description="Copy selected settings from source channel to target channel")
    @app_commands.describe(source="Source channel", target="Target channel to update")
    async def channel_copysettings(interaction: discord.Interaction, source: discord.TextChannel, target: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        before = {
            "topic": target.topic,
            "slowmode": target.slowmode_delay,
            "nsfw": target.nsfw
        }
        try:
            await target.edit(
                topic=source.topic,
                slowmode_delay=source.slowmode_delay,
                nsfw=source.nsfw
            )
            after = {
                "topic": source.topic,
                "slowmode": source.slowmode_delay,
                "nsfw": source.nsfw
            }
            action_id = log_undo_action(interaction.guild.id, "channel_settings", target.id, target.name, before, after, interaction.user.id)

            embed = discord.Embed(
                title="✅ Settings Transferred",
                description=f"Copied configuration from {source.mention} to {target.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.add_field(name="Topic", value=f"`{source.topic or 'None'}`", inline=False)
            embed.add_field(name="Slowmode", value=f"`{source.slowmode_delay}s`", inline=True)
            embed.add_field(name="NSFW", value="🟢 True" if source.nsfw else "⚪ False", inline=True)
            embed.set_footer(text=f"Undo ID: {action_id}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to copy settings: `{e}`")

    # 3. /channel copyperms (Top 1 Priority)
    @channel_group.command(name="copyperms", description="Copy role and member permission overwrites from source to target channel")
    @app_commands.describe(
        source="Source channel with desired permissions",
        target="Target channel where permissions will be applied",
        mode="replace (wipe target first) or merge (update matching, keep others)",
        role="Optional: copy permissions for this specific role only"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Replace (Overwrite existing target permissions)", value="replace"),
        app_commands.Choice(name="Merge (Preserve unmentioned roles on target)", value="merge")
    ])
    async def channel_copyperms(
        interaction: discord.Interaction,
        source: discord.abc.GuildChannel,
        target: discord.abc.GuildChannel,
        mode: app_commands.Choice[str] = None,
        role: typing.Optional[discord.Role] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        apply_mode = mode.value if mode else "replace"
        before_state = serialize_channel_overwrites(target)

        try:
            if role:
                # Selective role copy
                ow = source.overwrites_for(role)
                await target.set_permissions(role, overwrite=ow)
                copied_count = 1
            else:
                if apply_mode == "replace":
                    # Clear target overwrites
                    for t in list(target.overwrites.keys()):
                        await target.set_permissions(t, overwrite=None)
                # Apply source overwrites
                for t, ow in source.overwrites.items():
                    await target.set_permissions(t, overwrite=ow)
                copied_count = len(source.overwrites)

            after_state = serialize_channel_overwrites(target)
            action_id = log_undo_action(interaction.guild.id, "channel_perms", target.id, target.name, {"overwrites": before_state}, {"overwrites": after_state}, interaction.user.id)

            embed = discord.Embed(
                title="🛡️ Channel Permissions Replicated",
                description=f"Source: {source.mention}\nTarget: {target.mention}",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.add_field(name="Mode", value=f"`{apply_mode.upper()}`", inline=True)
            embed.add_field(name="Entities Copied", value=f"`{copied_count}` {'roles/members' if not role else f'Role: @{role.name}'}", inline=True)
            embed.set_footer(text=f"Undo Action ID: {action_id}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to copy permissions: `{e}`")

    # 4. /channel permtemplate (Top 2 Priority)
    @channel_group.command(name="permtemplate", description="Save, apply, list or delete reusable channel permission templates")
    @app_commands.describe(
        action="save (save channel perms), apply (apply to channel), list, delete",
        template_name="Template identifier name",
        channel="Channel to save from or apply to"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Save (Capture channel permissions as template)", value="save"),
        app_commands.Choice(name="Apply (Apply saved template to channel)", value="apply"),
        app_commands.Choice(name="List (Show all saved guild templates)", value="list"),
        app_commands.Choice(name="Delete (Remove a saved template)", value="delete")
    ])
    async def channel_permtemplate(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        template_name: typing.Optional[str] = None,
        channel: typing.Optional[discord.abc.GuildChannel] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        act = action.value
        guild_id = str(interaction.guild.id)
        conn = get_db()
        cursor = conn.cursor()

        if act == "list":
            cursor.execute("SELECT template_name, created_by, created_at FROM channel_perm_templates WHERE guild_id = ?", (guild_id,))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return await interaction.followup.send("ℹ️ No channel permission templates saved for this server.")

            embed = discord.Embed(title="📋 Saved Channel Permission Templates", color=discord.Color(THEME_PURPLE))
            for r in rows:
                creator = interaction.guild.get_member(int(r[1])) if r[1] and r[1].isdigit() else None
                creator_str = creator.name if creator else "Admin"
                embed.add_field(name=f"📦 {r[0]}", value=f"Created by: `{creator_str}` • Date: `{r[2][:10]}`", inline=False)
            return await interaction.followup.send(embed=embed)

        if not template_name:
            conn.close()
            return await interaction.followup.send("⚠️ Please provide a `template_name` for this operation.")

        t_name = template_name.strip().lower()

        if act == "save":
            target_ch = channel or interaction.channel
            serialized = serialize_channel_overwrites(target_ch)
            cursor.execute("""
                INSERT OR REPLACE INTO channel_perm_templates (guild_id, template_name, overwrites_json, created_by, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (guild_id, t_name, json.dumps(serialized), str(interaction.user.id)))
            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="💾 Template Saved",
                description=f"Saved `{len(serialized)}` role/member overwrites from {target_ch.mention} as template **`{t_name}`**.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text="Use '/channel permtemplate apply' to deploy to any channel.")
            return await interaction.followup.send(embed=embed)

        elif act == "apply":
            target_ch = channel or interaction.channel
            cursor.execute("SELECT overwrites_json FROM channel_perm_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return await interaction.followup.send(f"❌ Template **`{t_name}`** not found.")

            data = json.loads(row[0])
            before_state = serialize_channel_overwrites(target_ch)
            await apply_serialized_overwrites(target_ch, data, mode="replace")
            after_state = serialize_channel_overwrites(target_ch)
            action_id = log_undo_action(interaction.guild.id, "perm_template_apply", target_ch.id, target_ch.name, {"overwrites": before_state}, {"overwrites": after_state}, interaction.user.id)

            embed = discord.Embed(
                title="🚀 Template Applied",
                description=f"Applied template **`{t_name}`** (`{len(data)}` overwrites) to {target_ch.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=f"Undo Action ID: {action_id}")
            return await interaction.followup.send(embed=embed)

        elif act == "delete":
            cursor.execute("DELETE FROM channel_perm_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            conn.commit()
            conn.close()
            return await interaction.followup.send(f"🗑️ Deleted template **`{t_name}`**.")

    # 5. /channel compare (Top 5 Priority)
    @channel_group.command(name="compare", description="Side-by-side comparison of 2 channels (permissions, slowmode, topic)")
    @app_commands.describe(channel1="First channel", channel2="Second channel")
    async def channel_compare(interaction: discord.Interaction, channel1: discord.abc.GuildChannel, channel2: discord.abc.GuildChannel):
        await interaction.response.defer()

        c1_cat = channel1.category.name if channel1.category else "None"
        c2_cat = channel2.category.name if channel2.category else "None"
        c1_topic = getattr(channel1, "topic", "N/A") or "None"
        c2_topic = getattr(channel2, "topic", "N/A") or "None"
        c1_slow = getattr(channel1, "slowmode_delay", 0)
        c2_slow = getattr(channel2, "slowmode_delay", 0)

        embed = discord.Embed(
            title=f"⚖️ Channel Comparison: #{channel1.name} vs #{channel2.name}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="Category", value=f"**#{channel1.name}:** `{c1_cat}`\n**#{channel2.name}:** `{c2_cat}`", inline=True)
        embed.add_field(name="Slowmode", value=f"**#{channel1.name}:** `{c1_slow}s`\n**#{channel2.name}:** `{c2_slow}s`", inline=True)
        embed.add_field(name="Type", value=f"**#{channel1.name}:** `{channel1.type}`\n**#{channel2.name}:** `{channel2.type}`", inline=True)

        # Compare Overwrites
        c1_targets = {t.name for t in channel1.overwrites.keys()}
        c2_targets = {t.name for t in channel2.overwrites.keys()}

        common = c1_targets & c2_targets
        only_c1 = c1_targets - c2_targets
        only_c2 = c2_targets - c1_targets

        perm_summary = [
            f"• **Matching Entities ({len(common)}):** {', '.join(list(common)[:5]) if common else 'None'}",
            f"• **Only in #{channel1.name} ({len(only_c1)}):** {', '.join(list(only_c1)[:5]) if only_c1 else 'None'}",
            f"• **Only in #{channel2.name} ({len(only_c2)}):** {', '.join(list(only_c2)[:5]) if only_c2 else 'None'}"
        ]
        embed.add_field(name="Permission Overwrites Diff", value="\n".join(perm_summary), inline=False)
        await interaction.followup.send(embed=embed)

    # 6. /channel movebulk
    @channel_group.command(name="movebulk", description="Bulk move channels into a target category")
    @app_commands.describe(category="Target category", query="Filter keyword in channel name (leave empty for all)")
    async def channel_movebulk(interaction: discord.Interaction, category: discord.CategoryChannel, query: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        moved = 0
        q = query.lower() if query else None
        for ch in interaction.guild.channels:
            if isinstance(ch, discord.CategoryChannel) or ch.category_id == category.id:
                continue
            if not q or q in ch.name.lower():
                try:
                    await ch.edit(category=category)
                    moved += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="📦 Bulk Channel Migration",
            description=f"Moved **`{moved}`** channels into category **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 7. /channel renamebulk
    @channel_group.command(name="renamebulk", description="Bulk rename channels using naming patterns (e.g. ticket-{n})")
    @app_commands.describe(pattern="Naming pattern with {n} counter, e.g. room-{n}", category="Category to apply inside")
    async def channel_renamebulk(interaction: discord.Interaction, pattern: str, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        renamed = 0
        idx = 1
        for ch in category.channels:
            new_title = pattern.replace("{n}", str(idx)).replace("{name}", ch.name)
            try:
                await ch.edit(name=new_title)
                renamed += 1
                idx += 1
            except Exception:
                pass

        embed = discord.Embed(
            title="✏️ Bulk Rename Complete",
            description=f"Renamed **`{renamed}`** channels in category **{category.name}** with pattern `{pattern}`.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 8. /channel topicbulk
    @channel_group.command(name="topicbulk", description="Bulk set or update topic across all text channels in a category")
    @app_commands.describe(category="Category to update", topic="New topic description")
    async def channel_topicbulk(interaction: discord.Interaction, category: discord.CategoryChannel, topic: str):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        updated = 0
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                try:
                    await ch.edit(topic=topic)
                    updated += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="📝 Bulk Topic Update",
            description=f"Applied topic to **`{updated}`** text channels in **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.add_field(name="Topic", value=f"`{topic}`", inline=False)
        await interaction.followup.send(embed=embed)

    # 9. /channel slowmodebulk
    @channel_group.command(name="slowmodebulk", description="Bulk apply slowmode delay across channels in a category")
    @app_commands.describe(category="Target category", seconds="Cooldown in seconds (0 to disable)")
    async def channel_slowmodebulk(interaction: discord.Interaction, category: discord.CategoryChannel, seconds: int):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        count = 0
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                try:
                    await ch.edit(slowmode_delay=seconds)
                    count += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="⏱️ Bulk Slowmode Configured",
            description=f"Configured `{seconds}s` slowmode for **`{count}`** channels in **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 10. /channel nsfw
    @channel_group.command(name="nsfw", description="Enable or disable age-restricted (NSFW) flag for a text channel")
    @app_commands.describe(channel="Target channel", enabled="Enable (True) or Disable (False)")
    async def channel_nsfw(interaction: discord.Interaction, channel: discord.TextChannel, enabled: bool):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        try:
            await channel.edit(nsfw=enabled)
            embed = discord.Embed(
                title="🔞 Channel NSFW State Updated",
                description=f"{channel.mention} is now marked as **{'NSFW (Age-Restricted)' if enabled else 'Family Friendly / Standard'}**.",
                color=discord.Color(THEME_SUCCESS if not enabled else THEME_WARNING)
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update NSFW status: `{e}`")

    # 11. /channel typeinfo
    @channel_group.command(name="typeinfo", description="Detailed forensic report of channel type, overwrites, slowmode, and category")
    @app_commands.describe(channel="Target channel")
    async def channel_typeinfo(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"🔍 Channel Audit Dossier: #{channel.name}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="Type", value=f"`{channel.type}`", inline=True)
        embed.add_field(name="Position", value=f"`{channel.position}`", inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "`None`", inline=True)

        if isinstance(channel, discord.TextChannel):
            embed.add_field(name="Slowmode", value=f"`{channel.slowmode_delay}s`", inline=True)
            embed.add_field(name="NSFW", value="🟢 True" if channel.nsfw else "⚪ False", inline=True)
            embed.add_field(name="Topic", value=f"`{channel.topic or 'None'}`", inline=False)

        role_count = sum(1 for t in channel.overwrites.keys() if isinstance(t, discord.Role))
        member_count = sum(1 for t in channel.overwrites.keys() if isinstance(t, discord.Member))
        embed.add_field(name="Permission Overwrites", value=f"Roles: `{role_count}` • Members: `{member_count}`", inline=False)
        embed.set_footer(text=f"Created At: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await interaction.followup.send(embed=embed)

    # 12. /channel restore
    @channel_group.command(name="restore", description="Restore channel configuration or overwrites from an undo action ID")
    @app_commands.describe(action_id="Transaction action ID (from previous operations)")
    async def channel_restore(interaction: discord.Interaction, action_id: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT target_id, before_state, action_type FROM customization_undo_log WHERE action_id = ? AND guild_id = ?", (action_id, str(interaction.guild.id)))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return await interaction.followup.send("❌ Action ID not found in server undo ledger.")

        target_ch_id = int(row[0])
        before_state = json.loads(row[1])
        act_type = row[2]
        ch = interaction.guild.get_channel(target_ch_id)

        if not ch:
            return await interaction.followup.send("⚠️ Target channel no longer exists on this server.")

        try:
            if "overwrites" in before_state:
                await apply_serialized_overwrites(ch, before_state["overwrites"], mode="replace")
            if "topic" in before_state:
                await ch.edit(topic=before_state.get("topic"), slowmode_delay=before_state.get("slowmode", 0), nsfw=before_state.get("nsfw", False))

            embed = discord.Embed(
                title="🔄 State Restored",
                description=f"Successfully reverted changes for {ch.mention} using ledger `{action_id}`.",
                color=discord.Color(THEME_SUCCESS)
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Restoration failed: `{e}`")


# ── 4. CATEGORY CUSTOMIZATION COMMANDS (8 COMMANDS) ──────────────────────────
def register_category_customization(category_group: app_commands.Group, bot: commands.Bot):

    # 13. /category clone
    @category_group.command(name="clone", description="Clone category and its child channels with full permission structures")
    @app_commands.describe(category="Category to clone", name="New category title")
    async def category_clone(interaction: discord.Interaction, category: discord.CategoryChannel, name: typing.Optional[str] = None):
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

            embed = discord.Embed(
                title="📁 Category & Channels Cloned",
                description=f"Cloned **{category.name}** into **{new_cat.name}** (`{new_cat.id}`).\nCreated `{created_channels}` child channels with identical permission overwrites.",
                color=discord.Color(THEME_SUCCESS)
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Category clone failed: `{e}`")

    # 14. /category copyperms
    @category_group.command(name="copyperms", description="Copy category permission overwrites to another category")
    @app_commands.describe(source="Source category", target="Target category to update")
    async def category_copyperms(interaction: discord.Interaction, source: discord.CategoryChannel, target: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        try:
            for t in list(target.overwrites.keys()):
                await target.set_permissions(t, overwrite=None)
            for t, ow in source.overwrites.items():
                await target.set_permissions(t, overwrite=ow)

            embed = discord.Embed(
                title="🛡️ Category Permissions Replicated",
                description=f"Copied `{len(source.overwrites)}` permission overwrites from **{source.name}** to **{target.name}**.",
                color=discord.Color(THEME_SUCCESS)
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to copy category permissions: `{e}`")

    # 15. /category syncall
    @category_group.command(name="syncall", description="Sync all child channels to category permissions")
    @app_commands.describe(category="Category whose channels will be synced")
    async def category_syncall(interaction: discord.Interaction, category: discord.CategoryChannel):
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

        embed = discord.Embed(
            title="🔄 Category Channels Synced",
            description=f"Successfully synced `{synced}` channels with **{category.name}** permissions.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 16. /category movechannels
    @category_group.command(name="movechannels", description="Move selected channels into a category")
    @app_commands.describe(category="Destination category", keyword="Filter keyword in channel name")
    async def category_movechannels(interaction: discord.Interaction, category: discord.CategoryChannel, keyword: str):
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
            title="📦 Channels Relocated",
            description=f"Moved `{moved}` channels matching `{keyword}` into **{category.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 17. /category renamebulk
    @category_group.command(name="renamebulk", description="Bulk rename categories with prefix/suffix formatting")
    @app_commands.describe(prefix="Optional prefix (e.g. '📂 ')", suffix="Optional suffix")
    async def category_renamebulk(interaction: discord.Interaction, prefix: typing.Optional[str] = "", suffix: typing.Optional[str] = ""):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        count = 0
        for cat in interaction.guild.categories:
            new_title = f"{prefix}{cat.name}{suffix}"
            try:
                await cat.edit(name=new_title)
                count += 1
            except Exception:
                pass

        embed = discord.Embed(
            title="✏️ Bulk Category Rename",
            description=f"Updated `{count}` categories with prefix `{prefix}` and suffix `{suffix}`.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 18. /category lockall
    @category_group.command(name="lockall", description="Lock all text channels in a category, saving original overwrites for undo")
    @app_commands.describe(category="Category to lock down")
    async def category_lockall(interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()
        locked = 0

        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                # Save original overwrite
                serialized = serialize_channel_overwrites(ch)
                cursor.execute("""
                    INSERT OR REPLACE INTO category_lock_states (channel_id, category_id, guild_id, original_overwrites, locked_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (str(ch.id), str(category.id), str(guild.id), json.dumps(serialized)))

                ow = ch.overwrites_for(guild.default_role)
                ow.send_messages = False
                try:
                    await ch.set_permissions(guild.default_role, overwrite=ow)
                    locked += 1
                except Exception:
                    pass

        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="🔒 Category Lockdown Engaged",
            description=f"Sealed `{locked}` text channels in **{category.name}**.\nOriginal permissions saved to ledger for instant restoration.",
            color=discord.Color(THEME_ERROR)
        )
        embed.set_footer(text="Use '/category unlockall' to restore exact previous states.")
        await interaction.followup.send(embed=embed)

    # 19. /category unlockall
    @category_group.command(name="unlockall", description="Restore category channels to exact pre-lockdown permissions")
    @app_commands.describe(category="Category to unlock")
    async def category_unlockall(interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, original_overwrites FROM category_lock_states WHERE category_id = ?", (str(category.id),))
        rows = cursor.fetchall()

        restored = 0
        for r in rows:
            ch_id = int(r[0])
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                try:
                    data = json.loads(r[1])
                    await apply_serialized_overwrites(ch, data, mode="replace")
                    restored += 1
                except Exception:
                    pass

        cursor.execute("DELETE FROM category_lock_states WHERE category_id = ?", (str(category.id),))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="🔓 Category Lockdown Lifted",
            description=f"Restored `{restored}` channels in **{category.name}** to their pre-lockdown permission state.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 20. /category template (Top 3 Priority)
    @category_group.command(name="template", description="Save, apply, list or delete category + child channel layout templates")
    @app_commands.describe(
        action="save (save structure), apply (create from template), list, delete",
        template_name="Template identifier",
        category="Category to capture or clone into"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Save (Capture category structure as template)", value="save"),
        app_commands.Choice(name="Apply (Instantiate category from template)", value="apply"),
        app_commands.Choice(name="List (Show saved category templates)", value="list"),
        app_commands.Choice(name="Delete (Remove saved category template)", value="delete")
    ])
    async def category_template(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        template_name: typing.Optional[str] = None,
        category: typing.Optional[discord.CategoryChannel] = None
    ):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        act = action.value
        guild_id = str(interaction.guild.id)
        conn = get_db()
        cursor = conn.cursor()

        if act == "list":
            cursor.execute("SELECT template_name, created_by, created_at FROM category_templates WHERE guild_id = ?", (guild_id,))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return await interaction.followup.send("ℹ️ No category templates saved for this server.")

            embed = discord.Embed(title="📁 Saved Category Structure Templates", color=discord.Color(THEME_PURPLE))
            for r in rows:
                embed.add_field(name=f"📦 {r[0]}", value=f"Saved on `{r[2][:10]}`", inline=False)
            return await interaction.followup.send(embed=embed)

        if not template_name:
            conn.close()
            return await interaction.followup.send("⚠️ Please provide a `template_name`.")

        t_name = template_name.strip().lower()

        if act == "save":
            if not category:
                conn.close()
                return await interaction.followup.send("⚠️ Please specify a category to capture.")

            structure = {
                "category_name": category.name,
                "overwrites": serialize_channel_overwrites(category),
                "channels": []
            }
            for ch in category.channels:
                structure["channels"].append({
                    "name": ch.name,
                    "type": str(ch.type),
                    "topic": getattr(ch, "topic", None),
                    "slowmode": getattr(ch, "slowmode_delay", 0),
                    "nsfw": getattr(ch, "nsfw", False),
                    "overwrites": serialize_channel_overwrites(ch)
                })

            cursor.execute("""
                INSERT OR REPLACE INTO category_templates (guild_id, template_name, structure_json, created_by, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (guild_id, t_name, json.dumps(structure), str(interaction.user.id)))
            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="💾 Category Template Saved",
                description=f"Saved blueprint **`{t_name}`** with **`{len(structure['channels'])}`** child channels from **{category.name}**.",
                color=discord.Color(THEME_SUCCESS)
            )
            return await interaction.followup.send(embed=embed)

        elif act == "apply":
            cursor.execute("SELECT structure_json FROM category_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return await interaction.followup.send(f"❌ Template **`{t_name}`** not found.")

            blueprint = json.loads(row[0])
            guild = interaction.guild
            new_cat = await guild.create_category(name=blueprint["category_name"])
            await apply_serialized_overwrites(new_cat, blueprint["overwrites"], mode="replace")

            spawned = 0
            for c_info in blueprint["channels"]:
                if c_info["type"] == "ChannelType.text":
                    new_ch = await guild.create_text_channel(
                        name=c_info["name"],
                        category=new_cat,
                        topic=c_info.get("topic"),
                        slowmode_delay=c_info.get("slowmode", 0),
                        nsfw=c_info.get("nsfw", False)
                    )
                    await apply_serialized_overwrites(new_ch, c_info["overwrites"], mode="replace")
                    spawned += 1
                elif c_info["type"] == "ChannelType.voice":
                    new_ch = await guild.create_voice_channel(
                        name=c_info["name"],
                        category=new_cat
                    )
                    await apply_serialized_overwrites(new_ch, c_info["overwrites"], mode="replace")
                    spawned += 1

            embed = discord.Embed(
                title="🚀 Category Template Deployed",
                description=f"Instantiated category **{new_cat.name}** with `{spawned}` channels from template **`{t_name}`**.",
                color=discord.Color(THEME_SUCCESS)
            )
            return await interaction.followup.send(embed=embed)

        elif act == "delete":
            cursor.execute("DELETE FROM category_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            conn.commit()
            conn.close()
            return await interaction.followup.send(f"🗑️ Deleted category template **`{t_name}`**.")


# ── 5. ROLE CUSTOMIZATION COMMANDS (10 COMMANDS) ─────────────────────────────
def register_role_customization(role_group: app_commands.Group, bot: commands.Bot):

    # 21. /role clone
    @role_group.command(name="clone", description="Clone existing role settings, color, hoist, and permissions")
    @app_commands.describe(role="Role to clone", name="New role name")
    async def role_clone(interaction: discord.Interaction, role: discord.Role, name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        if role >= guild.me.top_role:
            return await interaction.followup.send("❌ Cannot clone a role equal to or higher than the bot's top role.")

        new_name = name or f"{role.name}-copy"
        try:
            new_role = await guild.create_role(
                name=new_name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            embed = discord.Embed(
                title="🎭 Role Cloned Successfully",
                description=f"Source: {role.mention} (`{role.id}`)\nNew Role: {new_role.mention} (`{new_role.id}`)",
                color=new_role.color
            )
            embed.add_field(name="Color Hex", value=f"`{str(role.color)}`", inline=True)
            embed.add_field(name="Permissions Value", value=f"`{role.permissions.value}`", inline=True)
            embed.add_field(name="Hoist", value="🟢 True" if role.hoist else "⚪ False", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to clone role: `{e}`")

    # 22. /role copyperms
    @role_group.command(name="copyperms", description="Copy permission flags from source role to target role")
    @app_commands.describe(source="Source role with desired permissions", target="Target role to update")
    async def role_copyperms(interaction: discord.Interaction, source: discord.Role, target: discord.Role):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        if target >= guild.me.top_role:
            return await interaction.followup.send("❌ Cannot modify a role equal to or higher than the bot's top role.")

        before_val = target.permissions.value
        try:
            await target.edit(permissions=source.permissions)
            embed = discord.Embed(
                title="🛡️ Role Permissions Replicated",
                description=f"Copied all permissions from {source.mention} to {target.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.add_field(name="Previous Value", value=f"`{before_val}`", inline=True)
            embed.add_field(name="New Value", value=f"`{source.permissions.value}`", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Role permissions update failed: `{e}`")

    # 23. /role template (Top 4 Priority)
    @role_group.command(name="template", description="Save, apply, list or delete reusable role templates")
    @app_commands.describe(
        action="save (save role as template), apply (apply to role), list, delete",
        template_name="Template identifier",
        role="Target role"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Save (Save role config as template)", value="save"),
        app_commands.Choice(name="Apply (Apply template to role or create new)", value="apply"),
        app_commands.Choice(name="List (Show saved role templates)", value="list"),
        app_commands.Choice(name="Delete (Remove saved role template)", value="delete")
    ])
    async def role_template(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        template_name: typing.Optional[str] = None,
        role: typing.Optional[discord.Role] = None
    ):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        act = action.value
        guild_id = str(interaction.guild.id)
        conn = get_db()
        cursor = conn.cursor()

        if act == "list":
            cursor.execute("SELECT template_name, color_hex, hoist, mentionable FROM role_templates WHERE guild_id = ?", (guild_id,))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return await interaction.followup.send("ℹ️ No role templates saved for this server.")

            embed = discord.Embed(title="🎭 Saved Role Templates", color=discord.Color(THEME_PURPLE))
            for r in rows:
                embed.add_field(name=f"📦 {r[0]}", value=f"Color: `{r[1]}` • Hoist: `{'Yes' if r[2] else 'No'}`", inline=False)
            return await interaction.followup.send(embed=embed)

        if not template_name:
            conn.close()
            return await interaction.followup.send("⚠️ Please provide a `template_name`.")

        t_name = template_name.strip().lower()

        if act == "save":
            if not role:
                conn.close()
                return await interaction.followup.send("⚠️ Please provide a `role` to capture.")

            cursor.execute("""
                INSERT OR REPLACE INTO role_templates (guild_id, template_name, permissions_value, color_hex, hoist, mentionable, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (guild_id, t_name, role.permissions.value, str(role.color), 1 if role.hoist else 0, 1 if role.mentionable else 0, str(interaction.user.id)))
            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="💾 Role Template Saved",
                description=f"Saved configuration from {role.mention} as template **`{t_name}`**.",
                color=discord.Color(THEME_SUCCESS)
            )
            return await interaction.followup.send(embed=embed)

        elif act == "apply":
            cursor.execute("SELECT permissions_value, color_hex, hoist, mentionable FROM role_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return await interaction.followup.send(f"❌ Role template **`{t_name}`** not found.")

            perms_val, color_hex, hoist_val, mention_val = row
            perms = discord.Permissions(perms_val)
            color = discord.Color(int(color_hex.lstrip("#"), 16)) if color_hex.startswith("#") else discord.Color.default()

            if role:
                if role >= interaction.guild.me.top_role:
                    return await interaction.followup.send("❌ Cannot modify a role equal to or higher than the bot's top role.")
                await role.edit(permissions=perms, color=color, hoist=bool(hoist_val), mentionable=bool(mention_val))
                target_role = role
            else:
                target_role = await interaction.guild.create_role(name=t_name.title(), permissions=perms, color=color, hoist=bool(hoist_val), mentionable=bool(mention_val))

            embed = discord.Embed(
                title="🚀 Role Template Applied",
                description=f"Applied template **`{t_name}`** to {target_role.mention}.",
                color=target_role.color
            )
            return await interaction.followup.send(embed=embed)

        elif act == "delete":
            cursor.execute("DELETE FROM role_templates WHERE guild_id = ? AND template_name = ?", (guild_id, t_name))
            conn.commit()
            conn.close()
            return await interaction.followup.send(f"🗑️ Deleted role template **`{t_name}`**.")

    # 24. /role renamebulk
    @role_group.command(name="renamebulk", description="Bulk rename roles using custom naming patterns")
    @app_commands.describe(search="Keyword to search in role names", replace_with="Replacement text")
    async def role_renamebulk(interaction: discord.Interaction, search: str, replace_with: str):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        count = 0
        for r in interaction.guild.roles:
            if r < interaction.guild.me.top_role and search.lower() in r.name.lower():
                new_title = r.name.replace(search, replace_with)
                try:
                    await r.edit(name=new_title)
                    count += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="✏️ Bulk Role Rename",
            description=f"Renamed `{count}` roles replacing `{search}` with `{replace_with}`.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 25. /role colorbulk
    @role_group.command(name="colorbulk", description="Bulk apply color hex across roles matching keyword")
    @app_commands.describe(color_hex="Hex code (e.g. #a855f7)", keyword="Filter keyword in role names")
    async def role_colorbulk(interaction: discord.Interaction, color_hex: str, keyword: str):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        clean_hex = color_hex.lstrip("#")
        try:
            col = discord.Color(int(clean_hex, 16))
        except ValueError:
            return await interaction.followup.send("❌ Invalid hexadecimal color string.")

        count = 0
        kw = keyword.lower()
        for r in interaction.guild.roles:
            if r < interaction.guild.me.top_role and kw in r.name.lower():
                try:
                    await r.edit(color=col)
                    count += 1
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎨 Bulk Role Colors Updated",
            description=f"Set color `{color_hex}` for `{count}` roles matching `{keyword}`.",
            color=col
        )
        await interaction.followup.send(embed=embed)

    # 26. /role permissions
    @role_group.command(name="permissions", description="Interactive role permission inspector and dangerous flags analyzer")
    @app_commands.describe(role="Role to inspect")
    async def role_permissions(interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()

        perms = role.permissions
        dangerous = []
        if perms.administrator: dangerous.append("⚠️ Administrator")
        if perms.manage_guild: dangerous.append("⚠️ Manage Server")
        if perms.manage_roles: dangerous.append("⚠️ Manage Roles")
        if perms.manage_channels: dangerous.append("⚠️ Manage Channels")
        if perms.ban_members: dangerous.append("🔨 Ban Members")
        if perms.kick_members: dangerous.append("👢 Kick Members")
        if perms.mention_everyone: dangerous.append("📢 Mention Everyone")
        if perms.manage_webhooks: dangerous.append("🔗 Manage Webhooks")

        embed = discord.Embed(
            title=f"🛡️ Role Permission Profile: @{role.name}",
            color=role.color if role.color.value != 0 else discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="Members Count", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="Raw Bitfield", value=f"`{perms.value}`", inline=True)
        embed.add_field(name="Hoist", value="🟢 True" if role.hoist else "⚪ False", inline=True)
        embed.add_field(name="Mentionable", value="🟢 True" if role.mentionable else "⚪ False", inline=True)

        if dangerous:
            embed.add_field(name="🚨 Elevated / Dangerous Permissions", value="\n".join(dangerous), inline=False)
        else:
            embed.add_field(name="🔒 Elevated Permissions", value="None (Standard Member Role)", inline=False)

        await interaction.followup.send(embed=embed)

    # 27. /role compare
    @role_group.command(name="compare", description="Side-by-side comparison of 2 server roles")
    @app_commands.describe(role1="First role", role2="Second role")
    async def role_compare(interaction: discord.Interaction, role1: discord.Role, role2: discord.Role):
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"⚖️ Role Comparison: @{role1.name} vs @{role2.name}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(name="Color", value=f"**@{role1.name}:** `{str(role1.color)}`\n**@{role2.name}:** `{str(role2.color)}`", inline=True)
        embed.add_field(name="Position", value=f"**@{role1.name}:** `{role1.position}`\n**@{role2.name}:** `{role2.position}`", inline=True)
        embed.add_field(name="Members", value=f"**@{role1.name}:** `{len(role1.members)}`\n**@{role2.name}:** `{len(role2.members)}`", inline=True)

        p1_flags = {p for p, val in role1.permissions if val}
        p2_flags = {p for p, val in role2.permissions if val}

        only_p1 = p1_flags - p2_flags
        only_p2 = p2_flags - p1_flags

        embed.add_field(name=f"Exclusive to @{role1.name} ({len(only_p1)})", value=", ".join(list(only_p1)[:8]) if only_p1 else "None", inline=False)
        embed.add_field(name=f"Exclusive to @{role2.name} ({len(only_p2)})", value=", ".join(list(only_p2)[:8]) if only_p2 else "None", inline=False)
        await interaction.followup.send(embed=embed)

    # 28. /role reorder
    @role_group.command(name="reorder", description="Reorder role position safely within bot hierarchy limits")
    @app_commands.describe(role="Role to move", position="New integer position number")
    async def role_reorder(interaction: discord.Interaction, role: discord.Role, position: int):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        if role >= guild.me.top_role:
            return await interaction.followup.send("❌ Cannot reorder a role equal to or higher than the bot's top role.")

        max_pos = guild.me.top_role.position - 1
        target_pos = max(1, min(position, max_pos))

        try:
            positions = {role: target_pos}
            await guild.edit_role_positions(positions=positions)
            embed = discord.Embed(
                title="✅ Role Position Updated",
                description=f"Moved {role.mention} to position `{target_pos}`.",
                color=discord.Color(THEME_SUCCESS)
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reorder role: `{e}`")

    # 29. /role cleanup
    @role_group.command(name="cleanup", description="Identify and clean up unused roles with 0 members")
    @app_commands.describe(confirm="Set to True to execute actual deletion")
    async def role_cleanup(interaction: discord.Interaction, confirm: bool = False):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        empty_roles = [
            r for r in guild.roles
            if len(r.members) == 0 and not r.is_default() and not r.managed and r < guild.me.top_role
        ]

        if not confirm:
            names = [f"• **@{r.name}** (`{r.id}`)" for r in empty_roles[:15]]
            embed = discord.Embed(
                title=f"🧹 Role Cleanup Preview ({len(empty_roles)} Unused Roles)",
                description="\n".join(names) if names else "No unused or empty roles found on this server.",
                color=discord.Color(THEME_WARNING)
            )
            embed.set_footer(text="Run with confirm=True to permanently delete these empty roles.")
            return await interaction.followup.send(embed=embed)

        deleted = 0
        for r in empty_roles:
            try:
                await r.delete()
                deleted += 1
            except Exception:
                pass

        embed = discord.Embed(
            title="🗑️ Role Cleanup Executed",
            description=f"Permanently purged **`{deleted}`** empty roles from the server.",
            color=discord.Color(THEME_SUCCESS)
        )
        await interaction.followup.send(embed=embed)

    # 30. /role restore
    @role_group.command(name="restore", description="Recreate a deleted or corrupted role from saved template")
    @app_commands.describe(template_name="Template name to restore from", new_name="Optional new role name")
    async def role_restore(interaction: discord.Interaction, template_name: str, new_name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT permissions_value, color_hex, hoist, mentionable FROM role_templates WHERE guild_id = ? AND template_name = ?", (str(interaction.guild.id), template_name.lower().strip()))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return await interaction.followup.send(f"❌ No template found with name **`{template_name}`**.")

        perms_val, color_hex, hoist_val, mention_val = row
        perms = discord.Permissions(perms_val)
        color = discord.Color(int(color_hex.lstrip("#"), 16)) if color_hex.startswith("#") else discord.Color.default()
        r_name = new_name or template_name.title()

        try:
            role = await interaction.guild.create_role(name=r_name, permissions=perms, color=color, hoist=bool(hoist_val), mentionable=bool(mention_val))
            embed = discord.Embed(
                title="🔄 Role Restored & Recreated",
                description=f"Spawned {role.mention} (`{role.id}`) with exact historical permissions and color.\n\n⚠️ *Note: Per Discord architecture, the historical role ID was newly allocated and previous members must be reassigned.*",
                color=role.color
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to restore role: `{e}`")


# ── 6. PREFIX COMMANDS EXTENSION ─────────────────────────────────────────────
def register_customization_prefix_commands(bot: commands.Bot):
    """
    Exposes high-speed prefix commands (.channel, .category, .role, .permcopy, .permcompare, etc.)
    """

    @bot.command(name="permcopy", description="Copy channel permission overwrites")
    @commands.has_permissions(manage_channels=True)
    async def p_permcopy(ctx, source: discord.abc.GuildChannel, target: discord.abc.GuildChannel, mode: str = "replace"):
        for t in list(target.overwrites.keys()):
            if mode == "replace":
                await target.set_permissions(t, overwrite=None)
        for t, ow in source.overwrites.items():
            await target.set_permissions(t, overwrite=ow)
        await ctx.send(f"✅ Replicated `{len(source.overwrites)}` permissions from {source.mention} to {target.mention} (Mode: `{mode.upper()}`).")

    @bot.command(name="permcompare", description="Compare permissions of two channels")
    @commands.has_permissions(manage_channels=True)
    async def p_permcompare(ctx, ch1: discord.abc.GuildChannel, ch2: discord.abc.GuildChannel):
        c1 = {t.name for t in ch1.overwrites.keys()}
        c2 = {t.name for t in ch2.overwrites.keys()}
        common = c1 & c2
        diff = (c1 - c2) | (c2 - c1)
        await ctx.send(f"⚖️ **Comparison:** #{ch1.name} vs #{ch2.name}\n• Common Roles/Members: `{len(common)}`\n• Differing Entities: `{len(diff)}` ({', '.join(list(diff)[:5]) or 'None'})")

    @bot.command(name="channeltemplate", description="Save or apply channel template")
    @commands.has_permissions(manage_channels=True)
    async def p_channeltemplate(ctx, action: str, name: str, channel: discord.abc.GuildChannel = None):
        target = channel or ctx.channel
        conn = get_db()
        cursor = conn.cursor()
        act = action.lower()
        if act == "save":
            data = serialize_channel_overwrites(target)
            cursor.execute("INSERT OR REPLACE INTO channel_perm_templates (guild_id, template_name, overwrites_json, created_by) VALUES (?, ?, ?, ?)", (str(ctx.guild.id), name.lower(), json.dumps(data), str(ctx.author.id)))
            conn.commit()
            await ctx.send(f"💾 Saved template **`{name}`** from {target.mention}.")
        elif act == "apply":
            cursor.execute("SELECT overwrites_json FROM channel_perm_templates WHERE guild_id = ? AND template_name = ?", (str(ctx.guild.id), name.lower()))
            row = cursor.fetchone()
            if not row:
                await ctx.send("❌ Template not found.")
            else:
                await apply_serialized_overwrites(target, json.loads(row[0]), mode="replace")
                await ctx.send(f"🚀 Applied template **`{name}`** to {target.mention}.")
        conn.close()

    @bot.command(name="roletemplate", description="Save or apply role template")
    @commands.has_permissions(manage_roles=True)
    async def p_roletemplate(ctx, action: str, name: str, role: discord.Role = None):
        conn = get_db()
        cursor = conn.cursor()
        act = action.lower()
        if act == "save":
            if not role:
                return await ctx.send("⚠️ Please mention a role.")
            cursor.execute("INSERT OR REPLACE INTO role_templates (guild_id, template_name, permissions_value, color_hex, hoist, mentionable, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(ctx.guild.id), name.lower(), role.permissions.value, str(role.color), 1 if role.hoist else 0, 1 if role.mentionable else 0, str(ctx.author.id)))
            conn.commit()
            await ctx.send(f"💾 Saved role template **`{name}`** from {role.mention}.")
        elif act == "apply":
            cursor.execute("SELECT permissions_value, color_hex, hoist, mentionable FROM role_templates WHERE guild_id = ? AND template_name = ?", (str(ctx.guild.id), name.lower()))
            row = cursor.fetchone()
            if not row:
                await ctx.send("❌ Template not found.")
            else:
                perms_val, color_hex, hoist_val, mention_val = row
                perms = discord.Permissions(perms_val)
                color = discord.Color(int(color_hex.lstrip("#"), 16)) if color_hex.startswith("#") else discord.Color.default()
                if role:
                    await role.edit(permissions=perms, color=color, hoist=bool(hoist_val), mentionable=bool(mention_val))
                    await ctx.send(f"🚀 Applied template **`{name}`** to {role.mention}.")
                else:
                    new_r = await ctx.guild.create_role(name=name.title(), permissions=perms, color=color, hoist=bool(hoist_val), mentionable=bool(mention_val))
                    await ctx.send(f"🚀 Created new role {new_r.mention} from template **`{name}`**.")
        conn.close()

    print("✅ Registered Advanced Channel, Category & Role Customization Commands.")
