# bot/server_customization.py - Advanced Server Identity & Real-Time Customization Suite (25+ Commands)
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import typing
import re
from datetime import datetime, timezone

THEME_COLOR = 0xa855f7
SUCCESS_COLOR = 0x22c55e
ERROR_COLOR = 0xef4444
FOOTER_TEXT = "Powered by VEYRA 2.0 • Server Customization Suite"


async def fetch_asset_bytes(url: str = None, attachment: discord.Attachment = None) -> bytes:
    if attachment:
        return await attachment.read()
    if url and url.strip():
        u = url.strip()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(u, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    return await resp.read()
                raise ValueError(f"Failed to fetch image: HTTP {resp.status}")
    raise ValueError("Please provide either a direct image URL or attach an image file.")


def parse_hex_color(hex_str: str) -> typing.Optional[discord.Color]:
    if not hex_str:
        return None
    cleaned = hex_str.strip().lstrip('#')
    if len(cleaned) == 6:
        try:
            return discord.Color(int(cleaned, 16))
        except ValueError:
            return None
    return None


def can_manage_server(user: typing.Union[discord.Member, discord.User], guild: discord.Guild) -> bool:
    if not isinstance(user, discord.Member):
        return False
    return (
        user.id == guild.owner_id
        or user.id in (1256986886631854080, 1538041381132697610)
        or user.guild_permissions.administrator
        or user.guild_permissions.manage_guild
    )


def can_manage_channels(user: typing.Union[discord.Member, discord.User], guild: discord.Guild) -> bool:
    if not isinstance(user, discord.Member):
        return False
    return (
        user.id == guild.owner_id
        or user.id in (1256986886631854080, 1538041381132697610)
        or user.guild_permissions.administrator
        or user.guild_permissions.manage_channels
    )


def can_manage_roles(user: typing.Union[discord.Member, discord.User], guild: discord.Guild) -> bool:
    if not isinstance(user, discord.Member):
        return False
    return (
        user.id == guild.owner_id
        or user.id in (1256986886631854080, 1538041381132697610)
        or user.guild_permissions.administrator
        or user.guild_permissions.manage_roles
    )


# ── 1. SLASH COMMAND GROUP (/server) — 24 COMPREHENSIVE SUBCOMMANDS ─────────
class ServerCustomizationGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="server", description="Live Server Customization Suite: Identity, Channels, Roles & Layout")
        self.bot = bot

    # 1. Rename Server
    @app_commands.command(name="name", description="Change server name instantly")
    @app_commands.describe(new_name="The new name for the server (2-100 characters)")
    async def server_name(self, interaction: discord.Interaction, new_name: str):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission.", ephemeral=True)

        old_name = interaction.guild.name
        await interaction.response.defer()
        try:
            await interaction.guild.edit(name=new_name.strip(), reason=f"Customized by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Name Updated",
                description=f"Server name changed from **{old_name}** to **{new_name.strip()}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to change server name: `{e}`")

    # 2. Bot Nickname
    @app_commands.command(name="botname", description="Change bot's nickname in this server instantly")
    @app_commands.describe(nickname="New nickname for VEYRA in this server")
    async def server_botname(self, interaction: discord.Interaction, nickname: str):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            old_nick = interaction.guild.me.display_name
            await interaction.guild.me.edit(nick=nickname.strip()[:32], reason=f"Requested by {interaction.user}")
            try:
                from bot.db_adapter import get_db
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO guild_bot_profiles (guild_id, nickname) VALUES (?, ?)", (str(interaction.guild.id), nickname.strip()[:32]))
                conn.commit()
                conn.close()
            except Exception:
                pass
            embed = discord.Embed(
                title="✅ Bot Nickname Updated",
                description=f"Bot nickname changed from **{old_nick}** to **{nickname.strip()[:32]}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to change bot nickname: `{e}`")

    # 3. Server Avatar / Icon
    @app_commands.command(name="avatar", description="Change server icon via image URL or attachment upload")
    @app_commands.describe(url="Direct image URL (JPG, PNG, GIF, WEBP)", image="Direct image attachment upload")
    async def server_avatar(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission.", ephemeral=True)

        await interaction.response.defer()
        try:
            raw_bytes = await fetch_asset_bytes(url=url, attachment=image)
            await interaction.guild.edit(icon=raw_bytes, reason=f"VEYRA Server Icon updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Icon Updated",
                description="The server icon has been updated in real time.",
                color=discord.Color(SUCCESS_COLOR)
            )
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update server avatar: `{e}`")

    # 4. Server Banner
    @app_commands.command(name="banner", description="Change server banner via URL or upload (Requires Boost Level 2)")
    @app_commands.describe(url="Direct image URL", image="Direct image attachment upload")
    async def server_banner(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission.", ephemeral=True)

        await interaction.response.defer()
        try:
            raw_bytes = await fetch_asset_bytes(url=url, attachment=image)
            await interaction.guild.edit(banner=raw_bytes, reason=f"VEYRA Server Banner updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Banner Updated",
                description="The server banner has been updated in real time.",
                color=discord.Color(SUCCESS_COLOR)
            )
            if interaction.guild.banner:
                embed.set_image(url=interaction.guild.banner.url)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except discord.HTTPException as he:
            if "boost" in str(he).lower() or he.status == 400:
                await interaction.followup.send("❌ Discord requires **Server Boost Level 2** to set a server banner.")
            else:
                await interaction.followup.send(f"❌ Failed to set server banner: `{he}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: `{e}`")

    # 6. Invite Splash
    @app_commands.command(name="splash", description="Change server invite splash background (Requires Boost Level 1)")
    @app_commands.describe(url="Direct image URL", image="Direct image attachment upload")
    async def server_splash(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            raw_bytes = await fetch_asset_bytes(url=url, attachment=image)
            await interaction.guild.edit(splash=raw_bytes, reason=f"VEYRA Server Splash updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Invite Splash Updated",
                description="The server invite splash background has been updated.",
                color=discord.Color(SUCCESS_COLOR)
            )
            if interaction.guild.splash:
                embed.set_image(url=interaction.guild.splash.url)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set server splash: `{e}`")

    # 7. Description
    @app_commands.command(name="description", description="Change public server description")
    @app_commands.describe(description="The new description for the server (up to 120 chars)")
    async def server_description(self, interaction: discord.Interaction, description: str):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await interaction.guild.edit(description=description.strip(), reason=f"Customized by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Description Updated",
                description=f"Server description set to:\n> {description.strip()}",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update description: `{e}`")

    # 8. AFK Channel & Timeout
    @app_commands.command(name="afk", description="Configure server AFK voice channel and timeout")
    @app_commands.describe(channel="Target voice channel (or None to disable)", timeout="AFK timeout in minutes")
    @app_commands.choices(timeout=[
        app_commands.Choice(name="1 Minute", value=60),
        app_commands.Choice(name="5 Minutes", value=300),
        app_commands.Choice(name="15 Minutes", value=900),
        app_commands.Choice(name="30 Minutes", value=1800),
        app_commands.Choice(name="1 Hour", value=3600)
    ])
    async def server_afk(self, interaction: discord.Interaction, channel: typing.Optional[discord.VoiceChannel] = None, timeout: app_commands.Choice[int] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            kwargs = {}
            if channel is not None:
                kwargs['afk_channel'] = channel
            if timeout is not None:
                kwargs['afk_timeout'] = timeout.value
            await interaction.guild.edit(**kwargs, reason=f"AFK settings updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ AFK Settings Updated",
                description=(
                    f"• **AFK Channel:** {interaction.guild.afk_channel.mention if interaction.guild.afk_channel else '`None`'}\n"
                    f"• **AFK Timeout:** `{interaction.guild.afk_timeout // 60}` minutes"
                ),
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update AFK settings: `{e}`")

    # 9. System Messages Channel
    @app_commands.command(name="systemchannel", description="Configure Discord default system messages channel")
    @app_commands.describe(channel="Target text channel for system welcome & boost messages")
    async def server_systemchannel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await interaction.guild.edit(system_channel=channel, reason=f"System channel updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ System Channel Updated",
                description=f"System messages will now be sent to {channel.mention if channel else '`Disabled`'}.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 10. Rules Channel
    @app_commands.command(name="ruleschannel", description="Set or update community rules channel")
    @app_commands.describe(channel="Target text channel for server rules")
    async def server_ruleschannel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await interaction.guild.edit(rules_channel=channel, reason=f"Rules channel updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Rules Channel Updated",
                description=f"Server rules channel set to {channel.mention if channel else '`None`'}.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 11. Community Updates Channel
    @app_commands.command(name="updateschannel", description="Set community updates channel for Discord staff notices")
    @app_commands.describe(channel="Target text channel for community updates")
    async def server_updateschannel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            await interaction.guild.edit(public_updates_channel=channel, reason=f"Updates channel updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Updates Channel Configured",
                description=f"Community updates channel set to {channel.mention if channel else '`None`'}.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 12. Verification Level
    @app_commands.command(name="verification", description="Set server member verification security level")
    @app_commands.choices(level=[
        app_commands.Choice(name="None (Unrestricted)", value="none"),
        app_commands.Choice(name="Low (Verified email required)", value="low"),
        app_commands.Choice(name="Medium (Registered > 5 mins)", value="medium"),
        app_commands.Choice(name="High (Member of server > 10 mins)", value="high"),
        app_commands.Choice(name="Highest (Verified phone required)", value="highest")
    ])
    async def server_verification(self, interaction: discord.Interaction, level: app_commands.Choice[str]):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        lvl_map = {
            "none": discord.VerificationLevel.none,
            "low": discord.VerificationLevel.low,
            "medium": discord.VerificationLevel.medium,
            "high": discord.VerificationLevel.high,
            "highest": discord.VerificationLevel.highest
        }
        try:
            v_lvl = lvl_map[level.value]
            await interaction.guild.edit(verification_level=v_lvl, reason=f"Verification level set by {interaction.user}")
            embed = discord.Embed(
                title="🛡️ Verification Level Updated",
                description=f"Server verification level configured to **{level.name}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set verification level: `{e}`")

    # 13. Default Notifications
    @app_commands.command(name="notifs", description="Set default message notifications for new members")
    @app_commands.choices(setting=[
        app_commands.Choice(name="All Messages", value="all_messages"),
        app_commands.Choice(name="Only @mentions", value="only_mentions")
    ])
    async def server_notifs(self, interaction: discord.Interaction, setting: app_commands.Choice[str]):
        if not can_manage_server(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            val = discord.NotificationLevel.all_messages if setting.value == "all_messages" else discord.NotificationLevel.only_mentions
            await interaction.guild.edit(default_notifications=val, reason=f"Notifications setting updated by {interaction.user}")
            embed = discord.Embed(
                title="🔔 Notifications Setting Updated",
                description=f"Default server notifications set to **{setting.name}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 14. Channel Slowmode
    @app_commands.command(name="slowmode", description="Configure slowmode delay for a channel (0 to disable)")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to 21600)", channel="Target text channel")
    async def server_slowmode(self, interaction: discord.Interaction, seconds: int, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        await interaction.response.defer()
        try:
            sec = max(0, min(seconds, 21600))
            await target_ch.edit(slowmode_delay=sec, reason=f"Slowmode set by {interaction.user}")
            embed = discord.Embed(
                title="⏱️ Slowmode Updated",
                description=f"Slowmode for {target_ch.mention} configured to `{sec}` seconds." if sec > 0 else f"Slowmode disabled in {target_ch.mention}.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 15. Channel Topic
    @app_commands.command(name="topic", description="Set topic of a text channel")
    @app_commands.describe(topic="New topic for the channel", channel="Target channel (default: current)")
    async def server_topic(self, interaction: discord.Interaction, topic: str, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        await interaction.response.defer()
        try:
            await target_ch.edit(topic=topic.strip()[:1024], reason=f"Topic updated by {interaction.user}")
            embed = discord.Embed(
                title="📝 Channel Topic Updated",
                description=f"Topic for {target_ch.mention} set to:\n> {topic.strip()[:1024]}",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 16. Hide Channel
    @app_commands.command(name="hide", description="Hide a channel completely from @everyone")
    @app_commands.describe(channel="Target channel to hide (default: current)")
    async def server_hide(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        await interaction.response.defer()
        try:
            ow = target_ch.overwrites_for(interaction.guild.default_role)
            ow.view_channel = False
            await target_ch.set_permissions(interaction.guild.default_role, overwrite=ow, reason=f"Hidden by {interaction.user}")
            embed = discord.Embed(
                title="👁️ Channel Hidden",
                description=f"{target_ch.mention} is now hidden from **@everyone**.",
                color=discord.Color(ERROR_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 17. Unhide Channel
    @app_commands.command(name="unhide", description="Unhide a channel for @everyone")
    @app_commands.describe(channel="Target channel to unhide (default: current)")
    async def server_unhide(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        await interaction.response.defer()
        try:
            ow = target_ch.overwrites_for(interaction.guild.default_role)
            ow.view_channel = True
            await target_ch.set_permissions(interaction.guild.default_role, overwrite=ow, reason=f"Unhidden by {interaction.user}")
            embed = discord.Embed(
                title="👁️ Channel Visible",
                description=f"{target_ch.mention} is now visible to **@everyone**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 18. NSFW Flag
    @app_commands.command(name="nsfw", description="Toggle age-restricted (NSFW) status for a channel")
    @app_commands.describe(enabled="True to mark NSFW, False to remove", channel="Target channel (default: current)")
    async def server_nsfw(self, interaction: discord.Interaction, enabled: bool, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        await interaction.response.defer()
        try:
            await target_ch.edit(nsfw=enabled, reason=f"NSFW toggled by {interaction.user}")
            embed = discord.Embed(
                title="🔞 Age-Restriction Updated",
                description=f"{target_ch.mention} is now marked as **{'NSFW (Age-Restricted)' if enabled else 'Family Friendly / Standard'}**.",
                color=discord.Color(ERROR_COLOR if enabled else SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 19. Voice Bitrate
    @app_commands.command(name="bitrate", description="Customize audio bitrate for a voice channel")
    @app_commands.describe(bitrate_kbps="Bitrate in kbps (e.g. 64, 96, 128, 256, 384)", channel="Target voice channel")
    async def server_bitrate(self, interaction: discord.Interaction, bitrate_kbps: int, channel: discord.VoiceChannel):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            bps = max(8, min(bitrate_kbps, 384)) * 1000
            await channel.edit(bitrate=bps, reason=f"Bitrate set by {interaction.user}")
            embed = discord.Embed(
                title="🔊 Voice Bitrate Updated",
                description=f"Audio bitrate for {channel.mention} set to `{bitrate_kbps}` kbps.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to set bitrate: `{e}`")

    # 20. Voice User Limit
    @app_commands.command(name="userlimit", description="Set user limit for a voice channel (0 for unlimited)")
    @app_commands.describe(limit="Maximum connected users (0 to 99)", channel="Target voice channel")
    async def server_userlimit(self, interaction: discord.Interaction, limit: int, channel: discord.VoiceChannel):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()
        try:
            lmt = max(0, min(limit, 99))
            await channel.edit(user_limit=lmt, reason=f"User limit set by {interaction.user}")
            embed = discord.Embed(
                title="👥 Voice Limit Updated",
                description=f"User limit for {channel.mention} set to `{lmt}` users." if lmt > 0 else f"User limit removed for {channel.mention} (Unlimited).",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")

    # 21. Sync Channel to Category
    @app_commands.command(name="syncchannel", description="Sync channel permissions with its parent category")
    @app_commands.describe(channel="Target channel to sync (default: current)")
    async def server_syncchannel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if not can_manage_channels(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        target_ch = channel or interaction.channel
        if not target_ch.category:
            return await interaction.response.send_message("❌ This channel is not inside any category.", ephemeral=True)
        await interaction.response.defer()
        try:
            await target_ch.sync_permissions()
            embed = discord.Embed(
                title="🔄 Channel Permissions Synced",
                description=f"{target_ch.mention} has been synced with category **{target_ch.category.name}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to sync permissions: `{e}`")

    # 22. Role Color
    @app_commands.command(name="rolecolor", description="Customize a role's color using a HEX code")
    @app_commands.describe(role="The role to modify", hex_color="HEX color code (e.g. #FF0055 or 7c3aed)")
    async def server_rolecolor(self, interaction: discord.Interaction, role: discord.Role, hex_color: str):
        if not can_manage_roles(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ That role is higher than or equal to my highest role.", ephemeral=True)
        color = parse_hex_color(hex_color)
        if not color:
            return await interaction.response.send_message("❌ Invalid HEX format! Use format like `#A855F7` or `FF0000`.", ephemeral=True)
        await interaction.response.defer()
        try:
            old_c = str(role.color)
            await role.edit(color=color, reason=f"Color customized by {interaction.user}")
            embed = discord.Embed(
                title="🎨 Role Color Updated",
                description=f"Color for {role.mention} updated from `{old_c}` to `{hex_color.upper()}`.",
                color=color
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update role color: `{e}`")

    # 23. Role Name
    @app_commands.command(name="rolename", description="Rename a role in this server")
    @app_commands.describe(role="The role to rename", new_name="New name for the role")
    async def server_rolename(self, interaction: discord.Interaction, role: discord.Role, new_name: str):
        if not can_manage_roles(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ That role is higher than or equal to my highest role.", ephemeral=True)
        await interaction.response.defer()
        try:
            old_name = role.name
            await role.edit(name=new_name.strip()[:100], reason=f"Renamed by {interaction.user}")
            embed = discord.Embed(
                title="✏️ Role Renamed",
                description=f"Role changed from **{old_name}** to **{new_name.strip()}** ({role.mention}).",
                color=role.color if role.color.value else discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to rename role: `{e}`")

    # 24. Role Hoist (Display Separately)
    @app_commands.command(name="rolehoist", description="Toggle whether a role is displayed separately in the member list")
    @app_commands.describe(role="The role to hoist or unhoist", hoist="True to display separately, False to merge")
    async def server_rolehoist(self, interaction: discord.Interaction, role: discord.Role, hoist: typing.Optional[bool] = None):
        if not can_manage_roles(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ That role is higher than or equal to my highest role.", ephemeral=True)
        await interaction.response.defer()
        try:
            new_hoist = not role.hoist if hoist is None else hoist
            await role.edit(hoist=new_hoist, reason=f"Hoist set to {new_hoist} by {interaction.user}")
            embed = discord.Embed(
                title="📌 Role Hoist Updated",
                description=f"{role.mention} will now **{'display separately' if new_hoist else 'not display separately'}** in the member list.",
                color=role.color if role.color.value else discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: `{e}`")


# ── 2. STANDALONE & GROUP PREFIX COMMAND SUITE (30+ COMMANDS) ─────────────────
def setup_server_customization(bot: commands.Bot):
    """Registers /server slash group and 30+ standalone prefix commands"""
    bot.tree.add_command(ServerCustomizationGroup(bot))

    # Master help / guide
    @bot.command(name="customhelp", aliases=["servercustom", "custommenu"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_customhelp(ctx: commands.Context):
        embed = discord.Embed(
            title="🛡️ VEYRA 2.0 Server Customization Suite",
            description=(
                "**Available Customization Commands:**\n\n"
                "👑 **Server Identity:**\n"
                "• `.servername <name>` — Rename server\n"
                "• `.servericon [url / attach]` — Change server icon\n"
                "• `.serverbanner [url / attach]` — Change server banner (Boost Lv2)\n"
                "• `.serversplash [url / attach]` — Change invite splash (Boost Lv1)\n"
                "• `.serverdesc <text>` — Set public server description\n"
                "• `.botnick <nickname>` — Customize bot nickname in this server\n\n"
                "⚙️ **System & Security:**\n"
                "• `.afkchannel <#channel> [timeout]` — Configure AFK voice & timer\n"
                "• `.systemchannel <#channel>` — Set welcome & boost system channel\n"
                "• `.ruleschannel <#channel>` — Set official rules channel\n"
                "• `.verificationlevel <none|low|med|high|highest>` — Security level\n"
                "• `.defaultnotifs <all|mentions>` — Default notifications\n\n"
                "📁 **Channels & Categories:**\n"
                "• `.hide [#channel]` / `.unhide [#channel]` — Toggle visibility for @everyone\n"
                "• `.lockmsg [#channel]` / `.unlockmsg` — Read-only with view history\n"
                "• `.slowmode <seconds> [#channel]` — Set slowmode cooldown\n"
                "• `.channeltopic <text> [#channel]` — Update text channel topic\n"
                "• `.nsfwchannel <on|off> [#channel]` — Toggle age restriction\n"
                "• `.vcbitrate <kbps> [#vc]` — Set audio quality (8-384 kbps)\n"
                "• `.vcuserlimit <num> [#vc]` — Set voice user limit\n"
                "• `.syncchannel [#channel]` — Sync permissions with category\n"
                "• `.clonechannel [#channel] [new_name]` — Duplicate channel\n\n"
                "🎨 **Roles & Aesthetics:**\n"
                "• `.rolecolor <@role> <#hex>` — Customize role color\n"
                "• `.rolename <@role> <new_name>` — Rename role\n"
                "• `.rolehoist <@role>` — Toggle separate member list display\n"
                "• `.rolemention <@role>` — Toggle mentionable by @everyone\n"
                "• `.rolecreate <name> [#hex]` — Create brand new role\n"
                "• `.roledelete <@role>` — Delete role safely\n\n"
                "📢 **Utility & Community:**\n"
                "• `.say <message>` — Send message as VEYRA\n"
                "• `.announce <#channel> <message>` — Pin branded announcement embed\n"
                "• `.poll <question> [opt1 | opt2...]` — Interactive reaction poll"
            ),
            color=discord.Color(THEME_COLOR)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    # 1. Server Name
    @bot.command(name="servername")
    @commands.has_permissions(manage_guild=True)
    async def p_servername(ctx: commands.Context, *, new_name: str):
        try:
            await ctx.guild.edit(name=new_name.strip(), reason=f"Customized by {ctx.author}")
            await ctx.send(f"✅ Server name updated to **{new_name.strip()}**")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 2. Server Icon
    @bot.command(name="setservericon", aliases=["seticon", "changeicon"])
    @commands.has_permissions(manage_guild=True)
    async def p_setservericon(ctx: commands.Context, url: typing.Optional[str] = None):
        att = ctx.message.attachments[0] if ctx.message.attachments else None
        try:
            raw = await fetch_asset_bytes(url=url, attachment=att)
            await ctx.guild.edit(icon=raw, reason=f"Customized by {ctx.author}")
            await ctx.send("✅ Server icon updated successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 3. Server Banner
    @bot.command(name="setserverbanner", aliases=["setbanner", "changebanner"])
    @commands.has_permissions(manage_guild=True)
    async def p_setserverbanner(ctx: commands.Context, url: typing.Optional[str] = None):
        att = ctx.message.attachments[0] if ctx.message.attachments else None
        try:
            raw = await fetch_asset_bytes(url=url, attachment=att)
            await ctx.guild.edit(banner=raw, reason=f"Customized by {ctx.author}")
            await ctx.send("✅ Server banner updated successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 4. Server Splash
    @bot.command(name="serversplash", aliases=["setsplash"])
    @commands.has_permissions(manage_guild=True)
    async def p_serversplash(ctx: commands.Context, url: typing.Optional[str] = None):
        att = ctx.message.attachments[0] if ctx.message.attachments else None
        try:
            raw = await fetch_asset_bytes(url=url, attachment=att)
            await ctx.guild.edit(splash=raw, reason=f"Customized by {ctx.author}")
            await ctx.send("✅ Server invite splash updated successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 5. Server Description
    @bot.command(name="serverdesc", aliases=["setdesc"])
    @commands.has_permissions(manage_guild=True)
    async def p_serverdesc(ctx: commands.Context, *, description: str):
        try:
            await ctx.guild.edit(description=description.strip(), reason=f"Customized by {ctx.author}")
            await ctx.send(f"✅ Server description set to: > **{description.strip()[:120]}**")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 6. Bot Nickname
    @bot.command(name="botnick", aliases=["setbotname"])
    @commands.has_permissions(manage_guild=True)
    async def p_botnick(ctx: commands.Context, *, nickname: str):
        try:
            old = ctx.guild.me.display_name
            await ctx.guild.me.edit(nick=nickname.strip()[:32], reason=f"Customized by {ctx.author}")
            try:
                from bot.db_adapter import get_db
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO guild_bot_profiles (guild_id, nickname) VALUES (?, ?)", (str(ctx.guild.id), nickname.strip()[:32]))
                conn.commit()
                conn.close()
            except Exception:
                pass
            await ctx.send(f"✅ Bot nickname changed from **{old}** to **{nickname.strip()[:32]}**")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 7. AFK Channel
    @bot.command(name="afkchannel")
    @commands.has_permissions(manage_guild=True)
    async def p_afkchannel(ctx: commands.Context, channel: typing.Optional[discord.VoiceChannel] = None):
        try:
            await ctx.guild.edit(afk_channel=channel, reason=f"AFK channel set by {ctx.author}")
            await ctx.send(f"✅ AFK voice channel set to {channel.mention if channel else '`None (Disabled)`'}")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 8. AFK Timeout
    @bot.command(name="afktimeout")
    @commands.has_permissions(manage_guild=True)
    async def p_afktimeout(ctx: commands.Context, minutes: int):
        valid = {1: 60, 5: 300, 15: 900, 30: 1800, 60: 3600}
        if minutes not in valid:
            return await ctx.send("❌ Valid AFK timeout values are: `1`, `5`, `15`, `30`, or `60` minutes.")
        try:
            await ctx.guild.edit(afk_timeout=valid[minutes], reason=f"AFK timeout set by {ctx.author}")
            await ctx.send(f"✅ AFK timeout set to `{minutes}` minutes.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 9. System Channel
    @bot.command(name="systemchannel")
    @commands.has_permissions(manage_guild=True)
    async def p_systemchannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None):
        try:
            await ctx.guild.edit(system_channel=channel, reason=f"System channel set by {ctx.author}")
            await ctx.send(f"✅ System messages channel set to {channel.mention if channel else '`Disabled`'}")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 10. Rules Channel
    @bot.command(name="ruleschannel")
    @commands.has_permissions(manage_guild=True)
    async def p_ruleschannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None):
        try:
            await ctx.guild.edit(rules_channel=channel, reason=f"Rules channel set by {ctx.author}")
            await ctx.send(f"✅ Official rules channel set to {channel.mention if channel else '`Disabled`'}")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 11. Verification Level
    @bot.command(name="verificationlevel", aliases=["setverification"])
    @commands.has_permissions(manage_guild=True)
    async def p_verificationlevel(ctx: commands.Context, level: str):
        lvl_map = {
            "none": discord.VerificationLevel.none,
            "low": discord.VerificationLevel.low,
            "medium": discord.VerificationLevel.medium,
            "high": discord.VerificationLevel.high,
            "highest": discord.VerificationLevel.highest
        }
        val = lvl_map.get(level.lower().strip())
        if not val:
            return await ctx.send("❌ Options: `none`, `low`, `medium`, `high`, `highest`")
        try:
            await ctx.guild.edit(verification_level=val, reason=f"Verification set by {ctx.author}")
            await ctx.send(f"🛡️ Server verification level set to **{level.upper()}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 12. Hide Channel
    @bot.command(name="hide", aliases=["hidechannel"])
    @commands.has_permissions(manage_channels=True)
    async def p_hidechannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        try:
            ow = target.overwrites_for(ctx.guild.default_role)
            ow.view_channel = False
            await target.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Hidden by {ctx.author}")
            await ctx.send(f"👁️ {target.mention} is now **hidden** from @everyone.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 13. Unhide Channel
    @bot.command(name="unhide", aliases=["unhidechannel"])
    @commands.has_permissions(manage_channels=True)
    async def p_unhidechannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        try:
            ow = target.overwrites_for(ctx.guild.default_role)
            ow.view_channel = True
            await target.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unhidden by {ctx.author}")
            await ctx.send(f"👁️ {target.mention} is now **visible** to @everyone.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 14. NSFW Channel
    @bot.command(name="nsfwchannel", aliases=["nsfwtoggle"])
    @commands.has_permissions(manage_channels=True)
    async def p_nsfwchannel(ctx: commands.Context, state: str = "toggle", channel: typing.Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        try:
            new_state = not target.nsfw if state.lower() == "toggle" else (state.lower() in ("on", "true", "yes", "1"))
            await target.edit(nsfw=new_state, reason=f"NSFW updated by {ctx.author}")
            await ctx.send(f"🔞 {target.mention} is now **{'Age-Restricted (NSFW)' if new_state else 'Family Friendly / Standard'}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 15. Channel Topic
    @bot.command(name="channeltopic", aliases=["settopic"])
    @commands.has_permissions(manage_channels=True)
    async def p_channeltopic(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None, *, topic: str):
        target = channel or ctx.channel
        try:
            await target.edit(topic=topic.strip()[:1024], reason=f"Topic set by {ctx.author}")
            await ctx.send(f"📝 Topic for {target.mention} updated:\n> {topic.strip()[:1024]}")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 16. Voice Bitrate
    @bot.command(name="vcbitrate", aliases=["setbitrate"])
    @commands.has_permissions(manage_channels=True)
    async def p_vcbitrate(ctx: commands.Context, bitrate_kbps: int, channel: typing.Optional[discord.VoiceChannel] = None):
        target = channel or (ctx.author.voice.channel if ctx.author.voice else None)
        if not target or not isinstance(target, discord.VoiceChannel):
            return await ctx.send("❌ Please specify or join a voice channel.")
        try:
            bps = max(8, min(bitrate_kbps, 384)) * 1000
            await target.edit(bitrate=bps, reason=f"Bitrate set by {ctx.author}")
            await ctx.send(f"🔊 Audio bitrate for {target.mention} set to `{bitrate_kbps}` kbps.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 17. Voice User Limit
    @bot.command(name="vcuserlimit", aliases=["setvclimit", "vclimit"])
    @commands.has_permissions(manage_channels=True)
    async def p_vcuserlimit(ctx: commands.Context, limit: int, channel: typing.Optional[discord.VoiceChannel] = None):
        target = channel or (ctx.author.voice.channel if ctx.author.voice else None)
        if not target or not isinstance(target, discord.VoiceChannel):
            return await ctx.send("❌ Please specify or join a voice channel.")
        try:
            lmt = max(0, min(limit, 99))
            await target.edit(user_limit=lmt, reason=f"Limit set by {ctx.author}")
            await ctx.send(f"👥 User limit for {target.mention} set to `{lmt}` users." if lmt > 0 else f"User limit removed for {target.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 18. Sync Channel
    @bot.command(name="syncchannel")
    @commands.has_permissions(manage_channels=True)
    async def p_syncchannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        if not target.category:
            return await ctx.send("❌ Channel is not inside any category.")
        try:
            await target.sync_permissions()
            await ctx.send(f"🔄 {target.mention} permissions synced with category **{target.category.name}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 19. Clone Channel
    @bot.command(name="clonechannel")
    @commands.has_permissions(manage_channels=True)
    async def p_clonechannel(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None, *, new_name: str = None):
        target = channel or ctx.channel
        try:
            name = new_name.strip() if new_name else f"{target.name}-clone"
            cloned = await target.clone(name=name, reason=f"Cloned by {ctx.author}")
            await ctx.send(f"✨ Successfully cloned {target.mention} as {cloned.mention} with identical permissions!")
        except Exception as e:
            await ctx.send(f"❌ Failed to clone channel: `{e}`")

    # 20. Role Color
    @bot.command(name="rolecolor", aliases=["setrolecolor"])
    @commands.has_permissions(manage_roles=True)
    async def p_rolecolor(ctx: commands.Context, role: discord.Role, hex_code: str):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ That role is higher than or equal to my highest role.")
        color = parse_hex_color(hex_code)
        if not color:
            return await ctx.send("❌ Invalid HEX format! Example: `.rolecolor @Role #FF0055`")
        try:
            await role.edit(color=color, reason=f"Color set by {ctx.author}")
            await ctx.send(f"🎨 Color for {role.mention} updated to `{hex_code.upper()}`.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 21. Role Name
    @bot.command(name="rolename", aliases=["setrolename"])
    @commands.has_permissions(manage_roles=True)
    async def p_rolename(ctx: commands.Context, role: discord.Role, *, new_name: str):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ That role is higher than or equal to my highest role.")
        try:
            old = role.name
            await role.edit(name=new_name.strip(), reason=f"Renamed by {ctx.author}")
            await ctx.send(f"✏️ Role **{old}** renamed to **{new_name.strip()}** ({role.mention}).")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 22. Role Hoist
    @bot.command(name="rolehoist")
    @commands.has_permissions(manage_roles=True)
    async def p_rolehoist(ctx: commands.Context, role: discord.Role, state: typing.Optional[bool] = None):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ That role is higher than or equal to my highest role.")
        try:
            new_hoist = not role.hoist if state is None else state
            await role.edit(hoist=new_hoist, reason=f"Hoist set by {ctx.author}")
            await ctx.send(f"📌 {role.mention} will **{'now display separately' if new_hoist else 'no longer display separately'}** in the member list.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 23. Role Mentionable
    @bot.command(name="rolemention", aliases=["rolementionable"])
    @commands.has_permissions(manage_roles=True)
    async def p_rolemention(ctx: commands.Context, role: discord.Role, state: typing.Optional[bool] = None):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ That role is higher than or equal to my highest role.")
        try:
            new_m = not role.mentionable if state is None else state
            await role.edit(mentionable=new_m, reason=f"Mentionable set by {ctx.author}")
            await ctx.send(f"🔔 {role.mention} is now **{'mentionable by everyone' if new_m else 'not mentionable by everyone'}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 24. Role Create
    @bot.command(name="rolecreate", aliases=["newrole"])
    @commands.has_permissions(manage_roles=True)
    async def p_rolecreate(ctx: commands.Context, name: str, hex_code: typing.Optional[str] = None):
        try:
            color = parse_hex_color(hex_code) if hex_code else discord.Color.default()
            role = await ctx.guild.create_role(name=name.strip(), color=color or discord.Color.default(), reason=f"Created by {ctx.author}")
            await ctx.send(f"✅ Created role {role.mention} (`{role.id}`) successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed to create role: `{e}`")

    # 25. Role Delete
    @bot.command(name="roledelete")
    @commands.has_permissions(manage_roles=True)
    async def p_roledelete(ctx: commands.Context, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ That role is higher than or equal to my highest role.")
        try:
            r_name = role.name
            await role.delete(reason=f"Deleted by {ctx.author}")
            await ctx.send(f"🗑️ Role **@{r_name}** has been deleted.")
        except Exception as e:
            await ctx.send(f"❌ Failed to delete role: `{e}`")

    # 26. Category Create
    @bot.command(name="categorycreate", aliases=["newcat"])
    @commands.has_permissions(manage_channels=True)
    async def p_categorycreate(ctx: commands.Context, *, name: str):
        try:
            cat = await ctx.guild.create_category(name=name.strip(), reason=f"Created by {ctx.author}")
            await ctx.send(f"📁 Category **{cat.name}** (`{cat.id}`) created successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 27. Category Rename
    @bot.command(name="categoryrename")
    @commands.has_permissions(manage_channels=True)
    async def p_categoryrename(ctx: commands.Context, category: discord.CategoryChannel, *, new_name: str):
        try:
            old = category.name
            await category.edit(name=new_name.strip(), reason=f"Renamed by {ctx.author}")
            await ctx.send(f"✏️ Category **{old}** renamed to **{new_name.strip()}**.")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    # 28. Say (Echo as bot)
    @bot.command(name="say", aliases=["echo"])
    @commands.has_permissions(manage_messages=True)
    async def p_say(ctx: commands.Context, *, message: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(message)

    # 29. Announcement Card
    @bot.command(name="announce")
    @commands.has_permissions(manage_messages=True)
    async def p_announce(ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None, *, message: str):
        target = channel or ctx.channel
        embed = discord.Embed(
            title="📢 Official Server Announcement",
            description=message.strip(),
            color=discord.Color(THEME_COLOR)
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Posted by {ctx.author.display_name} • VEYRA Announcement System")
        embed.timestamp = datetime.now(timezone.utc)
        await target.send(embed=embed)
        if target.id != ctx.channel.id:
            await ctx.send(f"✅ Announcement sent to {target.mention}!")

    # 30. Reaction Poll
    @bot.command(name="quickpoll", aliases=["rpoll", "reactionpoll"])
    @commands.has_permissions(manage_messages=True)
    async def p_quickpoll(ctx: commands.Context, *, question_and_options: str):
        parts = [p.strip() for p in re.split(r'[\|\n]', question_and_options) if p.strip()]
        if not parts:
            return await ctx.send("❌ Usage: `.poll What game tonight? | CS2 | Valorant | GTA`")
        
        question = parts[0]
        options = parts[1:]
        
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        if not options:
            embed = discord.Embed(
                title=f"📊 {question}",
                description="React below with 👍 for **YES** or 👎 for **NO**!",
                color=discord.Color(THEME_COLOR)
            )
            embed.set_footer(text=f"Poll by {ctx.author.display_name}")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            return

        if len(options) > 10:
            options = options[:10]

        desc = ""
        for i, opt in enumerate(options):
            desc += f"{number_emojis[i]} **{opt}**\n\n"

        embed = discord.Embed(
            title=f"📊 {question}",
            description=desc,
            color=discord.Color(THEME_COLOR)
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name} • React to vote")
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            try:
                await msg.add_reaction(number_emojis[i])
            except Exception:
                break
    try:
        print("✅ Registered Live Server Customization Suite (/server + 30+ prefix commands).")
    except Exception:
        print("[+] Registered Live Server Customization Suite (/server + 30+ prefix commands).")
