# bot/server_customization.py - Instant Real-Time Server Identity & Asset Customization Suite
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import typing

THEME_COLOR = 0xa855f7
SUCCESS_COLOR = 0x22c55e
ERROR_COLOR = 0xef4444
FOOTER_TEXT = "Powered By Veyra Development™ | Designed By Arun"


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


class ServerCustomizationGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="server", description="Live Server Customization: Change name, avatar/icon, banner, description")
        self.bot = bot

    @app_commands.command(name="name", description="Change server name instantly")
    @app_commands.describe(new_name="The new name for the server (2-100 characters)")
    async def server_name(self, interaction: discord.Interaction, new_name: str):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission to modify server identity.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission in this guild.", ephemeral=True)

        old_name = interaction.guild.name
        await interaction.response.defer()
        try:
            await interaction.guild.edit(name=new_name.strip(), reason=f"VEYRA Server Customization by {interaction.user} ({interaction.user.id})")
            embed = discord.Embed(
                title="✅ Server Name Updated",
                description=f"Server name successfully changed from **{old_name}** to **{new_name.strip()}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to change server name: `{e}`")

    @app_commands.command(name="botname", description="Change bot's nickname in this server instantly")
    @app_commands.describe(nickname="New nickname for VEYRA in this server (e.g. VEYRA)")
    async def server_botname(self, interaction: discord.Interaction, nickname: str):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id and interaction.user.id != 1256986886631854080:
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
                description=f"Bot nickname in this server changed from **{old_nick}** to **{nickname.strip()[:32]}**.",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to change bot nickname: `{e}`")

    @app_commands.command(name="avatar", description="Change server avatar/icon via URL or image upload")
    @app_commands.describe(url="Direct image URL (JPG, PNG, GIF, WEBP)", image="Direct image attachment upload")
    async def server_avatar(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission to modify server icon.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission in this guild.", ephemeral=True)

        await interaction.response.defer()
        try:
            raw_bytes = await fetch_asset_bytes(url=url, attachment=image)
            await interaction.guild.edit(icon=raw_bytes, reason=f"VEYRA Server Icon updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Icon / Avatar Updated",
                description="The server icon has been updated in real time.",
                color=discord.Color(SUCCESS_COLOR)
            )
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update server avatar: `{e}`")

    @app_commands.command(name="icon", description="Change server icon via image URL or attachment upload")
    @app_commands.describe(url="Direct image URL", image="Direct image attachment upload")
    async def server_icon(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        await self.server_avatar.callback(self, interaction, url=url, image=image)

    @app_commands.command(name="banner", description="Change server banner via URL or upload (Requires Boost Level 2)")
    @app_commands.describe(url="Direct image URL", image="Direct image attachment upload")
    async def server_banner(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission to modify server banner.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission in this guild.", ephemeral=True)

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

    @app_commands.command(name="splash", description="Change server invite splash background (Requires Boost Level 1)")
    @app_commands.describe(url="Direct image URL", image="Direct image attachment upload")
    async def server_splash(self, interaction: discord.Interaction, url: typing.Optional[str] = None, image: typing.Optional[discord.Attachment] = None):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission.", ephemeral=True)

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

    @app_commands.command(name="description", description="Change server public description")
    @app_commands.describe(description="The new description for the server (up to 120 chars)")
    async def server_description(self, interaction: discord.Interaction, description: str):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ VEYRA requires `Manage Server` permission.", ephemeral=True)

        await interaction.response.defer()
        try:
            await interaction.guild.edit(description=description.strip(), reason=f"VEYRA Server Description updated by {interaction.user}")
            embed = discord.Embed(
                title="✅ Server Description Updated",
                description=f"Server description set to:\n> {description.strip()}",
                color=discord.Color(SUCCESS_COLOR)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update description: `{e}`")


def setup_server_customization(bot: commands.Bot):
    """Registers /server slash group and .server prefix commands"""
    bot.tree.add_command(ServerCustomizationGroup(bot))

    @bot.group(name="server", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def prefix_server(ctx: commands.Context):
        embed = discord.Embed(
            title="⚙️ VEYRA Server Customization Commands",
            description=(
                "**Available Commands:**\n"
                "• `.server name <new name>` — Rename server\n"
                "• `.server avatar <url or attach image>` — Update server icon\n"
                "• `.server icon <url or attach image>` — Update server icon\n"
                "• `.server banner <url or attach image>` — Update server banner\n"
                "• `.server splash <url or attach image>` — Update invite splash\n"
                "• `.server description <text>` — Update server description"
            ),
            color=discord.Color(THEME_COLOR)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @prefix_server.command(name="name")
    @commands.has_permissions(manage_guild=True)
    async def prefix_server_name(ctx: commands.Context, *, new_name: str):
        try:
            await ctx.guild.edit(name=new_name.strip(), reason=f"Customized by {ctx.author}")
            await ctx.send(f"✅ Server name updated to **{new_name.strip()}**")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    @prefix_server.command(name="botname", aliases=["nick", "botnick"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_server_botname(ctx: commands.Context, *, nickname: str):
        try:
            old_nick = ctx.guild.me.display_name
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
            await ctx.send(f"✅ Bot nickname changed from **{old_nick}** to **{nickname.strip()[:32]}**")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    @prefix_server.command(name="avatar", aliases=["icon"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_server_avatar(ctx: commands.Context, url: typing.Optional[str] = None):
        att = ctx.message.attachments[0] if ctx.message.attachments else None
        try:
            raw = await fetch_asset_bytes(url=url, attachment=att)
            await ctx.guild.edit(icon=raw, reason=f"Customized by {ctx.author}")
            await ctx.send("✅ Server icon updated successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    @prefix_server.command(name="banner")
    @commands.has_permissions(manage_guild=True)
    async def prefix_server_banner(ctx: commands.Context, url: typing.Optional[str] = None):
        att = ctx.message.attachments[0] if ctx.message.attachments else None
        try:
            raw = await fetch_asset_bytes(url=url, attachment=att)
            await ctx.guild.edit(banner=raw, reason=f"Customized by {ctx.author}")
            await ctx.send("✅ Server banner updated successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed: `{e}`")

    print("✅ Registered Live Server Customization Suite (/server).")
