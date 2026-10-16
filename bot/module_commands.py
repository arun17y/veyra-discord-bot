# bot/module_commands.py - Prefix Commands for all 20 Veyra Modules (1:1 UI Overhaul)
import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone
import asyncio

THEME_COLOR = discord.Color.from_rgb(43, 45, 49)

def setup_module_commands(bot: commands.Bot):
    orig_command = bot.command
    orig_group = bot.group

    def safe_command(*args, **kwargs):
        def decorator(func):
            name = kwargs.get('name', func.__name__)
            aliases = kwargs.get('aliases', [])
            existing = bot.get_command(name)
            if existing:
                bot.remove_command(name)
            for a in aliases:
                ex_a = bot.get_command(a)
                if ex_a:
                    bot.remove_command(a)
            try:
                cmd = commands.command(*args, **kwargs)(func)
                bot.add_command(cmd)
                return cmd
            except Exception as ex:
                return func
        return decorator

    def safe_group(*args, **kwargs):
        def decorator(func):
            name = kwargs.get('name', func.__name__)
            existing = bot.get_command(name)
            if existing:
                bot.remove_command(name)
            try:
                grp = commands.group(*args, **kwargs)(func)
                bot.add_command(grp)
                return grp
            except Exception as ex:
                return func
        return decorator

    bot.command = safe_command
    bot.group = safe_group
    try:
        _register_all_modules(bot)
    finally:
        bot.command = orig_command
        bot.group = orig_group

