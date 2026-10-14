# bot/music_system.py - Production Music Bot Engine for VEYRA
# Full Audio Architecture: yt-dlp + SpotifyResolver + FFmpeg + GuildPlayer + Real-Time Interactive Music Panel

import asyncio
import importlib
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db

logger = logging.getLogger("veyra.music")

# ─────────────────────────────────────────────
#             AUDIO & OPUS SETUP
# ─────────────────────────────────────────────

# Ensure Opus audio codec is loaded on Windows and Linux
try:
    if not discord.opus.is_loaded():
        for opus_lib in [
            os.path.join(os.path.dirname(__file__), "libopus-0.x64.dll"),
            os.path.join(os.path.dirname(__file__), "..", "libopus-0.x64.dll"),
            r"C:\Users\Arun Yadav\.gemini\antigravity\scratch\Veyra All in one Discord Bot\bot\libopus-0.x64.dll",
            r"C:\Users\Arun Yadav\.gemini\antigravity\scratch\Veyra All in one Discord Bot\libopus-0.x64.dll",
            r"E:\Bot\music bot 1\libopus-0.x64.dll",
            'libopus-0.x64.dll',
            'libopus.so.0',
            'libopus.so',
            '/usr/lib/x86_64-linux-gnu/libopus.so.0',
            '/usr/lib/aarch64-linux-gnu/libopus.so.0',
            'opus'
        ]:
            try:
                discord.opus.load_opus(opus_lib)
                if discord.opus.is_loaded():
                    logger.info("Loaded Opus audio codec: %s", opus_lib)
                    break
            except Exception:
                pass
except Exception:
    pass

def get_ffmpeg_executable() -> str:
    candidates = [
        shutil.which("ffmpeg"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg"
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "ffmpeg"

# Spotify credentials from environment
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

COOKIE_ARG = None
possible_cookie_paths = [
    os.path.join(os.path.dirname(__file__), "cookies.txt"),
    os.path.join(os.path.dirname(__file__), "..", "cookies.txt"),
    r"C:\Users\Arun Yadav\.gemini\antigravity\scratch\Veyra All in one Discord Bot\cookies.txt",
    r"E:\Bot\music bot 1\cookies.txt"
]
for cp in possible_cookie_paths:
    if os.path.exists(cp):
        COOKIE_ARG = os.path.abspath(cp)
        break

YTDL_OPTIONS = {
    "format": "bestaudio/18/best",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "cookiefile": COOKIE_ARG,
    "js_runtimes": {"node": {}},
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "mweb"]
        }
    },
}

# ─────────────────────────────────────────────
#             EMBED & UI HELPERS (OBSIDIAN)
# ─────────────────────────────────────────────

EMBED_COLOR = 0x2B2D31
BRAND_FOOTER = "Powered By Veyra Development™ | Designed By Arun"

def make_embed(title: str = "", desc: str = "", color: int = EMBED_COLOR) -> discord.Embed:
    e = discord.Embed(
        title=title[:256] if title else None,
        description=desc[:4096] if desc else None,
        color=color
    )
    e.set_footer(text=BRAND_FOOTER)
    return e

