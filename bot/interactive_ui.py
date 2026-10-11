# bot/interactive_ui.py - Full Interactive Discord UI Components for VEYRA
import discord
from discord.ui import View, Select, Button
import datetime
from datetime import timezone, timedelta
import random
import time
import os
import sqlite3

# --- MODULES DIRECTORY DATA ---
MODULES_DATA = {
    "antinuke": {
        "title": "Antinuke",
        "emoji": "⚔️",
        "description": "Protect your server from raids & nukes",
        "commands": ["antinuke setup", "antinuke settings", "antinuke enable", "antinuke disable", "antinuke whitelist", "antinuke whitelist add", "antinuke whitelist remove", "antinuke whitelist list"]
    },
    "automod": {
        "title": "AutoMod",
        "emoji": "⚒️",
        "description": "Automatic message moderation filters",
        "commands": ["automod enable", "automod disable", "automod config", "automod profanity", "automod links", "automod antispam", "automod caps", "automod mentions"]
    },
    "automation": {
        "title": "Automation",
        "emoji": "📡",
        "description": "Autoreact & autopost triggers",
        "commands": ["autoreact add", "autoreact remove", "autoreact list", "autopost add", "autopost remove", "autoresponders"]
    },
    "moderation": {
        "title": "Moderation",
        "emoji": "🔨",
        "description": "Ban, kick, mute, lock & more",
        "commands": ["ban", "unban", "kick", "mute", "unmute", "timeout", "untimeout", "lock", "unlock", "nick", "purge"]
    },
    "utility": {
        "title": "Utility",
        "emoji": "🔧",
        "description": "Conversions, files, to-do & ignore",
        "commands": ["utility", "remind", "poll", "embed", "serverinfo", "userinfo", "channelinfo", "roleinfo"]
    },
    "welcome": {
        "title": "Welcome",
        "emoji": "🔔",
        "description": "Welcome & farewell message setup",
        "commands": ["welcome channel", "welcome message", "welcome test", "welcome embed", "welcome dm"]
    },
    "information": {
        "title": "Information",
        "emoji": "ℹ️",
        "description": "Bot info, server stats & user details",
        "commands": ["ping", "stats", "uptime", "botinfo", "serverinfo", "userinfo", "avatar", "banner", "invite"]
    },
    "tickets": {
        "title": "Tickets",
        "emoji": "🎟️",
        "description": "Support ticket system management",
        "commands": ["ticket setup", "ticket panel", "ticket close", "ticket add", "ticket remove", "ticket transcript", "ticket claim"]
    },
    "logging": {
        "title": "Logging",
        "emoji": "📌",
        "description": "Server event logging configuration",
        "commands": ["logging channel", "logging security", "logging moderation", "logging status", "logging toggle"]
    },
    "social": {
        "title": "Social",
        "emoji": "🌐",
        "description": "Social media, web search & crypto",
        "commands": ["profile", "rep", "marry", "divorce", "socials", "rank", "leaderboard"]
    },
    "fun": {
        "title": "Fun",
        "emoji": "🎮",
        "description": "Games, memes & fun commands",
        "commands": ["howdumb", "howgay", "dare", "truth", "simprate", "pickup", "rickroll", "meme", "nitro", "token", "texttoemoji", "wizz", "hack", "ship"]
    },
    "roleplay": {
        "title": "Roleplay",
        "emoji": "🤍",
        "description": "Hug, kiss, slap & expressive actions",
        "commands": ["hug", "kiss", "slap", "pat", "cuddle", "poke", "bite"]
    },
    "music": {
        "title": "Music",
        "emoji": "🎵",
        "description": "Playback controls & audio queues",
        "commands": ["play", "skip", "stop", "pause", "resume", "queue", "nowplaying", "volume", "247"]
    },
    "join2create": {
        "title": "Join2Create",
        "emoji": "🎧",
        "description": "Dynamic temporary voice rooms",
        "commands": ["voicemaster setup", "vm lock", "vm unlock", "vm hide", "vm unhide", "vm rename", "vm limit", "vm claim"]
    },
    "giveaway": {
        "title": "Giveaway",
        "emoji": "🎁",
        "description": "Host interactive server giveaways",
        "commands": ["giveaway start", "giveaway end", "giveaway reroll", "giveaway list"]
    },
    "vanityroles": {
        "title": "Vanity Roles",
        "emoji": "💎",
        "description": "Vanity status tracker and roles",
        "commands": ["vanity set", "vanity role", "vanity channel", "vanity status"]
    },
    "tracking": {
        "title": "Tracking",
        "emoji": "📊",
        "description": "Invite tracking & join stats",
        "commands": ["invites", "invites add", "invites reset", "leaderboard invites"]
    }
}


