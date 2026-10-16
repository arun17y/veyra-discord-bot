"""
music_bot - Production Music Architecture for VEYRA All-in-One Bot
Ported directly from shadow-music-bot (E:\Bot\music bot 1)
"""
import os
import sys
import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("veyra.music")

music_dir = os.path.dirname(os.path.abspath(__file__))
if music_dir not in sys.path:
    sys.path.insert(0, music_dir)

# Ensure local ffmpeg bin is in PATH
ffmpeg_bin = os.path.join(music_dir, "ffmpeg", "bin")
if os.path.exists(ffmpeg_bin) and ffmpeg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

# Import the core music bot module
from . import bot as mbot

# Expose core classes and singletons
Database = mbot.Database
SpotifyResolver = mbot.SpotifyResolver
YTSource = mbot.YTSource
GuildPlayer = mbot.GuildPlayer
MusicPanel = mbot.MusicPanel
ensure_vc = mbot.ensure_vc
play_next = mbot.play_next
panel_embed = mbot.panel_embed
history_embed = mbot.history_embed

def setup_music_system(target_bot: commands.Bot):
    """
    Registers the complete music suite from music_bot directly into VEYRA,
    transforming VEYRA into the full All-in-One Bot.
    """
    # 1. Add player management dictionary if not present
    if not hasattr(target_bot, "players"):
        target_bot.players = {}

    def _get_player(guild_id: int) -> GuildPlayer:
        if guild_id not in target_bot.players:
            mbot.Database.init_guild(guild_id)
            p = GuildPlayer(guild_id)
            try:
                vol = mbot.Database.get_volume(guild_id)
                p.volume = vol / 100
                stay_247, _, _ = mbot.Database.get_247(guild_id)
                p.stay_247 = bool(stay_247)
                p.announce = bool(mbot.Database.get_announcement(guild_id))
                p.dj_role_id = mbot.Database.get_dj_role(guild_id)
            except Exception:
                pass
            target_bot.players[guild_id] = p
        return target_bot.players[guild_id]

    # 1. Capture all commands from the music bot module first
    mbot_commands = list(mbot.bot.commands)

    target_bot.get_player = _get_player
    target_bot.booted = True
    mbot.bot = target_bot
    mbot.bot.get_player = _get_player
    mbot.bot.booted = True

    # Hook voice state listener for self-healing 24/7 voice and DAVE protocol
    target_bot.add_listener(mbot.on_voice_state_update, "on_voice_state_update")

    # Hook on_ready listener for 24/7 watchdog and auto-reconnect
    @target_bot.listen("on_ready")
    async def _on_music_ready():
        target_bot.booted = True
        mbot.bot.booted = True
        if not mbot.check_voice_channels.is_running():
            try:
                mbot.check_voice_channels.start()
                print("🔊 Music 24/7 Watchdog task loop started.")
            except Exception as e:
                logger.debug(f"Watchdog start notice: {e}")

        async def _reconnect_247():
            await asyncio.sleep(4)
            try:
                records = mbot.Database.get_all_247()
                for row in records:
                    guild_id, stay_247, vc_id, tx_id = row
                    if stay_247 and vc_id:
                        guild = target_bot.get_guild(guild_id)
                        if not guild:
                            continue
                        p = target_bot.get_player(guild_id)
                        p.stay_247 = True
                        ch = guild.get_channel(vc_id)
                        if ch and isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                            try:
                                if not guild.voice_client:
                                    p.is_connecting = True
                                    p.voice = await ch.connect(timeout=20, reconnect=True)
                                    if tx_id:
                                        p.text_ch = guild.get_channel(tx_id)
                                    print(f"🎙️ [Music 24/7] Connected to {ch.name} in {guild.name}")
                            except Exception as ex:
                                print(f"⚠️ [Music 24/7] Reconnect notice for {guild.name}: {ex}")
                            finally:
                                p.is_connecting = False
            except Exception as e:
                print(f"⚠️ [Music 24/7] DB query error: {e}")

        asyncio.create_task(_reconnect_247())

    # 2. Register all music commands as prefix commands so all 110+ controls are available
    skip_cmds = {"sync", "help", "about", "invite", "ping", "stats", "uptime"}
    for cmd in mbot_commands:
        if cmd.name in skip_cmds:
            continue
        try:
            if target_bot.get_command(cmd.name):
                target_bot.remove_command(cmd.name)
            p_cmd = commands.Command(cmd.callback, name=cmd.name, aliases=cmd.aliases, description=cmd.description)
            target_bot.add_command(p_cmd)
        except Exception as e:
            logger.debug(f"Could not add prefix command {cmd.name}: {e}")

    # 3. Register Core Top-Level Slash Commands for instant Discord autocomplete UI (stays safely under 100 slash ceiling)

    try:
        @target_bot.tree.command(name="play", description="Play any song or playlist from YouTube or Spotify")
        @app_commands.describe(query="Song title, YouTube URL/playlist, or Spotify link")
        async def tree_play(interaction: discord.Interaction, query: str):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_play(ctx, query=query)
    except Exception as e:
        logger.debug(f"tree_play registration: {e}")

    try:
        @target_bot.tree.command(name="panel", description="Open the live interactive music control panel")
        async def tree_panel(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_panel(ctx)
    except Exception as e:
        logger.debug(f"tree_panel registration: {e}")

    try:
        @target_bot.tree.command(name="skip", description="Skip current playing track")
        async def tree_skip(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_skip(ctx)
    except Exception as e:
        logger.debug(f"tree_skip registration: {e}")

    try:
        @target_bot.tree.command(name="stop", description="Stop music, clear queue, and disconnect")
        async def tree_stop(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_stop(ctx)
    except Exception as e:
        logger.debug(f"tree_stop registration: {e}")

    try:
        @target_bot.tree.command(name="pause", description="Pause playback")
        async def tree_pause(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_pause(ctx)
    except Exception as e:
        logger.debug(f"tree_pause registration: {e}")

    try:
        @target_bot.tree.command(name="resume", description="Resume playback")
        async def tree_resume(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_resume(ctx)
    except Exception as e:
        logger.debug(f"tree_resume registration: {e}")

    try:
        @target_bot.tree.command(name="queue", description="Show music queue")
        async def tree_queue(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_queue(ctx)
    except Exception as e:
        logger.debug(f"tree_queue registration: {e}")

    try:
        @target_bot.tree.command(name="stay247", description="Toggle 24/7 channel presence (bot stays in VC)")
        async def tree_stay247(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_stay247(ctx)
    except Exception as e:
        logger.debug(f"tree_stay247 registration: {e}")

    try:
        @target_bot.tree.command(name="247", description="Set 24/7 system (toggle staying in voice channel)")
        async def tree_247(interaction: discord.Interaction):
            ctx = await target_bot.get_context(interaction)
            await mbot.slash_247(ctx)
    except Exception as e:
        logger.debug(f"tree_247 registration: {e}")

    print("✅ VEYRA All-in-One Bot: Loaded complete Music Suite from music_bot.")