def err(msg: str) -> discord.Embed:
    formatted = f">>> {msg}" if not msg.startswith(">>>") else msg
    e = discord.Embed(
        title="❌ Music Notice",
        description=formatted[:4096],
        color=EMBED_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    e.set_footer(text=BRAND_FOOTER)
    return e

def ok(title: str, desc: str = "") -> discord.Embed:
    formatted_desc = f">>> {desc}" if desc and not desc.startswith(">>>") else desc
    e = discord.Embed(
        title=f"✅ {title}",
        description=formatted_desc[:4096] if formatted_desc else None,
        color=EMBED_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    e.set_footer(text=BRAND_FOOTER)
    return e

def _fmt(secs: int) -> str:
    if not secs:
        return "0:00"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def parse_time(val: str, duration: int = 0) -> Optional[int]:
    val = val.strip()
    try:
        if val.endswith("%"):
            pct = float(val[:-1])
            return int((pct / 100) * duration)
        elif ":" in val:
            parts = val.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return int(val)
    except Exception:
        return None

def make_progress_bar(pos: int, total: int, width: int = 14) -> str:
    if total <= 0:
        return "━" * width
    percentage = max(0.0, min(1.0, pos / total))
    idx = int(percentage * (width - 1))
    return "━" * idx + "🔘" + "─" * (width - 1 - idx)

async def send_response(
    ctx: commands.Context,
    embed: discord.Embed,
    view: Optional[discord.ui.View] = None,
    delete_after: Optional[float] = None
) -> Optional[discord.Message]:
    if ctx.interaction:
        try:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=False)
                try:
                    return await ctx.interaction.original_response()
                except Exception:
                    return None
            else:
                return await ctx.interaction.followup.send(embed=embed, view=view, ephemeral=False, wait=True)
        except Exception:
            pass
    try:
        return await ctx.channel.send(embed=embed, view=view, delete_after=delete_after)
    except Exception:
        return None

# ─────────────────────────────────────────────
#             DATABASE ADAPTER WRAPPER
# ─────────────────────────────────────────────

class MusicDB:
    @staticmethod
    def init_schema():
        try:
            conn = get_db()
            cursor = conn.cursor()
            for col, ctype in [
                ("volume", "INTEGER DEFAULT 100"),
                ("stay_247", "INTEGER DEFAULT 0"),
                ("stay_voice_id", "TEXT"),
                ("stay_text_id", "TEXT"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS {col} {ctype}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def init_guild(guild_id: int):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def increment_stat(stat_name: str, by: int = 1):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO global_stats (stat_name, stat_value) VALUES (?, ?) ON CONFLICT(stat_name) DO UPDATE SET stat_value = global_stats.stat_value + ?",
                (stat_name, by, by)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def get_stat(stat_name: str) -> int:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT stat_value FROM global_stats WHERE stat_name = ?", (stat_name,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception:
            return 0

    @staticmethod
    def get_volume(guild_id: int) -> int:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT volume FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
            row = cursor.fetchone()
            conn.close()
            return row[0] if (row and row[0] is not None) else 100
        except Exception:
            return 100

    @staticmethod
    def set_volume(guild_id: int, volume: int):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO guild_settings (guild_id, volume) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET volume = ?",
                (str(guild_id), volume, volume)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def get_247(guild_id: int) -> tuple:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT stay_247, stay_voice_id, stay_text_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
            row = cursor.fetchone()
            conn.close()
            return row if row else (0, None, None)
        except Exception:
            return (0, None, None)

    @staticmethod
    def set_247(guild_id: int, enabled: int, voice_id: Optional[int] = None, text_id: Optional[int] = None):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO guild_settings (guild_id, stay_247, stay_voice_id, stay_text_id) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET stay_247 = ?, stay_voice_id = ?, stay_text_id = ?",
                (str(guild_id), enabled, str(voice_id) if voice_id else None, str(text_id) if text_id else None, enabled, str(voice_id) if voice_id else None, str(text_id) if text_id else None)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def like_track(user_id: int, url: str, title: str, author: str, thumbnail: str, duration: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO liked_tracks (user_id, track_url, track_title, track_author, track_thumbnail, track_duration) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, url, title, author, thumbnail, duration)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def unlike_track(user_id: int, url: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM liked_tracks WHERE user_id = ? AND track_url = ?", (user_id, url))
        conn.commit()
        conn.close()

    @staticmethod
    def get_liked_tracks(user_id: int) -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT track_title, track_url, track_author, track_duration, track_thumbnail FROM liked_tracks WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"title": r[0], "url": r[1], "author": r[2], "duration": r[3], "thumbnail": r[4]} for r in rows]

    @staticmethod
    def create_playlist(user_id: int, name: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM playlists WHERE user_id = ? AND name = ?", (user_id, name))
        if cursor.fetchone():
            conn.close()
            return False
        cursor.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete_playlist(user_id: int, name: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute("DELETE FROM playlists WHERE id = ?", (pl_id,))
        cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_playlists(user_id: int) -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM playlists WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    @staticmethod
    def add_to_playlist(user_id: int, pl_name: str, title: str, author: str, url: str, thumbnail: str, duration: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, pl_name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute(
            "INSERT INTO playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (pl_id, title, author, url, thumbnail, duration)
        )
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_playlist_tracks(user_id: int, pl_name: str) -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, pl_name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []
        pl_id = row[0]
        cursor.execute("SELECT title, author, url, thumbnail, duration FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"title": r[0], "author": r[1], "url": r[2], "thumbnail": r[3], "duration": r[4]} for r in rows]

    @staticmethod
    def remove_from_playlist(user_id: int, pl_name: str, index: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, pl_name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute("SELECT id FROM playlist_tracks WHERE playlist_id = ? ORDER BY id", (pl_id,))
        rows = cursor.fetchall()
        if index < 0 or index >= len(rows):
            conn.close()
            return False
        track_db_id = rows[index][0]
        cursor.execute("DELETE FROM playlist_tracks WHERE id = ?", (track_db_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def remove_dupes_playlist(user_id: int, pl_name: str) -> int:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, pl_name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0
        pl_id = row[0]
        cursor.execute("SELECT id, url FROM playlist_tracks WHERE playlist_id = ? ORDER BY id", (pl_id,))
        rows = cursor.fetchall()
        seen = set()
        removed = 0
        for track_db_id, url in rows:
            if url in seen:
                cursor.execute("DELETE FROM playlist_tracks WHERE id = ?", (track_db_id,))
                removed += 1
            else:
                seen.add(url)
        conn.commit()
        conn.close()
        return removed

    @staticmethod
    def create_global_playlist(user_id: int, name: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM global_playlists WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return False
        cursor.execute("INSERT INTO global_playlists (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete_global_playlist(name: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute("DELETE FROM global_playlists WHERE id = ?", (pl_id,))
        cursor.execute("DELETE FROM global_playlist_tracks WHERE playlist_id = ?", (pl_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_global_playlists() -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, user_id FROM global_playlists")
        rows = cursor.fetchall()
        conn.close()
        return [{"name": r[0], "user_id": r[1]} for r in rows]

    @staticmethod
    def add_to_global_playlist(name: str, title: str, author: str, url: str, thumbnail: str, duration: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute(
            "INSERT INTO global_playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (pl_id, title, author, url, thumbnail, duration)
        )
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_global_playlist_tracks(pl_name: str) -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (pl_name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []
        pl_id = row[0]
        cursor.execute("SELECT title, author, url, thumbnail, duration FROM global_playlist_tracks WHERE playlist_id = ?", (pl_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"title": r[0], "author": r[1], "url": r[2], "thumbnail": r[3], "duration": r[4]} for r in rows]

    @staticmethod
    def remove_from_global_playlist(pl_name: str, index: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (pl_name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        cursor.execute("SELECT id FROM global_playlist_tracks WHERE playlist_id = ? ORDER BY id", (pl_id,))
        rows = cursor.fetchall()
        if index < 0 or index >= len(rows):
            conn.close()
            return False
        track_db_id = rows[index][0]
        cursor.execute("DELETE FROM global_playlist_tracks WHERE id = ?", (track_db_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def remove_dupes_global_playlist(pl_name: str) -> int:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (pl_name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0
        pl_id = row[0]
        cursor.execute("SELECT id, url FROM global_playlist_tracks WHERE playlist_id = ? ORDER BY id", (pl_id,))
        rows = cursor.fetchall()
        seen = set()
        removed = 0
        for track_db_id, url in rows:
            if url in seen:
                cursor.execute("DELETE FROM global_playlist_tracks WHERE id = ?", (track_db_id,))
                removed += 1
            else:
                seen.add(url)
        conn.commit()
        conn.close()
        return removed

    @staticmethod
    def get_dj_role(guild_id: int) -> Optional[int]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM dj_roles WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] else None

    @staticmethod
    def set_dj_role(guild_id: int, role_id: Optional[int]):
        conn = get_db()
        cursor = conn.cursor()
        if role_id is None:
            cursor.execute("DELETE FROM dj_roles WHERE guild_id = ?", (str(guild_id),))
        else:
            cursor.execute("INSERT OR REPLACE INTO dj_roles (guild_id, role_id) VALUES (?, ?)", (str(guild_id), str(role_id)))
        conn.commit()
        conn.close()

# ─────────────────────────────────────────────
#             SPOTIFY RESOLVER CLASS
# ─────────────────────────────────────────────

class SpotifyResolver:
    token = None
    token_expires = 0

    @classmethod
    async def get_token(cls):
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            return None
        if cls.token and time.time() < cls.token_expires:
            return cls.token

        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials"}
        auth = aiohttp.BasicAuth(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data, auth=auth) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        cls.token = res["access_token"]
                        cls.token_expires = time.time() + res["expires_in"] - 60
                        return cls.token
        except Exception:
            pass
        return None

    @classmethod
    async def resolve(cls, url: str) -> Tuple[List[dict], bool]:
        match = re.search(r"spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)", url)
        if not match:
            return [], False

        item_type, item_id = match.groups()
        token = await cls.get_token()
        if not token:
            return [], False

        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with aiohttp.ClientSession() as session:
                if item_type == "track":
                    track_url = f"https://api.spotify.com/v1/tracks/{item_id}"
                    async with session.get(track_url, headers=headers) as resp:
                        if resp.status == 200:
                            track = await resp.json()
                            query = f"{track['name']} {track['artists'][0]['name']}"
                            return [{
                                "title": track['name'],
                                "query": query,
                                "artists": [a['name'] for a in track['artists']],
                                "duration": int(track['duration_ms'] / 1000),
                                "thumbnail": track['album']['images'][0]['url'] if track['album']['images'] else ""
                            }], False
                elif item_type == "playlist":
                    playlist_url = f"https://api.spotify.com/v1/playlists/{item_id}/tracks?limit=100"
                    async with session.get(playlist_url, headers=headers) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            tracks = []
                            for item in res.get("items", []):
                                track = item.get("track")
                                if track:
                                    query = f"{track['name']} {track['artists'][0]['name']}"
                                    tracks.append({
                                        "title": track['name'],
                                        "query": query,
                                        "artists": [a['name'] for a in track['artists']],
                                        "duration": int(track['duration_ms'] / 1000),
                                        "thumbnail": track['album']['images'][0]['url'] if track['album']['images'] else ""
                                    })
                            return tracks, True
                elif item_type == "album":
                    album_url = f"https://api.spotify.com/v1/albums/{item_id}/tracks?limit=50"
                    async with session.get(album_url, headers=headers) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            tracks = []
                            for track in res.get("items", []):
                                query = f"{track['name']} {track['artists'][0]['name']}"
                                tracks.append({
                                    "title": track['name'],
                                    "query": query,
                                    "artists": [a['name'] for a in track['artists']],
                                    "duration": int(track['duration_ms'] / 1000),
                                    "thumbnail": ""
                                })
                            return tracks, True
        except Exception:
            pass
        return [], False

# ─────────────────────────────────────────────
#               AUDIO FILTER OPTIONS
# ─────────────────────────────────────────────

def get_ffmpeg_options(filter_name: Optional[str] = None, speed: float = 1.0, pitch: float = 1.0) -> dict:
    before_opts = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    opts = "-vn -ar 48000 -ac 2"

    audio_filters = []

    if filter_name in ["bassboost", "bassboost_medium"]:
        audio_filters.append("bass=g=15")
    elif filter_name == "bassboost_low":
        audio_filters.append("bass=g=8")
    elif filter_name == "bassboost_high":
        audio_filters.append("bass=g=22")
    elif filter_name == "bassboost_extreme":
        audio_filters.append("bass=g=30")
    elif filter_name == "nightcore":
        audio_filters.append("asetrate=48000*1.25,aresample=48000,atempo=1.05")
    elif filter_name == "8d":
        audio_filters.append("apulsator=hz=0.125")
    elif filter_name == "vaporwave":
        audio_filters.append("asetrate=48000*0.8,aresample=48000,atempo=1.0")
    elif filter_name == "karaoke":
        audio_filters.append("stereotools=mlev=0.01")
    elif filter_name == "doubletime":
        audio_filters.append("atempo=2.0")
    elif filter_name == "slowmo":
        audio_filters.append("atempo=0.5")
    elif filter_name == "daycore":
        audio_filters.append("asetrate=48000*0.85,aresample=48000")
    elif filter_name == "lofi":
        audio_filters.append("lowpass=f=3200,highpass=f=200")
    elif filter_name == "pop":
        audio_filters.append("equalizer=f=1000:width_type=o:width=2:g=4")
    elif filter_name == "earrape":
        audio_filters.append("volume=15.0,bass=g=35")
    elif filter_name == "chipmunk":
        audio_filters.append("asetrate=48000*1.5,aresample=48000")
    elif filter_name == "soft":
        audio_filters.append("lowpass=f=1000")
    elif filter_name == "treblebass":
        audio_filters.append("bass=g=5,treble=g=5")
    elif filter_name == "bass":
        audio_filters.append("bass=g=12")
    elif filter_name == "classical":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=-1,equalizer=f=250:width_type=o:width=2:g=1,equalizer=f=1000:width_type=o:width=2:g=2,equalizer=f=4000:width_type=o:width=2:g=1,equalizer=f=12000:width_type=o:width=2:g=-2")
    elif filter_name == "jazz":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=3,equalizer=f=250:width_type=o:width=2:g=2,equalizer=f=1000:width_type=o:width=2:g=-1,equalizer=f=4000:width_type=o:width=2:g=2,equalizer=f=12000:width_type=o:width=2:g=3")
    elif filter_name == "metal":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=4,equalizer=f=250:width_type=o:width=2:g=1,equalizer=f=1000:width_type=o:width=2:g=-3,equalizer=f=4000:width_type=o:width=2:g=4,equalizer=f=12000:width_type=o:width=2:g=2")
    elif filter_name == "rock":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=4,equalizer=f=250:width_type=o:width=2:g=2,equalizer=f=1000:width_type=o:width=2:g=-2,equalizer=f=4000:width_type=o:width=2:g=2,equalizer=f=12000:width_type=o:width=2:g=4")
    elif filter_name == "vocal":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=-2,equalizer=f=250:width_type=o:width=2:g=-1,equalizer=f=1000:width_type=o:width=2:g=3,equalizer=f=4000:width_type=o:width=2:g=3,equalizer=f=12000:width_type=o:width=2:g=-2")
    elif filter_name == "electronic":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=4,equalizer=f=250:width_type=o:width=2:g=2,equalizer=f=1000:width_type=o:width=2:g=0,equalizer=f=4000:width_type=o:width=2:g=1,equalizer=f=12000:width_type=o:width=2:g=4")

    effective_speed = speed
    if pitch != 1.0:
        has_preset_pitch = filter_name in ["nightcore", "vaporwave", "daycore"]
        if not has_preset_pitch:
            audio_filters.append(f"asetrate=48000*{pitch},aresample=48000")
            effective_speed = speed / pitch

    has_preset_speed = filter_name in ["nightcore", "vaporwave", "doubletime", "slowmo", "daycore"]
    if (effective_speed != 1.0 and not has_preset_speed) or (pitch != 1.0 and not has_preset_speed):
        rem = effective_speed
        while rem > 2.0:
            audio_filters.append("atempo=2.0")
            rem /= 2.0
        while rem < 0.5:
            audio_filters.append("atempo=0.5")
            rem /= 0.5
        if rem != 1.0:
            audio_filters.append(f"atempo={rem}")

    if audio_filters:
        opts += f' -af "{",".join(audio_filters)}"'

    return {
        "before_options": before_opts,
        "options": opts
    }

# ─────────────────────────────────────────────
#               AUDIO SOURCE
# ─────────────────────────────────────────────

class YTSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)
        self.data = data

    @classmethod
    async def search(cls, query: str, loop, max_results: int = 1):
        opts = YTDL_OPTIONS.copy()
        if not query.startswith("http"):
            query = f"ytsearch{max_results}:{query}"

        def run():
            ytdl = yt_dlp.YoutubeDL(opts)
            try:
                return ytdl.extract_info(query, download=False)
            except Exception:
                if opts.get("cookiefile"):
                    opts_no = opts.copy()
                    opts_no["cookiefile"] = None
                    try:
                        return yt_dlp.YoutubeDL(opts_no).extract_info(query, download=False)
                    except Exception:
                        pass
                return None

        data = await loop.run_in_executor(None, run)
        if not data:
            return [] if max_results > 1 else {}

        if "entries" in data and data["entries"]:
            entries = [e for e in data["entries"] if e]
            return entries if max_results > 1 else (entries[0] if entries else {})
        return [] if max_results > 1 else data

    @classmethod
    async def extract_tracks(cls, query: str, loop) -> Tuple[List[dict], bool]:
        opts = YTDL_OPTIONS.copy()
        is_search = not query.startswith("http")
        q = f"ytsearch1:{query}" if is_search else query

        def run():
            ytdl = yt_dlp.YoutubeDL(opts)
            try:
                return ytdl.extract_info(q, download=False)
            except Exception:
                if opts.get("cookiefile"):
                    opts_no = opts.copy()
                    opts_no["cookiefile"] = None
                    try:
                        return yt_dlp.YoutubeDL(opts_no).extract_info(q, download=False)
                    except Exception:
                        pass
                return None

        data = await loop.run_in_executor(None, run)
        if not data:
            return [], False

        if is_search:
            if "entries" in data and data["entries"] and data["entries"][0]:
                return [data["entries"][0]], False
            return [], False
        else:
            is_playlist = "entries" in data and not data.get("_type") == "video"
            if is_playlist:
                tracks = [e for e in data["entries"] if e]
                return tracks, True
            else:
                return [data], False

    @classmethod
    async def stream(cls, url: str, loop, volume=1.0, active_filter=None, seek_time=0, speed=1.0, pitch=1.0, track_title=None):
        opts = YTDL_OPTIONS.copy()
        opts["extract_flat"] = False

        def run():
            # 1. Primary: Android + MWeb with cookies
            opts_android = opts.copy()
            opts_android["cookiefile"] = COOKIE_ARG
            opts_android["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "mweb"]
                }
            }
            try:
                res = yt_dlp.YoutubeDL(opts_android).extract_info(url, download=False)
                if res and (res.get("url") or (res.get("entries") and res["entries"][0].get("url"))):
                    return res
            except Exception as e:
                logger.info("Primary android extract attempt: %s", e)

            # 2. TV & Android VR
            opts_tv = opts.copy()
            opts_tv["cookiefile"] = COOKIE_ARG
            opts_tv["extractor_args"] = {
                "youtube": {
                    "player_client": ["tv", "android_vr"]
                }
            }
            try:
                res = yt_dlp.YoutubeDL(opts_tv).extract_info(url, download=False)
                if res and (res.get("url") or (res.get("entries") and res["entries"][0].get("url"))):
                    return res
            except Exception as e:
                logger.info("TV client extract attempt: %s", e)

            # 3. VisionOS fallback
            opts_vision = opts.copy()
            opts_vision["cookiefile"] = COOKIE_ARG
            opts_vision["extractor_args"] = {
                "youtube": {
                    "player_client": ["visionos"]
                }
            }
            try:
                res = yt_dlp.YoutubeDL(opts_vision).extract_info(url, download=False)
                if res and (res.get("url") or (res.get("entries") and res["entries"][0].get("url"))):
                    return res
            except Exception as e:
                logger.info("VisionOS client extract attempt: %s", e)

            # 4. Mobile Android / iOS without cookies (fallback)
            opts_mobile = opts.copy()
            opts_mobile["cookiefile"] = None
            opts_mobile["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "ios"]
                }
            }
            try:
                res = yt_dlp.YoutubeDL(opts_mobile).extract_info(url, download=False)
                if res and (res.get("url") or (res.get("entries") and res["entries"][0].get("url"))):
                    return res
            except Exception:
                pass

            # 5. SoundCloud fallback (if YouTube failed completely)
            try:
                search_term = track_title
                if not search_term:
                    try:
                        import urllib.request, json
                        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                        o_req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(o_req, timeout=3) as o_resp:
                            o_data = json.loads(o_resp.read().decode())
                            search_term = o_data.get("title")
                    except Exception:
                        pass
                if not search_term:
                    vid_match = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})', url)
                    q = f"ytsearch1:{vid_match.group(1)}" if vid_match else url
                    flat_ytdl = yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True, "cookiefile": COOKIE_ARG})
                    info = flat_ytdl.extract_info(q, download=False)
                    entries = info.get("entries", [info]) if info else []
                    if entries and entries[0]:
                        search_term = entries[0].get("title")

                if search_term:
                    clean_term = re.sub(r'\(.*?\)|\[.*?\]', '', search_term).strip()
                    clean_term = re.sub(r'(?i)\b(official\s*(video|audio|music\s*video|lyric\s*video)?|full\s*video|4k|hd|remastered|lyrics?)\b', '', clean_term).strip()
                    if "|" in clean_term:
                        clean_term = clean_term.split("|")[0].strip()
                    logger.info("Resolving audio via SoundCloud CDN for: %s", clean_term)

                    sc_opts = {
                        "format": "bestaudio/best",
                        "quiet": True,
                        "ignoreerrors": True,
                        "extract_flat": False,
                        "nocheckcertificate": True
                    }
                    sc_ytdl = yt_dlp.YoutubeDL(sc_opts)
                    sc_data = sc_ytdl.extract_info(f"scsearch5:{clean_term}", download=False)
                    sc_entries = sc_data.get("entries", []) if sc_data else []
                    valid_sc = [
                        e for e in sc_entries 
                        if e and (e.get("duration") or 0) >= 60 and e.get("url")
                        and "slowed" not in (e.get("title") or "").lower()
                        and "reverb" not in (e.get("title") or "").lower()
                        and "mashup" not in (e.get("title") or "").lower()
                    ]
                    if valid_sc:
                        logger.info("SoundCloud audio fallback succeeded: %s", valid_sc[0].get('title'))
                        return valid_sc[0]
                    elif sc_entries and sc_entries[0].get("url"):
                        logger.info("SoundCloud audio fallback succeeded: %s", sc_entries[0].get('title'))
                        return sc_entries[0]
            except Exception as sc_err:
                logger.warning("SoundCloud audio fallback failed: %s", sc_err)

            # 6. Default extract_info
            opts_def = opts.copy()
            opts_def["cookiefile"] = COOKIE_ARG
            return yt_dlp.YoutubeDL(opts_def).extract_info(url, download=False)

        data = await loop.run_in_executor(None, run)
        if data and "entries" in data and len(data["entries"]) > 0:
            data = data["entries"][0]

        stream_url = data.get("url") if data else None
        if not stream_url:
            raise Exception("No direct audio stream URL extracted.")

        headers = data.get("http_headers", {})
        if "c=VISIONOS" in stream_url:
            ua = "Mozilla/5.0 (VisionOS; Mobile/21N307) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        elif "c=ANDROID" in stream_url:
            ua = "com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip"
        elif "c=IOS" in stream_url:
            ua = "com.google.ios.youtube/19.45.4 (iPhone14,3; U; CPU iOS 17_7 like Mac OS X; en_US)"
        elif "c=ANDROID_VR" in stream_url:
            ua = "com.google.android.apps.youtube.vr.oculus/1.65.10 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip"
        else:
            ua = headers.get("User-Agent", headers.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"))

        ffmpeg_opts = get_ffmpeg_options(active_filter, speed, pitch)
        ffmpeg_opts["before_options"] += f' -user_agent "{ua}"'

        if seek_time > 0:
            ffmpeg_opts["before_options"] += f" -ss {seek_time}"

        src = discord.FFmpegPCMAudio(stream_url, executable=get_ffmpeg_executable(), **ffmpeg_opts)
        return cls(src, data=data, volume=volume)

# ─────────────────────────────────────────────
#             GUILD PLAYER STATE
# ─────────────────────────────────────────────

class GuildPlayer:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue = deque()
        self.history = deque(maxlen=30)
        self.current: Optional[dict] = None
        self.voice: Optional[discord.VoiceClient] = None
        self.volume = 1.0
        self.loop = "off"  # "off", "track", "queue"
        self.autoplay = False
        self.stay_247 = True
        self.filter: Optional[str] = None
        self.seek_offset = 0
        self.speed = 1.0
        self.pitch = 1.0
        self.restarting_track = False
        self.start_time: Optional[float] = None
        self.paused_at: Optional[float] = None
        self.text_ch: Optional[discord.TextChannel] = None
        self.panel_msg: Optional[discord.Message] = None
        self.updater_task: Optional[asyncio.Task] = None
        self.skip_votes = set()
        self.is_connecting = False

    @property
    def position(self) -> int:
        if not self.start_time:
            return 0
        elapsed = time.time() - self.start_time
        if self.paused_at:
            elapsed = self.paused_at - self.start_time
        return int(elapsed * self.speed + self.seek_offset)

    def is_playing(self) -> bool:
        return bool(self.voice and self.voice.is_playing())

    def is_paused(self) -> bool:
        return bool(self.voice and self.voice.is_paused())

    def fmt(self, s: int) -> str:
        return _fmt(int(s or 0))

    def reset_start_time(self):
        self.start_time = time.time()
        self.paused_at = None

    async def archive_panel(self):
        if not self.panel_msg or not self.current:
            self.panel_msg = None
            return
        try:
            await self.panel_msg.edit(embed=history_embed(self.current), view=None)
        except Exception:
            pass
        self.panel_msg = None

    async def update_panel(self):
        if self.panel_msg:
            try:
                await self.panel_msg.edit(embed=panel_embed(self))
            except Exception:
                pass

    async def _progress_loop(self):
        while self.is_playing() or self.is_paused():
            await self.update_panel()
            await asyncio.sleep(4)
        await self.update_panel()

    def ensure_updater(self):
        if self.updater_task and not self.updater_task.done():
            self.updater_task.cancel()
        if self.is_playing() or self.is_paused():
            self.updater_task = asyncio.create_task(self._progress_loop())

def history_embed(track: dict) -> discord.Embed:
    title = track.get("title", "Unknown Track")
    url = track.get("url", "")
    dur = _fmt(int(track.get("duration") or 0))
    uploader = track.get("uploader", "Unknown Artist")
    req_id = track.get("requester_id")
    thumb = track.get("thumbnail", "")

    req_str = f"<@{req_id}>" if req_id else "`AutoPlay`"
    title_display = f"### [{title[:100]}]({url})" if url else f"### {title[:100]}"

    e = discord.Embed(
        color=EMBED_COLOR,
        description=(
            f"{title_display}\n\n"
            f">>> 👤 **Artist:** `{uploader[:35]}`\n"
            f"⏱️ **Duration:** `{dur}`  •  🎧 **Requester:** {req_str}"
        ),
        timestamp=datetime.now(timezone.utc)
    )
    e.set_author(name="Track Finished • VEYRA MUSIC", icon_url="https://images.discordapp.net/avatars/1337446506385473637/10b98eb6cbfb0b9be001cb74ef1b933a.png?size=1024")
    if thumb:
        e.set_thumbnail(url=thumb)
    e.set_footer(text=BRAND_FOOTER)
    return e

def panel_embed(p: GuildPlayer) -> discord.Embed:
    e = discord.Embed(color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.set_author(name="VEYRA MUSIC PLAYER", icon_url="https://images.discordapp.net/avatars/1337446506385473637/10b98eb6cbfb0b9be001cb74ef1b933a.png?size=1024")

    loop_s = "Track" if p.loop == "track" else ("Queue" if p.loop == "queue" else "Off")
    speed_s = f"{p.speed}x" if p.speed != 1.0 else "Normal"
    vol_pct = int(p.volume * 100)

    if p.current:
        title = p.current.get("title", "Unknown Track")
        url = p.current.get("video_url") or p.current.get("url", "")
        dur = p.fmt(p.current.get("duration", 0))
        author = p.current.get("uploader", "Unknown Artist")
        req_id = p.current.get("requester_id")

        pos = p.position
        total = int(p.current.get("duration") or 0)
        bar = make_progress_bar(pos, total, width=12)

        req_str = f"<@{req_id}>" if req_id else "`AutoPlay`"

        e.title = title[:256]
        if url:
            e.url = url

        e.description = (
            f"`{p.fmt(pos)}` {bar} `{dur}`\n\n"
            f"👤 **Artist:** `{author[:35]}`\n"
            f"🎧 **Requester:** {req_str}\n"
            f"🔊 {vol_pct}% | Loop: {loop_s} | Speed: {speed_s} | Queue: {len(p.queue)} tracks"
        )
        if thumb := p.current.get("thumbnail"):
            e.set_thumbnail(url=thumb)
    else:
        e.description = (
            "*Nothing is currently playing.*\n"
            "Use `/play` or `,play` to start the vibe!\n\n"
            f"🔊 {vol_pct}% | Loop: {loop_s} | Speed: {speed_s} | Queue: {len(p.queue)} tracks"
        )
    e.set_footer(text="Veyra All in One", icon_url="https://images.discordapp.net/avatars/1337446506385473637/10b98eb6cbfb0b9be001cb74ef1b933a.png?size=1024")
    return e

# ─────────────────────────────────────────────
#             INTERACTIVE UI CONTROLS
# ─────────────────────────────────────────────

class SeekModal(discord.ui.Modal, title="Seek to Position"):
    time_input = discord.ui.TextInput(
        label="Enter timestamp or seconds",
        placeholder="e.g. 1:30 or 90 (or 50% for percentage)",
        required=True,
        max_length=15
    )

    def __init__(self, player: GuildPlayer):
        super().__init__()
        self.player = player

    async def on_submit(self, interaction: discord.Interaction):
        p = self.player
        if not p.voice or not p.current:
            return await interaction.response.send_message(embed=err("Nothing is currently playing."), ephemeral=True)

        val = self.time_input.value.strip()
        duration = int(p.current.get("duration") or 0)
        sec = parse_time(val, duration)

        if sec is None or sec < 0:
            return await interaction.response.send_message(embed=err("Invalid format! Use seconds (e.g. 90) or mm:ss (e.g. 1:30)."), ephemeral=True)

        if duration > 0 and sec > duration:
            return await interaction.response.send_message(embed=err("Seek position cannot exceed song duration!"), ephemeral=True)

        p.seek_offset = max(0, sec)
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()

        await interaction.response.send_message(embed=ok("Seeking Track", f"Jumped directly to **{_fmt(sec)}**."), ephemeral=True)

class MusicPanel(discord.ui.View):
    def __init__(self, player: GuildPlayer):
        super().__init__(timeout=None)
        self.player = player

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        logger.error(f"MusicPanel UI error on item {item}: {error}", exc_info=error)
        try:
            e = err(f"Action failed: {error}")
            if interaction.response.is_done():
                await interaction.followup.send(embed=e, ephemeral=True)
            else:
                await interaction.response.send_message(embed=e, ephemeral=True)
        except Exception:
            pass

    async def _update(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=panel_embed(self.player), view=self)
                return
            await interaction.edit_original_response(embed=panel_embed(self.player), view=self)
        except Exception:
            pass

    async def _toast(self, interaction: discord.Interaction, embed: discord.Embed):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            pass

    # Row 0: Volume & Core Track Navigation
    @discord.ui.button(label="Vol -", emoji="🔉", style=discord.ButtonStyle.secondary, row=0)
    async def vol_down(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        p.volume = max(0.0, round(p.volume - 0.1, 1))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        MusicDB.set_volume(p.guild_id, int(p.volume * 100))
        await self._update(i)
        await self._toast(i, ok("Volume Down", f"Volume set to **{int(p.volume*100)}%**"))

    @discord.ui.button(label="Back", emoji="⏮", style=discord.ButtonStyle.primary, row=0)
    async def back(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        hist = list(p.history)
        if len(hist) < 2:
            return await self._toast(i, err("No previous track in history."))
        prev = hist[1]
        if p.current:
            p.queue.appendleft(p.current)
        p.queue.appendleft(prev)
        if p.voice:
            p.voice.stop()
        await self._update(i)

    @discord.ui.button(label="Pause", emoji="⏸", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if p.is_playing():
            p.voice.pause()
            p.paused_at = time.time()
            b.label = "Resume"
            b.emoji = discord.PartialEmoji.from_str("▶️")
        elif p.is_paused():
            p.voice.resume()
            if p.paused_at and p.start_time:
                p.start_time += time.time() - p.paused_at
            p.paused_at = None
            b.label = "Pause"
            b.emoji = discord.PartialEmoji.from_str("⏸")
            p.ensure_updater()
        await self._update(i)

    @discord.ui.button(label="Skip", emoji="⏭", style=discord.ButtonStyle.primary, row=0)
    async def skip(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if p.voice and (p.is_playing() or p.is_paused()):
            p.voice.stop()
        await self._update(i)
        await self._toast(i, ok("Skipped ⏭"))

    @discord.ui.button(label="Vol +", emoji="🔊", style=discord.ButtonStyle.secondary, row=0)
    async def vol_up(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        p.volume = min(2.0, round(p.volume + 0.1, 1))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        MusicDB.set_volume(p.guild_id, int(p.volume * 100))
        await self._update(i)
        await self._toast(i, ok("Volume Up", f"Volume set to **{int(p.volume*100)}%**"))

    # Row 1: Fast Seek & Jump Controls
    @discord.ui.button(label="-15s", emoji="⏪", style=discord.ButtonStyle.primary, row=1)
    async def rewind_15(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        pos = max(0, p.position - 15)
        p.seek_offset = pos
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        if p.voice:
            p.voice.stop()
        await self._update(i)
        await self._toast(i, ok("Rewound 15s", f"Playback moved to **{_fmt(pos)}**."))

    @discord.ui.button(label="Seek", emoji="⏱️", style=discord.ButtonStyle.secondary, row=1)
    async def seek_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        await i.response.send_modal(SeekModal(p))

    @discord.ui.button(label="+15s", emoji="⏩", style=discord.ButtonStyle.primary, row=1)
    async def forward_15(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        duration = int(p.current.get("duration") or 0)
        pos = p.position + 15
        if duration > 0 and pos >= duration:
            return await self._toast(i, err("Cannot seek past the end of the song!"))
        p.seek_offset = pos
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        if p.voice:
            p.voice.stop()
        await self._update(i)
        await self._toast(i, ok("Forwarded 15s", f"Playback moved to **{_fmt(pos)}**."))

    # Row 2: Queue Modes & Stop
    @discord.ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.primary, row=2)
    async def shuffle(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if len(p.queue) < 2:
            return await self._toast(i, err("Not enough tracks in queue to shuffle."))
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await self._update(i)
        await self._toast(i, ok("Shuffled Queue!", f"Shuffled {len(q)} tracks."))

    @discord.ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.primary, row=2)
    async def loop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        order = ["off", "track", "queue"]
        next_idx = (order.index(p.loop) + 1) % len(order)
        p.loop = order[next_idx]
        b.label = f"Loop: {p.loop.title()}"
        await self._update(i)
        await self._toast(i, ok("Loop Mode", f"Loop mode set to **{p.loop.title()}**."))

    @discord.ui.button(label="Stop", emoji="⏹", style=discord.ButtonStyle.primary, row=2)
    async def stop(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        finished = p.current
        p.queue.clear()
        p.current = None
        p.loop = "off"
        if p.voice:
            p.voice.stop()
        
        is_247 = p.stay_247 or bool(MusicDB.get_247(p.guild_id)[0])
        if not is_247:
            if p.voice:
                try: await p.voice.disconnect()
                except Exception: pass
                p.voice = None
            msg_desc = "Queue cleared & voice disconnected."
        else:
            p.stay_247 = True
            msg_desc = "Playback stopped & queue cleared. Bot remains in voice channel (24/7 active)."

        if p.panel_msg and finished:
            try:
                await p.panel_msg.edit(embed=history_embed(finished), view=None)
            except Exception:
                pass
            p.panel_msg = None
        await self._toast(i, ok("Stopped Playing", msg_desc))

    # Row 3: AutoPlay & Queue List
    @discord.ui.button(label="AutoPlay", emoji="▶️", style=discord.ButtonStyle.primary, row=3)
    async def autoplay_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        p.autoplay = not p.autoplay
        await self._update(i)
        await self._toast(i, ok(f"AutoPlay {'Enabled ✅' if p.autoplay else 'Disabled ❌'}"))

    @discord.ui.button(label="Queue List", emoji="🎵", style=discord.ButtonStyle.primary, row=3)
    async def queue_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if not p.queue and not p.current:
            return await self._toast(i, err("Queue is empty!"))
        lines = []
        if p.current:
            lines.append(f"▶ **Now playing:** {p.current['title']} `{p.fmt(p.current.get('duration', 0))}`")
        for idx, t in enumerate(list(p.queue)[:10], 1):
            lines.append(f"`{idx}.` {t['title']} `{p.fmt(t.get('duration', 0))}`")
        if len(p.queue) > 10:
            lines.append(f"*...and {len(p.queue)-10} more tracks*")
        await self._toast(i, discord.Embed(title="🎵 Queue List", description="\n".join(lines), color=0x2B2D31))

    # Row 4: Like & Close Panel
    @discord.ui.button(label="Like", emoji="⭐", style=discord.ButtonStyle.secondary, row=4)
    async def like_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        track = p.current
        MusicDB.like_track(i.user.id, track.get("url") or track.get("webpage_url", ""), track.get("title", ""), track.get("uploader", "Unknown"), track.get("thumbnail", ""), track.get("duration", 0))
        await self._toast(i, ok("Song Liked", f"Added **{track.get('title', 'Track')}** to your Liked tracks."))

    @discord.ui.button(label="Close Panel", emoji="❌", style=discord.ButtonStyle.secondary, row=4)
    async def close_panel_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self.player
        if p.panel_msg and p.current:
            try:
                await p.panel_msg.edit(embed=history_embed(p.current), view=None)
            except Exception:
                pass
            p.panel_msg = None
        elif p.panel_msg:
            try:
                await p.panel_msg.delete()
            except Exception:
                pass
            p.panel_msg = None
        await self._toast(i, ok("Panel Closed", "Use `/panel` or `,player` to reopen the player."))

class QueuePaginationView(discord.ui.View):
    def __init__(self, pages: list, user_id: int):
        super().__init__(timeout=60)
        self.pages = pages
        self.user_id = user_id
        self.current_page = 0
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.pages) - 1

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await i.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await i.response.edit_message(embed=self.pages[self.current_page], view=self)

class VolumeControlsView(discord.ui.View):
    def __init__(self, player: GuildPlayer, user_id: int):
        super().__init__(timeout=60)
        self.player = player
        self.user_id = user_id

    async def _update_volume_embed(self, i: discord.Interaction):
        p = self.player
        level = int(p.volume * 100)
        bar_len = min(10, level // 20)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        e = ok("Volume Config", f"`{bar}` **{level}%**")
        await i.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="-10%", emoji="🔉", style=discord.ButtonStyle.secondary)
    async def vol_down(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self.player
        p.volume = max(0.0, round(p.volume - 0.1, 2))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        MusicDB.set_volume(p.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

    @discord.ui.button(label="Mute", emoji="🔇", style=discord.ButtonStyle.danger)
    async def mute_unmute(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self.player
        if p.volume > 0.0:
            self.prev_vol = p.volume
            p.volume = 0.0
            b.label = "Unmute"
            b.style = discord.ButtonStyle.success
            b.emoji = "🔊"
        else:
            p.volume = getattr(self, "prev_vol", 1.0)
            b.label = "Mute"
            b.style = discord.ButtonStyle.danger
            b.emoji = "🔇"
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        MusicDB.set_volume(p.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

    @discord.ui.button(label="+10%", emoji="🔊", style=discord.ButtonStyle.secondary)
    async def vol_up(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self.player
        p.volume = min(2.0, round(p.volume + 0.1, 2))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        MusicDB.set_volume(p.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

# ─────────────────────────────────────────────
#             CORE PLAYBACK ENGINE
# ─────────────────────────────────────────────

# Global registry of active players per guild
PLAYERS: Dict[int, GuildPlayer] = {}

def get_player(bot: commands.Bot, guild_id: int) -> GuildPlayer:
    if guild_id not in PLAYERS:
        MusicDB.init_guild(guild_id)
        p = GuildPlayer(guild_id)
        vol = MusicDB.get_volume(guild_id)
        p.volume = vol / 100
        stay_247, _, _ = MusicDB.get_247(guild_id)
        p.stay_247 = bool(stay_247)
        guild = bot.get_guild(guild_id)
        if guild and guild.voice_client and guild.voice_client.is_connected():
            p.voice = guild.voice_client
        PLAYERS[guild_id] = p
    else:
        p = PLAYERS[guild_id]
        if not p.voice or not p.voice.is_connected():
            guild = bot.get_guild(guild_id)
            if guild and guild.voice_client and guild.voice_client.is_connected():
                p.voice = guild.voice_client
    return PLAYERS[guild_id]

async def ensure_vc(ctx: commands.Context, bot: commands.Bot) -> Optional[discord.VoiceClient]:
    p = get_player(bot, ctx.guild.id)
    p.text_ch = ctx.channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send(embed=err("You must join a voice channel first!"))
        return None
    ch = ctx.author.voice.channel

    # Check guild voice client or player voice client
    guild_vc = ctx.guild.voice_client or p.voice

    if guild_vc and guild_vc.is_connected():
        p.voice = guild_vc
        if guild_vc.channel.id != ch.id:
            p.is_connecting = True
            try:
                await guild_vc.move_to(ch)
            except Exception:
                pass
            finally:
                p.is_connecting = False
        return p.voice

    try:
        p.is_connecting = True
        # If lingering unconnected voice client exists, clear it
        if ctx.guild.voice_client and not ctx.guild.voice_client.is_connected():
            try:
                await ctx.guild.voice_client.disconnect(force=True)
            except Exception:
                pass

        p.voice = await ch.connect(timeout=15, reconnect=True, self_deaf=True)
        conn = getattr(p.voice, "_connection", None)
        if conn and getattr(conn, "dave_protocol_version", 0) > 0:
            for _ in range(15):
                if getattr(conn, "can_encrypt", False):
                    break
                await asyncio.sleep(0.1)

        if isinstance(ch, discord.StageChannel):
            try:
                await ctx.guild.me.edit(suppress=False)
            except Exception:
                try:
                    await ctx.guild.me.request_to_speak()
                except Exception:
                    pass
        p.stay_247 = True
        MusicDB.set_247(ctx.guild.id, 1, ch.id, ctx.channel.id)
        return p.voice
    except discord.ClientException as ce:
        # If already connected, hook to the live voice client seamlessly
        if "Already connected" in str(ce) and ctx.guild.voice_client:
            p.voice = ctx.guild.voice_client
            if p.voice.channel.id != ch.id:
                try:
                    await p.voice.move_to(ch)
                except Exception:
                    pass
            return p.voice
        await ctx.send(embed=err(f"Voice Notice: {ce}"))
        return None
    except Exception as ex:
        # Fallback check if bot actually is connected
        if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
            p.voice = ctx.guild.voice_client
            return p.voice
        await ctx.send(embed=err(f"Could not connect to voice channel: {ex}"))
        return None
    finally:
        p.is_connecting = False

async def get_autoplay_track(current_track: dict, loop) -> Optional[dict]:
    title = current_track.get("title", "")
    author = current_track.get("uploader", "")
    search_query = f"similar to {title} {author}"
    try:
        tracks = await YTSource.search(search_query, loop, max_results=5)
        current_url = current_track.get("url")
        candidates = [t for t in tracks if t.get("webpage_url") != current_url]
        if candidates:
            c = random.choice(candidates)
            return {
                "title": c.get("title", "Unknown"),
                "url": c.get("webpage_url", ""),
                "duration": int(c.get("duration") or 0),
                "thumbnail": c.get("thumbnail", ""),
                "uploader": c.get("uploader", "Unknown"),
                "requester_id": None,
                "queued_msg": None,
            }
    except Exception:
        pass
    return None

async def play_next(bot: commands.Bot, guild: discord.Guild, interaction: Optional[discord.Interaction] = None):
    p = get_player(bot, guild.id)
    p.skip_votes.clear()
    if not p.voice or not p.voice.is_connected():
        return

    # Check track restarting flag
    if getattr(p, "restarting_track", False):
        p.restarting_track = False
        track = p.current
    else:
        if p.loop == "track" and p.current:
            track = p.current
            p.seek_offset = 0
            p.speed = 1.0
            p.reset_start_time()
        elif p.queue:
            track = p.queue.popleft()
            if p.loop == "queue" and p.current:
                p.queue.append(p.current)
            await p.archive_panel()
            p.current = track
            p.seek_offset = 0
            p.speed = 1.0
            p.reset_start_time()
        else:
            if p.autoplay and p.current:
                await p.archive_panel()
                auto_track = await get_autoplay_track(p.current, bot.loop)
                if auto_track:
                    p.current = auto_track
                    track = auto_track
                    p.seek_offset = 0
                    p.speed = 1.0
                    p.reset_start_time()
                else:
                    p.current = None
                    if p.panel_msg:
                        try:
                            await p.panel_msg.edit(embed=panel_embed(p), view=None)
                        except Exception:
                            pass
                    return
            else:
                p.current = None
                if p.panel_msg:
                    try:
                        await p.panel_msg.edit(embed=panel_embed(p), view=None)
                    except Exception:
                        pass
                return

    # JIT resolver for queries
    if track and not track.get("url") and track.get("query"):
        try:
            yt_track = await YTSource.search(track["query"], bot.loop)
            if yt_track:
                track["url"] = yt_track.get("webpage_url") or yt_track.get("url", "")
                if not track.get("thumbnail"):
                    track["thumbnail"] = yt_track.get("thumbnail", "")
                if not track.get("duration"):
                    track["duration"] = int(yt_track.get("duration") or 0)
            else:
                if p.text_ch:
                    await p.text_ch.send(embed=err(f"Could not find YouTube stream for: **{track['title']}**"), delete_after=10)
                await play_next(bot, guild)
                return
        except Exception as e:
            if p.text_ch:
                await p.text_ch.send(embed=err(f"Error resolving track: {e}"), delete_after=10)
            await play_next(bot, guild)
            return

    try:
        src = await YTSource.stream(
            track["url"],
            bot.loop,
            volume=p.volume,
            active_filter=p.filter,
            seek_time=p.seek_offset,
            speed=p.speed,
            pitch=p.pitch,
            track_title=track.get("title")
        )
        if src.data:
            track["url"] = src.data.get("webpage_url") or src.data.get("url", track["url"])
            track["title"] = src.data.get("title", track["title"])
            track["duration"] = int(src.data.get("duration") or 0)
            track["thumbnail"] = src.data.get("thumbnail", track["thumbnail"])
            track["uploader"] = src.data.get("uploader", track["uploader"])

        p.history.appendleft(track)

        # DAVE MLS Protocol Sync before playing
        conn = getattr(p.voice, "_connection", None)
        if conn and getattr(conn, "dave_protocol_version", 0) > 0 and not getattr(conn, "can_encrypt", False):
            logger.info("[DAVE] can_encrypt is False before play — re-syncing session")
            try:
                await conn.reinit_dave_session()
                for _ in range(15):
                    if getattr(conn, "can_encrypt", False):
                        break
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"[DAVE] reinit error: {e}")
            if not getattr(conn, "can_encrypt", False) and p.voice.channel:
                ch = p.voice.channel
                try:
                    await p.voice.disconnect(force=True)
                    await asyncio.sleep(0.3)
                    p.voice = await ch.connect(timeout=15, reconnect=True, self_deaf=True)
                except Exception as e:
                    logger.warning(f"[DAVE] reconnect fallback error: {e}")

        def after_cb(error):
            if error:
                logger.error("Audio playback error: %s", error)
            bot.loop.call_soon_threadsafe(lambda: bot.loop.create_task(play_next(bot, guild)))

        p.voice.play(src, after=after_cb)
        MusicDB.increment_stat("songs_played")
        p.ensure_updater()

        # Update or spawn live control panel
        if p.panel_msg:
            try:
                await p.panel_msg.edit(embed=panel_embed(p), view=MusicPanel(p))
            except Exception:
                p.panel_msg = None
        if not p.panel_msg and p.text_ch:
            try:
                msg = await p.text_ch.send(embed=panel_embed(p), view=MusicPanel(p))
                p.panel_msg = msg
            except Exception:
                pass

    except Exception as ex:
        logger.error("Playback streaming error: %s", ex)
        if p.text_ch:
            await p.text_ch.send(embed=err(f"Could not stream track: {ex}"), delete_after=10)
        await play_next(bot, guild)

# ─────────────────────────────────────────────
#             RADIO STATIONS DATA
# ─────────────────────────────────────────────

RADIO_STATIONS = {
    "lofi-chill": {
        "title": "Lofi Girl - Chill Beats 24/7",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "uploader": "Lofi Girl"
    },
    "lofi-synthwave": {
        "title": "Lofi Girl - Synthwave Radio 24/7",
        "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY",
        "uploader": "Lofi Girl"
    },
    "coffee-shop": {
        "title": "Coffee Shop Lofi Radio",
        "url": "https://www.youtube.com/watch?v=a7GITgqwDVg",
        "uploader": "Lofi Chill"
    },
    "jazz-lofi": {
        "title": "Smooth Jazz Lofi Radio",
        "url": "https://www.youtube.com/watch?v=k3141fBwE3E",
        "uploader": "Lofi Records"
    }
}

# ─────────────────────────────────────────────
#          REGISTER MUSIC COMMANDS
# ─────────────────────────────────────────────

def setup_music_system(bot: commands.Bot):
    """Registers all music commands, audio filters, queue managers, and panels into Veyra."""
    MusicDB.init_schema()

    orig_command = bot.command
    def safe_command(*args, **kwargs):
        name = kwargs.get("name") or (args[0] if args and isinstance(args[0], str) else None)
        aliases = kwargs.get("aliases", [])
        if name:
            try: bot.remove_command(name)
            except Exception: pass
        for a in aliases:
            try: bot.remove_command(a)
            except Exception: pass
        return orig_command(*args, **kwargs)
    bot.command = safe_command

    orig_tree_command = bot.tree.command
    def safe_tree_command(*args, **kwargs):
        def decorator(func):
            name = kwargs.get("name") or (args[0] if args and isinstance(args[0], str) else func.__name__)
            try:
                bot.tree.remove_command(name)
            except Exception:
                pass
            try:
                return orig_tree_command(*args, **kwargs)(func)
            except Exception as ex:
                logger.warning(f"Could not register slash command /{name}: {ex}")
                return func
        return decorator
    bot.tree.command = safe_tree_command

    async def _check_dj(ctx: commands.Context) -> bool:
        if ctx.author.guild_permissions.administrator:
            return True
        dj_id = MusicDB.get_dj_role(ctx.guild.id)
        if not dj_id:
            return True
        return any(r.id == dj_id for r in ctx.author.roles)

    # 1. Play Command
    @bot.command(name="play", aliases=["p"], description="Play any song or playlist from YouTube or Spotify")
    async def cmd_play(ctx: commands.Context, *, query: Optional[str] = None):
        p = get_player(bot, ctx.guild.id)
        if not query:
            if p.voice and p.is_paused():
                p.voice.resume()
                if p.paused_at and p.start_time:
                    p.start_time += time.time() - p.paused_at
                p.paused_at = None
                p.ensure_updater()
                return await send_response(ctx, embed=ok("Resumed", "Playback resumed."))
            return await send_response(ctx, embed=err("Please provide a song title or URL.\nUsage: `,play <song title or URL>`"))

        is_slash = ctx.interaction is not None
        searching_msg = None
        if is_slash:
            try:
                await ctx.interaction.response.defer()
                searching_msg = await ctx.interaction.followup.send(embed=make_embed("🔍 Searching...", f"Searching for `{query}`..."))
            except Exception:
                searching_msg = await ctx.send(embed=make_embed("🔍 Searching...", f"Searching for `{query}`..."))
        else:
            searching_msg = await ctx.reply(embed=make_embed("🔍 Searching...", f"Searching for `{query}`..."))

        p.text_ch = ctx.channel
        if not p.voice or not p.voice.is_connected():
            vc = await ensure_vc(ctx, bot)
            if not vc:
                try:
                    await searching_msg.delete()
                except Exception:
                    pass
                return

        # Check Spotify links
        if "spotify.com" in query:
            spotify_tracks, is_playlist = await SpotifyResolver.resolve(query)
            if not spotify_tracks:
                return await searching_msg.edit(embed=err("Could not resolve Spotify link. Ensure it is public."))

            first_play = not p.is_playing() and not p.is_paused()
            for idx, s_track in enumerate(spotify_tracks):
                track = {
                    "title": s_track["title"],
                    "url": None,
                    "query": s_track["query"],
                    "duration": s_track["duration"],
                    "thumbnail": s_track["thumbnail"],
                    "uploader": ", ".join(s_track["artists"]),
                    "requester_id": ctx.author.id,
                    "queued_msg": searching_msg if (idx == 0 and first_play) else None
                }
                p.queue.append(track)

            e = ok("Spotify Queued", f"Successfully queued **{len(spotify_tracks)}** track(s) from Spotify.")
            await searching_msg.edit(embed=e)

            if first_play:
                await play_next(bot, ctx.guild, ctx.interaction)
            else:
                await p.update_panel()
                async def del_later():
                    await asyncio.sleep(5)
                    try: await searching_msg.delete()
                    except Exception: pass
                bot.loop.create_task(del_later())
            return

        # YouTube Extraction
        try:
            tracks, is_playlist = await YTSource.extract_tracks(query, bot.loop)
            if not tracks:
                return await searching_msg.edit(embed=err("No search results found."))

            if is_playlist:
                first_play = not p.is_playing() and not p.is_paused()
                for idx, t_data in enumerate(tracks):
                    track = {
                        "title": t_data.get("title", "Unknown"),
                        "url": t_data.get("webpage_url") or t_data.get("url", ""),
                        "duration": int(t_data.get("duration") or 0),
                        "thumbnail": t_data.get("thumbnail", ""),
                        "uploader": t_data.get("uploader", "Unknown"),
                        "requester_id": ctx.author.id,
                        "queued_msg": searching_msg if (idx == 0 and first_play) else None
                    }
                    p.queue.append(track)

                if first_play:
                    await play_next(bot, ctx.guild, ctx.interaction)
                else:
                    e = ok("Playlist Added", f"Added **{len(tracks)}** tracks from playlist to queue.")
                    await searching_msg.edit(embed=e)
                    await p.update_panel()
                    async def del_later():
                        await asyncio.sleep(5)
                        try: await searching_msg.delete()
                        except Exception: pass
                    bot.loop.create_task(del_later())
            else:
                track_data = tracks[0]
                track = {
                    "title": track_data.get("title", "Unknown"),
                    "url": track_data.get("webpage_url") or track_data.get("url", ""),
                    "duration": int(track_data.get("duration") or 0),
                    "thumbnail": track_data.get("thumbnail", ""),
                    "uploader": track_data.get("uploader", "Unknown"),
                    "requester_id": ctx.author.id,
                    "queued_msg": searching_msg
                }
                p.queue.append(track)
                if not p.is_playing() and not p.is_paused():
                    await play_next(bot, ctx.guild, ctx.interaction)
                else:
                    dur = p.fmt(track.get("duration", 0))
                    e = ok("Added to Queue", f"**{track['title']}**\nPosition: `#{len(p.queue)}` | Duration: `{dur}`")
                    if track["thumbnail"]:
                        e.set_thumbnail(url=track["thumbnail"])
                    await searching_msg.edit(embed=e)
                    await p.update_panel()
                    async def del_later():
                        await asyncio.sleep(5)
                        try: await searching_msg.delete()
                        except Exception: pass
                    bot.loop.create_task(del_later())
        except Exception as ex:
            await searching_msg.edit(embed=err(f"Could not load track: {ex}"))

    # 2. Player / Music Panel Command
    @bot.command(name="player", aliases=["m", "musicpanel"], description="Open the live interactive music control panel")
    async def cmd_panel(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if p.panel_msg:
            try: await p.panel_msg.delete()
            except Exception: pass
            p.panel_msg = None
        view = MusicPanel(p)
        msg = await ctx.send(embed=panel_embed(p), view=view)
        p.panel_msg = msg

    # 3. Join Command
    @bot.command(name="join", description="Connect bot to voice channel")
    async def cmd_join(ctx: commands.Context):
        vc = await ensure_vc(ctx, bot)
        if vc:
            await send_response(ctx, embed=ok("Connected", f"Connected to **{vc.channel.name}** and staying 24/7."))

    # 4. Leave / Stop Command
    @bot.command(name="leave", aliases=["dc", "disconnect"], description="Disconnect from voice channel")
    async def cmd_leave(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.voice.is_connected():
            return await send_response(ctx, embed=err("I am not connected to a voice channel."))
        ch_name = p.voice.channel.name
        p.queue.clear()
        p.current = None
        p.loop = "off"
        p.stay_247 = False
        MusicDB.set_247(ctx.guild.id, 0, None, None)
        if p.voice.is_playing() or p.voice.is_paused():
            p.voice.stop()
        await p.voice.disconnect()
        p.voice = None
        await send_response(ctx, embed=ok("Disconnected", f"Disconnected from **{ch_name}**."))

    @bot.command(name="stop", description="Stop music, clear queue, and disconnect")
    async def cmd_stop(ctx: commands.Context):
        await cmd_leave(ctx)

    # 5. Skip Command
    @bot.command(name="skip", aliases=["s", "next"], description="Skip the current track")
    async def cmd_skip(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.is_playing() and not p.is_paused():
            return await send_response(ctx, embed=err("Nothing is currently playing."))
        p.voice.stop()
        await send_response(ctx, embed=ok("Track Skipped ⏭"))

    # 6. Vote Skip Command
    @bot.command(name="voteskip", description="Vote to skip currently playing track")
    async def cmd_voteskip(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.current:
            return await send_response(ctx, embed=err("Nothing is currently playing."))
        if await _check_dj(ctx):
            p.voice.stop()
            return await send_response(ctx, embed=ok("Skipped Song", "Skipped immediately by DJ/Admin."))
        if ctx.author.id in p.skip_votes:
            return await send_response(ctx, embed=err("You have already voted to skip."))
        listeners = [m for m in p.voice.channel.members if not m.bot]
        needed = max(1, len(listeners) // 2)
        p.skip_votes.add(ctx.author.id)
        if len(p.skip_votes) >= needed:
            p.voice.stop()
            await send_response(ctx, embed=ok("Song Skipped", f"Vote passed: **{len(p.skip_votes)}/{needed}** votes."))
        else:
            await send_response(ctx, embed=ok("Vote Registered", f"Progress: **{len(p.skip_votes)}/{needed}** votes."))

    # 7. Queue Command
    @bot.command(name="queue", aliases=["q"], description="Show current playback queue")
    async def cmd_queue(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.current and not p.queue:
            return await send_response(ctx, embed=err("The music queue is currently empty."))

        queue_list = list(p.queue)
        per_page = 10
        total_pages = max(1, (len(queue_list) + per_page - 1) // per_page)
        pages = []
        for p_idx in range(total_pages):
            lines = []
            if p_idx == 0 and p.current:
                lines.append(f"**▶ Now Playing:** {p.current['title']} `{p.fmt(p.current.get('duration',0))}`\n")
            start = p_idx * per_page
            for idx, track in enumerate(queue_list[start:start+per_page], start + 1):
                lines.append(f"`{idx}.` {track['title']} `{p.fmt(track.get('duration',0))}`")
            desc = "\n".join(lines) if lines else "*No queued songs.*"
            e = discord.Embed(
                title=f"📋 Music Queue ({len(p.queue)} tracks)",
                description=desc,
                color=EMBED_COLOR
            )
            e.set_footer(text=f"Page {p_idx + 1} of {total_pages} | {BRAND_FOOTER}")
            pages.append(e)

        view = QueuePaginationView(pages, ctx.author.id) if len(pages) > 1 else None
        msg = await send_response(ctx, embed=pages[0], view=view)
        if view and msg:
            view.message = msg

    # 8. Now Playing
    @bot.command(name="nowplaying", aliases=["np"], description="Show details of the track currently playing")
    async def cmd_np(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.current:
            return await send_response(ctx, embed=err("Nothing is currently playing."))
        await send_response(ctx, embed=panel_embed(p))

    # 9. Volume Command
    @bot.command(name="volume", aliases=["vol", "v"], description="Adjust audio playback volume (1-200)")
    async def cmd_volume(ctx: commands.Context, level: Optional[int] = None):
        p = get_player(bot, ctx.guild.id)
        if level is not None:
            level = max(1, min(200, level))
            p.volume = level / 100
            if p.voice and p.voice.source:
                p.voice.source.volume = p.volume
            MusicDB.set_volume(ctx.guild.id, level)
            await p.update_panel()
        else:
            level = int(p.volume * 100)

        bar_len = min(10, level // 20)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        view = VolumeControlsView(p, ctx.author.id)
        await send_response(ctx, embed=ok("Volume Config", f"`{bar}` **{level}%**"), view=view)

    # 10. Loop Command
    @bot.command(name="loop", description="Toggle loop mode (off, track, queue)")
    async def cmd_loop(ctx: commands.Context, mode: str = "track"):
        p = get_player(bot, ctx.guild.id)
        p.loop = mode
        await p.update_panel()
        await send_response(ctx, embed=ok("Loop Mode Set", f"Loop mode set to **{mode.title()}**."))

    # 11. Shuffle Command
    @bot.command(name="shuffle", description="Shuffle the music queue")
    async def cmd_shuffle(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if len(p.queue) < 2:
            return await send_response(ctx, embed=err("Need at least 2 songs in queue to shuffle."))
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await p.update_panel()
        await send_response(ctx, embed=ok("Queue Shuffled!"))

    # 12. Audio Filters
    FILTERS = ["bassboost", "nightcore", "8d", "vaporwave", "karaoke", "doubletime", "slowmo", "daycore", "lofi", "pop", "chipmunk", "soft", "treblebass", "off"]
    @bot.command(name="filter", description="Apply real-time FFmpeg audio filters")
    async def cmd_filter(ctx: commands.Context, name: str):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if name == "off" else name
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok(f"Filter: {name.title()}", "Restarting track with active filter…"))

    # Equalizer
    EQ_PRESETS = ["flat", "classical", "jazz", "metal", "rock", "vocal", "electronic", "bassboost"]
    @bot.command(name="equalizer", aliases=["eq"], description="Apply preset equalizer acoustics")
    async def cmd_equalizer(ctx: commands.Context, preset: str):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if preset == "flat" else preset
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok(f"Equalizer Set: {preset.title()}", "Restarting track with equalizer applied…"))

    # Radio Command
    @bot.command(name="radio", description="Stream live 24/7 lofi and chill radio")
    async def cmd_radio(ctx: commands.Context, station: str = "lofi-chill"):
        p = get_player(bot, ctx.guild.id)
        p.text_ch = ctx.channel
        if not p.voice or not p.voice.is_connected():
            vc = await ensure_vc(ctx, bot)
            if not vc: return

        info = RADIO_STATIONS.get(station)
        if not info:
            return await ctx.send(embed=err("Invalid radio station selected."))

        track = {
            "title": info["title"],
            "url": info["url"],
            "duration": 0,
            "thumbnail": "https://i.imgur.com/4S72x1A.gif",
            "uploader": info["uploader"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        p.queue.clear()
        p.current = None
        p.queue.append(track)
        if p.voice.is_playing() or p.voice.is_paused():
            p.voice.stop()
        else:
            await play_next(bot, ctx.guild, ctx.interaction)
        await ctx.send(embed=ok("Radio Tuned", f"Tuned into **{info['title']}**."))

    # Autoplay Command
    @bot.command(name="autoplay", description="Toggle automatic related song playback")
    async def cmd_autoplay(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.autoplay = not p.autoplay
        await p.update_panel()
        await send_response(ctx, embed=ok("AutoPlay", f"AutoPlay is now **{'Enabled ✅' if p.autoplay else 'Disabled ❌'}**."))

    # Clear Queue Command
    @bot.command(name="clearqueue", aliases=["cq", "qclear"], description="Clear all songs from music queue")
    async def cmd_clear(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        cnt = len(p.queue)
        p.queue.clear()
        await p.update_panel()
        await send_response(ctx, embed=ok("Queue Cleared", f"Removed **{cnt}** tracks from queue."))

    # Pause Command
    @bot.command(name="pause", description="Pause the currently playing track")
    async def cmd_pause(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.current:
            return await send_response(ctx, embed=err("Nothing is currently playing."))
        if p.is_paused():
            return await send_response(ctx, embed=err("Playback is already paused."))
        p.voice.pause()
        p.paused_at = time.time()
        await p.update_panel()
        await send_response(ctx, embed=ok("Paused", "Use `,resume` to continue playing."))

    # Resume Command
    @bot.command(name="resume", description="Resume paused track")
    async def cmd_resume(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.current:
            return await send_response(ctx, embed=err("Nothing is currently playing."))
        if not p.is_paused():
            return await send_response(ctx, embed=err("Playback is not paused."))
        p.voice.resume()
        if p.start_time and p.paused_at:
            p.start_time += (time.time() - p.paused_at)
        p.paused_at = None
        await p.update_panel()
        await send_response(ctx, embed=ok("Resumed", "Playback resumed."))

    # Direct filter shortcuts
    @bot.command(name="lofifilter", description="Toggle lofi filter")
    async def cmd_lofifilter(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "lofi" else "lofi"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Lofi Filter", f"Lofi filter is now **{'Enabled' if p.filter == 'lofi' else 'Disabled'}**."))

    @bot.command(name="bassboost", description="Toggle bass boost filter")
    async def cmd_bassboost(ctx: commands.Context, level: str = "medium"):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if level == "off" else f"bassboost_{level}"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Bassboost", f"Bassboost set to **{level.title()}**."))

    @bot.command(name="nightcore", description="Toggle nightcore filter")
    async def cmd_nightcore(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "nightcore" else "nightcore"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Nightcore", f"Nightcore filter is now **{'Enabled' if p.filter == 'nightcore' else 'Disabled'}**."))

    @bot.command(name="vaporwave", description="Toggle vaporwave filter")
    async def cmd_vaporwave(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "vaporwave" else "vaporwave"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Vaporwave", f"Vaporwave filter is now **{'Enabled' if p.filter == 'vaporwave' else 'Disabled'}**."))

    @bot.command(name="8d", description="Toggle 8D audio filter")
    async def cmd_8d(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "8d" else "8d"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("8D Filter", f"8D filter is now **{'Enabled' if p.filter == '8d' else 'Disabled'}**."))

    @bot.command(name="chipmunk", description="Toggle chipmunk filter")
    async def cmd_chipmunk(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "chipmunk" else "chipmunk"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Chipmunk", f"Chipmunk filter is now **{'Enabled' if p.filter == 'chipmunk' else 'Disabled'}**."))

    @bot.command(name="earrape", description="Toggle earrape filter")
    async def cmd_earrape(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "earrape" else "earrape"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Earrape", f"Earrape filter is now **{'Enabled' if p.filter == 'earrape' else 'Disabled'}**."))

    @bot.command(name="karaoke", description="Toggle karaoke filter")
    async def cmd_karaoke(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "karaoke" else "karaoke"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Karaoke", f"Karaoke filter is now **{'Enabled' if p.filter == 'karaoke' else 'Disabled'}**."))

    @bot.command(name="slowmo", description="Toggle slow motion filter")
    async def cmd_slowmo(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "slowmo" else "slowmo"
        p.speed = 1.0 if p.filter is None else 0.5
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Slowmo", f"Slowmo filter is now **{'Enabled' if p.filter == 'slowmo' else 'Disabled'}**."))

    @bot.command(name="soft", description="Toggle soft filter")
    async def cmd_soft(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "soft" else "soft"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Soft Filter", f"Soft filter is now **{'Enabled' if p.filter == 'soft' else 'Disabled'}**."))

    @bot.command(name="treblebass", description="Toggle treble bass filter")
    async def cmd_treblebass(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "treblebass" else "treblebass"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("TrebleBass", f"TrebleBass filter is now **{'Enabled' if p.filter == 'treblebass' else 'Disabled'}**."))

    @bot.command(name="pop", description="Toggle pop filter")
    async def cmd_pop(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None if p.filter == "pop" else "pop"
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Pop Filter", f"Pop filter is now **{'Enabled' if p.filter == 'pop' else 'Disabled'}**."))

    @bot.command(name="clearfilter", description="Clear all active audio filters")
    async def cmd_clearfilter(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        p.filter = None
        p.speed = 1.0
        p.pitch = 1.0
        if p.current and p.voice:
            p.seek_offset = p.position
            p.start_time = time.time()
            p.paused_at = None
            p.restarting_track = True
            p.voice.stop()
        await ctx.send(embed=ok("Filters Cleared", "All active audio filters have been reset."))

    # Pitch & Speed
    @bot.command(name="pitch", description="Change playback pitch multiplier (0.5x - 2.0x)")
    async def cmd_pitch(ctx: commands.Context, multiplier: float):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        if multiplier < 0.5 or multiplier > 2.0:
            return await ctx.send(embed=err("Pitch multiplier must be between 0.5x and 2.0x."))
        p.pitch = multiplier
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Pitch Adjusted", f"Playback pitch multiplier set to **{multiplier}x**."))

    @bot.command(name="speed", description="Change playback speed multiplier (0.5x - 2.0x)")
    async def cmd_speed(ctx: commands.Context, multiplier: float):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        if multiplier < 0.5 or multiplier > 2.0:
            return await ctx.send(embed=err("Playback speed must be between 0.5x and 2.0x."))
        p.speed = multiplier
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Speed Adjusted", f"Playback speed multiplier set to **{multiplier}x**."))

    # Seek / Forward / Rewind / Replay
    @bot.command(name="seek", description="Seek to position (e.g. 90 or 1:30)")
    async def cmd_seek(ctx: commands.Context, time: str):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        sec = parse_time(time, int(p.current.get("duration", 0)))
        if sec is None or sec < 0:
            return await ctx.send(embed=err("Invalid format! Use seconds (e.g. 90) or mm:ss (e.g. 1:30)."))
        dur = int(p.current.get("duration", 0))
        if dur > 0 and sec > dur:
            return await ctx.send(embed=err(f"Seek position exceeds duration ({_fmt(dur)})."))
        p.seek_offset = sec
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Seeked", f"Playback jumped to **{_fmt(sec)}**."))

    @bot.command(name="forward", description="Fast forward song by seconds")
    async def cmd_forward(ctx: commands.Context, seconds: int = 15):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        dur = int(p.current.get("duration", 0))
        new_pos = p.position + seconds
        if dur > 0 and new_pos >= dur:
            new_pos = max(0, dur - 2)
        p.seek_offset = new_pos
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Fast Forwarded", f"Advanced **{seconds}s** (now at **{_fmt(new_pos)}**)."))

    @bot.command(name="rewind", description="Rewind song by seconds")
    async def cmd_rewind(ctx: commands.Context, seconds: int = 15):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        new_pos = max(0, p.position - seconds)
        p.seek_offset = new_pos
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Rewound", f"Rewound **{seconds}s** (now at **{_fmt(new_pos)}**)."))

    @bot.command(name="replay", description="Replay current song from beginning")
    async def cmd_replay(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.voice or not p.is_playing():
            return await ctx.send(embed=err("Nothing is currently playing."))
        p.seek_offset = 0
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        await ctx.send(embed=ok("Replayed", "Playing again from beginning."))

    # History & Replay from history
    @bot.command(name="history", description="Show recently played tracks")
    async def cmd_history(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.history:
            return await send_response(ctx, embed=err("No playback history available."))
        lines = [
            f"`{idx}.` {t['title']} `{p.fmt(t.get('duration',0))}` — "
            f"{'<@'+str(t['requester_id'])+'>' if t.get('requester_id') else 'AutoPlay'}"
            for idx, t in enumerate(list(p.history)[:15], 1)
        ]
        e = discord.Embed(title="📜 Recently Played History", description="\n".join(lines), color=EMBED_COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await send_response(ctx, embed=e)

    @bot.command(name="historyplay", aliases=["hp", "replayhistory"], description="Replay a song from history index")
    async def cmd_history_play(ctx: commands.Context, index: int):
        p = get_player(bot, ctx.guild.id)
        if not p.history or index < 1 or index > len(p.history):
            return await send_response(ctx, embed=err(f"Invalid index. Range: 1 to {len(p.history)}."))
        track_to_play = p.history[index - 1]
        p.queue.appendleft({
            "title": track_to_play["title"],
            "url": track_to_play["url"],
            "duration": track_to_play.get("duration", 0),
            "thumbnail": track_to_play.get("thumbnail", ""),
            "uploader": track_to_play.get("uploader", "Unknown"),
            "requester_id": ctx.author.id,
            "queued_msg": None
        })
        if p.voice and (p.is_playing() or p.is_paused()):
            p.voice.stop()
            await send_response(ctx, embed=ok("Replaying from History", f"Now playing **{track_to_play['title']}**."))
        else:
            if not p.voice or not p.voice.is_connected():
                vc = await ensure_vc(ctx, bot)
                if not vc: return
            await play_next(bot, ctx.guild, ctx.interaction)
            await send_response(ctx, embed=ok("Playing from History", f"Now playing **{track_to_play['title']}**."))

    # Queue manipulations: bump, move, remove, removeduplicates
    @bot.command(name="bump", description="Bump a queued track to the front")
    async def cmd_bump(ctx: commands.Context, position: int):
        p = get_player(bot, ctx.guild.id)
        if position < 1 or position > len(p.queue):
            return await ctx.send(embed=err(f"Invalid position. Range: 1 to {len(p.queue)}."))
        track = p.queue[position - 1]
        del p.queue[position - 1]
        p.queue.appendleft(track)
        await p.update_panel()
        await ctx.send(embed=ok("Track Bumped", f"Bumped **{track['title']}** to position #1."))

    @bot.command(name="move", description="Move a track's position in queue")
    async def cmd_move(ctx: commands.Context, from_pos: int, to_pos: int):
        p = get_player(bot, ctx.guild.id)
        if from_pos < 1 or from_pos > len(p.queue) or to_pos < 1 or to_pos > len(p.queue):
            return await ctx.send(embed=err(f"Positions must be between 1 and {len(p.queue)}."))
        track = p.queue[from_pos - 1]
        del p.queue[from_pos - 1]
        p.queue.insert(to_pos - 1, track)
        await p.update_panel()
        await ctx.send(embed=ok("Track Moved", f"Moved **{track['title']}** from #{from_pos} to #{to_pos}."))

    @bot.command(name="removetrack", aliases=["qremove", "trackremove"], description="Remove a track from queue")
    async def cmd_remove(ctx: commands.Context, position: int):
        p = get_player(bot, ctx.guild.id)
        if position < 1 or position > len(p.queue):
            return await ctx.send(embed=err(f"Position must be between 1 and {len(p.queue)}."))
        track = p.queue[position - 1]
        del p.queue[position - 1]
        await p.update_panel()
        await ctx.send(embed=ok("Track Removed", f"Removed **{track['title']}** from queue."))

    @bot.command(name="removeduplicates", aliases=["rmdupes"], description="Remove duplicate tracks from queue")
    async def cmd_removeduplicates(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        seen = set()
        new_q = deque()
        removed = 0
        for t in p.queue:
            u = t.get("url") or t.get("title")
            if u in seen:
                removed += 1
            else:
                seen.add(u)
                new_q.append(t)
        p.queue = new_q
        await p.update_panel()
        await ctx.send(embed=ok("Duplicates Cleaned", f"Removed **{removed}** duplicate track(s)."))

    # Liked songs system
    @bot.command(name="like", description="Add currently playing song to Liked Songs")
    async def cmd_like(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.current:
            return await ctx.send(embed=err("No song currently playing."))
        t = p.current
        MusicDB.like_track(ctx.author.id, t["url"], t["title"], t.get("uploader", "Unknown"), t.get("thumbnail", ""), t.get("duration", 0))
        await ctx.send(embed=ok("Track Liked", f"Added **{t['title']}** to your Liked Songs ⭐"))

    @bot.command(name="unlike", description="Remove currently playing song from Liked Songs")
    async def cmd_unlike(ctx: commands.Context):
        p = get_player(bot, ctx.guild.id)
        if not p.current:
            return await ctx.send(embed=err("No song currently playing."))
        MusicDB.unlike_track(ctx.author.id, p.current["url"])
        await ctx.send(embed=ok("Track Unliked", f"Removed **{p.current['title']}** from Liked Songs."))

    @bot.command(name="liked", description="List your Liked Songs")
    async def cmd_liked(ctx: commands.Context):
        songs = MusicDB.get_liked_tracks(ctx.author.id)
        if not songs:
            return await ctx.send(embed=err("You have not liked any songs yet."))
        lines = [f"`{idx}.` [{s['title']}]({s['url']}) by **{s['author']}** (`{_fmt(s['duration'])}`)" for idx, s in enumerate(songs[:20], 1)]
        e = discord.Embed(title="⭐ Your Liked Songs", description="\n".join(lines), color=EMBED_COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await ctx.send(embed=e)

    @bot.command(name="likedplay", description="Queue and play all your Liked Songs")
    async def cmd_likedplay(ctx: commands.Context):
        songs = MusicDB.get_liked_tracks(ctx.author.id)
        if not songs:
            return await ctx.send(embed=err("You have no liked songs to play."))
        p = get_player(bot, ctx.guild.id)
        p.text_ch = ctx.channel
        if not p.voice or not p.voice.is_connected():
            vc = await ensure_vc(ctx, bot)
            if not vc: return
        first_play = not p.is_playing() and not p.is_paused()
        for idx, s in enumerate(songs):
            track = {
                "title": s["title"],
                "url": s["url"],
                "duration": s["duration"],
                "thumbnail": s.get("thumbnail", ""),
                "uploader": s["author"],
                "requester_id": ctx.author.id,
                "queued_msg": None
            }
            p.queue.append(track)
        await ctx.send(embed=ok("Liked Songs Queued", f"Queued **{len(songs)}** songs from your liked tracks."))
        if first_play:
            await play_next(bot, ctx.guild, ctx.interaction)
        else:
            await p.update_panel()

    # Search & Lyrics
    @bot.command(name="search", description="Search YouTube and select from top 5 tracks")
    async def cmd_search(ctx: commands.Context, *, query: str):
        searching_msg = await ctx.send(embed=make_embed("🔍 Searching...", f"Searching for `{query}`..."))
        try:
            tracks = await YTSource.search(query, bot.loop, max_results=5)
            if not tracks:
                return await searching_msg.edit(embed=err("No search results found."))

            options = []
            lines = []
            for idx, t in enumerate(tracks):
                title = t.get("title", "Unknown")[:80]
                dur = _fmt(t.get("duration", 0))
                url = t.get("webpage_url", "")
                uploader = t.get("uploader", "Unknown")
                options.append(discord.SelectOption(label=f"{idx+1}. {title}", value=url, description=f"Duration: {dur}"))
                lines.append(f"`{idx+1}.` **[{title}]({url})** (`{dur}`) • `{uploader}`")

            class SearchSelect(discord.ui.Select):
                def __init__(self):
                    super().__init__(placeholder="Select a song to play...", options=options)

                async def callback(self, select_interaction: discord.Interaction):
                    await select_interaction.response.defer()
                    sel_url = self.values[0]
                    p = get_player(bot, select_interaction.guild_id)
                    sel_track = next(t for t in tracks if t.get("webpage_url") == sel_url)
                    track = {
                        "title": sel_track.get("title", "Unknown"),
                        "url": sel_url,
                        "duration": int(sel_track.get("duration") or 0),
                        "thumbnail": sel_track.get("thumbnail", ""),
                        "uploader": sel_track.get("uploader", "Unknown"),
                        "requester_id": select_interaction.user.id,
                        "queued_msg": None
                    }
                    guild_vc = select_interaction.guild.voice_client or p.voice
                    if guild_vc and guild_vc.is_connected():
                        p.voice = guild_vc
                    else:
                        ch = select_interaction.user.voice.channel if select_interaction.user.voice else None
                        if not ch:
                            return await select_interaction.followup.send(embed=err("Join a voice channel first!"), ephemeral=True)
                        try:
                            p.voice = await ch.connect(timeout=10, reconnect=True)
                            p.stay_247 = True
                            MusicDB.set_247(select_interaction.guild_id, 1, ch.id, select_interaction.channel.id)
                        except Exception:
                            if select_interaction.guild.voice_client:
                                p.voice = select_interaction.guild.voice_client

                    first_play = not p.is_playing() and not p.is_paused()
                    p.queue.append(track)
                    await searching_msg.edit(embed=ok("Added to Queue", f"**{track['title']}**"), view=None)
                    if first_play:
                        await play_next(bot, select_interaction.guild, select_interaction)
                    else:
                        await p.update_panel()

            view = discord.ui.View(timeout=60)
            view.add_item(SearchSelect())
            e = discord.Embed(title="🔍 YouTube Search Results", description="\n".join(lines), color=EMBED_COLOR)
            e.set_footer(text=BRAND_FOOTER)
            await searching_msg.edit(embed=e, view=view)
        except Exception as ex:
            await searching_msg.edit(embed=err(f"Search failed: {ex}"))

    @bot.command(name="lyrics", description="Fetch real-time lyrics for playing track")
    async def cmd_lyrics(ctx: commands.Context, query: Optional[str] = None):
        p = get_player(bot, ctx.guild.id)
        if not query:
            if not p.current:
                return await ctx.send(embed=err("No song playing. Specify a search query."))
            query = p.current["title"]
        await ctx.defer()
        clean = re.sub(r'\(.*?\)|\[.*?\]', '', query).strip()
        url = f"https://lyrist.vercel.app/api/{clean}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lyrics = data.get("lyrics", "")
                        title = data.get("title", clean.title())
                        artist = data.get("artist", "Unknown")
                        if not lyrics:
                            return await ctx.send(embed=err(f"No lyrics found for `{clean}`."))
                        if len(lyrics) > 4000:
                            lyrics = lyrics[:4000] + "\n\n*...lyrics truncated*"
                        e = discord.Embed(title=f"🎤 Lyrics: {title}", description=lyrics, color=EMBED_COLOR)
                        e.set_author(name=f"Artist: {artist}")
                        e.set_footer(text=BRAND_FOOTER)
                        await ctx.send(embed=e)
                    else:
                        await ctx.send(embed=err("Could not locate lyrics."))
        except Exception as ex:
            await ctx.send(embed=err(f"Failed to fetch lyrics: {ex}"))

    # Playlists system
    @bot.command(name="pl-create", description="Create a custom personal playlist")
    async def cmd_pl_create(ctx: commands.Context, name: str):
        ok_res = MusicDB.create_playlist(ctx.author.id, name)
        if ok_res:
            await send_response(ctx, embed=ok("Playlist Created", f"Created playlist **`{name}`**."))
        else:
            await send_response(ctx, embed=err(f"Playlist **`{name}`** already exists."))

    @bot.command(name="pl-delete", description="Delete a custom personal playlist")
    async def cmd_pl_delete(ctx: commands.Context, name: str):
        ok_res = MusicDB.delete_playlist(ctx.author.id, name)
        if ok_res:
            await send_response(ctx, embed=ok("Playlist Deleted", f"Deleted playlist **`{name}`**."))
        else:
            await send_response(ctx, embed=err(f"Playlist **`{name}`** not found."))

    @bot.command(name="pl-list", description="List your personal playlists")
    async def cmd_pl_list(ctx: commands.Context):
        lists = MusicDB.get_playlists(ctx.author.id)
        if not lists:
            return await send_response(ctx, embed=err("You have not created any playlists yet."))
        lines = [f"`{idx}.` **{name}**" for idx, name in enumerate(lists, 1)]
        e = discord.Embed(title="📋 Your Saved Playlists", description="\n".join(lines), color=EMBED_COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await send_response(ctx, embed=e)

    @bot.command(name="pl-play", description="Play all tracks from your saved playlist")
    async def cmd_pl_play(ctx: commands.Context, name: str):
        tracks = MusicDB.get_playlist_tracks(ctx.author.id, name)
        if not tracks:
            return await send_response(ctx, embed=err(f"Playlist **`{name}`** is empty or does not exist."))
        p = get_player(bot, ctx.guild.id)
        p.text_ch = ctx.channel
        if not p.voice or not p.voice.is_connected():
            vc = await ensure_vc(ctx, bot)
            if not vc: return
        first_play = not p.is_playing() and not p.is_paused()
        for s in tracks:
            p.queue.append({
                "title": s["title"],
                "url": s["url"],
                "duration": s["duration"],
                "thumbnail": s.get("thumbnail", ""),
                "uploader": s["author"],
                "requester_id": ctx.author.id,
                "queued_msg": None
            })
        await send_response(ctx, embed=ok("Playlist Loaded", f"Queued **{len(tracks)}** tracks from **`{name}`**."))
        if first_play:
            await play_next(bot, ctx.guild, ctx.interaction)
        else:
            await p.update_panel()

    # ─────────────────────────────────────────────
    #         SLASH COMMANDS (/music and /play)
    # ─────────────────────────────────────────────

    class MusicSlashGroup(app_commands.Group, name="music", description="VEYRA All-in-One Music Audio System"):
        @app_commands.command(name="play", description="Play any song or playlist from YouTube or Spotify")
        @app_commands.describe(query="Song title, URL, or Spotify link")
        async def slash_music_play(self, interaction: discord.Interaction, query: str):
            ctx = await bot.get_context(interaction)
            await cmd_play(ctx, query=query)

        @app_commands.command(name="panel", description="Open the live interactive music control panel")
        async def slash_music_panel(self, interaction: discord.Interaction):
            p = get_player(bot, interaction.guild_id)
            if p.panel_msg:
                try: await p.panel_msg.delete()
                except Exception: pass
                p.panel_msg = None
            view = MusicPanel(p)
            msg = await interaction.channel.send(embed=panel_embed(p), view=view)
            p.panel_msg = msg
            await interaction.response.send_message(embed=ok("Music Panel Opened"), ephemeral=True)

        @app_commands.command(name="skip", description="Skip current playing track")
        async def slash_music_skip(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_skip(ctx)

        @app_commands.command(name="stop", description="Stop music, clear queue, and disconnect")
        async def slash_music_stop(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_leave(ctx)

        @app_commands.command(name="pause", description="Pause playback")
        async def slash_music_pause(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_pause(ctx)

        @app_commands.command(name="resume", description="Resume playback")
        async def slash_music_resume(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_resume(ctx)

        @app_commands.command(name="queue", description="Show music queue")
        async def slash_music_queue(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_queue(ctx)

        @app_commands.command(name="volume", description="Set playback volume (1-200)")
        @app_commands.describe(level="Volume percentage")
        async def slash_music_volume(self, interaction: discord.Interaction, level: Optional[int] = None):
            ctx = await bot.get_context(interaction)
            await cmd_volume(ctx, level=level)

        @app_commands.command(name="loop", description="Set loop mode")
        @app_commands.choices(mode=[
            app_commands.Choice(name="Off", value="off"),
            app_commands.Choice(name="Track", value="track"),
            app_commands.Choice(name="Queue", value="queue"),
        ])
        async def slash_music_loop(self, interaction: discord.Interaction, mode: str = "track"):
            ctx = await bot.get_context(interaction)
            await cmd_loop(ctx, mode=mode)

        @app_commands.command(name="shuffle", description="Shuffle queue")
        async def slash_music_shuffle(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_shuffle(ctx)

        @app_commands.command(name="clear", description="Clear music queue")
        async def slash_music_clear(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_clear(ctx)

        @app_commands.command(name="nowplaying", description="Show currently playing track")
        async def slash_music_np(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_np(ctx)

        @app_commands.command(name="247", description="Toggle 24/7 standby voice mode")
        async def slash_music_247(self, interaction: discord.Interaction):
            ctx = await bot.get_context(interaction)
            await cmd_247(ctx)

    @bot.command(name="247", aliases=["24/7", "stay"], description="Configure or toggle 24/7 standby mode in voice channel")
    async def cmd_247(ctx: commands.Context, action: Optional[str] = None, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
        guild = ctx.guild
        if not guild:
            return
        
        # If action is 'set' or 'join'
        sub = (action or "").lower().strip()
        if sub in ("set", "join", "connect"):
            target_vc = channel or getattr(ctx.author.voice, "channel", None) if hasattr(ctx.author, "voice") else None
            if not target_vc:
                embed = err("Voice Channel Required", "Please join a voice channel first or mention a valid voice channel (`?247 set #channel`).")
                return await send_response(ctx, embed=embed)
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
                    INSERT INTO voice_247_settings (guild_id, channel_id, enabled, last_reconnect, updated_at)
                    VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?, enabled = 1, updated_at = CURRENT_TIMESTAMP
                """, (str(guild.id), str(target_vc.id), datetime.now(timezone.utc).isoformat(), str(target_vc.id)))
                conn.commit()
                conn.close()

                p = get_player(bot, guild.id)
                p.stay_247 = True
                MusicDB.set_247(guild.id, 1, target_vc.id, ctx.channel.id)

                embed = ok("24/7 Voice System Active", f"Connected and locked 24/7 to {target_vc.mention}.\nBot will automatically reconnect on restart.")
                return await send_response(ctx, embed=embed)
            except Exception as e:
                return await send_response(ctx, embed=err("Connection Error", f"Could not connect to {target_vc.mention}: `{e}`"))

        elif sub in ("leave", "stop", "off", "disable"):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE voice_247_settings SET enabled = 0 WHERE guild_id = ?", (str(guild.id),))
            conn.commit()
            conn.close()

            p = get_player(bot, guild.id)
            p.stay_247 = False
            MusicDB.set_247(guild.id, 0, None, None)

            vc = guild.voice_client
            if vc and vc.is_connected():
                await vc.disconnect(force=True)

            embed = ok("24/7 Voice Disabled", "Bot disconnected and 24/7 persistence turned off.")
            return await send_response(ctx, embed=embed)

        elif sub in ("status", "info"):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM voice_247_settings WHERE guild_id = ?", (str(guild.id),))
            row = cursor.fetchone()
            conn.close()
            enabled = bool(row['enabled']) if row else False
            ch_id = int(row['channel_id']) if (row and row['channel_id']) else None
            ch = guild.get_channel(ch_id) if ch_id else None
            status_desc = f"**Status:** {'🟢 Active (24/7)' if enabled else '🔴 Inactive'}\n"
            status_desc += f"**Bound Channel:** {ch.mention if ch else 'None'}\n"
            status_desc += f"**Voice State:** {'Connected' if (guild.voice_client and guild.voice_client.is_connected()) else 'Disconnected'}"
            embed = ok("24/7 Voice Status", status_desc)
            return await send_response(ctx, embed=embed)

        # Default: toggle
        p = get_player(bot, ctx.guild.id)
        p.stay_247 = not p.stay_247
        ch_id = p.voice.channel.id if (p.voice and p.voice.channel) else None
        txt_id = ctx.channel.id
        MusicDB.set_247(ctx.guild.id, 1 if p.stay_247 else 0, ch_id, txt_id)

        conn = get_db()
        cursor = conn.cursor()
        if p.stay_247 and ch_id:
            cursor.execute("""
                INSERT INTO voice_247_settings (guild_id, channel_id, enabled, last_reconnect, updated_at)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?, enabled = 1, updated_at = CURRENT_TIMESTAMP
            """, (str(guild.id), str(ch_id), datetime.now(timezone.utc).isoformat(), str(ch_id)))
        else:
            cursor.execute("UPDATE voice_247_settings SET enabled = 0 WHERE guild_id = ?", (str(guild.id),))
        conn.commit()
        conn.close()

        await send_response(ctx, embed=ok("24/7 Mode", f"24/7 Standby Mode is now **{'Enabled ✅' if p.stay_247 else 'Disabled ❌'}**."))

    try:
        bot.tree.add_command(MusicSlashGroup())
    except Exception as e:
        logger.warning("Could not add MusicSlashGroup: %s", e)

    # Core top-level slash commands
    @bot.tree.command(name="play", description="Play any song or playlist from YouTube or Spotify")
    @app_commands.describe(query="Song title, URL, or Spotify link")
    async def tree_play(interaction: discord.Interaction, query: str):
        ctx = await bot.get_context(interaction)
        await cmd_play(ctx, query=query)

    @bot.tree.command(name="panel", description="Open the live interactive music control panel")
    async def tree_panel(interaction: discord.Interaction):
        p = get_player(bot, interaction.guild_id)
        if p.panel_msg:
            try: await p.panel_msg.delete()
            except Exception: pass
            p.panel_msg = None
        view = MusicPanel(p)
        msg = await interaction.channel.send(embed=panel_embed(p), view=view)
        p.panel_msg = msg
        await interaction.response.send_message(embed=ok("Music Panel Opened"), ephemeral=True)

    @bot.tree.command(name="skip", description="Skip current playing track")
    async def tree_skip(interaction: discord.Interaction):
        ctx = await bot.get_context(interaction)
        await cmd_skip(ctx)

    @bot.tree.command(name="stop", description="Stop music, clear queue, and disconnect")
    async def tree_stop(interaction: discord.Interaction):
        ctx = await bot.get_context(interaction)
        await cmd_leave(ctx)

    @bot.tree.command(name="pause", description="Pause playback")
    async def tree_pause(interaction: discord.Interaction):
        ctx = await bot.get_context(interaction)
        await cmd_pause(ctx)

    @bot.tree.command(name="resume", description="Resume playback")
    async def tree_resume(interaction: discord.Interaction):
        ctx = await bot.get_context(interaction)
        await cmd_resume(ctx)

    @bot.tree.command(name="queue", description="Show music queue")
    async def tree_queue(interaction: discord.Interaction):
        ctx = await bot.get_context(interaction)
        await cmd_queue(ctx)

    bot.command = orig_command
    bot.tree.command = orig_tree_command

    logger.info("Veyra Music System initialized successfully with full audio suite.")