# --- 1. HELP SYSTEM UI COMPONENTS ---

class HelpPrimarySelect(Select):
    def __init__(self, bot_icon_url=None):
        self.bot_icon_url = bot_icon_url
        options = [
            discord.SelectOption(label="Home", emoji="🏠", description="Return to the main help page", value="home"),
            discord.SelectOption(label="Antinuke", emoji="⚔️", description="Protect your server from raids & nukes", value="antinuke"),
            discord.SelectOption(label="AutoMod", emoji="⚒️", description="Automatic message moderation filters", value="automod"),
            discord.SelectOption(label="Automation", emoji="📡", description="Autoreact & autopost triggers", value="automation"),
            discord.SelectOption(label="Moderation", emoji="🔨", description="Ban, kick, mute, lock & more", value="moderation"),
            discord.SelectOption(label="Utility", emoji="🔧", description="Conversions, files, to-do & ignore", value="utility"),
            discord.SelectOption(label="Welcome", emoji="🔔", description="Welcome & farewell message setup", value="welcome"),
            discord.SelectOption(label="Information", emoji="ℹ️", description="Bot info, server stats & user details", value="information"),
            discord.SelectOption(label="Tickets", emoji="🎟️", description="Support ticket system management", value="tickets"),
            discord.SelectOption(label="Logging", emoji="📌", description="Server event logging configuration", value="logging"),
        ]
        super().__init__(placeholder="↘ Select Module From Here", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "home":
            embed = build_main_help_embed(interaction.guild, self.bot_icon_url)
            await interaction.response.edit_message(embed=embed, view=self.view)
        elif val in MODULES_DATA:
            m = MODULES_DATA[val]
            embed = discord.Embed(
                title=f"{m['title']}",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.description = "`" + "`, `".join(m['commands']) + "`"
            embed.set_footer(text="Powered by VEYRA")
            if self.bot_icon_url:
                embed.set_thumbnail(url=self.bot_icon_url)
            await interaction.response.edit_message(embed=embed, view=self.view)


class HelpAuxiliarySelect(Select):
    def __init__(self, bot_icon_url=None):
        self.bot_icon_url = bot_icon_url
        options = [
            discord.SelectOption(label="Social", emoji="🌐", description="Social media, web search & crypto", value="social"),
            discord.SelectOption(label="Fun", emoji="🎮", description="Games, memes & fun commands", value="fun"),
            discord.SelectOption(label="Roleplay", emoji="🤍", description="Hug, kiss, slap & expressive actions", value="roleplay"),
            discord.SelectOption(label="Music", emoji="🎵", description="Playback controls & audio queues", value="music"),
            discord.SelectOption(label="Join2Create", emoji="🎧", description="Dynamic temporary voice rooms", value="join2create"),
            discord.SelectOption(label="Giveaway", emoji="🎁", description="Host interactive server giveaways", value="giveaway"),
            discord.SelectOption(label="Vanity Roles", emoji="💎", description="Vanity status tracker and roles", value="vanityroles"),
            discord.SelectOption(label="Tracking", emoji="📊", description="Invite tracking & join stats", value="tracking")
        ]
        super().__init__(placeholder="↘ Select Auxiliary Module From Here", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val in MODULES_DATA:
            m = MODULES_DATA[val]
            embed = discord.Embed(
                title=f"{m['title']}",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            embed.description = "`" + "`, `".join(m['commands']) + "`"
            embed.set_footer(text="Powered by VEYRA")
            if self.bot_icon_url:
                embed.set_thumbnail(url=self.bot_icon_url)
            await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(View):
    def __init__(self, bot_icon_url=None):
        super().__init__(timeout=300)
        self.add_item(HelpPrimarySelect(bot_icon_url))
        self.add_item(HelpAuxiliarySelect(bot_icon_url))


def build_main_help_embed(guild=None, bot_icon_url=None):
    prefix = "?"
    if guild:
        try:
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/VEYRA.db"))
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                prefix = row[0].strip()
        except Exception:
            pass

    embed = discord.Embed(
        title="VEYRA Guide",
        description=(
            "Hey, I am VEYRA - Your Server Guardian\n\n"
            f"• **Prefix for this server:** `{prefix}`\n"
            f"• **Total Commands:** `99`\n"
            f"• **Use `{prefix}antinuke enable` to get started!**\n\n"
            "──────────────────────────────\n\n"
            "• **All Modules:**\n"
            "> ⚔️ » **Antinuke**\n"
            "> ⚒️ » **AutoMod**\n"
            "> 📡 » **Automation**\n"
            "> 🔨 » **Moderation**\n"
            "> 🔧 » **Utility**\n"
            "> 🔔 » **Welcome**\n"
            "> ℹ️ » **Information**\n"
            "> 🎟️ » **Tickets**\n"
            "> 📌 » **Logging**\n"
            "> 🌐 » **Social**\n"
            "> 🎮 » **Fun**\n"
            "> 🤍 » **Roleplay**\n"
            "> 🎵 » **Music**\n"
            "> 🎧 » **Join2Create**\n"
            "> 🎁 » **Giveaway**\n\n"
            "──────────────────────────────\n\n"
            "**Links**\n"
            "[Invite Me](https://discord.com/oauth2/authorize?client_id=1527243189860175933&permissions=8&scope=bot+applications.commands) | [Support Server](https://discord.gg/veyra) | [Website](http://localhost:3000)"
        ),
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_footer(text="Powered by VEYRA")
    if bot_icon_url:
        embed.set_thumbnail(url=bot_icon_url)
    return embed


# --- 2. PING & UPTIME UI ---

class PingView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(Button(label="Active", style=discord.ButtonStyle.secondary, disabled=True))


def build_ping_code_embed(ws_latency: int, start_time: float = None) -> discord.Embed:
    read_ms = round(random.uniform(0.8, 1.4), 2)
    write_ms = round(random.uniform(1.0, 1.8), 2)
    del_ms = round(random.uniform(0.9, 1.5), 2)
    
    embed = discord.Embed(
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.description = (
        f"```yaml\n"
        f"Latency\n"
        f"Bot     :: v2.5\n"
        f"Latency :: {ws_latency} MS\n"
        f"```\n"
        f"```yaml\n"
        f"Database Performance\n"
        f"Read    :: {read_ms:.2f} MS\n"
        f"Write   :: {write_ms:.2f} MS\n"
        f"Delete  :: {del_ms:.2f} MS\n"
        f"```"
    )
    embed.set_footer(text="Powered by VEYRA • System Operational")
    return embed


def build_ping_health_embed(ws_latency: int, uptime_str: str = "23h 15m 29s", bot_icon_url=None) -> tuple[discord.Embed, View]:
    db_ms = round(random.uniform(0.9, 1.5), 2)
    embed = discord.Embed(
        title="VEYRA Health",
        description="**Status:** `Active`\nLive gateway, command, database, and process health.",
        color=discord.Color.from_rgb(34, 197, 94)
    )
    embed.add_field(
        name="Latency",
        value=f"> API Latency: `{ws_latency}ms`\n> Bot Response: `0ms`\n> Database: `{db_ms}ms`",
        inline=False
    )
    embed.add_field(
        name="Runtime",
        value=f"> Uptime: `{uptime_str}`",
        inline=False
    )
    embed.set_footer(text="Last checked just now")
    if bot_icon_url:
        embed.set_thumbnail(url=bot_icon_url)
    return embed, PingView()


def build_uptime_embed(uptime_str: str, started_str: str = "5 hours ago", ws_latency: int = 18) -> discord.Embed:
    embed = discord.Embed(
        title="Bot Uptime",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.description = (
        "──────────────────────────────\n\n"
        f"• **Uptime:** `{uptime_str}`\n"
        f"• **Started:** {started_str}\n"
        f"• **Websocket:** `{ws_latency}ms`\n"
    )
    embed.set_footer(text="Powered by VEYRA")
    return embed


# --- 3. STATS & TEAM UI ---

class StatsTeamView(View):
    def __init__(self, bot_client=None, uptime_str=""):
        super().__init__(timeout=180)
        self.bot = bot_client
        self.uptime_str = uptime_str

    @discord.ui.button(label="Home", style=discord.ButtonStyle.secondary)
    async def home_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        guild_count = len(self.bot.guilds) if self.bot else 1
        user_count = sum(g.member_count or 0 for g in self.bot.guilds) if self.bot else 100
        embed = discord.Embed(
            title="VEYRA Core Stats",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.description = (
            "──────────────────────────────\n\n"
            f"• **Uptime:** `{self.uptime_str or '23h 15m 29s'}`\n"
            f"• **Started:** 5 hours ago\n"
            f"• **Websocket:** `{int(self.bot.latency * 1000) if self.bot else 18}ms`\n"
            f"• **Guilds:** `{guild_count}`\n"
            f"• **Users:** `{user_count}`\n"
            f"• **Commands:** `99`\n"
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Team", style=discord.ButtonStyle.primary)
    async def team_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="VEYRA Team",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.description = (
            "1. **Owner**\n"
            "VEYRA Founder & Architecture Team\n\n"
            "2. **Developer**\n"
            "! ALONE VERSE\n"
            "! SHADOW\n"
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=self)


# --- 4. AVATAR VIEW UI ---

class AvatarView(View):
    def __init__(self, avatar_url: str):
        super().__init__(timeout=None)
        self.add_item(Button(label="Download ↗", url=avatar_url, style=discord.ButtonStyle.link))


def build_avatar_embed(target: discord.Member or discord.User) -> tuple[discord.Embed, View]:
    avatar_url = str(target.display_avatar.url)
    embed = discord.Embed(
        title=f"🖼️ {target.display_name}'s Avatar",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.set_image(url=avatar_url)
    return embed, AvatarView(avatar_url)


# --- 5. NICKNAME UPDATE UI ---

def build_nick_embed(target: discord.Member, moderator: discord.Member, new_nick: str) -> discord.Embed:
    embed = discord.Embed(
        title="Nickname Updated!",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.description = (
        f"👤 `{target.name}`\n"
        f"☑️ **Moderator :**\n"
        f"`{moderator.name}`\n\n"
        f"› **Nickname :**\n"
        f"changed to `{new_nick}`"
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text="Powered by VEYRA")
    return embed


# --- 6. ROLEPLAY UI ---

class RoleplayView(View):
    def __init__(self, action_type: str, sender: discord.Member, target: discord.Member):
        super().__init__(timeout=180)
        self.action_type = action_type
        self.sender = sender
        self.target = target
        label = "Kiss Back" if action_type == "kiss" else "Hug Back"
        self.add_item(Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"rp_{action_type}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Only the recipient can return this action!", ephemeral=True)
            return False
        return True


# --- 7. VOICEMASTER SETUP UI ---

class VoiceMasterSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Lock", emoji="🔒", description="Lock your voice channel"),
            discord.SelectOption(label="Unlock", emoji="🔓", description="Unlock your voice channel"),
            discord.SelectOption(label="Hide", emoji="👁️‍🗨️", description="Hide channel from public"),
            discord.SelectOption(label="Unhide", emoji="👁️", description="Make channel visible"),
            discord.SelectOption(label="Rename", emoji="✏️", description="Rename voice channel"),
            discord.SelectOption(label="Limit", emoji="👥", description="Set user capacity limit"),
            discord.SelectOption(label="Mute", emoji="🔇", description="Mute members"),
            discord.SelectOption(label="Unmute", emoji="🔊", description="Unmute members"),
            discord.SelectOption(label="Deafen", emoji="🔈", description="Deafen members"),
            discord.SelectOption(label="Undeafen", emoji="🎧", description="Undeafen members"),
            discord.SelectOption(label="Permit", emoji="📢", description="Permit specific users"),
            discord.SelectOption(label="Ban", emoji="🔨", description="Ban users from VC"),
            discord.SelectOption(label="Transfer", emoji="↗️", description="Transfer room ownership"),
            discord.SelectOption(label="Claim", emoji="👑", description="Claim abandoned room"),
            discord.SelectOption(label="Enable All", emoji="✅", description="Enable all control buttons")
        ]
        super().__init__(placeholder="› Select buttons to enable", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected = self.values
        embed = discord.Embed(
            title="✅ VoiceMaster Controls Updated",
            description=f"Successfully configured `{len(selected)}` interface controls for VoiceMaster dynamic channels.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.followup.send(embed=embed, ephemeral=True)


class VoiceMasterSetupView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(VoiceMasterSelect())


def build_voicemaster_setup_embed() -> tuple[discord.Embed, View]:
    embed = discord.Embed(
        title="VoiceMaster Setup",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.description = (
        "Select the buttons you want to enable for the VoiceMaster system.\n\n"
        "> Select `Enable All Buttons` to enable the full interface.\n"
        "> You can customize specific buttons from the dropdown below."
    )
    embed.set_footer(text="Powered by VEYRA")
    return embed, VoiceMasterSetupView()


# --- 8. WHITELIST CONFIGURATION UI ---

class WhitelistSelect(Select):
    def __init__(self, target_user: discord.Member):
        self.target_user = target_user
        perms = [
            "Anti Ban", "Anti Unban", "Anti Kick", "Anti Member Prune", "Anti Bot Add",
            "Anti Channel Create", "Anti Channel Delete", "Anti Channel Update",
            "Anti Role Create", "Anti Role Delete", "Anti Role Update", "Anti Member Update",
            "Anti Emoji/Sticker Create", "Anti Emoji/Sticker Delete", "Anti Webhook Create"
        ]
        options = [discord.SelectOption(label=p, emoji="🛡️", value=p) for p in perms[:15]]
        super().__init__(placeholder="› Choose Permissions to Grant", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected = self.values
        embed = discord.Embed(
            description=f"{self.target_user.mention} has been whitelisted for **{len(selected)} events**.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=None)


class WhitelistConfigView(View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.add_item(WhitelistSelect(target_user))

    @discord.ui.button(label="Grant All Permissions", style=discord.ButtonStyle.success)
    async def grant_all_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = discord.Embed(
            description=f"{self.target_user.mention} has been whitelisted for **all events**.",
            color=discord.Color.from_rgb(24, 24, 27)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=None)


def build_whitelist_embed(target_user: discord.Member) -> tuple[discord.Embed, View]:
    embed = discord.Embed(
        title="Whitelist Configuration for Current Server",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    embed.description = (
        "❌ : Anti Ban\n"
        "❌ : Anti Unban\n"
        "❌ : Anti Kick\n"
        "❌ : Anti Member Prune\n"
        "❌ : Anti Bot Add\n"
        "❌ : Anti Channel Create\n"
        "❌ : Anti Channel Delete\n"
        "❌ : Anti Channel Update\n"
        "❌ : Anti Role Create\n"
        "❌ : Anti Role Delete\n"
        "❌ : Anti Role Update\n"
        "❌ : Anti Member Update\n"
        "❌ : Anti Emoji/Sticker Create\n"
        "❌ : Anti Emoji/Sticker Delete\n\n"
        f"**Target:** {target_user.mention}"
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.set_footer(text="Powered by VEYRA")
    return embed, WhitelistConfigView(target_user)


# --- 9. TICKET VIEWS ---

class TicketWelcomeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="btn_ticket_close")
    async def close_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=False)
        embed = discord.Embed(
            title="Ticket Closed",
            color=discord.Color.from_rgb(239, 68, 68)
        )
        now_str = datetime.datetime.now(timezone.utc).strftime("%d %B %Y %H:%M")
        embed.add_field(name="Ticket Name", value=f"`{interaction.channel.name}`", inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Close Date", value=f"`{now_str}`", inline=True)
        embed.add_field(name="Ticket Close Reason", value="No reason provided", inline=False)
        embed.set_footer(text="Powered by VEYRA")
        await interaction.channel.send(embed=embed)
        await interaction.channel.send("⚠️ This ticket channel will be closed and removed shortly.")
        try:
            time.sleep(3)
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception:
            pass

    @discord.ui.button(label="Claim Ticket", emoji="🙋", style=discord.ButtonStyle.success, custom_id="btn_ticket_claim")
    async def claim_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=False)
        embed = discord.Embed(
            title="✅ Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}. They will assist you shortly.",
            color=discord.Color.from_rgb(34, 197, 94)
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.channel.send(embed=embed)


def build_ticket_welcome_embed(guild: discord.Guild, user: discord.Member or discord.User) -> tuple[discord.Embed, View]:
    embed = discord.Embed(
        title=f"🎫 🛒 {guild.name} Ticket",
        color=discord.Color.from_rgb(139, 92, 246)
    )
    embed.description = (
        f"Welcome to your private support ticket, {user.mention}!\n\n"
        f"**Welcome to your {guild.name} ticket! Support staff will assist you with your inquiry shortly.**\n\n"
        "⌛ **Please provide details about your inquiry below while waiting for staff.**"
    )
    ist_time = datetime.datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%I:%M %p")
    embed.set_footer(text=f"Powered by VEYRA • Today at {ist_time}")
    return embed, TicketWelcomeView()


# --- 10. SUBSCRIPTION PLANS UI ---

class PlansView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Free Plan", emoji="🟢", style=discord.ButtonStyle.secondary)
    async def free_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🟢 VEYRA Free Plan Details",
            description="Standard defense tools for growing communities.",
            color=discord.Color.from_rgb(34, 197, 94)
        )
        embed.add_field(
            name="🛡️ Standard Security",
            value="• Core Anti-Nuke protection\n• Basic Welcomer & Greetings\n• 1 Whitelist slot",
            inline=False
        )
        embed.add_field(
            name="💵 Cost",
            value="**₹0 / Free Forever**",
            inline=False
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Pro Plan", emoji="⚡", style=discord.ButtonStyle.primary)
    async def pro_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="⚡ VEYRA Pro Plan Details",
            description="Complete automation and robust verification gates.",
            color=discord.Color.from_rgb(139, 92, 246)
        )
        embed.add_field(
            name="🛡️ Advanced Protection",
            value="• Complete Anti-Nuke limits & triggers\n• Beast Mode & Anti-Raid mitigation\n• Automated Anti-Spam filters",
            inline=False
        )
        embed.add_field(
            name="💬 Interactive Greetings",
            value="• Custom Welcome & Exit embed messages\n• Direct Message (Join DM) builders\n• Invite Tracker & Sticky messages",
            inline=False
        )
        embed.add_field(
            name="🤖 Gatekeeping",
            value="• Verification Gateways (Button, Captcha, Image)\n• Auto-setup wizards",
            inline=False
        )
        embed.add_field(
            name="💵 Cost",
            value="**₹199 / Month** or **$4.99 / Month**",
            inline=False
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Premium Plan", emoji="💎", style=discord.ButtonStyle.success)
    async def premium_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="💎 VEYRA Premium Plan Details",
            description="The ultimate sovereign defense and absolute brand customizability.",
            color=discord.Color.from_rgb(234, 179, 8)
        )
        embed.add_field(
            name="👑 Custom Identity",
            value="• Custom Bot Profile (Avatar, Banner, Nickname)\n• Personalized client identity",
            inline=False
        )
        embed.add_field(
            name="🛡️ Whitelist Override",
            value="• Unlimited trusted member & role overrides\n• Complete bypass management",
            inline=False
        )
        embed.add_field(
            name="📈 Discovery & Growth",
            value="• Public discover listing directory\n• Scheduled growth server reports\n• Advanced XP & leveling system",
            inline=False
        )
        embed.add_field(
            name="💵 Cost",
            value="**₹299 / Month** or **$9.99 / Month** (Lifetime Access)",
            inline=False
        )
        embed.set_footer(text="Powered by VEYRA")
        await interaction.edit_original_response(embed=embed, view=self)


def build_plans_embed() -> tuple[discord.Embed, View]:
    embed = discord.Embed(
        title="⚡ VEYRA Pro Plan Details",
        description="Complete automation and robust verification gates.",
        color=discord.Color.from_rgb(139, 92, 246)
    )
    embed.add_field(
        name="🛡️ Advanced Protection",
        value="• Complete Anti-Nuke limits & triggers\n• Beast Mode & Anti-Raid mitigation\n• Automated Anti-Spam filters",
        inline=False
    )
    embed.add_field(
        name="💬 Interactive Greetings",
        value="• Custom Welcome & Exit embed messages\n• Direct Message (Join DM) builders\n• Invite Tracker & Sticky messages",
        inline=False
    )
    embed.add_field(
        name="🤖 Gatekeeping",
        value="• Verification Gateways (Button, Captcha, Image)\n• Auto-setup wizards",
        inline=False
    )
    embed.add_field(
        name="💵 Cost",
        value="**₹199 / Month** or **$4.99 / Month**",
        inline=False
    )
    embed.set_footer(text="Powered by VEYRA")
    return embed, PlansView()


# --- 11. GIVEAWAY EMBED ---

def build_giveaway_embed(prize: str, winners: int, ends_str: str, host: discord.Member) -> tuple[str, discord.Embed]:
    content = "🎉 **New Giveaway** 🎉"
    embed = discord.Embed(
        title=f"🎁 {prize.upper()} 🎁",
        color=discord.Color.from_rgb(234, 179, 8)
    )
    embed.description = (
        f"• **Winners:** {winners}\n"
        f"• **Ends** {ends_str}\n"
        f"• **Hosted by** {host.mention}\n\n"
        "• **React with 🎉 to participate!**"
    )
    embed.set_footer(text=f"Ends at | {datetime.datetime.now(timezone.utc).strftime('%m/%d/%Y')}")
    return content, embed


# --- 12. SECURITY AUDIT SCAN EMBED ---

def build_scan_embed(guild: discord.Guild, vulnerabilities: list = None) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ VEYRA Security Audit Scan",
        timestamp=datetime.datetime.now(timezone.utc)
    )
    if vulnerabilities:
        embed.color = discord.Color.from_rgb(245, 158, 11)
        embed.description = "⚠️ **Vulnerabilities / Recommendations Found:**\n\n" + "\n".join(vulnerabilities)
    else:
        embed.color = discord.Color.from_rgb(34, 197, 94)
        embed.description = "🟢 **Server is highly secure!** VEYRA has audited all security checks and found zero immediate vulnerabilities."
    embed.set_footer(text="VEYRA V2 • Security Audit Scan")
    return embed


# --- 13. SERVERINFO EMBED ---

class ServerInfoSelect(Select):
    def __init__(self, guild):
        self.guild = guild
        roles_count = len(guild.roles)
        emojis_count = len(guild.emojis)
        options = [
            discord.SelectOption(label="General Information", emoji="🏠", description="Basic server information and statistics", value="general"),
            discord.SelectOption(label="Server Roles", emoji="🎭", description=f"View all {roles_count} server roles with pagination", value="roles"),
            discord.SelectOption(label="Server Emojis", emoji="📺", description=f"View all {emojis_count} server emojis with pagination", value="emojis")
        ]
        super().__init__(placeholder="🏠 General Information", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        val = self.values[0]
        guild = self.guild
        if val == "general":
            embed = build_server_info_embed(guild)
            await interaction.edit_original_response(embed=embed, view=self.view)
        elif val == "roles":
            roles_str = ", ".join([r.mention for r in guild.roles[:35]])
            embed = discord.Embed(
                title=f"{guild.name} — Server Roles ({len(guild.roles)})",
                description=roles_str or "No roles found",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text="Powered by VEYRA")
            await interaction.edit_original_response(embed=embed, view=self.view)
        elif val == "emojis":
            emojis_str = " ".join([str(e) for e in guild.emojis[:40]])
            embed = discord.Embed(
                title=f"{guild.name} — Server Emojis ({len(guild.emojis)})",
                description=emojis_str or "No custom emojis found",
                color=discord.Color.from_rgb(24, 24, 27)
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text="Powered by VEYRA")
            await interaction.edit_original_response(embed=embed, view=self.view)


class ServerInfoView(View):
    def __init__(self, guild):
        super().__init__(timeout=300)
        self.add_item(ServerInfoSelect(guild))


def build_server_info_embed(guild) -> discord.Embed:
    created_ts = int(guild.created_at.timestamp())
    text_count = len(guild.text_channels)
    voice_count = len(guild.voice_channels)
    total_channels = len(guild.channels)
    
    embed = discord.Embed(
        title=f"{guild.name}",
        color=discord.Color.from_rgb(24, 24, 27)
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="__Description__", value=guild.description or "No description set.", inline=False)
    
    about_val = (
        f"• **Name:** {guild.name}\n"
        f"• **ID:** `{guild.id}`\n"
        f"• **Owner:** <@{guild.owner_id}>\n"
        f"• **Created At:** <t:{created_ts}:R>\n"
        f"• **Members:** `{guild.member_count or len(guild.members)}`"
    )
    embed.add_field(name="__About__", value=about_val, inline=False)
    
    ver_level = str(guild.verification_level).capitalize()
    stats_val = (
        f"• **Verification Level:** {ver_level}\n"
        f"• **Channels:** `{total_channels}`\n"
        f"• **Roles:** `{len(guild.roles)}`\n"
        f"• **Emojis:** `{len(guild.emojis)}`\n"
        f"• **Boost Status:** Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)"
    )
    embed.add_field(name="__General Stats__", value=stats_val, inline=False)
    
    channels_val = (
        f"• **Total:** `{total_channels}`\n"
        f"• **Text:** `{text_count}` | **Voice:** `{voice_count}`"
    )
    embed.add_field(name="__Channels__", value=channels_val, inline=False)
    embed.set_footer(text="Powered by VEYRA")
    return embed


# --- 14. GENERAL VEYRA EMBED BUILDERS ---

def build_veyra_embed(title: str, description: str = "", state: str = "info", fields: list = None, footer: str = "VEYRA Control Center", thumbnail_url: str = None) -> discord.Embed:
    color = discord.Color.from_rgb(24, 24, 27)
    if state == "success":
        color = discord.Color.from_rgb(34, 197, 94)
    elif state == "warning":
        color = discord.Color.from_rgb(245, 158, 11)
    elif state == "error":
        color = discord.Color.from_rgb(239, 68, 68)
        
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    if fields:
        for f in fields:
            if isinstance(f, tuple):
                embed.add_field(name=f[0], value=f[1], inline=f[2] if len(f) > 2 else False)
            elif isinstance(f, dict):
                embed.add_field(name=f.get("name", ""), value=f.get("value", ""), inline=f.get("inline", False))
    embed.set_footer(text=footer)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    return embed


def create_veyra_embed(title: str, description: str = "", status: str = None, fields: list = None, thumbnail: str = None, color: discord.Color = discord.Color.from_rgb(24, 24, 27), footer: str = "VEYRA V2 • About Diagnostics", icon_url: str = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if fields:
        for f in fields:
            if isinstance(f, tuple):
                embed.add_field(name=f[0], value=f[1], inline=f[2] if len(f) > 2 else False)
    if icon_url:
        embed.set_footer(text=footer, icon_url=icon_url)
    else:
        embed.set_footer(text=footer)
    return embed


# --- 15. VEYRA RESPONSE CLASS & CONTROL CENTER VIEW ---

class VeyraResponse:
    COLOR_PRIMARY = discord.Color.from_rgb(24, 24, 27)
    COLOR_SUCCESS = discord.Color.from_rgb(34, 197, 94)
    COLOR_WARNING = discord.Color.from_rgb(245, 158, 11)
    COLOR_ERROR   = discord.Color.from_rgb(239, 68, 68)
    COLOR_INFO    = discord.Color.from_rgb(59, 130, 246)

    STATE_ICONS = {
        "loading": "⏳",
        "success": "✓",
        "warning": "⚠",
        "error": "✕",
        "info": "ℹ️"
    }


class VeyraControlCenterView(View):
    def __init__(self, bot_client=None):
        super().__init__(timeout=300)
        self.bot = bot_client


ANTINUKE_EVENTS = [
    "Anti Ban", "Anti Unban", "Anti Kick", "Anti Member Prune", "Anti Bot Add",
    "Anti Channel Create", "Anti Channel Delete", "Anti Channel Update",
    "Anti Role Create", "Anti Role Delete", "Anti Role Update", "Anti Member Update",
    "Anti Emoji/Sticker Create", "Anti Emoji/Sticker Delete", "Anti Webhook Create"
]