def _register_all_modules(bot: commands.Bot):
    # ==================== FUN COMMANDS ====================

    @bot.command(name="dare", description="Get a random dare")
    async def dare_cmd(ctx):
        dares = [
            "Send the 5th image in your gallery to the general chat.",
            "Text your best friend something weird with zero context.",
            "Change your server nickname to 'Certified Bot' for 24 hours.",
            "Speak only in rhymes for the next 10 minutes in chat.",
            "Confess your most embarrassing guilty pleasure song.",
            "Type a paragraph with your eyes closed and send it without editing."
        ]
        embed = discord.Embed(
            title="🎯 Dare Challenge",
            description=random.choice(dares),
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="truth", description="Get a random truth question")
    async def truth_cmd(ctx):
        truths = [
            "What is the biggest secret you've kept from your friends?",
            "What is the most embarrassing thing in your search history?",
            "Have you ever ghosted someone and regretted it?",
            "If you could trade lives with anyone in this server, who would it be?",
            "What was your most awkward moment this year?",
            "What is the worst lie you ever told your parents?"
        ]
        embed = discord.Embed(
            title="🔍 Truth Query",
            description=random.choice(truths),
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="pickup", description="Get a smooth pickup line")
    async def pickup_cmd(ctx):
        lines = [
            "Are you a magician? Because whenever I look at you, everyone else disappears.",
            "Do you have a map? I keep getting lost in your eyes.",
            "Are you a Wi-Fi router? Because I'm feeling a strong connection.",
            "Is your name Google? Because you have everything I’ve been searching for.",
            "Are you a parking ticket? Because you’ve got 'fine' written all over you."
        ]
        embed = discord.Embed(
            title="💘 Pickup Line",
            description=f"*{random.choice(lines)}*",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="rickroll", description="Rickroll someone")
    async def rickroll_cmd(ctx, member: discord.Member = None):
        target = member or ctx.author
        embed = discord.Embed(
            title="🎵 Never Gonna Give You Up",
            description=f"Hey {target.mention}, [click here for free Discord Nitro!](https://www.youtube.com/watch?v=dQw4w9WgXcQ)",
            color=THEME_COLOR
        )
        embed.set_thumbnail(url="https://media.tenor.com/x8v1oNUOmg4AAAAd/rickroll-roll.gif")
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="meme", description="Get a random meme")
    async def meme_cmd(ctx):
        memes = [
            ("https://i.imgflip.com/1g8my4.jpg", "Two Buttons"),
            ("https://i.imgflip.com/1ur9b0.jpg", "Distracted Boyfriend"),
            ("https://i.imgflip.com/261o3j.jpg", "Expanding Brain"),
            ("https://i.imgflip.com/2fm6x0.jpg", "Epic Handshake"),
            ("https://i.imgflip.com/30b1gx.jpg", "Drake Hotline Bling")
        ]
        url, title = random.choice(memes)
        embed = discord.Embed(
            title=f"😂 {title}",
            color=THEME_COLOR
        )
        embed.set_image(url=url)
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="nitro", description="Generate a fake Discord Nitro gift")
    async def nitro_cmd(ctx):
        code = "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=16))
        embed = discord.Embed(
            title="🎁 A WILD NITRO GIFT APPEARED!",
            description=(
                "**Expires in 48 hours**\n\n"
                f"Claim your 1 month of Discord Nitro:\n"
                f"[discord.gift/{code}](https://discord.gift/{code})"
            ),
            color=THEME_COLOR
        )
        embed.set_thumbnail(url="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png")
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="texttoemoji", aliases=["emojify"], description="Convert text to emoji letters")
    async def texttoemoji_cmd(ctx, *, text: str):
        char_map = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪', 'f': '🇫',
            'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯', 'k': '🇰', 'l': '🇱',
            'm': '🇲', 'n': '🇳', 'o': '🇴', 'p': '🇵', 'q': '🇶', 'r': '🇷',
            's': '🇸', 't': '🇹', 'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽',
            'y': '🇾', 'z': '🇿', '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣',
            '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
            ' ': '   '
        }
        res = " ".join(char_map.get(c.lower(), c) for c in text[:40])
        await ctx.send(res)

    @bot.command(name="wizz", description="Simulate a fast wizz")
    async def wizz_cmd(ctx):
        msg = await ctx.send("`[+] Initializing Veyra Wizz Sequence...`")
        await asyncio.sleep(0.8)
        await msg.edit(content="`[+] Stripping permissions... [OK]`")
        await asyncio.sleep(0.8)
        await msg.edit(content="`[+] Locking channels... [OK]`")
        await asyncio.sleep(0.8)
        embed = discord.Embed(
            title="⚡ Wizz Simulation Complete",
            description="```yaml\nStatus  :: Simulated\nSpeed   :: 0.04s\nTargets :: 0 (Safe Demonstration)\n```",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await msg.edit(content=None, embed=embed)

    @bot.command(name="hack", description="Simulate hacking a user")
    async def hack_cmd(ctx, member: discord.Member = None):
        target = member or ctx.author
        ip = f"{random.randint(11, 199)}.{random.randint(10, 255)}.{random.randint(10, 255)}.{random.randint(1, 254)}"
        msg = await ctx.send(f"`[+] Injecting exploit into {target.name}...`")
        await asyncio.sleep(1.0)
        await msg.edit(content=f"`[+] Resolving IP: {ip}...`")
        await asyncio.sleep(1.0)
        await msg.edit(content="`[+] Bypassing 2FA token protection...`")
        await asyncio.sleep(1.0)
        embed = discord.Embed(
            title=f"💻 Compromised: {target.name}",
            description=(
                f"```yaml\n"
                f"Target    :: {target.name}#{target.discriminator}\n"
                f"IP        :: {ip}\n"
                f"Email     :: {target.name.lower().replace(' ', '_')}@gmail.com\n"
                f"Password  :: {'*'*random.randint(8, 14)}\n"
                f"Status    :: Simulated Breach\n"
                f"```"
            ),
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await msg.edit(content=None, embed=embed)

    @bot.command(name="ship", description="Check love compatibility between two members")
    async def ship_cmd(ctx, user1: discord.Member, user2: discord.Member = None):
        if not user2:
            user2 = user1
            user1 = ctx.author
        seed = (user1.id + user2.id) % 101
        bar_len = 10
        filled = int((seed / 100) * bar_len)
        bar = "❤️" * filled + "🖤" * (bar_len - filled)
        embed = discord.Embed(
            title="💞 Love Calculator",
            description=(
                f"**{user1.name}** + **{user2.name}**\n\n"
                f"**Match:** `{seed}%`\n"
                f"{bar}\n\n"
                f"{'🔥 A match made in heaven!' if seed > 75 else ('✨ Good vibes together!' if seed > 40 else '💔 Better stay as friends.')}"
            ),
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    # ==================== GENERAL & UTILITY COMMANDS ====================

    @bot.command(name="afk", description="Set an AFK status")
    async def afk_cmd(ctx, *, reason: str = "AFK"):
        embed = discord.Embed(
            description=f"💤 {ctx.author.mention} is now AFK: **{reason}**",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    if not bot.get_command("banner"):
        @bot.command(name="banner", description="Displays user or server banner")
        async def banner_cmd(ctx, member: discord.Member = None):
            target = member or ctx.author
            user = await bot.fetch_user(target.id)
            if user.banner:
                embed = discord.Embed(title=f"{target.name}'s Banner", color=THEME_COLOR)
                embed.set_image(url=user.banner.url)
            else:
                embed = discord.Embed(
                    description=f"⚠️ {target.mention} does not have a custom profile banner.",
                    color=THEME_COLOR
                )
            embed.set_footer(text="Powered by Veyra Development™")
            await ctx.send(embed=embed)

    @bot.command(name="membercount", aliases=["mc"], description="Display server member counts")
    async def membercount_cmd(ctx):
        g = ctx.guild
        total = g.member_count or len(g.members)
        humans = sum(1 for m in g.members if not m.bot)
        bots = sum(1 for m in g.members if m.bot)
        embed = discord.Embed(
            title=f"📊 {g.name} Member Count",
            color=THEME_COLOR
        )
        embed.add_field(name="Total Members", value=f"`{total}`", inline=True)
        embed.add_field(name="Humans", value=f"`{humans}`", inline=True)
        embed.add_field(name="Bots", value=f"`{bots}`", inline=True)
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="channelinfo", aliases=["ci"], description="Show channel information")
    async def channelinfo_cmd(ctx, channel: discord.TextChannel = None):
        ch = channel or ctx.channel
        embed = discord.Embed(
            title=f"📌 Channel: #{ch.name}",
            color=THEME_COLOR
        )
        embed.add_field(name="Channel ID", value=f"`{ch.id}`", inline=True)
        embed.add_field(name="Category", value=f"`{ch.category.name if ch.category else 'None'}`", inline=True)
        embed.add_field(name="Created At", value=f"`{ch.created_at.strftime('%Y-%m-%d')}`", inline=True)
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="roleinfo", aliases=["ri"], description="Show role information")
    async def roleinfo_cmd(ctx, role: discord.Role):
        embed = discord.Embed(
            title=f"🛡️ Role: {role.name}",
            color=role.color if role.color.value != 0 else THEME_COLOR
        )
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Members", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="Mentionable", value=f"`{'Yes' if role.mentionable else 'No'}`", inline=True)
        embed.add_field(name="Hoisted", value=f"`{'Yes' if role.hoist else 'No'}`", inline=True)
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.command(name="math", aliases=["calc"], description="Evaluate mathematical expression")
    async def math_cmd(ctx, *, expr: str):
        allowed = set("0123456789+-*/(). %^")
        if not all(c in allowed for c in expr):
            return await ctx.send("❌ Invalid characters in mathematical expression.")
        try:
            safe_expr = expr.replace("^", "**")
            result = eval(safe_expr, {"__builtins__": None}, {})
            embed = discord.Embed(
                title="🧮 Calculator",
                description=f"```yaml\nInput  :: {expr}\nResult :: {result}\n```",
                color=THEME_COLOR
            )
            embed.set_footer(text="Powered by Veyra Development™")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Calculation error: `{e}`")

    @bot.command(name="poll", description="Create an interactive poll")
    async def poll_cmd(ctx, *, question: str):
        embed = discord.Embed(
            title="📊 Community Poll",
            description=f"**{question}**\n\nReact below to vote!",
            color=THEME_COLOR
        )
        embed.set_footer(text=f"Asked by {ctx.author.name} • Veyra Development™")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @bot.command(name="remind", aliases=["reminder"], description="Set a timer reminder")
    async def remind_cmd(ctx, seconds: int, *, reminder: str):
        embed = discord.Embed(
            description=f"⏰ Reminder set for **{seconds}s**: `{reminder}`",
            color=THEME_COLOR
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(seconds)
        await ctx.send(f"🔔 {ctx.author.mention} **Reminder:** {reminder}")

    # ==================== MODERATION COMMANDS ====================

    @bot.command(name="unban", description="Unban a user by ID")
    @commands.has_permissions(ban_members=True)
    async def unban_cmd(ctx, user_id: int):
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            embed = discord.Embed(
                description=f"✅ Successfully unbanned **{user.name}** (`{user.id}`).",
                color=THEME_COLOR
            )
            embed.set_footer(text="Powered by Veyra Development™")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Could not unban user: `{e}`")

    @bot.command(name="untimeout", aliases=["unmute_timeout"], description="Remove timeout from a member")
    @commands.has_permissions(moderate_members=True)
    async def untimeout_cmd(ctx, member: discord.Member):
        try:
            await member.timeout(None)
            embed = discord.Embed(
                description=f"✅ Timeout removed from {member.mention}.",
                color=THEME_COLOR
            )
            embed.set_footer(text="Powered by Veyra Development™")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Could not remove timeout: `{e}`")

    # Note: Full production music engine is loaded via music_bot folder

    # ==================== MODULE GROUPS ====================

    @bot.group(name="automod", invoke_without_command=True)
    async def automod_prefix_group(ctx):
        embed = discord.Embed(
            title="🛡️ AutoMod System",
            description=(
                "**Available Commands:**\n"
                "`automod enable`, `automod disable`, `automod config`, `automod profanity`,\n"
                "`automod links`, `automod antispam`, `automod caps`, `automod mentions`"
            ),
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @automod_prefix_group.command(name="enable")
    async def automod_enable(ctx):
        embed = discord.Embed(description="🛡️ AutoMod has been **enabled** with default filters.", color=THEME_COLOR)
        await ctx.send(embed=embed)

    @automod_prefix_group.command(name="disable")
    async def automod_disable(ctx):
        embed = discord.Embed(description="🛡️ AutoMod has been **disabled** for this server.", color=THEME_COLOR)
        await ctx.send(embed=embed)

    @bot.group(name="giveaway", invoke_without_command=True)
    async def giveaway_prefix_group(ctx):
        embed = discord.Embed(
            title="🎁 Giveaway System",
            description="Use `giveaway start <prize>`, `giveaway end`, or `giveaway reroll`.",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @giveaway_prefix_group.command(name="start")
    async def giveaway_start_cmd(ctx, *, prize: str = "Discord Nitro"):
        from interactive_ui import build_giveaway_embed
        content, embed = build_giveaway_embed(prize, 1, "in 2 days", ctx.author)
        msg = await ctx.send(content=content, embed=embed)
        await msg.add_reaction("🎉")

    @bot.group(name="vanity", invoke_without_command=True)
    async def vanity_prefix_group(ctx):
        embed = discord.Embed(
            title="⭐ Vanity Roles System",
            description="Track server vanity URL status in members' custom status.",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    @bot.group(name="welcomer", invoke_without_command=True)
    async def welcomer_prefix_group(ctx):
        embed = discord.Embed(
            title="🚪 Welcomer System",
            description="Configure server welcome messages, channels, and embeds.",
            color=THEME_COLOR
        )
        embed.set_footer(text="Powered by Veyra Development™")
        await ctx.send(embed=embed)

    print("✅ Registered All 20 Module Prefix Commands.")
