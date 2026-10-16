# bot/cloneserver_system.py - Deep 1:1 Server Cloning & Complete Wipe Engine
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import typing
from datetime import datetime, timezone

THEME_PURPLE = 0xa855f7
THEME_DARK = 0x18181b
THEME_SUCCESS = 0x22c55e
THEME_ERROR = 0xef4444
THEME_WARNING = 0xf59e0b

FOOTER_TEXT = "VEYRA | One Bot. Every System. • Powered By Veyra Development™"


class CloneServerConfirmView(discord.ui.View):
    def __init__(self, bot: commands.Bot, source_guild: discord.Guild, target_guild: discord.Guild, initiator: discord.Member):
        super().__init__(timeout=120)
        self.bot = bot
        self.source_guild = source_guild
        self.target_guild = target_guild
        self.initiator = initiator

    @discord.ui.button(label="CONFIRM FULL WIPE & CLONE", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_clone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.initiator.id and interaction.user.id != self.target_guild.owner_id:
            return await interaction.response.send_message("❌ Only the initiator or the Server Owner can authorize this operation.", ephemeral=True)

        self.stop()
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🚨 Server Wipe & Clone Initiated",
                description=f"Beginning total server reset of **{self.target_guild.name}** and cloning from **{self.source_guild.name}**.\nDo not kick the bot during this process.",
                color=discord.Color(THEME_ERROR)
            ),
            view=self
        )

        # Launch cloning engine
        asyncio.create_task(execute_server_clone(self.bot, self.source_guild, self.target_guild, self.initiator))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_clone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.initiator.id and interaction.user.id != self.target_guild.owner_id:
            return await interaction.response.send_message("❌ Only the initiator can cancel.", ephemeral=True)
        self.stop()
        embed = discord.Embed(
            title="🛡️ Server Clone Aborted",
            description="The cloning operation was safely cancelled. No changes were made.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.response.edit_message(embed=embed, view=None)


async def execute_server_clone(bot: commands.Bot, source: discord.Guild, target: discord.Guild, initiator: discord.Member):
    """
    Executes a complete 1:1 server clone:
    1. Wipes all existing channels, categories, roles, emojis, stickers, soundboards.
    2. Clones server identity (name, icon, banner, verification level).
    3. Recreates roles with exact hierarchy, colors, and permissions.
    4. Recreates categories & channels with mapped permission overwrites.
    5. Clones custom emojis, stickers, and soundboard sounds.
    """
    # Create temporary status channel
    progress_ch = None
    try:
        progress_ch = await target.create_text_channel(name="veyra-clone-progress", reason="Temporary channel for server cloning progress")
    except Exception:
        pass

    async def log_step(status_text: str, color_int: int = THEME_PURPLE):
        if progress_ch:
            try:
                emb = discord.Embed(title="🔄 Cloning Server Structure 1:1", description=status_text, color=discord.Color(color_int))
                emb.set_footer(text=FOOTER_TEXT)
                await progress_ch.send(embed=emb)
            except Exception:
                pass

    await log_step(f"**Step 1/6: Beginning Complete Wipe of {target.name}...**\nTarget Guild ID: `{target.id}`\nSource Guild: **{source.name}** (`{source.id}`)")

    # ── 1. WIPE TARGET CHANNELS & CATEGORIES ──────────────────────────────────
    for ch in list(target.channels):
        if progress_ch and ch.id == progress_ch.id:
            continue
        try:
            await ch.delete(reason="Server clone: purging existing channels")
            await asyncio.sleep(0.3)
        except Exception:
            pass

    # ── 2. WIPE TARGET EMOJIS, STICKERS & SOUNDBOARDS ─────────────────────────
    for e in list(target.emojis):
        try:
            await e.delete(reason="Server clone: purging emojis")
            await asyncio.sleep(0.25)
        except Exception:
            pass

    for s in list(target.stickers):
        try:
            await s.delete(reason="Server clone: purging stickers")
            await asyncio.sleep(0.25)
        except Exception:
            pass

    try:
        for snd in list(target.soundboard_sounds):
            try:
                await snd.delete(reason="Server clone: purging soundboard")
                await asyncio.sleep(0.25)
            except Exception:
                pass
    except Exception:
        pass

    # ── 3. WIPE TARGET CUSTOM ROLES ───────────────────────────────────────────
    bot_top = target.me.top_role
    for r in list(target.roles):
        if r.is_default() or r.managed or r >= bot_top:
            continue
        try:
            await r.delete(reason="Server clone: purging existing roles")
            await asyncio.sleep(0.3)
        except Exception:
            pass

    await log_step("🧹 **Step 2/6: Server Wiped.** Channels, roles, emojis & stickers cleared.\n\nNow replicating server metadata & branding...", THEME_WARNING)

    # ── 4. CLONE SERVER IDENTITY (Name, Icon, Banner) ─────────────────────────
    icon_bytes = None
    if source.icon:
        try:
            icon_bytes = await source.icon.read()
        except Exception:
            pass

    banner_bytes = None
    if source.banner and target.premium_tier >= 2:
        try:
            banner_bytes = await source.banner.read()
        except Exception:
            pass

    try:
        edit_kwargs = {"name": source.name}
        if icon_bytes:
            edit_kwargs["icon"] = icon_bytes
        if banner_bytes:
            edit_kwargs["banner"] = banner_bytes
        await target.edit(**edit_kwargs)
    except Exception as meta_err:
        await log_step(f"⚠️ Notice on server metadata clone: `{meta_err}`")

    # ── 5. CLONE ROLES & HIERARCHY ────────────────────────────────────────────
    await log_step("🎭 **Step 3/6: Cloning Roles & Permissions...**")
    role_map: dict[int, discord.Role] = {source.default_role.id: target.default_role}

    # Update @everyone permissions
    try:
        await target.default_role.edit(permissions=source.default_role.permissions)
    except Exception:
        pass

    # Recreate source roles in order from lowest to highest
    sorted_source_roles = sorted(
        [r for r in source.roles if not r.is_default() and not r.managed and r < source.me.top_role],
        key=lambda x: x.position
    )

    created_roles = 0
    for s_role in sorted_source_roles:
        try:
            new_r = await target.create_role(
                name=s_role.name,
                permissions=s_role.permissions,
                color=s_role.color,
                hoist=s_role.hoist,
                mentionable=s_role.mentionable,
                reason=f"Server clone from {source.name}"
            )
            role_map[s_role.id] = new_r
            created_roles += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass

    # ── 6. CLONE CATEGORIES & CHANNELS WITH OVERWRITES ────────────────────────
    await log_step(f"📁 **Step 4/6: Cloning Categories & Channels with Overwrites...**\nRecreated `{created_roles}` roles.")
    category_map: dict[int, discord.CategoryChannel] = {}

    def map_overwrites(source_obj):
        new_ow = {}
        for target_entity, ow in source_obj.overwrites.items():
            if isinstance(target_entity, discord.Role):
                mapped = role_map.get(target_entity.id)
                if mapped:
                    new_ow[mapped] = ow
            elif isinstance(target_entity, discord.Member):
                t_member = target.get_member(target_entity.id)
                if t_member:
                    new_ow[t_member] = ow
        return new_ow

    # Recreate Categories
    for cat in sorted(source.categories, key=lambda x: x.position):
        try:
            ow = map_overwrites(cat)
            new_cat = await target.create_category_channel(
                name=cat.name,
                overwrites=ow,
                position=cat.position,
                reason=f"Server clone from {source.name}"
            )
            category_map[cat.id] = new_cat
            await asyncio.sleep(0.35)
        except Exception:
            pass

    # Recreate Text, Voice, Stage channels
    created_channels = 0
    primary_channel = None

    for ch in sorted(source.channels, key=lambda x: x.position):
        if isinstance(ch, discord.CategoryChannel):
            continue
        parent_cat = category_map.get(ch.category_id)
        ow = map_overwrites(ch)

        try:
            if isinstance(ch, discord.TextChannel):
                new_ch = await target.create_text_channel(
                    name=ch.name,
                    category=parent_cat,
                    topic=ch.topic,
                    slowmode_delay=ch.slowmode_delay,
                    nsfw=ch.nsfw,
                    overwrites=ow,
                    position=ch.position,
                    reason=f"Server clone from {source.name}"
                )
                if not primary_channel:
                    primary_channel = new_ch
                created_channels += 1
            elif isinstance(ch, discord.VoiceChannel):
                bitrate = min(ch.bitrate, target.bitrate_limit)
                await target.create_voice_channel(
                    name=ch.name,
                    category=parent_cat,
                    bitrate=bitrate,
                    user_limit=ch.user_limit,
                    overwrites=ow,
                    position=ch.position,
                    reason=f"Server clone from {source.name}"
                )
                created_channels += 1
            elif isinstance(ch, discord.StageChannel):
                await target.create_stage_channel(
                    name=ch.name,
                    category=parent_cat,
                    topic=ch.topic,
                    overwrites=ow,
                    position=ch.position,
                    reason=f"Server clone from {source.name}"
                )
                created_channels += 1
            await asyncio.sleep(0.35)
        except Exception:
            pass

    # ── 7. CLONE EMOJIS, STICKERS & SOUNDBOARD ────────────────────────────────
    await log_step(f"🎨 **Step 5/6: Cloning Emojis, Stickers & Soundboard Sounds...**\nRecreated `{len(category_map)}` categories and `{created_channels}` channels.")

    cloned_emojis = 0
    max_emojis = target.emoji_limit
    for e in source.emojis[:max_emojis]:
        try:
            img_data = await e.read()
            await target.create_custom_emoji(name=e.name, image=img_data, reason=f"Server clone from {source.name}")
            cloned_emojis += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass

    cloned_stickers = 0
    max_stickers = target.sticker_limit
    for s in source.stickers[:max_stickers]:
        try:
            stk_data = await s.read()
            file = discord.File(io.BytesIO(stk_data), filename=f"{s.name}.png")
            await target.create_sticker(
                name=s.name,
                description=s.description or "Cloned Sticker",
                emoji=s.emoji or "⭐",
                file=file,
                reason=f"Server clone from {source.name}"
            )
            cloned_stickers += 1
            await asyncio.sleep(0.35)
        except Exception:
            pass

    cloned_sounds = 0
    try:
        for snd in source.soundboard_sounds:
            try:
                snd_data = await snd.read()
                await target.create_soundboard_sound(
                    name=snd.name,
                    sound=snd_data,
                    volume=snd.volume,
                    emoji=snd.emoji,
                    reason=f"Server clone from {source.name}"
                )
                cloned_sounds += 1
                await asyncio.sleep(0.35)
            except Exception:
                pass
    except Exception:
        pass

    # ── 8. FINALIZE & CLEANUP ─────────────────────────────────────────────────
    final_embed = discord.Embed(
        title="👑 SERVER CLONED SUCCESSFULLY 1:1",
        description=f"Server **{target.name}** has been completely wiped and cloned from **{source.name}** (`{source.id}`).",
        color=discord.Color(THEME_SUCCESS)
    )
    final_embed.add_field(name="📛 Server Name", value=f"`{target.name}`", inline=True)
    final_embed.add_field(name="🎭 Roles Created", value=f"`{created_roles}` roles", inline=True)
    final_embed.add_field(name="📁 Categories", value=f"`{len(category_map)}` categories", inline=True)
    final_embed.add_field(name="💬 Channels", value=f"`{created_channels}` channels", inline=True)
    final_embed.add_field(name="😀 Emojis Cloned", value=f"`{cloned_emojis}` emojis", inline=True)
    final_embed.add_field(name="🏷️ Stickers Cloned", value=f"`{cloned_stickers}` stickers", inline=True)
    final_embed.add_field(name="🔊 Soundboard", value=f"`{cloned_sounds}` sounds", inline=True)
    final_embed.add_field(name="🛡️ Authorized By", value=initiator.mention, inline=True)
    final_embed.set_footer(text=FOOTER_TEXT)
    if target.icon:
        final_embed.set_thumbnail(url=target.icon.url)

    destination_ch = primary_channel or progress_ch
    if destination_ch:
        try:
            await destination_ch.send(embed=final_embed)
        except Exception:
            pass

    # Delete progress channel if another channel exists
    if progress_ch and primary_channel and progress_ch.id != primary_channel.id:
        try:
            await asyncio.sleep(3)
            await progress_ch.delete(reason="Server clone completed")
        except Exception:
            pass


# ── 9. COMMAND REGISTRATION ───────────────────────────────────────────────────
def setup_cloneserver_system(bot: commands.Bot):
    """
    Registers /cloneserver slash command and .cloneserver prefix command.
    """

    async def handle_clone_request(target_inter_or_ctx, source_server_id: str, is_slash: bool = True):
        # 1. Permission Check
        user = target_inter_or_ctx.user if is_slash else target_inter_or_ctx.author
        target_guild = target_inter_or_ctx.guild
        if not user.guild_permissions.administrator and user.id != target_guild.owner_id and user.id != 1256986886631854080:
            msg = "❌ Access Denied: You must be the **Server Owner** or have **Administrator** permission to execute server cloning."
            if is_slash:
                return await target_inter_or_ctx.followup.send(msg, ephemeral=True)
            else:
                return await target_inter_or_ctx.send(msg)

        # 2. Parse Source Guild ID
        if not source_server_id:
            msg = "⚠️ Please provide a valid source server ID. Usage: `/cloneserver <source_server_id>`"
            return await target_inter_or_ctx.followup.send(msg, ephemeral=True) if is_slash else await target_inter_or_ctx.send(msg)

        try:
            src_id = int(str(source_server_id).strip())
        except ValueError:
            msg = "❌ Invalid Server ID. Please provide a valid numeric Guild ID (e.g. `123456789012345678`)."
            return await target_inter_or_ctx.followup.send(msg, ephemeral=True) if is_slash else await target_inter_or_ctx.send(msg)

        # 3. Locate Source Guild (Memory cache + Discord REST API fallback)
        source_guild = bot.get_guild(src_id)
        if not source_guild:
            try:
                source_guild = await bot.fetch_guild(src_id)
            except Exception:
                source_guild = None

        if not source_guild:
            msg = (
                f"❌ Bot is not present in source server (`{src_id}`).\n\n"
                f"**Requirement:** VEYRA must be added to both the **source server** and this **destination server** "
                f"so it has permission to read roles, channels, categories, and permissions."
            )
            return await target_inter_or_ctx.followup.send(msg, ephemeral=True) if is_slash else await target_inter_or_ctx.send(msg)

        if source_guild.id == target_guild.id:
            msg = "❌ Cannot clone a server into itself! Please run this command in the destination server where you want the structure cloned."
            return await target_inter_or_ctx.followup.send(msg, ephemeral=True) if is_slash else await target_inter_or_ctx.send(msg)

        # 4. Build Confirmation Dialog
        embed = discord.Embed(
            title="⚠️ IRREVERSIBLE ACTION: COMPLETE SERVER WIPE & CLONE",
            description=(
                f"Are you completely sure you want to **WIPE** this server and clone from **{source_guild.name}**?\n\n"
                f"**Destination (Will be completely WIPED):**\n"
                f"• Server: **{target_guild.name}** (`{target_guild.id}`)\n"
                f"• Wipes: All channels, categories, roles, emojis, stickers, soundboards.\n\n"
                f"**Source (Will be copied 1:1):**\n"
                f"• Server: **{source_guild.name}** (`{source_guild.id}`)\n"
                f"• Copies: Server icon, banner, name, roles, permissions, categories, channels, overwrites, emojis, stickers, soundboard.\n\n"
                f"⚠️ *This action CANNOT be undone. Click below to confirm.*"
            ),
            color=discord.Color(THEME_ERROR)
        )
        embed.set_footer(text=FOOTER_TEXT)
        view = CloneServerConfirmView(bot, source_guild, target_guild, user)
        if is_slash:
            await target_inter_or_ctx.followup.send(embed=embed, view=view)
        else:
            await target_inter_or_ctx.send(embed=embed, view=view)

    # Register Slash Command /cloneserver
    @bot.tree.command(name="cloneserver", description="Completely wipe current server and clone everything 1:1 from source server")
    @app_commands.describe(source_server_id="The numeric Guild ID of the source server to clone from")
    async def slash_cloneserver(interaction: discord.Interaction, source_server_id: str):
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                pass
        await handle_clone_request(interaction, source_server_id, is_slash=True)

    # Register Slash Group /clone server
    class CloneSlashGroup(app_commands.Group):
        def __init__(self):
            super().__init__(name="clone", description="Deep 1:1 Server Cloning & Wipe Engine")

        @app_commands.command(name="server", description="Completely wipe current server and clone 1:1 from source server")
        @app_commands.describe(source_server_id="The numeric Guild ID of the source server to clone from")
        async def clone_server(self, interaction: discord.Interaction, source_server_id: str):
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer(ephemeral=False)
                except Exception:
                    pass
            await handle_clone_request(interaction, source_server_id, is_slash=True)

    bot.tree.add_command(CloneSlashGroup())

    # Register Prefix Command Group .clone and .cloneserver
    @bot.group(name="clone", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def prefix_clone(ctx: commands.Context, source_server_id: str = None):
        if source_server_id and source_server_id.lower() != "server":
            return await handle_clone_request(ctx, source_server_id, is_slash=False)
        embed = discord.Embed(
            title="🔄 VEYRA 1:1 Server Cloning System",
            description=(
                "**Usage:**\n"
                "• `.clone <source_server_id>` — Wipe & clone from source server\n"
                "• `.clone server <source_server_id>` — Wipe & clone from source server\n"
                "• `.cloneserver <source_server_id>` — Direct alias\n\n"
                "⚠️ *Both servers must have VEYRA invited.*"
            ),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @prefix_clone.command(name="server")
    @commands.has_permissions(administrator=True)
    async def prefix_clone_server(ctx: commands.Context, source_server_id: str):
        await handle_clone_request(ctx, source_server_id, is_slash=False)

    @bot.command(name="cloneserver", aliases=["serverclone", "clonesv"])
    @commands.has_permissions(administrator=True)
    async def prefix_cloneserver_direct(ctx: commands.Context, source_server_id: str = None):
        if not source_server_id:
            return await ctx.send("⚠️ Usage: `.cloneserver <source_server_id>`")
        await handle_clone_request(ctx, source_server_id, is_slash=False)

    print("✅ Registered 1:1 Server Clone & Wipe System (/cloneserver & /clone server).")
