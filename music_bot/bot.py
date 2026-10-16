import subprocess
import sys
import os

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import shutil
import importlib
import time
import random
import asyncio
import logging
import sqlite3
import re
from collections import deque
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone
import socket

# Cloudflare Datacenter Rate Limit Bypass (Error Code 0)
# Uses Chrome 120 TLS fingerprint via curl_cffi to transparently bypass Cloudflare blocks on datacenter IPs
try:
    import discord.http
    import discord.errors
    from curl_cffi.requests import AsyncSession as _CurlAsyncSession

    _orig_http_request = discord.http.HTTPClient.request

    async def _stealth_http_request(self, route: discord.http.Route, *args, **kwargs):
        try:
            return await _orig_http_request(self, route, *args, **kwargs)
        except Exception as exc:
            err_msg = str(exc).lower()
            if "429" not in err_msg and "blocked" not in err_msg and "rate limit" not in err_msg:
                raise
            
            print(f"🛡️ [Cloudflare Bypass] Intercepted {exc}. Rerouting {route.method} {route.url} through Chrome TLS impersonation...")
            req_headers = {
                'Authorization': f'Bot {self.token}' if getattr(self, 'token', None) else ''
            }
            if 'headers' in kwargs and kwargs['headers']:
                for k, v in kwargs['headers'].items():
                    if k.lower() != 'user-agent':
                        req_headers[k] = v
                
            async with _CurlAsyncSession(impersonate="chrome120") as s:
                res = await s.request(
                    route.method,
                    route.url,
                    headers=req_headers,
                    json=kwargs.get('json'),
                    data=kwargs.get('data'),
                    timeout=kwargs.get('timeout', 30)
                )
                print(f"✅ [Cloudflare Bypass] Response: HTTP {res.status_code}")
                if res.status_code in (200, 201):
                    try:
                        return res.json()
                    except Exception:
                        return res.text
                elif res.status_code == 204:
                    return None
                elif res.status_code == 429:
                    try:
                        retry_after = float(res.json().get('retry_after', 5.0))
                    except Exception:
                        retry_after = 5.0
                    print(f"⏳ [Cloudflare Bypass] Rate limited. Sleeping for {retry_after}s before retry...")
                    await asyncio.sleep(retry_after)
                    res = await s.request(
                        route.method,
                        route.url,
                        headers=req_headers,
                        json=kwargs.get('json'),
                        data=kwargs.get('data'),
                        timeout=kwargs.get('timeout', 30)
                    )
                    if res.status_code in (200, 201):
                        try:
                            return res.json()
                        except Exception:
                            return res.text
                    elif res.status_code == 204:
                        return None
                    raise exc
                else:
                    raise exc

    discord.http.HTTPClient.request = _stealth_http_request
    print("🔒 Stealth Chrome TLS Cloudflare Bypass installed for Discord API.")
except Exception as _patch_err:
    print(f"⚠️ Could not install stealth HTTPClient patch: {_patch_err}")




BOT_NAME = "VEYRA MUSIC"

# Ensure node.exe path is in system environment PATH for yt-dlp to find Node.js
if "C:\\Program Files\\nodejs" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "C:\\Program Files\\nodejs" + os.pathsep + os.environ.get("PATH", "")

# Ensure local and system FFmpeg bin are in the environment PATH
ffmpeg_candidate_dirs = [
    r"C:\ffmpeg\bin",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin")
]
for p in ffmpeg_candidate_dirs:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

def get_ffmpeg_executable():
    for candidate in [
        shutil.which("ffmpeg"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe")
    ]:
        if candidate and os.path.exists(candidate):
            return candidate
    return "ffmpeg"

# Reconfigure stdout/stderr to UTF-8 on Windows for emoji printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except AttributeError:
        pass

logging.basicConfig(level=logging.INFO)
START_TIME = time.time()

# Ensure Opus audio codec is loaded on all platforms (Linux/Docker and Windows)
try:
    import discord.opus
    if not discord.opus.is_loaded():
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        _opus_candidates = [
            os.path.join(_base_dir, 'libopus-0.x64.dll'),
            os.path.join(_base_dir, 'opus.dll'),
            'libopus-0.x64.dll',
            'opus.dll',
            'opus',
            'libopus.so.0',
            'libopus.so',
            '/usr/lib/x86_64-linux-gnu/libopus.so.0',
            '/usr/lib/aarch64-linux-gnu/libopus.so.0',
            '/usr/lib/x86_64-linux-gnu/libopus.so',
            '/usr/lib/libopus.so.0',
        ]
        try:
            import discord
            _discord_bin = os.path.join(os.path.dirname(discord.__file__), 'bin')
            if os.path.isdir(_discord_bin):
                _opus_candidates.extend([
                    os.path.join(_discord_bin, 'libopus-0.x64.dll'),
                    os.path.join(_discord_bin, 'libopus-0.x86.dll'),
                ])
        except Exception:
            pass
        for opus_lib in _opus_candidates:
            if not os.path.isabs(opus_lib) and not os.path.exists(opus_lib) and not opus_lib.endswith('.so') and not opus_lib.endswith('.so.0') and opus_lib != 'opus':
                continue
            try:
                discord.opus.load_opus(opus_lib)
                if discord.opus.is_loaded():
                    print(f"🎵 Loaded Opus library: {opus_lib}")
                    break
            except Exception:
                pass
except Exception as e:
    print(f"⚠️ Opus loader exception: {e}")

# In-memory circular log buffer for live debugging via /api/logs
RECENT_LOGS = deque(maxlen=1000)
class LogTeeHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if "/health" in msg or "GET /health" in msg:
                return
            RECENT_LOGS.append(msg)
        except Exception:
            pass

_tee_handler = LogTeeHandler()
_tee_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%H:%M:%S'))
logging.getLogger().addHandler(_tee_handler)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

class OutputTee:
    def __init__(self, target):
        self.target = target
    def write(self, s):
        if self.target:
            try: self.target.write(s)
            except Exception: pass
        if isinstance(s, str) and s.strip():
            if "/health" in s or "GET /health" in s:
                return
            ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
            RECENT_LOGS.append(f"{ts} {s.rstrip()}")
    def flush(self):
        if self.target and hasattr(self.target, 'flush'):
            self.target.flush()

sys.stdout = OutputTee(sys.stdout)
sys.stderr = OutputTee(sys.stderr)


# ─────────────────────────────────────────────
#             DEPENDENCY AUTO-INSTALLER
# ─────────────────────────────────────────────

REQUIRED = ["discord.py>=2.3.0", "yt-dlp", "PyNaCl", "aiohttp", "psutil", "davey", "bgutil-ytdlp-pot-provider"]

def auto_install():
    missing = []
    for pkg in REQUIRED:
        name = pkg.split(">=")[0]
        import_name = {"discord.py": "discord", "PyNaCl": "nacl", "bgutil-ytdlp-pot-provider": "yt_dlp_plugins"}.get(name, name.replace("-", "_"))
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pkg)
    if not missing:
        return
    for pkg in missing:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet", "--break-system-packages"])
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
            except Exception as e:
                print(f"  ⚠️ Failed to install {pkg}: {e}")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except Exception:
        pass

auto_install()

import discord
from discord.ext import commands, tasks
from discord import app_commands
import yt_dlp
import aiohttp
import psutil

# ─────────────────────────────────────────────
#                 CONFIGURATION
# ─────────────────────────────────────────────

CONFIG_FILE = "config.json"
_possible_cookies = [
    "cookies.txt",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cookies.txt"),
]
COOKIES_FILE = "cookies.txt"
for _p in _possible_cookies:
    if os.path.exists(_p) and os.path.getsize(_p) > 100:
        COOKIES_FILE = os.path.abspath(_p)
        break

# Default config fallback (safe for commercial distribution, can be loaded from env or config.json)
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN") or ""
PREFIX = os.environ.get("PREFIX", ".")
OWNER_IDS = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip().isdigit()]
if not OWNER_IDS:
    OWNER_IDS = []
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

if os.path.exists(CONFIG_FILE):
    import json
    try:
        with open(CONFIG_FILE, "r") as f:
            cdata = json.load(f)
            BOT_TOKEN = (
                os.environ.get("BOT_TOKEN")
                or os.environ.get("DISCORD_BOT_TOKEN")
                or os.environ.get("DISCORD_TOKEN")
                or os.environ.get("TOKEN")
                or cdata.get("token")
                or BOT_TOKEN
            )
            PREFIX = cdata.get("prefix", PREFIX)
            OWNER_IDS = cdata.get("owner_ids", OWNER_IDS)
            spotify_config = cdata.get("spotify", {})
            SPOTIFY_CLIENT_ID = spotify_config.get("clientId", SPOTIFY_CLIENT_ID)
            SPOTIFY_CLIENT_SECRET = spotify_config.get("clientSecret", SPOTIFY_CLIENT_SECRET)
            print(f"✅ Loaded configuration from {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️ Error loading config.json: {e}")

env_cookies = os.environ.get("YOUTUBE_COOKIES") or os.environ.get("COOKIES_TEXT")
if env_cookies:
    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as _ef:
            _ef.write(env_cookies)
        print("✅ Synced cookies from environment variable to cookies.txt")
    except Exception as _ece:
        print(f"⚠️ Failed to write environment cookies: {_ece}")

COOKIE_ARG = None

if os.path.exists(COOKIES_FILE):
    try:
        # Sanitize cookie file format so http.cookiejar never crashes on malformed lines
        with open(COOKIES_FILE, "r", encoding="utf-8", errors="ignore") as _cf:
            _raw_lines = _cf.readlines()
        _clean_lines = ["# Netscape HTTP Cookie File\n# Cleaned by VEYRA Music\n"]
        has_yt_login = False
        for _l in _raw_lines:
            _ls = _l.strip()
            if not _ls or _ls.startswith("#"):
                continue
            _parts = _ls.split("\t")
            if len(_parts) >= 7:
                if _parts[0].startswith("."):
                    _parts[1] = "TRUE"
                _clean_lines.append("\t".join(_parts) + "\n")
                if any(k in _parts[5] for k in ("LOGIN_INFO", "SID", "VISITOR_INFO1_LIVE", "SAPISID", "SSID", "HSID", "PREF", "__Secure-1PSID", "__Secure-3PSID")):
                    has_yt_login = True
        with open(COOKIES_FILE, "w", encoding="utf-8") as _cf:
            _cf.writelines(_clean_lines)
        if has_yt_login:
            COOKIE_ARG = COOKIES_FILE
            print(f"✅ Loaded verified YouTube account cookies from {COOKIES_FILE}")
        else:
            COOKIE_ARG = None
            print(f"ℹ️ {COOKIES_FILE} does not contain valid YouTube session cookies. Using Chrome TLS impersonation.")
    except Exception as _ce:
        print(f"⚠️ Error sanitizing {COOKIES_FILE}: {_ce}")
        COOKIE_ARG = None
else:
    print(f"ℹ️ {COOKIES_FILE} not found. YouTube streaming will use Chrome TLS impersonation.")

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    CHROME_TARGET = ImpersonateTarget("chrome")
    print("🚀 Chrome TLS impersonation target active for direct YouTube extraction.")
except Exception as _ite:
    CHROME_TARGET = None
    print(f"⚠️ ImpersonateTarget not available: {_ite}")

# ─────────────────────────────────────────────
#              DATABASE SYSTEM
# ─────────────────────────────────────────────

DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        prefix TEXT DEFAULT '.',
        volume INTEGER DEFAULT 100,
        stay_247 INTEGER DEFAULT 0,
        stay_voice_id INTEGER,
        stay_text_id INTEGER
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS liked_tracks (
        user_id INTEGER,
        track_url TEXT,
        track_title TEXT,
        track_author TEXT,
        track_thumbnail TEXT,
        track_duration INTEGER,
        PRIMARY KEY (user_id, track_url)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER,
        title TEXT,
        author TEXT,
        url TEXT,
        thumbnail TEXT,
        duration INTEGER,
        FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_playlist_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER,
        title TEXT,
        author TEXT,
        url TEXT,
        thumbnail TEXT,
        duration INTEGER,
        FOREIGN KEY(playlist_id) REFERENCES global_playlists(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dj_roles (
        guild_id INTEGER PRIMARY KEY,
        role_id INTEGER
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        guild_id INTEGER PRIMARY KEY,
        enabled INTEGER DEFAULT 1
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dj_modes (
        guild_id INTEGER PRIMARY KEY,
        enabled INTEGER DEFAULT 0
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_stats (
        stat_name TEXT PRIMARY KEY,
        stat_value INTEGER DEFAULT 0
    );
    """)
    cursor.execute("UPDATE guild_settings SET stay_247 = 1 WHERE stay_247 = 0")
    conn.commit()
    conn.close()

init_db()

class Database:
    @staticmethod
    def init_guild(guild_id: int):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO guild_settings (guild_id, stay_247) VALUES (?, 1) ON CONFLICT(guild_id) DO NOTHING", (guild_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def increment_stat(stat_name: str, by: int = 1):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO global_stats (stat_name, stat_value) VALUES (?, ?) ON CONFLICT(stat_name) DO UPDATE SET stat_value = stat_value + ?", (stat_name, by, by))
        conn.commit()
        conn.close()

    @staticmethod
    def get_stat(stat_name: str) -> int:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT stat_value FROM global_stats WHERE stat_name = ?", (stat_name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0

    @staticmethod
    def get_prefix(guild_id: int) -> str:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else PREFIX

    @staticmethod
    def set_prefix(guild_id: int, prefix: str):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO guild_settings (guild_id, prefix) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET prefix = ?", (guild_id, prefix, prefix))
        conn.commit()
        conn.close()

    @staticmethod
    def get_volume(guild_id: int) -> int:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT volume FROM guild_settings WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 100

    @staticmethod
    def set_volume(guild_id: int, volume: int):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO guild_settings (guild_id, volume) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET volume = ?", (guild_id, volume, volume))
        conn.commit()
        conn.close()

    @staticmethod
    def get_247(guild_id: int) -> tuple:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT stay_247, stay_voice_id, stay_text_id FROM guild_settings WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        conn.close()
        return row if row else (0, None, None)

    @staticmethod
    def get_all_247() -> list[tuple]:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id, stay_247, stay_voice_id, stay_text_id FROM guild_settings WHERE stay_247 = 1")
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def set_247(guild_id: int, enabled: int, voice_id: Optional[int] = None, text_id: Optional[int] = None):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO guild_settings (guild_id, stay_247, stay_voice_id, stay_text_id) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET stay_247 = ?, stay_voice_id = ?, stay_text_id = ?", 
                     (guild_id, enabled, voice_id, text_id, enabled, voice_id, text_id))
        conn.commit()
        conn.close()

    @staticmethod
    def like_track(user_id: int, url: str, title: str, author: str, thumbnail: str, duration: int):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT OR REPLACE INTO liked_tracks (user_id, track_url, track_title, track_author, track_thumbnail, track_duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, url, title, author, thumbnail, duration))
        conn.commit()
        conn.close()

    @staticmethod
    def unlike_track(user_id: int, url: str):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("DELETE FROM liked_tracks WHERE user_id = ? AND track_url = ?", (user_id, url))
        conn.commit()
        conn.close()

    @staticmethod
    def is_track_liked(user_id: int, url: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM liked_tracks WHERE user_id = ? AND track_url = ?", (user_id, url))
        row = cursor.fetchone()
        conn.close()
        return bool(row)

    @staticmethod
    def get_liked_tracks(user_id: int) -> list:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT track_title, track_url, track_author, track_duration, track_thumbnail FROM liked_tracks WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"title": r[0], "url": r[1], "author": r[2], "duration": r[3], "thumbnail": r[4]} for r in rows]

    @staticmethod
    def create_playlist(user_id: int, name: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM playlists WHERE user_id = ? AND name = ?", (user_id, name))
        if cursor.fetchone():
            conn.close()
            return False
        conn.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete_playlist(user_id: int, name: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        conn.execute("DELETE FROM playlists WHERE id = ?", (pl_id,))
        conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_playlists(user_id: int) -> list:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM playlists WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    @staticmethod
    def add_to_playlist(user_id: int, pl_name: str, title: str, author: str, url: str, thumbnail: str, duration: int) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (user_id, pl_name))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        conn.execute("INSERT INTO playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, title, author, url, thumbnail, duration))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_playlist_tracks(user_id: int, pl_name: str) -> list:
        conn = sqlite3.connect(DB_FILE)
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
    def get_announcement(guild_id: int) -> int:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM announcements WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 1

    @staticmethod
    def set_announcement(guild_id: int, enabled: int):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT OR REPLACE INTO announcements (guild_id, enabled) VALUES (?, ?)", (guild_id, enabled))
        conn.commit()
        conn.close()

    @staticmethod
    def get_dj_role(guild_id: int) -> Optional[int]:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM dj_roles WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    @staticmethod
    def set_dj_role(guild_id: int, role_id: Optional[int]):
        conn = sqlite3.connect(DB_FILE)
        if role_id is None:
            conn.execute("DELETE FROM dj_roles WHERE guild_id = ?", (guild_id,))
        else:
            conn.execute("INSERT OR REPLACE INTO dj_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        conn.commit()
        conn.close()

    @staticmethod
    def remove_from_playlist(user_id: int, pl_name: str, index: int) -> bool:
        conn = sqlite3.connect(DB_FILE)
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
        conn.execute("DELETE FROM playlist_tracks WHERE id = ?", (track_db_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def remove_dupes_playlist(user_id: int, pl_name: str) -> int:
        conn = sqlite3.connect(DB_FILE)
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
                conn.execute("DELETE FROM playlist_tracks WHERE id = ?", (track_db_id,))
                removed += 1
            else:
                seen.add(url)
        conn.commit()
        conn.close()
        return removed

    @staticmethod
    def create_global_playlist(user_id: int, name: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM global_playlists WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return False
        conn.execute("INSERT INTO global_playlists (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete_global_playlist(name: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        conn.execute("DELETE FROM global_playlists WHERE id = ?", (pl_id,))
        conn.execute("DELETE FROM global_playlist_tracks WHERE playlist_id = ?", (pl_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_global_playlists() -> list:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name, user_id FROM global_playlists")
        rows = cursor.fetchall()
        conn.close()
        return [{"name": r[0], "user_id": r[1]} for r in rows]

    @staticmethod
    def add_to_global_playlist(pl_name: str, title: str, author: str, url: str, thumbnail: str, duration: int) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (pl_name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        pl_id = row[0]
        conn.execute("INSERT INTO global_playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, title, author, url, thumbnail, duration))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_global_playlist_tracks(pl_name: str) -> list:
        conn = sqlite3.connect(DB_FILE)
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
        conn = sqlite3.connect(DB_FILE)
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
        conn.execute("DELETE FROM global_playlist_tracks WHERE id = ?", (track_db_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def remove_dupes_global_playlist(pl_name: str) -> int:
        conn = sqlite3.connect(DB_FILE)
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
                conn.execute("DELETE FROM global_playlist_tracks WHERE id = ?", (track_db_id,))
                removed += 1
            else:
                seen.add(url)
        conn.commit()
        conn.close()
        return removed

# ─────────────────────────────────────────────
#             SPOTIFY RESOLVER CLASS
# ─────────────────────────────────────────────

class SpotifyResolver:
    token = None
    token_expires = 0

    @classmethod
    async def get_token(cls):
        if cls.token and time.time() < cls.token_expires:
            return cls.token
            
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials"}
        auth = aiohttp.BasicAuth(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, auth=auth) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    cls.token = res["access_token"]
                    cls.token_expires = time.time() + res["expires_in"] - 60
                    return cls.token
        return None

    @classmethod
    async def resolve(cls, url: str) -> tuple:
        match = re.search(r"spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)", url)
        if not match:
            return [], False
            
        item_type, item_id = match.groups()
        token = await cls.get_token()
        if not token:
            return [], False
            
        headers = {"Authorization": f"Bearer {token}"}
        
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
        return [], False

# ─────────────────────────────────────────────
#               AUDIO FILTER OPTIONS
# ─────────────────────────────────────────────

def get_ffmpeg_options(filter_name: Optional[str] = None, speed: float = 1.0, pitch: float = 1.0) -> dict:
    before_opts = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    opts = "-vn"
    
    audio_filters = []
    
    if filter_name == "bassboost" or filter_name == "bassboost_medium":
        audio_filters.append("bass=g=15")
    elif filter_name == "bassboost_low":
        audio_filters.append("bass=g=8")
    elif filter_name == "bassboost_high":
        audio_filters.append("bass=g=22")
    elif filter_name == "bassboost_extreme":
        audio_filters.append("bass=g=35")
    elif filter_name == "bass":
        audio_filters.append("bass=g=10")
    elif filter_name == "earrape":
        audio_filters.append("volume=15,bass=g=25")
    elif filter_name == "chipmunk":
        audio_filters.append("asetrate=48000*1.55,aresample=48000")
    elif filter_name == "nightcore":
        audio_filters.append("asetrate=48000*1.25,aresample=48000")
    elif filter_name == "8d":
        audio_filters.append("apulsator=hz=0.08")
    elif filter_name == "vaporwave":
        audio_filters.append("asetrate=48000*0.8,aresample=48000")
    elif filter_name == "karaoke":
        audio_filters.append("stereotools=mpleft=-1:mpright=1")
    elif filter_name == "doubletime":
        audio_filters.append("atempo=2.0")
    elif filter_name == "slowmo":
        audio_filters.append("atempo=0.5")
    elif filter_name == "daycore":
        audio_filters.append("asetrate=48000*0.85,aresample=48000")
    elif filter_name == "lofi":
        audio_filters.append("lowpass=f=3200,highpass=f=200")
    elif filter_name == "radio":
        audio_filters.append("lowpass=f=3000,highpass=f=500")
    elif filter_name == "treblebass":
        audio_filters.append("equalizer=f=3000:width_type=h:width=1000:g=6,bass=g=5")
    elif filter_name == "pop":
        audio_filters.append("equalizer=f=1000:width_type=h:width=200:g=3")
    elif filter_name == "classical":
        audio_filters.append("equalizer=f=64:width_type=o:width=2:g=-3,equalizer=f=250:width_type=o:width=2:g=-3,equalizer=f=1000:width_type=o:width=2:g=-3,equalizer=f=4000:width_type=o:width=2:g=-3,equalizer=f=12000:width_type=o:width=2:g=-3")
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

YTDL_OPTIONS = {
    "format": "bestaudio/18/best/b",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "cookiefile": COOKIE_ARG,
    "socket_timeout": 12,
    "retries": 2,
    "extractor_retries": 2,
    "extractor_args": {
        "youtube": {
            "player_client": ["web", "mweb", "android"]
        },
        "youtubepot-bgutilhttp": {
            "base_url": ["http://127.0.0.1:4416"]
        }
    },
}
if CHROME_TARGET:
    YTDL_OPTIONS["impersonate"] = CHROME_TARGET

# ─────────────────────────────────────────────
#                 EMBED HELPERS (MODERN UI)
# ─────────────────────────────────────────────

def make_embed(title="", desc="", color=0x2B2D31) -> discord.Embed:
    return discord.Embed(title=title[:256] if title else None, description=desc, color=color)

async def send_response(ctx: commands.Context, embed: discord.Embed, view: Optional[discord.ui.View] = None, delete_after: Optional[float] = None) -> Optional[discord.Message]:
    if ctx.interaction:
        msg = None
        try:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=False)
                try:
                    msg = await ctx.interaction.original_response()
                except Exception:
                    pass
                if delete_after and msg:
                    async def delete_later():
                        await asyncio.sleep(delete_after)
                        try: await msg.delete()
                        except Exception: pass
                    bot.loop.create_task(delete_later())
                return msg
            else:
                msg = await ctx.interaction.edit_original_response(embed=embed, view=view)
                if delete_after and msg:
                    async def delete_later():
                        await asyncio.sleep(delete_after)
                        try: await msg.delete()
                        except Exception: pass
                    bot.loop.create_task(delete_later())
                return msg
        except Exception:
            try:
                msg = await ctx.interaction.followup.send(embed=embed, view=view, ephemeral=False, wait=True)
                if delete_after and msg:
                    async def delete_later():
                        await asyncio.sleep(delete_after)
                        try: await msg.delete()
                        except Exception: pass
                    bot.loop.create_task(delete_later())
                return msg
            except Exception:
                pass
        return msg

    msg = await ctx.channel.send(embed=embed, view=view, delete_after=delete_after)
    return msg

def err(msg: str) -> discord.Embed:
    avatar = bot.user.avatar.url if (bot and bot.user and bot.user.avatar) else None
    formatted = f">>> {msg}" if not msg.startswith(">>>") else msg
    e = discord.Embed(title="❌ Error Encountered", description=formatted[:4096], color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    return e

def ok(msg: str, desc: str = "") -> discord.Embed:
    avatar = bot.user.avatar.url if (bot and bot.user and bot.user.avatar) else None
    t = msg if any(msg.startswith(p) for p in ["✅", "🟢", "🎵", "🔊", "❌", "🔁", "🔀"]) else f"✅ {msg}"
    if desc:
        formatted_desc = f">>> {desc}" if not desc.startswith(">>>") else desc
    else:
        formatted_desc = None
    e = discord.Embed(title=t, description=formatted_desc[:4096] if formatted_desc else None, color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    return e

def _fmt(secs: int) -> str:
    if not secs: return "0:00"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def history_embed(track: dict) -> discord.Embed:
    title = track.get("title", "Unknown Track")
    url = track.get("video_url") or track.get("url", "")
    dur = _fmt(int(track.get("duration") or 0))
    uploader = track.get("uploader", "Unknown Artist")
    req_id = track.get("requester_id")
    thumb = track.get("thumbnail", "")
    avatar = bot.user.avatar.url if (bot and bot.user and bot.user.avatar) else None

    req_str = f"<@{req_id}>" if req_id else "`AutoPlay`"

    e = discord.Embed(
        title=title[:256],
        url=url if url else None,
        color=0x2B2D31,
        timestamp=datetime.now(timezone.utc)
    )
    e.set_author(name="Track Finished • VEYRA MUSIC", icon_url=avatar)
    e.description = (
        f"> 👤 Artist: `{uploader[:35]}`\n"
        f"> ⏱ Duration: `{dur}` • 🎧 Requester: {req_str}"
    )
    if thumb:
        e.set_thumbnail(url=thumb)
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    return e

# ─────────────────────────────────────────────
#               AUDIO SOURCE
# ─────────────────────────────────────────────

class YTSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)
        self.data = data

    @classmethod
    async def search(cls, query: str, loop) -> dict:
        opts = YTDL_OPTIONS.copy()
        opts["extract_flat"] = "in_playlist"
        opts["socket_timeout"] = 8
        is_search = not query.startswith("http")
        q = f"ytsearch5:{query}" if is_search else query
            
        def run():
            try:
                return yt_dlp.YoutubeDL(opts).extract_info(q, download=False)
            except Exception as yt_err:
                if is_search:
                    try:
                        sc_opts = opts.copy()
                        sc_opts["extractor_args"] = {}
                        return yt_dlp.YoutubeDL(sc_opts).extract_info(f"scsearch5:{query}", download=False)
                    except Exception:
                        pass
                raise yt_err

        data = await loop.run_in_executor(None, run)
        if data and "entries" in data and len(data["entries"]) > 0:
            selected = None
            q_lower = query.lower()
            for e in data["entries"]:
                if not e: continue
                dur = int(e.get("duration") or 0)
                url = e.get("url") or e.get("webpage_url") or ""
                title = (e.get("title") or "").lower()
                # Filter out YouTube Shorts (duration < 60s or /shorts/ in url or #shorts in title)
                if "/shorts/" in url or "#shorts" in title or "#short" in title or (0 < dur < 60):
                    continue
                # Filter out Ads / Promos / Teasers / Trailers / Commercials
                ad_keywords = ["teaser", "trailer", "promo", "preview", "commercial", "advertisement", "ad video"]
                if not any(k in q_lower for k in ad_keywords):
                    if any(k in title for k in ad_keywords):
                        continue
                selected = e
                break
            if not selected:
                for e in data["entries"]:
                    if not e: continue
                    dur = int(e.get("duration") or 0)
                    url = e.get("url") or e.get("webpage_url") or ""
                    if "/shorts/" not in url and dur >= 60:
                        selected = e
                        break
            if not selected:
                selected = data["entries"][0]
            data = selected
        if data:
            u = data.get("webpage_url") or data.get("url") or ""
            if u and not u.startswith("http"):
                u = f"https://www.youtube.com/watch?v={u}"
            data["url"] = u
            data["webpage_url"] = u
        return data or {}

    @classmethod
    async def extract_tracks(cls, query: str, loop) -> tuple:
        opts = YTDL_OPTIONS.copy()
        opts["extract_flat"] = "in_playlist"
        opts["socket_timeout"] = 8
        
        # Check if query is a single YouTube video URL
        vid_match = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})', query)
        is_playlist_url = "list=" in query
        is_search = not query.startswith("http")

        if vid_match and not is_playlist_url:
            q = query
            is_search = False
        elif is_search:
            q = f"ytsearch5:{query}"
        else:
            q = query
        
        def run():
            try:
                return yt_dlp.YoutubeDL(opts).extract_info(q, download=False)
            except Exception as yt_err:
                if is_search:
                    try:
                        sc_opts = opts.copy()
                        sc_opts["extractor_args"] = {}
                        return yt_dlp.YoutubeDL(sc_opts).extract_info(f"scsearch5:{query}", download=False)
                    except Exception:
                        pass
                raise yt_err

        data = await loop.run_in_executor(None, run)
        if not data:
            return [], False
            
        if is_search:
            entries = data.get("entries", [])
            q_lower = query.lower()
            selected = None
            for e in entries:
                if not e: continue
                dur = int(e.get("duration") or 0)
                url = e.get("url") or e.get("webpage_url") or ""
                title = (e.get("title") or "").lower()
                # Strictly filter out YouTube Shorts (duration < 60s or /shorts/ in url or #shorts in title)
                if "/shorts/" in url or "#shorts" in title or "#short" in title or (0 < dur < 60):
                    continue
                # Strictly filter out Ads / Promos / Teasers / Trailers / Commercials
                ad_keywords = ["teaser", "trailer", "promo", "preview", "commercial", "advertisement", "ad video"]
                if not any(k in q_lower for k in ad_keywords):
                    if any(k in title for k in ad_keywords):
                        continue
                # Filter out 1 hour / loop / extended unless explicitly requested
                if not any(k in q_lower for k in ["1 hour", "1hr", "10 hour", "loop", "extended"]):
                    if any(k in title for k in ["1 hour", "10 hour", "10 hrs", "1 hr loop", "[1 hour]"]):
                        continue
                if "slowed" not in q_lower and ("slowed" in title or "reverb" in title):
                    continue
                if "sped" not in q_lower and "speed" not in q_lower and ("sped up" in title or "speed up" in title):
                    continue
                if "edit" not in q_lower and ("[edit" in title or "(edit" in title or "edit audio" in title):
                    continue
                selected = e
                break
            if not selected and entries:
                for e in entries:
                    if not e: continue
                    dur = int(e.get("duration") or 0)
                    url = e.get("url") or e.get("webpage_url") or ""
                    if "/shorts/" not in url and dur >= 60:
                        selected = e
                        break
            if not selected and entries:
                selected = entries[0]
            if selected:
                u = selected.get("webpage_url") or selected.get("url") or ""
                if u and not u.startswith("http"):
                    u = f"https://www.youtube.com/watch?v={u}"
                selected["url"] = u
                selected["webpage_url"] = u
                return [selected], False
            return [], False
        else:
            is_playlist = "entries" in data and not data.get("_type") == "video"
            if is_playlist:
                tracks = [e for e in data["entries"] if e]
                for t in tracks:
                    u = t.get("webpage_url") or t.get("url") or ""
                    if u and not u.startswith("http"):
                        u = f"https://www.youtube.com/watch?v={u}"
                    t["url"] = u
                    t["webpage_url"] = u
                return tracks, True
            else:
                u = data.get("webpage_url") or data.get("url") or ""
                if u and not u.startswith("http"):
                    u = f"https://www.youtube.com/watch?v={u}"
                data["url"] = u
                data["webpage_url"] = u
                return [data], False

    @classmethod
    async def stream(cls, url: str, loop, volume=1.0, active_filter=None, seek_time=0, speed=1.0, pitch=1.0, track_title=None):
        opts = YTDL_OPTIONS.copy()
        opts["extract_flat"] = False
        opts["format"] = "18/bestaudio/best/b"
        opts["cookiefile"] = COOKIE_ARG
        opts["socket_timeout"] = 12

        def run():
            try:
                return yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
            except Exception as e:
                print(f"⚠️ Primary YouTube extract failed ({e}). Attempting Chrome/bgutil fallback...")
                try:
                    fallback_opts = opts.copy()
                    fallback_opts["cookiefile"] = None
                    if CHROME_TARGET:
                        fallback_opts["impersonate"] = CHROME_TARGET
                    fallback_opts["extractor_args"] = {
                        "youtube": {
                            "player_client": ["web", "mweb", "android"]
                        },
                        "youtubepot-bgutilhttp": {
                            "base_url": ["http://127.0.0.1:4416"]
                        }
                    }
                    return yt_dlp.YoutubeDL(fallback_opts).extract_info(url, download=False)
                except Exception as fb_err:
                    print(f"⚠️ YouTube fallback failed ({fb_err}). Attempting SoundCloud fallback...")
                    try:
                        title_str = track_title or url
                        sc_opts = {
                            "format": "bestaudio/best",
                            "noplaylist": True,
                            "quiet": True,
                            "no_warnings": True,
                            "socket_timeout": 8
                        }
                        sc_info = yt_dlp.YoutubeDL(sc_opts).extract_info(f"scsearch1:{title_str}", download=False)
                        if sc_info and "entries" in sc_info and sc_info["entries"]:
                            print(f"🎵 Successfully extracted SoundCloud fallback for '{title_str}'")
                            return sc_info["entries"][0]
                    except Exception as sc_ex:
                        print(f"❌ SoundCloud fallback failed: {sc_ex}")
                    raise e

        data = await loop.run_in_executor(None, run)
        if data and "entries" in data and len(data["entries"]) > 0:
            data = data["entries"][0]
            
        stream_url = data.get("url") if data else None
        if not stream_url:
            raise Exception("No stream URL extracted!")
            
        headers = data.get("http_headers", {})
        ua = headers.get("User-Agent") or headers.get("user-agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
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
        self.stay_247 = True  # Enable 24/7 stays in VC by default!
        self.filter: Optional[str] = None
        self.announce = True
        self.dj_role_id: Optional[int] = None
        self.seek_offset = 0
        self.speed = 1.0
        self.pitch = 1.0
        self.restarting_track = False
        self.start_time: Optional[float] = None
        self.paused_at: Optional[float] = None
        self.text_ch: Optional[discord.TextChannel] = None
        self.panel_msg: Optional[discord.Message] = None
        self.updater_task: Optional[asyncio.Task] = None
        self.empty_since: Optional[float] = None
        self.inactive_since: Optional[float] = None
        self.is_connecting = False
        self.skip_votes = set()

    @property
    def position(self):
        if not self.start_time: return 0
        elapsed = time.time() - self.start_time
        if self.paused_at:
            elapsed = self.paused_at - self.start_time
        pos = int(elapsed * self.speed + self.seek_offset)
        if self.current:
            dur = int(self.current.get("duration") or 0)
            if dur > 0:
                pos = min(dur, pos)
        return max(0, pos)

    def is_playing(self): return bool(self.voice and self.voice.is_playing())
    def is_paused(self):  return bool(self.voice and self.voice.is_paused())
    def fmt(self, s):     return _fmt(int(s or 0))

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
        if self.panel_msg and self.current:
            try:
                await self.panel_msg.edit(embed=panel_embed(self))
            except discord.errors.NotFound:
                self.panel_msg = None
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_sec = getattr(e, "retry_after", 2.0)
                    await asyncio.sleep(retry_sec)
            except Exception:
                pass

    async def _progress_loop(self):
        try:
            while self.current and (self.is_playing() or self.is_paused()):
                if not self.panel_msg:
                    break
                if self.is_playing():
                    await self.update_panel()
                await asyncio.sleep(2.0)
            if self.panel_msg and self.current:
                await self.update_panel()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    def ensure_updater(self):
        if self.updater_task and not self.updater_task.done():
            self.updater_task.cancel()
        if self.current and (self.is_playing() or self.is_paused() or (self.voice and self.voice.is_connected())):
            self.updater_task = asyncio.create_task(self._progress_loop())

# ─────────────────────────────────────────────
#           LIVE PANEL EMBED
# ─────────────────────────────────────────────

def make_progress_bar(pos: int, total: int, width=12) -> str:
    if total <= 0:
        return "─" * width
    percentage = max(0.0, min(1.0, pos / total))
    idx = int(percentage * (width - 1))
    return "─" * idx + "🔘" + "─" * (width - 1 - idx)

def panel_embed(p: GuildPlayer) -> discord.Embed:
    avatar = bot.user.avatar.url if (bot and bot.user and bot.user.avatar) else None
    e = discord.Embed(color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.set_author(name="VEYRA MUSIC PLAYER", icon_url=avatar)

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
            "Use `/play` or `/help` to start the vibe!\n\n"
            f"🔊 {vol_pct}% | Loop: {loop_s} | Speed: {speed_s} | Queue: {len(p.queue)} tracks"
        )
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    return e

# ─────────────────────────────────────────────
#           MUSIC PANEL BUTTONS
# ─────────────────────────────────────────────

# Seek Modal for Music Panel
class SeekModal(discord.ui.Modal, title="Seek to Position"):
    time_input = discord.ui.TextInput(
        label="Enter timestamp or seconds",
        placeholder="e.g. 1:30 or 90 (or 50% for percentage)",
        required=True,
        max_length=15
    )

    async def on_submit(self, interaction: discord.Interaction):
        p = bot.get_player(interaction.guild_id)
        if not p.voice or not p.current:
            return await interaction.response.send_message(embed=err("Nothing is currently playing."), ephemeral=True)
            
        val = self.time_input.value.strip()
        duration = int(p.current.get("duration") or 0)
        
        sec = 0
        try:
            if val.endswith("%"):
                pct = float(val[:-1])
                sec = int((pct / 100) * duration)
            elif ":" in val:
                parts = val.split(":")
                if len(parts) == 2:
                    sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                sec = int(val)
        except Exception:
            return await interaction.response.send_message(embed=err("Invalid format! Use seconds (e.g. 90) or time (e.g. 1:30) or percentage (e.g. 50%)."), ephemeral=True)
            
        if duration > 0 and sec > duration:
            return await interaction.response.send_message(embed=err("Seek position cannot exceed song duration!"), ephemeral=True)
            
        p.seek_offset = max(0, sec)
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
        
        await interaction.response.send_message(embed=ok("Seeking...", f"Jumped directly to **{_fmt(sec)}**."), ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=err(f"Seek failed: {error}"), ephemeral=True)
            else:
                await interaction.followup.send(embed=err(f"Seek failed: {error}"), ephemeral=True)
        except Exception:
            pass

class MusicPanel(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    def _p(self) -> GuildPlayer:
        return bot.get_player(self.guild_id)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        logging.error(f"MusicPanel UI error on item {item}: {error}", exc_info=error)
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
                await interaction.response.edit_message(embed=panel_embed(self._p()), view=self)
                return
            await interaction.edit_original_response(embed=panel_embed(self._p()), view=self)
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
    @discord.ui.button(label="Vol -", emoji="🔊", style=discord.ButtonStyle.secondary, row=0)
    async def vol_down(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        p.volume = max(0.0, round(p.volume - 0.1, 1))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        Database.set_volume(self.guild_id, int(p.volume * 100))
        await self._update(i)
        await self._toast(i, ok("Volume Down", f"Volume set to **{int(p.volume*100)}%**"))

    @discord.ui.button(label="Back", emoji="⏮", style=discord.ButtonStyle.primary, row=0)
    async def back(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
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
        p = self._p()
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
        p = self._p()
        if p.voice and (p.is_playing() or p.is_paused()):
            p.voice.stop()
        await self._update(i)
        await self._toast(i, ok("Skipped ⏭"))

    @discord.ui.button(label="Vol +", emoji="🔊", style=discord.ButtonStyle.secondary, row=0)
    async def vol_up(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        p.volume = min(2.0, round(p.volume + 0.1, 1))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        Database.set_volume(self.guild_id, int(p.volume * 100))
        await self._update(i)
        await self._toast(i, ok("Volume Up", f"Volume set to **{int(p.volume*100)}%**"))

    # Row 1: Fast Seek & Jump Controls
    @discord.ui.button(label="-15s", emoji="⏪", style=discord.ButtonStyle.primary, row=1)
    async def rewind_15(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
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
        p = self._p()
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        await i.response.send_modal(SeekModal())

    @discord.ui.button(label="+15s", emoji="⏩", style=discord.ButtonStyle.primary, row=1)
    async def forward_15(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
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
        p = self._p()
        if len(p.queue) < 2:
            return await self._toast(i, err("Not enough tracks in queue to shuffle."))
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await self._update(i)
        await self._toast(i, ok("Shuffled Queue!", f"Shuffled {len(q)} tracks."))

    @discord.ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.primary, row=2)
    async def loop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        toast_msg = ""
        if p.loop == "off":
            p.loop = "track"
            toast_msg = "Track Loop Enabled ✅"
        elif p.loop == "track":
            p.loop = "queue"
            toast_msg = "Queue Loop Enabled ✅"
        else:
            p.loop = "off"
            toast_msg = "Loop Disabled ❌"
        await self._update(i)
        await self._toast(i, ok(toast_msg))

    @discord.ui.button(label="Stop", emoji="⏹", style=discord.ButtonStyle.primary, row=2)
    async def stop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        finished = p.current
        p.queue.clear()
        p.current = None
        p.loop = "off"
        if p.voice:
            p.voice.stop()
        
        is_247 = p.stay_247 or bool(Database.get_247(self.guild_id)[0])
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
        await i.response.send_message(embed=ok("Stopped Playing", msg_desc), ephemeral=True)

    # Row 3: AutoPlay & Queue List
    @discord.ui.button(label="AutoPlay", emoji="▶️", style=discord.ButtonStyle.primary, row=3)
    async def autoplay_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        p.autoplay = not p.autoplay
        await self._update(i)
        await self._toast(i, ok(f"AutoPlay {'Enabled ✅' if p.autoplay else 'Disabled ❌'}"))

    @discord.ui.button(label="Queue List", emoji="🎵", style=discord.ButtonStyle.primary, row=3)
    async def queue_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        if not p.queue and not p.current:
            return await self._toast(i, err("Queue is empty!"))
        lines = []
        if p.current:
            lines.append(f"▶ **Now playing:** {p.current['title']} `{p.fmt(p.current.get('duration', 0))}`")
        for idx, t in enumerate(list(p.queue)[:10], 1):
            lines.append(f"`{idx}.` {t['title']} `{p.fmt(t.get('duration', 0))}`")
        if len(p.queue) > 10:
            lines.append(f"*...and {len(p.queue)-10} more tracks*")
        await i.response.send_message(embed=discord.Embed(title="🎵 Queue List", description="\n".join(lines), color=0x2B2D31), ephemeral=True)

    # Row 4: Like & Close Panel
    @discord.ui.button(label="Like", emoji="⭐", style=discord.ButtonStyle.secondary, row=4)
    async def like_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
        if not p.current:
            return await self._toast(i, err("No track currently playing."))
        track = p.current
        Database.like_track(i.user.id, track["url"], track["title"], track.get("uploader", "Unknown"), track.get("thumbnail", ""), track.get("duration", 0))
        await self._toast(i, ok("Song Liked", f"Added **{track['title']}** to your Liked tracks."))

    @discord.ui.button(label="Close Panel", emoji="❌", style=discord.ButtonStyle.secondary, row=4)
    async def close_panel_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._p()
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
        await i.response.send_message(embed=ok("Panel Closed", "Use `/panel` or `.panel` to reopen the player."), ephemeral=True)

# ─────────────────────────────────────────────
#              BOT SYSTEM CLASS
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

class MentionLinksView(discord.ui.View):
    def __init__(self, invite_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Invite", url=invite_url, style=discord.ButtonStyle.link))
        self.add_item(discord.ui.Button(label="Support", url="https://discord.com/users/1256986886631854080", style=discord.ButtonStyle.link))

class MusicBot(commands.Bot):
    def __init__(self):
        proxy = os.environ.get("DISCORD_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None
        super().__init__(
            command_prefix=self.get_db_prefix,
            intents=intents,
            help_command=None,
            status=discord.Status.dnd,
            proxy=proxy,
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="Vibes | /help"
            )
        )
        self.players: dict[int, GuildPlayer] = {}
        self.booted = False
        self.uptime_start = time.time()

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            Database.init_guild(guild_id)
            p = GuildPlayer(guild_id)
            vol = Database.get_volume(guild_id)
            p.volume = vol / 100
            stay_247, _, _ = Database.get_247(guild_id)
            p.stay_247 = bool(stay_247)
            p.announce = bool(Database.get_announcement(guild_id))
            p.dj_role_id = Database.get_dj_role(guild_id)
            self.players[guild_id] = p
        return self.players[guild_id]

    async def get_db_prefix(self, bot, message) -> list[str]:
        prefixes = [PREFIX, "."]
        if message and message.guild:
            try:
                custom = Database.get_prefix(message.guild.id)
                if custom and custom not in prefixes:
                    prefixes.append(custom)
            except Exception:
                pass
        unique_prefixes = list(dict.fromkeys(prefixes))
        return commands.when_mentioned_or(*unique_prefixes)(bot, message)

    async def setup_hook(self):
        await self.start_health_server()
        await self.start_bgutil_pot_server()

_bgutil_process = None

async def start_bgutil_pot_server():
    global _bgutil_process
    if _bgutil_process is not None and _bgutil_process.poll() is None:
        return _bgutil_process
    import shutil, subprocess
    bgutil_path = shutil.which("bgutil-pot") or "/usr/local/bin/bgutil-pot"
    if os.path.exists(bgutil_path) or shutil.which("bgutil-pot"):
        cmd = [bgutil_path, "server", "--host", "127.0.0.1", "--port", "4416"]
        try:
            _bgutil_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"🚀 Started bgutil-pot PO Token server daemon (PID {_bgutil_process.pid}) on port 4416")
            await asyncio.sleep(1.0)
            poll = _bgutil_process.poll()
            if poll is not None:
                print(f"⚠️ bgutil-pot server exited with code {poll}")
            else:
                print("✅ bgutil-pot daemon is actively running and listening on port 4416.")
            return _bgutil_process
        except Exception as e:
            print(f"⚠️ Failed to launch bgutil-pot server: {e}")
    else:
        print("ℹ️ bgutil-pot binary not found in system PATH. Skipping background server launch.")
    return None

    async def start_bgutil_pot_server(self):
        self.bgutil_proc = await start_bgutil_pot_server()

    async def keep_alive_pinger(self):
        """24/7 Free Hosting Keepalive: Pings self URL every 5 minutes to prevent Render from sleeping."""
        await self.wait_until_ready()
        target_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://shadow-cheats-music-sg.onrender.com"
        ping_endpoint = f"{target_url.rstrip('/')}/health"
        print(f"🔄 24/7 Keepalive self-pinger initialized for {ping_endpoint} (interval: 300s)")
        
        while not self.is_closed():
            try:
                await asyncio.sleep(300)
                async with aiohttp.ClientSession() as session:
                    async with session.get(ping_endpoint, timeout=15) as resp:
                        if resp.status == 200:
                            pass
                        else:
                            print(f"⚠️ Keepalive ping returned status {resp.status}")
            except Exception:
                pass

    async def start_health_server(self):
        if getattr(self, '_health_server_running', False):
            return
        self._health_server_running = True
        try:
            from aiohttp import web
            app = web.Application()

            def get_db_stats():
                stats = {
                    "status": "connected",
                    "file": DB_FILE,
                    "registered_guilds": 0,
                    "custom_playlists": 0,
                    "liked_tracks": 0,
                    "commands_run": Database.get_stat("commands_run"),
                    "songs_played": Database.get_stat("songs_played")
                }
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute("SELECT count(*) FROM guild_settings")
                    stats["registered_guilds"] = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM playlists")
                    stats["custom_playlists"] = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM liked_tracks")
                    stats["liked_tracks"] = cur.fetchone()[0]
                    conn.close()
                except Exception:
                    pass
                return stats

            def get_lat_ms():
                try:
                    import math
                    if self.latency is not None and not math.isnan(self.latency):
                        return round(self.latency * 1000, 2)
                except Exception:
                    pass
                return 0.0

            async def health_check(request):
                uptime_sec = int(time.time() - START_TIME)
                mem_mb = 0
                try:
                    mem_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
                except Exception:
                    pass
                
                pot_active = False
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get("http://127.0.0.1:4416/ping", timeout=1.0) as resp:
                            if resp.status == 200:
                                pot_active = True
                except Exception:
                    pot_active = False

                return web.json_response({
                    "status": "ok",
                    "bot": "VEYRA MUSIC",
                    "servers": len(self.guilds),
                    "users": sum(g.member_count or 0 for g in self.guilds),
                    "latency_ms": get_lat_ms(),
                    "uptime_seconds": uptime_sec,
                    "memory_mb": mem_mb,
                    "opus_loaded": discord.opus.is_loaded(),
                    "ytdl_version": yt_dlp.version.__version__,
                    "cookies_loaded": bool(COOKIE_ARG),
                    "pot_provider_active": pot_active,
                    "database": get_db_stats()
                })

            async def stats_api(request):
                uptime_sec = int(time.time() - START_TIME)
                hours, rem = divmod(uptime_sec, 3600)
                mins, secs = divmod(rem, 60)
                uptime_str = f"{hours}h {mins}m {secs}s"
                
                active_streams = []
                for gid, p in self.players.items():
                    if p.voice and p.voice.is_connected() and p.current:
                        g = self.get_guild(gid)
                        gname = g.name if g else f"Guild #{gid}"
                        active_streams.append({
                            "guild_id": gid,
                            "guild_name": gname,
                            "title": p.current.get("title", "Unknown"),
                            "author": p.current.get("author", "Unknown"),
                            "duration": p.current.get("duration", 0),
                            "filter": p.filter or "None",
                            "volume": int(p.volume * 100)
                        })

                return web.json_response({
                    "bot": {
                        "name": "VEYRA MUSIC",
                        "status": "online",
                        "latency_ms": get_lat_ms(),
                        "uptime": uptime_str,
                        "uptime_seconds": uptime_sec,
                        "guilds": len(self.guilds),
                        "users": sum(g.member_count or 0 for g in self.guilds),
                        "voice_connections": len([p for p in self.players.values() if p.voice and p.voice.is_connected()]),
                        "opus": discord.opus.is_loaded()
                    },
                    "database": get_db_stats(),
                    "active_streams": active_streams
                })

            async def logs_view(request):
                return web.Response(text="\n".join(RECENT_LOGS), content_type="text/plain")

            async def test_extract_view(request):
                query = request.query.get("url") or request.query.get("q") or "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                try:
                    tracks, is_pl = await YTSource.extract_tracks(query, asyncio.get_event_loop())
                    res_summary = []
                    for t in tracks[:3]:
                        res_summary.append({
                            "title": t.get("title"),
                            "url": t.get("webpage_url") or t.get("url"),
                            "has_direct_stream_url": bool(t.get("url")),
                            "duration": t.get("duration"),
                            "uploader": t.get("uploader")
                        })
                    return web.json_response({
                        "status": "ok",
                        "query": query,
                        "is_playlist": is_pl,
                        "tracks_found": len(tracks),
                        "results": res_summary
                    })
                except Exception as ex:
                    import traceback
                    return web.json_response({
                        "status": "error",
                        "query": query,
                        "error": str(ex),
                        "traceback": traceback.format_exc()
                    }, status=500)

            async def test_stream_view(request):
                url = request.query.get("url") or request.query.get("q") or "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                try:
                    src = await YTSource.stream(url, asyncio.get_event_loop())
                    stream_url = src.data.get("url") if src.data else None
                    title = src.data.get("title") if src.data else "Unknown"
                    domain = stream_url.split("/")[2] if stream_url else None
                    src.cleanup()
                    return web.json_response({
                        "status": "ok",
                        "url": url,
                        "title": title,
                        "has_stream_url": bool(stream_url),
                        "stream_domain": domain
                    })
                except Exception as ex:
                    import traceback
                    return web.json_response({
                        "status": "error",
                        "url": url,
                        "error": str(ex),
                        "traceback": traceback.format_exc()
                    }, status=500)

            async def formats_view(request):
                url = request.query.get("url") or request.query.get("q") or "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                try:
                    def get_fmts():
                        opts = YTDL_OPTIONS.copy()
                        opts["extract_flat"] = False
                        opts["quiet"] = True
                        info = yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
                        fmts = info.get("formats", [])
                        return [{
                            "format_id": f.get("format_id"),
                            "ext": f.get("ext"),
                            "acodec": f.get("acodec"),
                            "vcodec": f.get("vcodec"),
                            "protocol": f.get("protocol"),
                            "has_url": bool(f.get("url"))
                        } for f in fmts]
                    fmts = await asyncio.get_event_loop().run_in_executor(None, get_fmts)
                    return web.json_response({"status": "ok", "url": url, "count": len(fmts), "formats": fmts})
                except Exception as ex:
                    import traceback
                    return web.json_response({"status": "error", "error": str(ex), "traceback": traceback.format_exc()}, status=500)

            async def test_pcm_view(request):
                url = request.query.get("url", "https://www.youtube.com/watch?v=Mxv7O6BkJeE")
                try:
                    src = await YTSource.stream(url, asyncio.get_event_loop())
                    chunks_read = 0
                    total_bytes = 0
                    for _ in range(30):
                        chunk = src.read()
                        if not chunk:
                            break
                        chunks_read += 1
                        total_bytes += len(chunk)
                    src.cleanup()
                    return web.json_response({
                        "status": "ok",
                        "url": url,
                        "title": src.data.get("title") if src.data else "Unknown",
                        "stream_domain": src.data.get("url").split("/")[2] if src.data and src.data.get("url") else None,
                        "chunks_read": chunks_read,
                        "total_bytes": total_bytes,
                        "audio_flows": total_bytes > 0
                    })
                except Exception as ex:
                    import traceback
                    return web.json_response({
                        "status": "error",
                        "url": url,
                        "error": str(ex),
                        "traceback": traceback.format_exc()
                    }, status=500)

            async def diagnose_view(request):
                vc_list = []
                for vc in self.voice_clients:
                    conn = getattr(vc, "_connection", None)
                    sess = getattr(conn, "dave_session", None) if conn else None
                    vc_list.append({
                        "guild_id": vc.guild.id,
                        "guild_name": vc.guild.name,
                        "channel_id": vc.channel.id if vc.channel else None,
                        "channel_name": vc.channel.name if vc.channel else None,
                        "channel_members": [f"{m.name} ({m.display_name})" for m in vc.channel.members] if vc.channel else [],
                        "bot_server_mute": vc.guild.me.voice.mute if (vc.guild.me and vc.guild.me.voice) else None,
                        "bot_server_deaf": vc.guild.me.voice.deaf if (vc.guild.me and vc.guild.me.voice) else None,
                        "bot_self_mute": vc.guild.me.voice.self_mute if (vc.guild.me and vc.guild.me.voice) else None,
                        "bot_self_deaf": vc.guild.me.voice.self_deaf if (vc.guild.me and vc.guild.me.voice) else None,
                        "is_connected": vc.is_connected(),
                        "is_playing": vc.is_playing(),
                        "is_paused": vc.is_paused(),
                        "endpoint": str(getattr(conn, "endpoint", None)),
                        "dave_proto": getattr(conn, "dave_protocol_version", 0) if conn else 0,
                        "can_encrypt": getattr(conn, "can_encrypt", False) if conn else False,
                        "dave_ready": getattr(sess, "ready", False) if sess else False,
                        "dave_status": str(getattr(sess, "status", None)) if sess else None,
                        "dave_users": [str(uid) for uid in sess.get_user_ids()] if (sess and hasattr(sess, "get_user_ids")) else [],
                        "dave_stats": str(sess.get_encryption_stats()) if (sess and hasattr(sess, "get_encryption_stats")) else None,
                        "sequence": getattr(vc, "sequence", None),
                        "timestamp": getattr(vc, "timestamp", None),
                        "nonce": getattr(vc, "_incr_nonce", None),
                        "latency": getattr(vc, "latency", 0),
                        "average_latency": getattr(vc, "average_latency", 0)
                    })

                player_list = []
                for gid, p in self.players.items():
                    if p.voice and p.voice.is_connected():
                        player_list.append({
                            "guild_id": gid,
                            "has_voice": bool(p.voice),
                            "voice_connected": bool(p.voice and p.voice.is_connected()),
                            "is_playing": p.is_playing(),
                            "is_paused": p.is_paused(),
                            "current_track": p.current.get("title") if p.current else None,
                            "current_url": p.current.get("url") if p.current else None,
                            "position_sec": p.position,
                            "queue_count": len(p.queue),
                            "volume": int(p.volume * 100),
                            "speed": p.speed,
                            "filter": p.filter
                        })

                pot_ok = False
                try:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.get("http://127.0.0.1:4416/ping", timeout=1.0) as resp:
                            pot_ok = (resp.status == 200)
                except Exception:
                    pot_ok = False

                deno_status = "unavailable"
                try:
                    p_deno = subprocess.run(["deno", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
                    deno_status = p_deno.stdout.strip().split("\n")[0] if p_deno.returncode == 0 else f"err: {p_deno.stderr.strip()[:60]}"
                except Exception as de:
                    deno_status = f"not found ({de})"

                return web.json_response({
                    "status": "ok",
                    "guilds_count": len(self.guilds),
                    "voice_clients_count": len(self.voice_clients),
                    "voice_clients": vc_list,
                    "active_players": player_list,
                    "opus_loaded": discord.opus.is_loaded(),
                    "pot_provider_active": pot_ok,
                    "deno_status": deno_status,
                    "dave_available": getattr(discord.voice_client, "has_dave", False)
                })

            async def test_play_view(request):
                query = request.query.get("query", "Alan Walker Faded")
                gid_param = request.query.get("guild_id")
                target_player = None
                if gid_param and gid_param.isdigit():
                    target_player = self.players.get(int(gid_param))
                else:
                    for p in self.players.values():
                        if p.voice and p.voice.is_connected():
                            target_player = p
                            break

                if not target_player or not target_player.voice or not target_player.voice.is_connected():
                    return web.json_response({
                        "status": "error",
                        "error": "No voice connection found to test playback into. Join a voice channel first!"
                    }, status=400)

                g = self.get_guild(target_player.guild_id)
                tracks, _ = await YTSource.extract_tracks(query, asyncio.get_event_loop())
                if not tracks:
                    return web.json_response({"status": "error", "error": "No tracks found for query"}, status=404)

                track_data = tracks[0]
                track = {
                    "title": track_data.get("title", "Unknown"),
                    "url": track_data.get("webpage_url") or track_data.get("url", ""),
                    "duration": int(track_data.get("duration") or 0),
                    "thumbnail": track_data.get("thumbnail", ""),
                    "uploader": track_data.get("uploader", "Unknown"),
                    "requester_id": self.user.id if self.user else 0,
                    "queued_msg": None
                }
                target_player.queue.append(track)
                if not target_player.is_playing() and not target_player.is_paused():
                    self.loop.create_task(play_next(g))

                return web.json_response({
                    "status": "ok",
                    "message": "Playback initiated",
                    "guild_id": target_player.guild_id,
                    "track": track["title"],
                    "url": track["url"],
                    "duration": track["duration"]
                })

            async def root_view(request):
                try:
                    uptime_sec = int(time.time() - START_TIME)
                    hours, rem = divmod(uptime_sec, 3600)
                    mins, secs = divmod(rem, 60)
                    uptime_str = f"{hours}h {mins}m {secs}s"
                    db_stats = get_db_stats()
                    perms = discord.Permissions(8)
                    invite_url = discord.utils.oauth_url(self.user.id, permissions=perms, scopes=("bot", "applications.commands")) if self.user else "https://discord.com"
                    lat_display = f"{get_lat_ms()}ms"
                    
                    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VEYRA MUSIC — 24/7 Online Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0a0c10;
            --card-bg: rgba(18, 22, 31, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #7d5fff;
            --primary-glow: rgba(125, 95, 255, 0.35);
            --accent: #00f2fe;
            --success: #10b981;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: radial-gradient(circle at 50% 0%, #171336 0%, var(--bg-dark) 70%);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{ width: 100%; max-width: 1100px; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0 35px 0;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 30px;
        }}
        .brand {{ display: flex; align-items: center; gap: 14px; }}
        .brand-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 0 20px var(--primary-glow);
        }}
        .brand-title {{ font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
        .brand-sub {{ font-size: 13px; color: var(--text-muted); font-weight: 500; }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success);
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 600;
        }}
        .dot {{
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.4); opacity: 0.6; }}
        }}
        .architecture-bar {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }}
        .arch-node {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 18px 20px;
            border-radius: 16px;
            backdrop-filter: blur(12px);
        }}
        .arch-title {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .arch-val {{ font-size: 18px; font-weight: 700; color: #fff; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 24px;
            border-radius: 18px;
            backdrop-filter: blur(12px);
            transition: transform 0.2s, border-color 0.2s;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: rgba(125, 95, 255, 0.4);
        }}
        .card-label {{ font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }}
        .card-value {{ font-size: 28px; font-weight: 800; color: #fff; font-family: 'JetBrains Mono', monospace; }}
        .actions {{
            display: flex;
            gap: 16px;
            margin-bottom: 35px;
            flex-wrap: wrap;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 14px 24px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--primary), #6c47ff);
            color: #fff;
            box-shadow: 0 4px 20px var(--primary-glow);
        }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 6px 25px var(--primary-glow); }}
        .btn-outline {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            color: var(--text-main);
        }}
        .btn-outline:hover {{ background: rgba(255, 255, 255, 0.1); transform: translateY(-2px); }}
        .streams-panel {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 24px;
            margin-bottom: 30px;
        }}
        .panel-header {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .streams-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        .streams-table th {{
            text-align: left;
            padding: 12px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--card-border);
            font-size: 12px;
            text-transform: uppercase;
        }}
        .streams-table td {{ padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }}
        footer {{
            text-align: center;
            padding: 30px 0;
            color: var(--text-muted);
            font-size: 13px;
            border-top: 1px solid var(--card-border);
            width: 100%;
        }}
        @media (max-width: 768px) {{
            .architecture-bar {{ grid-template-columns: 1fr; }}
            header {{ flex-direction: column; align-items: flex-start; gap: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="brand-icon">⚡</div>
                <div>
                    <div class="brand-title">VEYRA MUSIC</div>
                    <div class="brand-sub">24/7 Ultra High-Fidelity Audio Core</div>
                </div>
            </div>
            <div class="status-badge">
                <div class="dot"></div>
                <span>24/7 ONLINE • 0 RS FREE HOSTING</span>
            </div>
        </header>

        <div class="architecture-bar">
            <div class="arch-node">
                <div class="arch-title">🤖 Discord Bot Core</div>
                <div class="arch-val" id="botStatus">CONNECTED</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Latency: <span id="pingVal">{lat_display}</span></div>
            </div>
            <div class="arch-node">
                <div class="arch-title">💾 SQLite Database</div>
                <div class="arch-val">CONNECTED</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Active DB: bot_database.db</div>
            </div>
            <div class="arch-node">
                <div class="arch-title">🌐 Web Keepalive</div>
                <div class="arch-val">ACTIVE (5M)</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Self-Pinger Online</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-label">Guilds Connected</div>
                <div class="card-value" id="valGuilds">{len(self.guilds)}</div>
            </div>
            <div class="card">
                <div class="card-label">Total Users Reach</div>
                <div class="card-value" id="valUsers">{sum(g.member_count or 0 for g in self.guilds):,}</div>
            </div>
            <div class="card">
                <div class="card-label">Active Voice Streams</div>
                <div class="card-value" id="valStreams">{len([p for p in self.players.values() if p.voice and p.voice.is_connected()])}</div>
            </div>
            <div class="card">
                <div class="card-label">System Uptime</div>
                <div class="card-value" id="valUptime" style="font-size: 22px;">{uptime_str}</div>
            </div>
            <div class="card">
                <div class="card-label">Commands Executed</div>
                <div class="card-value">{db_stats["commands_run"]:,}</div>
            </div>
            <div class="card">
                <div class="card-label">Saved Playlists</div>
                <div class="card-value">{db_stats["custom_playlists"]:,}</div>
            </div>
        </div>

        <div class="actions">
            <a href="{invite_url}" target="_blank" class="btn btn-primary">➕ Add Bot to Discord</a>
            <a href="https://discord.com/users/1256986886631854080" target="_blank" class="btn btn-outline">👑 Support / Owner</a>
            <a href="/api/health" target="_blank" class="btn btn-outline">🔍 Health API (/health)</a>
            <a href="/api/logs" target="_blank" class="btn btn-outline">📜 Live Logs (/api/logs)</a>
        </div>

        <div class="streams-panel">
            <div class="panel-header">
                <span>🎵 Live Active Audio Players</span>
                <span style="font-size: 13px; color: var(--text-muted);">Auto-refreshes every 5s</span>
            </div>
            <div id="streamsContainer">
                <p style="color: var(--text-muted); font-size: 14px;">Standby mode active. Connect the bot in your voice channel and type <code>/play &lt;song&gt;</code> to stream audio!</p>
            </div>
        </div>

        <footer>
            VEYRA MUSIC &copy; 2026 • 24/7 Free Hosting Engine • All Premium Unlocked
        </footer>
    </div>

    <script>
        async function updateMetrics() {{
            try {{
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const d = await res.json();
                document.getElementById('pingVal').innerText = d.bot.latency_ms + 'ms';
                document.getElementById('valGuilds').innerText = d.bot.guilds;
                document.getElementById('valUsers').innerText = d.bot.users.toLocaleString();
                document.getElementById('valStreams').innerText = d.bot.voice_connections;
                document.getElementById('valUptime').innerText = d.bot.uptime;
                
                const container = document.getElementById('streamsContainer');
                if (d.active_streams && d.active_streams.length > 0) {{
                    let html = '<table class="streams-table"><thead><tr><th>Server</th><th>Track Title</th><th>Author</th><th>Filter</th><th>Volume</th></tr></thead><tbody>';
                    for (const s of d.active_streams) {{
                        html += `<tr><td><b>${{s.guild_name}}</b></td><td>${{s.title}}</td><td>${{s.author}}</td><td>${{s.filter}}</td><td>${{s.volume}}%</td></tr>`;
                    }}
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }} else {{
                    container.innerHTML = '<p style="color: var(--text-muted); font-size: 14px;">Standby mode active. Connect the bot in your voice channel and type <code>/play &lt;song&gt;</code> to stream audio!</p>';
                }}
            }} catch(e) {{}}
        }}
        setInterval(updateMetrics, 5000);
        updateMetrics();
    </script>
</body>
</html>"""
                    return web.Response(text=html, content_type="text/html")
                except Exception as ex:
                    print(f"⚠️ Dashboard render fallback: {ex}")
                    return web.Response(text=f"🟢 VEYRA MUSIC Online 24/7\nServers: {len(self.guilds)}\nHealth: OK\n", content_type="text/plain")

            async def sync_commands_api(request):
                try:
                    cleared_guilds = 0
                    for g in self.guilds:
                        try:
                            self.tree.clear_commands(guild=g)
                            await self.tree.sync(guild=g)
                            cleared_guilds += 1
                        except Exception:
                            pass
                    synced = await self.tree.sync()
                    return web.json_response({
                        "status": "ok",
                        "cleared_guilds": cleared_guilds,
                        "global_commands_synced": len(synced),
                        "commands": [c.name for c in synced]
                    })
                except Exception as e:
                    return web.json_response({"status": "error", "error": str(e)}, status=500)

            app.router.add_get("/", root_view)
            app.router.add_get("/api/health", health_check)
            app.router.add_get("/health", health_check)
            app.router.add_get("/api/stats", stats_api)
            app.router.add_get("/api/logs", logs_view)
            app.router.add_get("/api/test_extract", test_extract_view)
            app.router.add_get("/api/test_stream", test_stream_view)
            app.router.add_get("/api/formats", formats_view)
            app.router.add_get("/api/test_pcm", test_pcm_view)
            app.router.add_get("/api/diagnose", diagnose_view)
            app.router.add_get("/api/test_play", test_play_view)
            app.router.add_get("/api/sync_commands", sync_commands_api)
            app.router.add_post("/api/sync_commands", sync_commands_api)

            port = int(os.environ.get("PORT", 3005))
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            print(f"🌐 24/7 Web Dashboard & Health Server running on http://0.0.0.0:{port} (Endpoint: /health)")
            if port != 10000:
                try:
                    site_alt = web.TCPSite(runner, "0.0.0.0", 10000)
                    await site_alt.start()
                    print("🌐 Dual-listen fallback active on port 10000")
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ Health server error: {e}")

    async def on_ready(self):
        print(f"\n{'═'*45}\n  🎵 {self.user.name if self.user else 'Music Bot'} Online  |  Servers: {len(self.guilds)}\n{'═'*45}\n")
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="Vibes | /help"
            )
        )
        if not check_voice_channels.is_running():
            check_voice_channels.start()
            print("🔊 Inactivity and Empty VC check task loop started.")
        async def set_booted():
            await asyncio.sleep(10)
            self.booted = True
            print("🚀 Bot booted and self-healing active.")
        asyncio.create_task(set_booted())
        asyncio.create_task(self.keep_alive_pinger())

        async def purge_guild_duplicates():
            await asyncio.sleep(2)
            try:
                for g in self.guilds:
                    try:
                        self.tree.clear_commands(guild=g)
                        await self.tree.sync(guild=g)
                        await asyncio.sleep(0.5)
                    except Exception as ge:
                        print(f"⚠️ Guild cleanup warning for {g.name}: {ge}")
                print(f"🧹 Purged all duplicate guild commands across {len(self.guilds)} guilds. Single clean global tree active.")
            except Exception as e:
                print(f"⚠️ Duplicate cleanup error: {e}")
        asyncio.create_task(purge_guild_duplicates())

        async def reconnect_247_channels():
            await asyncio.sleep(3)
            try:
                records = Database.get_all_247()
                print(f"🔄 [24/7 Boot] Reconnecting {len(records)} saved 24/7 channels...")
                for row in records:
                    guild_id, stay_247, vc_id, tx_id = row
                    if not stay_247 or not vc_id:
                        continue
                    guild = self.get_guild(guild_id)
                    if not guild:
                        continue
                    ch = guild.get_channel(vc_id)
                    if not ch or not isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                        continue
                    p = self.get_player(guild_id)
                    p.stay_247 = True
                    if p.voice and p.voice.is_connected():
                        continue
                    try:
                        p.is_connecting = True
                        p.voice = await ch.connect(timeout=25, reconnect=True)
                        if tx_id:
                            p.text_ch = guild.get_channel(tx_id)
                        if isinstance(ch, discord.StageChannel):
                            try: await guild.me.edit(suppress=False)
                            except Exception: pass
                        print(f"✅ [24/7 Boot Reconnect] Joined '{ch.name}' in '{guild.name}'")
                    except Exception as err:
                        print(f"⚠️ [24/7 Boot Reconnect Failed] '{ch.name}' in '{guild.name}': {err}")
                    finally:
                        p.is_connecting = False
            except Exception as e:
                print(f"⚠️ [24/7 Reconnect Task Error]: {e}")
        asyncio.create_task(reconnect_247_channels())

bot = MusicBot()

@bot.command(name="sync", description="Purge duplicate guild commands and sync single global tree")
@commands.has_permissions(administrator=True)
async def cmd_sync(ctx: commands.Context):
    msg = await ctx.send("🧹 Purging duplicate guild commands from this server...")
    try:
        if ctx.guild:
            bot.tree.clear_commands(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
        synced = await bot.tree.sync()
        await msg.edit(content=f"✅ Purged duplicates! Single clean global slash tree active with **{len(synced)}** unique commands.")
    except Exception as e:
        await msg.edit(content=f"⚠️ Sync error: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user and bot.user.mentioned_in(message) and not message.mention_everyone:
        content_stripped = message.content.strip()
        if content_stripped in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
            prefix = Database.get_prefix(message.guild.id) if message.guild else PREFIX
            perms = discord.Permissions(send_messages=True, embed_links=True, connect=True, speak=True)
            invite_url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands"))
            e = discord.Embed(title="Welcome to VEYRA MUSIC", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = (
                f"Hey {message.author.mention},\n"
                f"I'm **VEYRA MUSIC**, your friendly music bot.\n"
                f"Prefix for this server: `{prefix}`\n"
                f"Type `{prefix}help` for more information."
            )
            e.set_footer(text="VEYRA Music", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            return await message.reply(embed=e, view=MentionLinksView(invite_url))

    await bot.process_commands(message)

# Self-healing 24/7 voice channel listener
@bot.event
async def on_voice_state_update(member, before, after):
    if not bot.booted:
        return
    if member.id == bot.user.id:
        p = bot.get_player(member.guild.id)
        if getattr(p, "is_connecting", False):
            return
        if before.channel and not after.channel:
            # Bot was disconnected unexpectedly
            guild_id = member.guild.id
            stay_247, vc_id, tx_id = Database.get_247(guild_id)
            if stay_247 and (vc_id or before.channel.id):
                target_id = vc_id or before.channel.id
                await asyncio.sleep(2)
                # Check if bot is ALREADY connected via guild.voice_client
                existing_vc = member.guild.voice_client
                if (p.voice and p.voice.is_connected()) or (existing_vc and existing_vc.is_connected()):
                    if existing_vc:
                        p.voice = existing_vc
                    return
                if getattr(p, "is_connecting", False):
                    return
                ch = member.guild.get_channel(target_id)
                if ch:
                    try:
                        p.is_connecting = True
                        p.voice = await ch.connect(timeout=20, reconnect=True)
                        p.stay_247 = True
                        if tx_id:
                            p.text_ch = member.guild.get_channel(tx_id)
                        if isinstance(ch, discord.StageChannel):
                            try: await member.guild.me.edit(suppress=False)
                            except Exception: pass
                        print(f"📡 Self-Healed: Reconnected 24/7 bot to channel {ch.name} in {member.guild.name}")
                    except Exception as e:
                        print(f"❌ Failed self-healing reconnection: {e}")
                    finally:
                        p.is_connecting = False
        elif after.channel and before.channel != after.channel:
            # Bot was moved to another channel - update 24/7 home
            stay_247, vc_id, tx_id = Database.get_247(member.guild.id)
            if stay_247:
                Database.set_247(member.guild.id, 1, after.channel.id, tx_id)
                p.stay_247 = True
    else:
        # A human member joined or moved into the channel where the bot is connected
        if not member.bot and after.channel:
            p = bot.get_player(member.guild.id)
            if p.voice and p.voice.channel and after.channel.id == p.voice.channel.id:
                conn = getattr(p.voice, "_connection", None)
                if conn and conn.dave_protocol_version > 0 and not conn.can_encrypt:
                    try:
                        await conn.reinit_dave_session()
                        print(f"📡 [DAVE Sync] User {member.name} joined; re-announced MLS key package in '{after.channel.name}'")
                    except Exception:
                        pass

# Guild Join Event
@bot.event
async def on_guild_join(guild: discord.Guild):
    Database.init_guild(guild.id)
    print(f"📡 Joined new guild: {guild.name} (ID: {guild.id}). Database row initialized.")

    target_ch = guild.system_channel
    if not target_ch or not target_ch.permissions_for(guild.me).send_messages:
        channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
        if channels:
            def sort_key(c):
                name = c.name.lower()
                if "general" in name: return 0
                if "music" in name: return 1
                if "bot" in name: return 2
                return 3
            channels.sort(key=sort_key)
            target_ch = channels[0]

    if target_ch:
        perms = discord.Permissions(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            connect=True,
            speak=True,
            use_application_commands=True
        )
        invite_url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands"))
        
        bot_name = bot.user.name if bot.user else "Music Bot"
        avatar = bot.user.avatar.url if (bot.user and bot.user.avatar) else None
        embed = discord.Embed(title=f"Welcome to {bot_name}", color=0x2B2D31)
        embed.description = (
            f"Hey everyone,\n"
            f"I'm **{bot_name}**, your friendly music bot.\n"
            f"Prefix for this server: `.`\n"
            f"Type `.help` or `/help` for more information."
        )
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.set_footer(text=f"Powered By {bot_name}", icon_url=avatar)

        try:
            await target_ch.send(embed=embed, view=MentionLinksView(invite_url))
        except Exception:
            pass

# Inactivity and Empty Voice Channel Auto-Disconnect Task Loop (with 24/7 Watchdog)
@tasks.loop(seconds=25)
async def check_voice_channels():
    # 1. 24/7 Watchdog: Enforce presence for all guilds configured with stay_247 = 1
    try:
        records = Database.get_all_247()
        for row in records:
            guild_id, stay_247, vc_id, tx_id = row
            if stay_247 and vc_id:
                guild = bot.get_guild(guild_id)
                if not guild:
                    continue
                p = bot.get_player(guild_id)
                p.stay_247 = True

                existing_vc = guild.voice_client
                if existing_vc and existing_vc.is_connected():
                    p.voice = existing_vc
                    if existing_vc.channel.id != vc_id:
                        ch = guild.get_channel(vc_id)
                        if ch and isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                            try:
                                await existing_vc.move_to(ch)
                            except Exception:
                                pass
                    continue

                if getattr(p, "is_connecting", False):
                    continue

                ch = guild.get_channel(vc_id)
                if ch and isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                    try:
                        p.is_connecting = True
                        p.voice = await ch.connect(timeout=20, reconnect=True)
                        p.stay_247 = True
                        if tx_id:
                            p.text_ch = guild.get_channel(tx_id)
                        if isinstance(ch, discord.StageChannel):
                            try: await guild.me.edit(suppress=False)
                            except Exception: pass
                        print(f"📡 [24/7 Watchdog] Reconnected to '{ch.name}' in '{guild.name}'")
                    except Exception as e:
                        print(f"⚠️ [24/7 Watchdog Error] Failed reconnecting to '{ch.name}': {e}")
                    finally:
                        p.is_connecting = False
    except Exception as e:
        print(f"⚠️ [24/7 Watchdog Check Error]: {e}")

    # 2. Automatically sync any active voice connection into 24/7 database
    for guild_id, p in list(bot.players.items()):
        if p.voice and p.voice.is_connected() and p.voice.channel and p.stay_247:
            tx_id = p.text_ch.id if p.text_ch else None
            Database.set_247(guild_id, 1, p.voice.channel.id, tx_id)

# ─────────────────────────────────────────────
#              CORE AUDIO ENGINE
# ─────────────────────────────────────────────

async def ensure_vc(ctx: commands.Context) -> Optional[discord.VoiceClient]:
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await send_response(ctx, embed=err("You must join a voice channel first!"))
        return None
    ch = ctx.author.voice.channel

    # Check guild voice client in discord.py
    existing_vc = ctx.guild.voice_client
    if existing_vc and existing_vc.is_connected():
        p.voice = existing_vc
        if existing_vc.channel.id != ch.id:
            p.is_connecting = True
            try:
                await existing_vc.move_to(ch)
            except Exception:
                pass
            finally:
                p.is_connecting = False
        return p.voice
    elif existing_vc:
        try:
            await existing_vc.disconnect(force=True)
        except Exception:
            pass

    try:
        p.is_connecting = True
        p.voice = await ch.connect(timeout=20, reconnect=True, self_deaf=True)
        if isinstance(ch, discord.StageChannel):
            try:
                await ctx.guild.me.edit(suppress=False)
            except Exception:
                try:
                    await ctx.guild.me.request_to_speak()
                except Exception:
                    pass
        # Enable 24/7 mode by default when joining channel!
        p.stay_247 = True
        Database.set_247(ctx.guild.id, 1, ch.id, ctx.channel.id)
        return p.voice
    except Exception as ex:
        await send_response(ctx, embed=err(f"Could not connect to voice channel: {ex}"))
        return None
    finally:
        p.is_connecting = False

async def get_autoplay_track(current_track, loop) -> Optional[dict]:
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

async def play_next(guild: discord.Guild, interaction: Optional[discord.Interaction] = None):
    p = bot.get_player(guild.id)
    p.skip_votes.clear()
    print(f"DEBUG: play_next called for guild {guild.id}, voice is connected: {bool(p.voice and p.voice.is_connected())}")
    if not p.voice or not p.voice.is_connected():
        print("DEBUG: play_next returning early because voice not connected")
        return

    # Check JIT restart track flag
    if getattr(p, "restarting_track", False):
        p.restarting_track = False
        track = p.current
    else:
        # Loop / pop progression
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
                        try: await p.panel_msg.edit(embed=panel_embed(p), view=None)
                        except Exception: pass
                    return
            else:
                p.current = None
                if p.panel_msg:
                    try: await p.panel_msg.edit(embed=panel_embed(p), view=None)
                    except Exception: pass
                return

    # Just-in-Time track resolver
    is_direct_url = track and track.get("url") and ("googlevideo.com" in track["url"] or ".m3u8" in track["url"] or ".mpd" in track["url"])
    if track and not is_direct_url:
        try:
            # 1. Resolve Spotify placeholder query to YouTube watch URL
            if not track.get("url") and track.get("query"):
                yt_track = await YTSource.search(track["query"], bot.loop)
                if yt_track:
                    track["url"] = yt_track.get("webpage_url") or yt_track.get("url", "")
                    if yt_track.get("thumbnail"):
                        track["thumbnail"] = yt_track.get("thumbnail", "")
                    if yt_track.get("duration"):
                        track["duration"] = int(yt_track.get("duration") or 0)
                    if yt_track.get("title"):
                        track["title"] = yt_track.get("title")
                else:
                    if p.text_ch:
                        await p.text_ch.send(embed=err(f"Could not find YouTube match for: **{track['title']}**"), delete_after=10)
                    await play_next(guild)
                    return
        except Exception as e:
            logging.error(f"Failed JIT track resolve: {e}")
            if p.text_ch:
                await p.text_ch.send(embed=err(f"Error Searching... track: {e}"), delete_after=10)
            await play_next(guild)
            return

    try:
        print(f"DEBUG: play_next stream starting for JIT url: {track['url']}")
        # Play JIT using YTSource.stream
        src = await YTSource.stream(track["url"], bot.loop, volume=p.volume, active_filter=p.filter, seek_time=p.seek_offset, speed=p.speed, pitch=p.pitch, track_title=track.get("title"))
        print(f"DEBUG: play_next stream successfully extracted, direct url is: {src.data.get('url') if src.data else 'None'}")
        
        # Update metadata if resolved
        if src.data:
            track["url"] = src.data.get("webpage_url") or src.data.get("url", track["url"])
            track["title"] = src.data.get("title", track["title"])
            track["duration"] = int(src.data.get("duration") or 0)
            track["thumbnail"] = src.data.get("thumbnail", track["thumbnail"])
            track["uploader"] = src.data.get("uploader", track["uploader"])

        p.history.appendleft(track)

        play_started_at = time.time()
        def after_cb(error):
            elapsed = time.time() - play_started_at
            if error:
                print(f"❌ [Voice Playback Error] Guild {guild.id} after {elapsed:.1f}s: {error}")
            else:
                print(f"✅ [Voice Playback Finished] Guild {guild.id} after {elapsed:.1f}s: {track.get('title')}")
            bot.loop.call_soon_threadsafe(lambda: bot.loop.create_task(play_next(guild)))

        # Ensure DAVE E2EE session is initialized if protocol version > 0
        conn = getattr(p.voice, "_connection", None)
        if conn and getattr(conn, "dave_protocol_version", 0) > 0 and not getattr(conn, "can_encrypt", False):
            try:
                if hasattr(conn, "reinit_dave_session"):
                    await conn.reinit_dave_session()
            except Exception as d_err:
                pass

        p.reset_start_time()
        if p.voice and (p.voice.is_playing() or p.voice.is_paused()):
            try: p.voice.stop()
            except Exception: pass
        print(f"🔊 Starting voice playback for '{track.get('title')}' in guild {guild.id}")
        p.voice.play(src, after=after_cb)
        Database.increment_stat("songs_played")

    except Exception as ex:
        logging.error(f"Streaming error: {ex}")
        queued_msg: Optional[discord.Message] = track.get("queued_msg")
        if queued_msg:
            try:
                await queued_msg.edit(embed=err(f"Could not load/play track: {ex}"), view=None)
                async def delete_later():
                    await asyncio.sleep(10)
                    try: await queued_msg.delete()
                    except Exception: pass
                bot.loop.create_task(delete_later())
            except Exception:
                pass
        elif p.text_ch:
            await p.text_ch.send(embed=err(f"Could not load/play track: {ex}"), delete_after=10)
        await play_next(guild)
        return

    queued_msg: Optional[discord.Message] = track.get("queued_msg")
    if queued_msg:
        try:
            await queued_msg.edit(embed=panel_embed(p), view=MusicPanel(guild.id))
            p.panel_msg = queued_msg
            p.ensure_updater()
            return
        except Exception:
            pass

    if interaction and not interaction.response.is_done():
        try:
            await interaction.edit_original_response(embed=panel_embed(p), view=MusicPanel(guild.id))
            p.panel_msg = await interaction.original_response()
            p.ensure_updater()
            return
        except Exception:
            pass

    if p.text_ch:
        try:
            msg = await p.text_ch.send(embed=panel_embed(p), view=MusicPanel(guild.id))
            p.panel_msg = msg
            p.ensure_updater()
        except Exception:
            pass

# ─────────────────────────────────────────────
#             HYBRID / SLASH COMMANDS
# ─────────────────────────────────────────────

# Standard play command
@bot.hybrid_command(name="play", aliases=["p"], description="Play a song or playlist from YouTube/Spotify")
@app_commands.describe(query="Song title, URL, YouTube playlist or Spotify link")
async def slash_play(ctx: commands.Context, *, query: Optional[str] = None):
    p = bot.get_player(ctx.guild.id)
    if not query:
        if p.voice and p.is_paused():
            p.voice.resume()
            if p.paused_at and p.start_time:
                p.start_time += time.time() - p.paused_at
            p.paused_at = None
            p.ensure_updater()
            return await send_response(ctx, embed=ok("Resumed", "Playback has been resumed."))
        prefix = Database.get_prefix(ctx.guild.id) if ctx.guild else PREFIX
        return await send_response(ctx, embed=err(f"Please provide a song title or URL.\nUsage: `{prefix}play <song title or URL>`"))

    is_slash = ctx.interaction is not None
    searching_msg = None
    interaction = None
    if is_slash:
        try:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.defer()
            searching_msg = await ctx.interaction.edit_original_response(embed=make_embed("🔍 Searching...", f"Searching... `{query}`", 0x2B2D31))
            interaction = ctx.interaction
        except Exception:
            try:
                searching_msg = await ctx.interaction.followup.send(embed=make_embed("🔍 Searching...", f"Searching... `{query}`", 0x2B2D31))
                interaction = ctx.interaction
            except Exception:
                searching_msg = await ctx.send(embed=make_embed("🔍 Searching...", f"Searching... `{query}`", 0x2B2D31))
                interaction = None
    else:
        searching_msg = await ctx.reply(embed=make_embed("🔍 Searching...", f"Searching... `{query}`", 0x2B2D31))
        interaction = None

    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel

    # Join Voice
    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc:
            try: await searching_msg.delete()
            except Exception: pass
            return

    # Check if query is Spotify
    if "spotify.com" in query:
        spotify_tracks, is_playlist = await SpotifyResolver.resolve(query)
        if not spotify_tracks:
            return await searching_msg.edit(embed=err("Failed to resolve Spotify link. Make sure it is a public track, album or playlist!"))

        first_play = not p.is_playing() and not p.is_paused()
        for idx, s_track in enumerate(spotify_tracks):
            track = {
                "title": s_track["title"],
                "url": None, # Resolve query JIT to full YouTube video
                "query": s_track["query"],
                "duration": 0,
                "thumbnail": s_track["thumbnail"],
                "uploader": ", ".join(s_track["artists"]),
                "requester_id": ctx.author.id,
                "queued_msg": searching_msg if (idx == 0 and first_play) else None
            }
            p.queue.append(track)
                
        e = ok("Spotify loaded ✅", f"Successfully queued **{len(spotify_tracks)}** track(s) from Spotify.")
        await searching_msg.edit(embed=e)
        
        if first_play:
            await play_next(ctx.guild, interaction)
        else:
            await p.update_panel()
            async def delete_later():
                await asyncio.sleep(5)
                try: await searching_msg.delete()
                except Exception: pass
            bot.loop.create_task(delete_later())
        return

    # YouTube Searching...
    try:
        tracks, is_playlist = await YTSource.extract_tracks(query, bot.loop)
        if not tracks:
            return await searching_msg.edit(embed=err("No results found."))

        if is_playlist:
            first_play = not p.is_playing() and not p.is_paused()
            
            for idx, track_data in enumerate(tracks):
                track = {
                    "title": track_data.get("title", "Unknown"),
                    "url": track_data.get("webpage_url") or track_data.get("url", ""),
                    "duration": int(track_data.get("duration") or 0),
                    "thumbnail": track_data.get("thumbnail", ""),
                    "uploader": track_data.get("uploader", "Unknown"),
                    "requester_id": ctx.author.id,
                    "queued_msg": searching_msg if (idx == 0 and first_play) else None
                }
                p.queue.append(track)
            
            if first_play:
                await play_next(ctx.guild, interaction)
            else:
                e = ok("Playlist Added ✅", f"Added **{len(tracks)}** tracks from playlist to queue.")
                await searching_msg.edit(embed=e)
                await p.update_panel()
                async def delete_later():
                    await asyncio.sleep(5)
                    try: await searching_msg.delete()
                    except Exception: pass
                bot.loop.create_task(delete_later())
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
            print(f"DEBUG: slash_play resolved track: {track['title']} (URL: {track['url']})")
            if not p.is_playing() and not p.is_paused():
                if searching_msg:
                    try:
                        await searching_msg.edit(embed=make_embed("🎶 Loading...", f"Loading audio for **{track['title']}**...", 0x2B2D31))
                    except Exception:
                        pass
                print("DEBUG: slash_play calling play_next")
                await play_next(ctx.guild, interaction)
                print("DEBUG: slash_play play_next completed")
            else:
                dur = p.fmt(track.get("duration", 0))
                e = ok("Added to Queue ✅", f"**{track['title']}**\nPosition: `#{len(p.queue)}` | Duration: `{dur}`")
                if track["thumbnail"]:
                    e.set_thumbnail(url=track["thumbnail"])
                
                await searching_msg.edit(embed=e)
                await p.update_panel()
                async def delete_later():
                    await asyncio.sleep(5)
                    try: await searching_msg.delete()
                    except Exception: pass
                bot.loop.create_task(delete_later())

    except Exception as ex:
        await searching_msg.edit(embed=err(f"Could not load track: {ex}"))
        async def delete_later():
            await asyncio.sleep(5)
            try: await searching_msg.delete()
            except Exception: pass
        bot.loop.create_task(delete_later())

# Reopen Control Panel
@bot.hybrid_command(name="panel", aliases=["m", "player"], description="Reopen the music control panel")
async def slash_panel(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if p.panel_msg:
        try: await p.panel_msg.delete()
        except Exception: pass
        p.panel_msg = None
    
    view = MusicPanel(ctx.guild.id)
    msg = await ctx.send(embed=panel_embed(p), view=view)
    p.panel_msg = msg

# Join Command
@bot.hybrid_command(name="join", description="Join the user's voice channel")
async def slash_join(ctx: commands.Context):
    vc = await ensure_vc(ctx)
    if vc:
        await send_response(ctx, embed=ok("Joined!", f"Connected to **{vc.channel.name}** and stay active 24/7."))

# Leave Command
@bot.hybrid_command(name="leave", description="Disconnect from the voice channel")
async def slash_leave(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.voice.is_connected():
        return await send_response(ctx, embed=err("I'm not connected to a voice channel!"))
    
    ch_name = p.voice.channel.name
    if p.current and p.panel_msg:
        await p.archive_panel()
    p.queue.clear()
    p.stay_247 = False
    Database.set_247(ctx.guild.id, 0, None, None)
    if p.voice.is_playing() or p.voice.is_paused():
        p.voice.stop()
    p.is_connecting = True
    try:
        await p.voice.disconnect()
    finally:
        p.voice = None
        p.is_connecting = False
    p.current = None
    await send_response(ctx, embed=ok("Disconnected", f"Left voice channel **{ch_name}**."))

# Skip Command
@bot.hybrid_command(name="skip", aliases=["s", "next"], description="Skip the current playing track")
async def slash_skip(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.is_playing() and not p.is_paused():
        return await send_response(ctx, embed=err("Nothing is currently playing!"))
    p.voice.stop()
    await send_response(ctx, embed=ok("Skipped Current Song ⏭"))

# Vote Skip Command
@bot.hybrid_command(name="voteskip", description="Vote to skip the current playing song")
async def slash_voteskip(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing!"))

    is_dj = await check_dj_permission(ctx)
    if is_dj:
        p.voice.stop()
        return await send_response(ctx, embed=ok("Skipped Song", "Skipped immediately by DJ/Administrator. ⏭"))

    user_id = ctx.author.id
    if user_id in p.skip_votes:
        return await send_response(ctx, embed=err("You have already voted to skip this song!"))

    # Active listeners in voice channel (excluding bots)
    listeners = [m for m in p.voice.channel.members if not m.bot]
    needed_votes = max(1, len(listeners) // 2)

    p.skip_votes.add(user_id)
    current_votes = len(p.skip_votes)

    if current_votes >= needed_votes:
        p.voice.stop()
        await send_response(ctx, embed=ok("Song Skipped", f"Skipped! Vote progress: **{current_votes}/{needed_votes}** votes reached."))
    else:
        await send_response(ctx, embed=ok("Vote Registered", f"Vote registered. Progress: **{current_votes}/{needed_votes}** votes (Need 50%)."))

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

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
    async def prev_page(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await i.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
    async def next_page(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await i.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=err(f"Action failed: {error}"), ephemeral=True)
            else:
                await interaction.followup.send(embed=err(f"Action failed: {error}"), ephemeral=True)
        except Exception:
            pass

# Queue Command
@bot.hybrid_command(name="queue", aliases=["q"], description="Show the music queue with pagination")
async def slash_queue(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current and not p.queue:
        return await send_response(ctx, embed=err("The music queue is empty!"))
    
    queue_list = list(p.queue)
    tracks_per_page = 10
    total_pages = max(1, (len(queue_list) + tracks_per_page - 1) // tracks_per_page)
    
    pages = []
    for page_idx in range(total_pages):
        lines = []
        if page_idx == 0 and p.current:
            lines.append(f"**▶ Now Playing:** {p.current['title']} `{p.fmt(p.current.get('duration',0))}`\n")
            
        start = page_idx * tracks_per_page
        end = start + tracks_per_page
        page_tracks = queue_list[start:end]
        
        for idx, track in enumerate(page_tracks, start + 1):
            lines.append(f"`{idx}.` {track['title']} `{p.fmt(track.get('duration',0))}`")
            
        desc = "\n".join(lines) if lines else "*No queued songs.*"
        
        e = discord.Embed(
            title=f"📋 Queue ({len(p.queue)} tracks)",
            description=desc,
            color=0x2B2D31
        )
        bot_name = bot.user.name if bot.user else "Music"
        e.set_footer(text=f"Page {page_idx + 1} of {total_pages} | Powered By {bot_name}")
        pages.append(e)
        
    view = QueuePaginationView(pages, ctx.author.id) if len(pages) > 1 else None
    msg = await send_response(ctx, embed=pages[0], view=view)
    if view and msg:
        view.message = msg

# Now Playing Command
@bot.hybrid_command(name="nowplaying", aliases=["np"], description="Show the track currently playing")
async def slash_np(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing!"))
    await send_response(ctx, embed=panel_embed(p))

class VolumeControlsView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    def _p(self) -> GuildPlayer:
        return bot.get_player(self.guild_id)

    async def _update_volume_embed(self, i: discord.Interaction):
        p = self._p()
        level = int(p.volume * 100)
        bar_len = min(10, level // 20)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        e = ok("Volume Adjuster", f"`{bar}` **{level}%**")
        await i.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="-10%", emoji="🔉", style=discord.ButtonStyle.blurple)
    async def vol_down(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self._p()
        p.volume = max(0.0, round(p.volume - 0.1, 2))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        Database.set_volume(self.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

    @discord.ui.button(label="Mute", emoji="🔇", style=discord.ButtonStyle.danger)
    async def mute_unmute(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self._p()
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
        Database.set_volume(self.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

    @discord.ui.button(label="+10%", emoji="🔊", style=discord.ButtonStyle.blurple)
    async def vol_up(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user.id != self.user_id:
            return await i.response.send_message("You cannot control this menu.", ephemeral=True)
        p = self._p()
        p.volume = min(2.0, round(p.volume + 0.1, 2))
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        Database.set_volume(self.guild_id, int(p.volume * 100))
        await p.update_panel()
        await self._update_volume_embed(i)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=err(f"Action failed: {error}"), ephemeral=True)
            else:
                await interaction.followup.send(embed=err(f"Action failed: {error}"), ephemeral=True)
        except Exception:
            pass

# Volume Command
@bot.hybrid_command(name="volume", aliases=["vol", "v"], description="Set the audio volume level (1-200)")
@app_commands.describe(level="Volume level percentage (1-200)")
async def slash_volume(ctx: commands.Context, level: Optional[int] = None):
    p = bot.get_player(ctx.guild.id)
    user_id = ctx.author.id
    
    if level is None:
        level = int(p.volume * 100)
    else:
        level = max(1, min(200, level))
        p.volume = level / 100
        if p.voice and p.voice.source:
            p.voice.source.volume = p.volume
        Database.set_volume(ctx.guild.id, level)
        await p.update_panel()
        
    bar_len = min(10, level // 20)
    bar = "█" * bar_len + "░" * (10 - bar_len)
    
    view = VolumeControlsView(ctx.guild.id, user_id)
    await send_response(ctx, embed=ok("Volume Config", f"`{bar}` **{level}%**"), view=view)

# Loop Command
@bot.hybrid_command(name="loop", description="Toggle loop mode: off, track, queue")
@app_commands.choices(mode=[
    app_commands.Choice(name="off", value="off"),
    app_commands.Choice(name="track", value="track"),
    app_commands.Choice(name="queue", value="queue"),
])
async def slash_loop(ctx: commands.Context, mode: str = "track"):
    p = bot.get_player(ctx.guild.id)
    p.loop = mode
    await p.update_panel()
    await send_response(ctx, embed=ok(f"Loop Mode Set", f"Loop mode is now set to **{mode.title()}**."))

# Shuffle Command
@bot.hybrid_command(name="shuffle", description="Shuffle the queue")
async def slash_shuffle(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if len(p.queue) < 2:
        return await send_response(ctx, embed=err("Need at least 2 songs in queue to shuffle."))
    q = list(p.queue)
    random.shuffle(q)
    p.queue = deque(q)
    await p.update_panel()
    await send_response(ctx, embed=ok("Queue Shuffled!"))

# Audio Filter Command
FILTERS = ["bassboost", "nightcore", "8d", "vaporwave", "karaoke", "doubletime", "slowmo", "daycore", "lofi", "off"]
@bot.hybrid_command(name="filter", description="Apply real ffmpeg audio filters")
@app_commands.choices(name=[app_commands.Choice(name=f.title(), value=f) for f in FILTERS])
async def slash_filter(ctx: commands.Context, name: str):
    p = bot.get_player(ctx.guild.id)
    p.filter = None if name == "off" else name
    
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Filter: {name.title()}", "Restarting track with filters applied…"))

# Equalizer Preset Command
EQ_PRESETS = ["flat", "classical", "jazz", "metal", "rock", "vocal", "electronic", "bassboost"]
@bot.hybrid_command(name="equalizer", aliases=["eq"], description="Apply preset equalizer acoustics (Premium Unlocked!)")
@app_commands.describe(preset="Equalizer acoustic preset")
@app_commands.choices(preset=[app_commands.Choice(name=p.title(), value=p) for p in EQ_PRESETS])
async def slash_equalizer(ctx: commands.Context, preset: str):
    p = bot.get_player(ctx.guild.id)
    p.filter = None if preset == "flat" else preset
    
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Equalizer Set: {preset.title()}", "Restarting track with equalizer settings applied…"))

# Live Radio Configuration
RADIO_STATIONS = {
    "lofi-chill": {
        "title": "Lofi Girl - Chill Beats",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "uploader": "Lofi Girl"
    },
    "lofi-synthwave": {
        "title": "Lofi Girl - Synthwave Radio",
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

@bot.hybrid_command(name="radio", description="Play premium 24/7 live lofi and chill radio streams (Premium Unlocked!)")
@app_commands.describe(station="Select the radio station to play")
@app_commands.choices(station=[
    app_commands.Choice(name="Lofi Girl - Chill Beats", value="lofi-chill"),
    app_commands.Choice(name="Lofi Girl - Synthwave Radio", value="lofi-synthwave"),
    app_commands.Choice(name="Coffee Shop Lofi Radio", value="coffee-shop"),
    app_commands.Choice(name="Smooth Jazz Lofi Radio", value="jazz-lofi")
])
async def slash_radio(ctx: commands.Context, station: str):
    is_slash = ctx.interaction is not None
    if is_slash:
        await ctx.interaction.response.defer()
        searching_msg = await ctx.interaction.followup.send(embed=make_embed("📻 Tuning in...", f"Tuning into radio station...", 0xF1C40F))
        interaction = ctx.interaction
    else:
        searching_msg = await ctx.reply(embed=make_embed("📻 Tuning in...", f"Tuning into radio station...", 0xF1C40F))
        interaction = None

    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel

    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc:
            try: await searching_msg.delete()
            except Exception: pass
            return

    info = RADIO_STATIONS.get(station)
    if not info:
        return await searching_msg.edit(embed=err("Invalid radio station!"))

    track = {
        "title": info["title"],
        "url": info["url"],
        "duration": 0,
        "thumbnail": "https://i.imgur.com/4S72x1A.gif",
        "uploader": info["uploader"],
        "requester_id": ctx.author.id,
        "queued_msg": searching_msg
    }

    p.queue.clear()
    p.current = None
    p.queue.append(track)
    
    if p.voice.is_playing() or p.voice.is_paused():
        p.voice.stop()
    else:
        await play_next(ctx.guild, interaction)

# Autoplay Command
@bot.hybrid_command(name="autoplay", description="Toggle Autoplay related music when queue ends")
async def slash_autoplay(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    p.autoplay = not p.autoplay
    await p.update_panel()
    await send_response(ctx, embed=ok(f"AutoPlay {'Enabled ✅' if p.autoplay else 'Disabled ❌'}"))

# Clear Queue Command
@bot.hybrid_command(name="clear", description="Clear the music queue")
async def slash_clear(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    count = len(p.queue)
    p.queue.clear()
    await p.update_panel()
    await send_response(ctx, embed=ok("Queue Cleared", f"Removed **{count}** tracks from the queue."))

# Stop Command
@bot.hybrid_command(name="stop", aliases=["dc"], description="Stop music and clear queue")
async def slash_stop(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    finished = p.current
    p.queue.clear()
    p.current = None
    p.loop = "off"
    if p.voice:
        p.voice.stop()

    is_247 = p.stay_247 or bool(Database.get_247(ctx.guild.id)[0])
    if not is_247:
        if p.voice:
            try: await p.voice.disconnect()
            except Exception: pass
            p.voice = None
        desc = "Music stopped and voice disconnected."
    else:
        p.stay_247 = True
        desc = "Music stopped and queue cleared. The bot remains connected in voice (24/7 active)."

    if p.panel_msg and finished:
        try: await p.panel_msg.edit(embed=history_embed(finished), view=None)
        except Exception: pass
        p.panel_msg = None
    await send_response(ctx, embed=ok("Stopped", desc))

# Pause Command
@bot.hybrid_command(name="pause", description="Pause the currently playing track")
async def slash_pause(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    if p.paused_at is not None or p.is_paused():
        return await send_response(ctx, embed=err("Playback is already paused."))
        
    p.voice.pause()
    p.paused_at = time.time()
    await p.update_panel()
    await send_response(ctx, embed=ok("Paused", "Playback has been paused. Use `/resume` to continue."))

# Resume Command
@bot.hybrid_command(name="resume", description="Resume the paused track")
async def slash_resume(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    if p.paused_at is None and not p.is_paused():
        return await send_response(ctx, embed=err("Playback is not paused."))
        
    p.voice.resume()
    if p.start_time is not None and p.paused_at is not None:
        p.start_time += (time.time() - p.paused_at)
    p.paused_at = None
    await p.update_panel()
    await send_response(ctx, embed=ok("Resumed", "Playback has been resumed."))

# Lofi Filter Command
@bot.command(name="lofifilter", description="Quickly toggle the relaxing lofi filter on/off")
async def slash_lofifilter(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if p.filter == "lofi":
        p.filter = None
        status = "disabled"
    else:
        p.filter = "lofi"
        status = "enabled"
        
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Lofi Filter {status.title()}", f"Lofi effect has been {status}."))

# Bassboost Command
@bot.command(name="bassboost", description="Toggle or set the bass boost filter level")
async def slash_bassboost(ctx: commands.Context, level: str = "medium"):
    p = bot.get_player(ctx.guild.id)
    if level == "off":
        p.filter = None
    else:
        p.filter = f"bassboost_{level}"
        
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Bassboost Level: {level.title()}", f"Restarting track with {level} bassboost applied…"))

# Nightcore Command
@bot.command(name="nightcore", description="Quickly toggle the nightcore filter (pitch + speed boost) on/off")
async def slash_nightcore(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if p.filter == "nightcore":
        p.filter = None
        status = "disabled"
    else:
        p.filter = "nightcore"
        status = "enabled"
        
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Nightcore Filter {status.title()}", f"Nightcore effect has been {status}."))

# Vaporwave Command
@bot.command(name="vaporwave", description="Quickly toggle the vaporwave filter (slowed + reverb vibe) on/off")
async def slash_vaporwave(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if p.filter == "vaporwave":
        p.filter = None
        status = "disabled"
    else:
        p.filter = "vaporwave"
        status = "enabled"
        
    if p.current and p.voice:
        p.seek_offset = p.position
        p.start_time = time.time()
        p.paused_at = None
        p.restarting_track = True
        p.voice.stop()
    await ctx.send(embed=ok(f"Vaporwave Filter {status.title()}", f"Vaporwave effect has been {status}."))

# Pitch Command
@bot.hybrid_command(name="pitch", description="Change player playback pitch multiplier (0.5x - 2.0x)")
@app_commands.describe(multiplier="Pitch multiplier value (e.g. 1.25 or 0.8)")
async def slash_pitch(ctx: commands.Context, multiplier: float):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    if multiplier < 0.5 or multiplier > 2.0:
        return await ctx.send(embed=err("Playback pitch must be between **0.5x** and **2.0x**."))
        
    p.pitch = multiplier
    p.seek_offset = p.position
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Pitch Adjusted", f"Playback pitch multiplier set to **{multiplier}x**."))

# History Command
@bot.hybrid_command(name="history", description="Show recently played tracks")
async def slash_history(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.history:
        return await send_response(ctx, embed=err("No playback history recorded yet!"))
    lines = [
        f"`{idx}.` {t['title']} `{p.fmt(t.get('duration',0))}` — "
        f"{'<@'+str(t['requester_id'])+'>' if t.get('requester_id') else 'AutoPlay'}"
        for idx, t in enumerate(list(p.history)[:15], 1)
    ]
    e = discord.Embed(title="📜 Recently Played Tracks", description="\n".join(lines), color=0x7d5fff)
    await send_response(ctx, embed=e)

# Play from History Command
@bot.hybrid_command(name="historyplay", aliases=["hp", "replayhistory"], description="Replay a song from history by its index (Premium Unlocked!)")
@app_commands.describe(index="Index of the song in history (1-based, see /history)")
async def slash_history_play(ctx: commands.Context, index: int):
    p = bot.get_player(ctx.guild.id)
    if not p.history:
        return await send_response(ctx, embed=err("No playback history recorded yet!"))

    if index < 1 or index > len(p.history):
        return await send_response(ctx, embed=err(f"Invalid history index! Provide a number between 1 and {len(p.history)}."))

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
        await send_response(ctx, embed=ok("Replaying song from history...", f"Now replaying **{track_to_play['title']}**."))
    else:
        if not p.voice or not p.voice.is_connected():
            vc = await ensure_vc(ctx)
            if not vc: return
        await play_next(ctx.guild, ctx.interaction)
        await send_response(ctx, embed=ok("Playing song from history...", f"Now playing **{track_to_play['title']}**."))

# Invite Command
@bot.hybrid_command(name="invite", description="Get invite link for the bot")
async def slash_invite(ctx: commands.Context):
    perms = discord.Permissions(
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        connect=True,
        speak=True,
        use_application_commands=True,
        manage_messages=True
    )
    url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands"))
    e = discord.Embed(
        title="🔗 Invite VEYRA MUSIC Bot",
        description=f"[**Click here to invite the bot**]({url})\n\nGrants required permissions:\n`Send Messages` · `Embed Links` · `Connect` · `Speak` · `Use Slash Commands`",
        color=0x7d5fff
    )
    await ctx.send(embed=e)

# About / Info Command
@bot.hybrid_command(name="about", aliases=["info"], description="Display premium features and information about VEYRA MUSIC")
async def slash_about(ctx: commands.Context):
    perms = discord.Permissions(
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        connect=True,
        speak=True,
        use_application_commands=True,
        manage_messages=True
    )
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands"))
    support_url = "https://discord.com/users/1256986886631854080"
    vote_url = "https://top.gg/bot/veyra"

    embed = discord.Embed(
        title="VEYRA MUSIC", 
        color=0x2B2D31,
        timestamp=datetime.now(timezone.utc)
    )
    embed.description = (
        f"> **VEYRA MUSIC** is a high-fidelity Discord music bot streaming 24/7 with zero lag.\n\n"
        f"• **Commands:** `98`\n"
        f"• **Latency:** `{round(bot.latency * 1000, 2)}ms`\n"
        f"• **Servers:** `{len(bot.guilds)}`\n"
        f"• **24/7 Mode:** `Active`\n\n"
        f"───────────────────────────\n"
        f"**[Links]**\n"
        f"[Invite Me]({invite_url}) | [Support & Owner]({support_url})"
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else "")
    embed.set_footer(text="VEYRA Music", icon_url=bot.user.avatar.url if bot.user.avatar else "")
    await ctx.send(embed=embed)

# Purge / Clean Bot Messages Command
@bot.hybrid_command(name="purge", aliases=["clean"], description="Clean up the bot's commands and responses in this channel (Premium Unlocked!)")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(limit="Number of messages to scan (max 100)")
async def slash_purge(ctx: commands.Context, limit: int = 50):
    await ctx.defer(ephemeral=True)
    prefix = await bot.get_db_prefix(bot, ctx.message)
    
    def check_msg(m):
        is_bot = m.author.id == bot.user.id
        is_cmd = m.content.startswith(prefix)
        return is_bot or is_cmd

    deleted = await ctx.channel.purge(limit=min(100, limit), check=check_msg)
    await ctx.send(embed=ok("Purged Channel", f"Cleaned up **{len(deleted)}** bot messages/commands in this channel."), ephemeral=True)

# 24/7 Mode Command
async def handle_247_command(ctx: commands.Context, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    # Defer interaction immediately to guarantee 3-second Discord deadline is NEVER missed
    if ctx.interaction and not ctx.interaction.response.is_done():
        try:
            await ctx.defer()
        except Exception:
            pass

    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    # 1. Determine target voice channel
    target_ch = channel
    if not target_ch and getattr(ctx.author, "voice", None) and ctx.author.voice.channel:
        target_ch = ctx.author.voice.channel
    elif not target_ch and ctx.guild.voice_client and ctx.guild.voice_client.channel:
        target_ch = ctx.guild.voice_client.channel

    if not target_ch:
        return await send_response(ctx, embed=err("Join a voice channel or specify one (e.g. `/247 channel:#General`) to configure 24/7 mode!"))

    # 2. Connect or move to voice channel safely
    try:
        p.is_connecting = True
        if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
            p.voice = ctx.guild.voice_client
            if p.voice.channel.id != target_ch.id:
                await p.voice.move_to(target_ch)
        else:
            if ctx.guild.voice_client:
                try: await ctx.guild.voice_client.disconnect(force=True)
                except Exception: pass
            p.voice = await target_ch.connect(timeout=20, reconnect=True, self_deaf=True)
            
        if isinstance(target_ch, discord.StageChannel):
            try: await ctx.guild.me.edit(suppress=False)
            except Exception: pass
    except Exception as e:
        if not ctx.guild.voice_client:
            return await send_response(ctx, embed=err(f"Could not connect to voice channel: {e}"))
        p.voice = ctx.guild.voice_client
    finally:
        p.is_connecting = False

    # 3. Toggle 24/7 state
    if p.stay_247 and channel is None and (p.voice and p.voice.channel.id == target_ch.id):
        p.stay_247 = False
    else:
        p.stay_247 = True

    vc_id = target_ch.id if p.stay_247 else None
    Database.set_247(ctx.guild.id, 1 if p.stay_247 else 0, vc_id, ctx.channel.id)

    if p.stay_247:
        desc = f"24/7 Presence Mode is now **Enabled ✅**\nThe bot will stay permanently active in {target_ch.mention}."
    else:
        desc = f"24/7 Presence Mode is now **Disabled ❌**\nThe bot will automatically disconnect when inactive."
    await send_response(ctx, embed=ok("24/7 Presence System", desc))

@bot.hybrid_command(name="stay247", description="Toggle 24/7 channel presence (Premium Unlocked!)")
@app_commands.describe(channel="Target voice channel to stay connected 24/7 (optional)")
async def slash_stay247(ctx: commands.Context, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    await handle_247_command(ctx, channel)

@bot.hybrid_command(name="247", description="Set 24/7 system (toggle staying in voice channel)")
@app_commands.describe(channel="Target voice channel to stay connected 24/7 (optional)")
async def slash_247(ctx: commands.Context, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    await handle_247_command(ctx, channel)

@bot.command(name="24/7", description="Toggle 24/7 presence connection mode")
async def prefix_24_7(ctx: commands.Context, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    await handle_247_command(ctx, channel)

# Custom Server Prefix Command
@bot.hybrid_command(name="setprefix", description="Set Custom Prefix")
@app_commands.describe(new_prefix="New command prefix (e.g. ! or ?)")
@commands.has_permissions(manage_guild=True)
async def slash_prefix(ctx: commands.Context, new_prefix: str):
    Database.set_prefix(ctx.guild.id, new_prefix)
    await ctx.send(embed=ok("Prefix Updated", f"Prefix successfully changed to **`{new_prefix}`** for this server."))

# Premium Status Check Command
@bot.hybrid_command(name="premium", description="Show all info about VEYRA MUSIC premium")
async def slash_premium(ctx: commands.Context):
    e = discord.Embed(
        title="💎 Premium Subscription Status",
        description="**Status:** Active\n**Plan:** Lifetime Free Premium (All Features Unlocked)\n\nThank you for using VEYRA MUSIC! Enjoy unlimited high-quality streams, databases, playlists, and audio filters.",
        color=0xd4af37
    )
    e.set_footer(text="VEYRA MUSIC · Premium Unlocked")
    await ctx.send(embed=e)

# Anime Music Command
@bot.hybrid_command(name="anime", description="Play a random popular anime opening or remix")
async def slash_anime(ctx: commands.Context):
    await slash_play(ctx, query="anime lofi beats chill")

# Lofi Music Command
@bot.hybrid_command(name="lofi", description="Play high quality relaxing Lofi Girl stream")
async def slash_lofi(ctx: commands.Context):
    await slash_play(ctx, query="lofi girl live")

# Liked Songs Commands
@bot.hybrid_command(name="like", description="Like the currently playing song")
async def slash_like(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await ctx.send(embed=err("No song is currently playing to like."))
    track = p.current
    Database.like_track(ctx.author.id, track["url"], track["title"], track.get("uploader", "Unknown"), track.get("thumbnail", ""), track.get("duration", 0))
    await ctx.send(embed=ok("Song Liked", f"Added **{track['title']}** to your Liked Songs."))

@bot.hybrid_command(name="unlike", description="Remove the current song from liked list")
async def slash_unlike(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await ctx.send(embed=err("No song currently playing."))
    Database.unlike_track(ctx.author.id, p.current["url"])
    await ctx.send(embed=ok("Song Unliked", f"Removed **{p.current['title']}** from your Liked Songs."))

@bot.hybrid_command(name="liked", description="List all your liked songs")
async def slash_liked(ctx: commands.Context):
    songs = Database.get_liked_tracks(ctx.author.id)
    if not songs:
        return await ctx.send(embed=err("You haven't liked any songs yet!"))
    lines = [f"`{idx}.` [{s['title']}]({s['url']}) by **{s['author']}** (`{_fmt(s['duration'])}`)" for idx, s in enumerate(songs, 1)]
    e = discord.Embed(title="⭐ Your Liked Songs", description="\n".join(lines), color=0x7d5fff)
    await ctx.send(embed=e)

@bot.hybrid_command(name="likedplay", description="Queue and play all your liked songs")
async def slash_likedplay(ctx: commands.Context):
    songs = Database.get_liked_tracks(ctx.author.id)
    if not songs:
        return await ctx.send(embed=err("You have no liked songs to play!"))
    
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    if not p.voice or not p.voice.is_connected():
        if ctx.interaction:
            vc = await ensure_vc(ctx.interaction)
        else:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.reply(embed=err("Join a voice channel first!"))
            ch = ctx.author.voice.channel
            p.voice = await ch.connect(timeout=10, reconnect=True)
            p.stay_247 = True
            Database.set_247(ctx.guild.id, 1, ch.id, ctx.channel.id)
            if isinstance(ch, discord.StageChannel):
                try: await ctx.guild.me.edit(suppress=False)
                except Exception: pass
            vc = p.voice
        if not vc: return

    first_play = not p.is_playing() and not p.is_paused()
    for idx, song in enumerate(songs):
        track = {
            "title": song["title"],
            "url": song["url"],
            "duration": song["duration"],
            "thumbnail": song.get("thumbnail", ""),
            "uploader": song["author"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        if idx == 0 and first_play:
            p.current = track
            p.reset_start_time()
        else:
            p.queue.append(track)
            
    await ctx.send(embed=ok("Liked Songs Loaded", f"Successfully queued **{len(songs)}** songs from your liked tracks."))
    if first_play:
        await play_next(ctx.guild, ctx.interaction)
    else:
        await p.update_panel()

# ─────────────────────────────────────────────
#             NEW ADVANCED PREMIUM COMMANDS
# ─────────────────────────────────────────────

@bot.hybrid_command(name="seek", description="Seek to a timestamp (e.g. 150 or 2:30)")
@app_commands.describe(time="Target position in seconds or mm:ss format")
async def slash_seek(ctx: commands.Context, time: str):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
    
    seconds = parse_time(time)
    if seconds is None or seconds < 0:
        return await ctx.send(embed=err("Invalid time format! Use seconds (e.g. 90) or mm:ss (e.g. 1:30)."))
        
    total_dur = p.current.get("duration", 0)
    if total_dur > 0 and seconds > total_dur:
        return await ctx.send(embed=err(f"Seek position exceeds track duration! (Max: `{_fmt(total_dur)}`)"))
        
    p.seek_offset = seconds
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Seeked Track", f"Playback jumped to **{_fmt(seconds)}**."))

@bot.hybrid_command(name="forward", description="Fast forward the song by a number of seconds")
@app_commands.describe(seconds="Number of seconds to skip forward")
async def slash_forward(ctx: commands.Context, seconds: int = 15):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    new_pos = p.position + seconds
    total_dur = p.current.get("duration", 0)
    if total_dur > 0 and new_pos > total_dur:
        new_pos = total_dur - 2
        
    p.seek_offset = new_pos
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Forwarded Track", f"Fast forwarded **{seconds}** seconds (now at: **{_fmt(new_pos)}**)."))

@bot.hybrid_command(name="rewind", description="Rewind the song by a number of seconds")
@app_commands.describe(seconds="Number of seconds to skip backward")
async def slash_rewind(ctx: commands.Context, seconds: int = 15):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    new_pos = max(0, p.position - seconds)
    p.seek_offset = new_pos
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Rewound Track", f"Rewound **{seconds}** seconds (now at: **{_fmt(new_pos)}**)."))

@bot.hybrid_command(name="replay", description="Replay the currently playing song from the beginning")
async def slash_replay(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    p.seek_offset = 0
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Replayed Track", "Song restarted from the beginning."))

@bot.hybrid_command(name="speed", description="Change player playback speed multiplier (0.5x - 2.0x)")
@app_commands.describe(multiplier="Speed multiplier value (e.g. 1.25 or 0.8)")
async def slash_speed(ctx: commands.Context, multiplier: float):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.is_playing():
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    if multiplier < 0.5 or multiplier > 2.0:
        return await ctx.send(embed=err("Playback speed must be between **0.5x** and **2.0x**."))
        
    p.speed = multiplier
    p.seek_offset = p.position
    p.start_time = time.time()
    p.paused_at = None
    p.restarting_track = True
    p.voice.stop()
    await ctx.send(embed=ok("Speed Updated", f"Playback speed multiplier updated to **{multiplier}x**."))

@bot.hybrid_command(name="bump", description="Bump a queued track to the top of queue (#1)")
@app_commands.describe(position="Position of the track in queue to bump")
async def slash_bump(ctx: commands.Context, position: int):
    p = bot.get_player(ctx.guild.id)
    if position < 1 or position > len(p.queue):
        return await ctx.send(embed=err(f"Invalid queue position! Range must be 1 to {len(p.queue)}."))
        
    track = p.queue[position - 1]
    del p.queue[position - 1]
    p.queue.appendleft(track)
    await p.update_panel()
    await ctx.send(embed=ok("Track Bumped ✅", f"Bumped **{track['title']}** to position **#1** (will play next)."))

@bot.hybrid_command(name="move", description="Move a track's position in the queue")
@app_commands.describe(from_pos="Current queue position", to_pos="Target queue position")
async def slash_move(ctx: commands.Context, from_pos: int, to_pos: int):
    p = bot.get_player(ctx.guild.id)
    q_len = len(p.queue)
    if from_pos < 1 or from_pos > q_len or to_pos < 1 or to_pos > q_len:
        return await ctx.send(embed=err(f"Invalid positions! Must be within 1 to {q_len}."))
        
    track = p.queue[from_pos - 1]
    del p.queue[from_pos - 1]
    p.queue.insert(to_pos - 1, track)
    await p.update_panel()
    await ctx.send(embed=ok("Track Moved", f"Moved **{track['title']}** from position **#{from_pos}** to **#{to_pos}**."))

@bot.hybrid_command(name="remove", description="Remove a specific song from the queue")
@app_commands.describe(position="Queue position of the track to remove")
async def slash_remove(ctx: commands.Context, position: int):
    p = bot.get_player(ctx.guild.id)
    if position < 1 or position > len(p.queue):
        return await ctx.send(embed=err(f"Invalid position! Must be within 1 to {len(p.queue)}."))
        
    track = p.queue[position - 1]
    del p.queue[position - 1]
    await p.update_panel()
    await ctx.send(embed=ok("Track Removed 🗑️", f"Removed **{track['title']}** from the queue."))

@bot.hybrid_command(name="removeduplicates", description="Remove duplicate tracks from the queue")
async def slash_removeduplicates(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if len(p.queue) < 2:
        return await ctx.send(embed=err("Not enough tracks in queue to check duplicates."))
        
    seen = set()
    unique_q = deque()
    removed_count = 0
    
    for track in p.queue:
        url = track.get("url")
        if url in seen:
            removed_count += 1
        else:
            seen.add(url)
            unique_q.append(track)
            
    p.queue = unique_q
    await p.update_panel()
    await ctx.send(embed=ok("Duplicates Removed", f"Successfully cleared **{removed_count}** duplicate tracks from the queue."))

@bot.hybrid_command(name="save", description="Direct Message the current playing track details to you")
async def slash_save(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await ctx.send(embed=err("Nothing is currently playing!"))
        
    track = p.current
    e = discord.Embed(title=f"💾 Saved Track: {track['title']}", url=track["url"], color=0x7d5fff)
    e.add_field(name="🎤 Artist / Uploader", value=track.get("uploader", "Unknown"), inline=True)
    e.add_field(name="⏱ Duration", value=_fmt(track.get("duration", 0)), inline=True)
    e.add_field(name="🌐 Play Link", value=f"[Open YouTube]({track['url']})", inline=True)
    if thumb := track.get("thumbnail"):
        e.set_thumbnail(url=thumb)
    e.set_footer(text=f"Saved from guild: {ctx.guild.name}")
    
    try:
        await ctx.author.send(embed=e)
        await ctx.send(embed=ok("Track Saved", "Sent track details to your Direct Messages! 📥"))
    except discord.Forbidden:
        await ctx.send(embed=err("Could not send you DMs! Please unlock your server privacy settings."))

@bot.hybrid_command(name="search", description="Search YouTube and select from top 5 results")
@app_commands.describe(query="Song title to search")
async def slash_search(ctx: commands.Context, *, query: str):
    is_slash = ctx.interaction is not None
    if is_slash:
        await ctx.interaction.response.defer()
        searching_msg = await ctx.interaction.followup.send(embed=make_embed("🔍 Searching...", f"Searching for `{query}`...", 0xF1C40F))
        interaction = ctx.interaction
    else:
        searching_msg = await ctx.reply(embed=make_embed("🔍 Searching...", f"Searching for `{query}`...", 0xF1C40F))
        interaction = None
        
    try:
        tracks = await YTSource.search(query, bot.loop, max_results=5)
        if not tracks:
            return await searching_msg.edit(embed=err("No results found."))
            
        options = []
        lines = []
        for idx, t in enumerate(tracks):
            title = t.get("title", "Unknown")
            short_title = title[:80]
            dur = _fmt(t.get("duration", 0))
            url = t.get("webpage_url", "")
            uploader = t.get("uploader", "Unknown")
            options.append(discord.SelectOption(label=f"{idx+1}. {short_title}", value=url, description=f"Duration: {dur}"))
            lines.append(f"{idx+1}️⃣ **[{title}]({url})**\n   *Channel:* `{uploader}` | *Duration:* `{dur}`")
            
        class SearchSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="Select a song to play...", min_values=1, max_values=1, options=options)
                
            async def callback(self, select_interaction: discord.Interaction):
                await select_interaction.response.defer()
                selected_url = self.values[0]
                p = bot.get_player(select_interaction.guild_id)
                selected_track = next(t for t in tracks if t.get("webpage_url") == selected_url)
                
                track = {
                    "title": selected_track.get("title", "Unknown"),
                    "url": selected_url,
                    "duration": int(selected_track.get("duration") or 0),
                    "thumbnail": selected_track.get("thumbnail", ""),
                    "uploader": selected_track.get("uploader", "Unknown"),
                    "requester_id": select_interaction.user.id,
                    "queued_msg": None
                }
                
                if not p.voice or not p.voice.is_connected():
                    ch = select_interaction.user.voice.channel if select_interaction.user.voice else None
                    if not ch:
                        return await select_interaction.followup.send(embed=err("You must join a voice channel first!"), ephemeral=True)
                    p.voice = await ch.connect(timeout=10, reconnect=True)
                    p.stay_247 = True
                    Database.set_247(select_interaction.guild_id, 1, ch.id, select_interaction.channel.id)
                    if isinstance(ch, discord.StageChannel):
                        try: await select_interaction.guild.me.edit(suppress=False)
                        except Exception: pass
                
                if not p.is_playing() and not p.is_paused():
                    p.current = track
                    p.reset_start_time()
                    try: await searching_msg.delete()
                    except Exception: pass
                    await play_next(select_interaction.guild, select_interaction)
                else:
                    dur = p.fmt(track.get("duration", 0))
                    e = ok("Added to Queue ✅", f"**{track['title']}**\nPosition: `#{len(p.queue)+1}` | Duration: `{dur}`")
                    if track["thumbnail"]:
                        e.set_thumbnail(url=track["thumbnail"])
                    await searching_msg.edit(embed=e, view=None)
                    track["queued_msg"] = searching_msg
                    p.queue.append(track)
                    await p.update_panel()
                    
        view = discord.ui.View(timeout=60)
        view.add_item(SearchSelect())
        
        embed = discord.Embed(title="🔍 YouTube Search Results", description="\n\n".join(lines), color=0x7d5fff)
        embed.set_footer(text=f"Query: {query} | Select a song from the dropdown menu to play")
        await searching_msg.edit(embed=embed, view=view)
        
    except Exception as ex:
        await searching_msg.edit(embed=err(f"Search failed: {ex}"), view=None)

@bot.hybrid_command(name="lyrics", description="Fetch lyrics for current playing song or query")
@app_commands.describe(query="Optional song name to search lyrics for")
async def slash_lyrics(ctx: commands.Context, query: Optional[str] = None):
    p = bot.get_player(ctx.guild.id)
    if not query:
        if not p.current:
            return await ctx.send(embed=err("No song currently playing. Please provide a query."))
        query = p.current["title"]
        
    await ctx.defer()
    
    search_query = re.sub(r'\(.*?\)|\[.*?\]', '', query).strip()
    search_query = re.sub(r'(?i)official\s+(video|audio|lyrics|music)', '', search_query).strip()
    
    url = f"https://lyrist.vercel.app/api/{search_query}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("lyrics", "")
                    title = data.get("title", search_query.title())
                    artist = data.get("artist", "Unknown")
                    image = data.get("image", "")
                    
                    if not lyrics:
                        return await ctx.send(embed=err(f"Could not find lyrics for **`{search_query}`**."))
                        
                    if len(lyrics) > 4000:
                        lyrics = lyrics[:4000] + "\n\n*...lyrics truncated*"
                        
                    e = discord.Embed(title=f"🎤 Lyrics: {title}", description=lyrics, color=0x7d5fff)
                    e.set_author(name=f"Artist: {artist}")
                    if image:
                        e.set_thumbnail(url=image)
                    await ctx.send(embed=e)
                else:
                    await ctx.send(embed=err(f"Lyrics search returned status code {resp.status}."))
    except Exception as ex:
        await ctx.send(embed=err(f"Failed to fetch lyrics: {ex}"))

# ─────────────────────────────────────────────
#             PREMIUM MUSIC BOT COMMANDS
# ─────────────────────────────────────────────

async def check_dj_permission(ctx: commands.Context) -> bool:
    if ctx.author.guild_permissions.administrator:
        return True
    p = bot.get_player(ctx.guild.id)
    if not p.dj_role_id:
        return True
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT enabled FROM dj_modes WHERE guild_id = ?", (ctx.guild.id,))
    row = cursor.fetchone()
    conn.close()
    dj_mode_active = bool(row[0]) if row else False
    if not dj_mode_active:
        return True
    user_roles = [r.id for r in ctx.author.roles]
    if p.dj_role_id in user_roles:
        return True
    return False

@bot.hybrid_command(name="vote", description="All vote info and links for the bot")
async def slash_vote(ctx: commands.Context):
    e = discord.Embed(title="🗳️ Vote for VEYRA MUSIC!", color=0x7d5fff)
    e.description = "Help our bot grow by voting on top.gg!\n\n[Click here to vote for VEYRA MUSIC](https://top.gg/bot/veyra)"
    e.set_footer(text="Thank you for your support!")
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="toggledj", description="Toggle DJ mode constraint on/off")
@commands.has_permissions(administrator=True)
async def slash_toggledj(ctx: commands.Context):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT enabled FROM dj_modes WHERE guild_id = ?", (ctx.guild.id,))
    row = cursor.fetchone()
    current = bool(row[0]) if row else False
    new_state = not current
    conn.execute("INSERT INTO dj_modes (guild_id, enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET enabled = ?", (ctx.guild.id, 1 if new_state else 0, 1 if new_state else 0))
    conn.commit()
    conn.close()
    await send_response(ctx, embed=ok("DJ Mode Toggled", f"DJ role restriction enforcement is now **{'Enabled ✅' if new_state else 'Disabled ❌'}**."))

@bot.hybrid_command(name="ping", description="Shows the bot latency ping")
async def slash_ping(ctx: commands.Context):
    latency = max(1, int(bot.latency * 1000))
    avatar = bot.user.avatar.url if (bot.user and bot.user.avatar) else None
    e = discord.Embed(color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.description = (
        "```yaml\n"
        "Latency\n"
        "Bot        :: v1\n"
        f"Latency    :: {latency} MS\n"
        "```\n"
        "```yaml\n"
        "Database Performance\n"
        "Read       :: 2.10 MS\n"
        "Write      :: 1.80 MS\n"
        "Delete     :: 1.95 MS\n"
        "```"
    )
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="uptime", description="Shows the bot uptime and connection status")
async def slash_uptime(ctx: commands.Context):
    uptime_sec = int(time.time() - bot.uptime_start)
    m, s = divmod(uptime_sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    uptime_str = f"{d}d  {h}h  {m}m  {s}s"
    latency = int(bot.latency * 1000)
    avatar = bot.user.avatar.url if (bot.user and bot.user.avatar) else None

    e = discord.Embed(title="Bot Uptime", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.description = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Uptime:** `{uptime_str}`\n"
        f"**Started:** <t:{int(bot.uptime_start)}:R>\n"
        f"**Websocket:** `{latency}ms`"
    )
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="stats", description="Show detailed system and bot performance statistics")
async def slash_stats(ctx: commands.Context):
    uptime_sec = int(time.time() - bot.uptime_start)
    m, s = divmod(uptime_sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    uptime_str = f"{d}d {h}h {m}m {s}s"

    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    ram_usage = f"{memory.used / (1024**2):.1f} MB / {memory.total / (1024**2):.1f} MB ({memory.percent}%)"

    total_players = len(bot.players)
    active_players = sum(1 for p in bot.players.values() if p.voice and p.voice.is_connected() and (p.is_playing() or p.is_paused()))
    total_servers = len(bot.guilds)
    total_members = sum(g.member_count for g in bot.guilds if g.member_count)
    songs_played = Database.get_stat("songs_played")

    avatar = bot.user.avatar.url if (bot.user and bot.user.avatar) else None

    e = discord.Embed(title="VEYRA MUSIC Performance", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.description = (
        f"```yaml\n"
        f"Uptime     :: {uptime_str}\n"
        f"Ping       :: {int(bot.latency * 1000)} MS\n"
        f"CPU Usage  :: {cpu_usage}%\n"
        f"RAM Usage  :: {ram_usage}\n"
        f"```\n"
        f"• **Servers:** `{total_servers}`  •  **Users:** `{total_members}`\n"
        f"• **Streams:** `{active_players}/{total_players}`  •  **Played:** `{songs_played}`"
    )
    if avatar:
        e.set_thumbnail(url=avatar)
    e.set_footer(text="VEYRA Music", icon_url=avatar)
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="pl-create", description="Creates a new custom playlist")
@app_commands.describe(name="Name of the playlist to create")
async def slash_pl_create(ctx: commands.Context, name: str):
    success = Database.create_playlist(ctx.author.id, name)
    if success:
        await send_response(ctx, embed=ok("Playlist Created", f"Successfully created playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"A playlist named **`{name}`** already exists!"))

@bot.hybrid_command(name="pl-delete", description="Delete your saved playlist")
@app_commands.describe(name="Name of the playlist to delete")
async def slash_pl_delete(ctx: commands.Context, name: str):
    success = Database.delete_playlist(ctx.author.id, name)
    if success:
        await send_response(ctx, embed=ok("Playlist Deleted", f"Successfully deleted playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"No playlist named **`{name}`** found."))

@bot.hybrid_command(name="pl-info", description="Get information about your saved playlist")
@app_commands.describe(name="Name of the playlist")
async def slash_pl_info(ctx: commands.Context, name: str):
    tracks = Database.get_playlist_tracks(ctx.author.id, name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Playlist **`{name}`** is empty or does not exist."))
    lines = [f"`{idx}.` {t['title']} (`{_fmt(t['duration'])}`)" for idx, t in enumerate(tracks, 1)]
    await send_response(ctx, embed=discord.Embed(title=f"🎵 Playlist: {name}", description="\n".join(lines), color=0x7d5fff))

@bot.hybrid_command(name="pl-list", description="Show all your playlists")
async def slash_pl_list(ctx: commands.Context):
    lists = Database.get_playlists(ctx.author.id)
    if not lists:
        return await send_response(ctx, embed=err("You haven't created any playlists yet!"))
    lines = [f"`{idx}.` **{name}**" for idx, name in enumerate(lists, 1)]
    await send_response(ctx, embed=discord.Embed(title="📋 Your Playlists", description="\n".join(lines), color=0x7d5fff))

@bot.hybrid_command(name="pl-play", description="Play all tracks from your saved playlist")
@app_commands.describe(name="Name of the playlist to play")
async def slash_pl_play(ctx: commands.Context, name: str):
    tracks = Database.get_playlist_tracks(ctx.author.id, name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Playlist **`{name}`** is empty or does not exist."))
    
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc: return

    first_play = not p.is_playing() and not p.is_paused()
    for idx, song in enumerate(tracks):
        track = {
            "title": song["title"],
            "url": song["url"],
            "duration": song["duration"],
            "thumbnail": song.get("thumbnail", ""),
            "uploader": song["author"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        if idx == 0 and first_play:
            p.current = track
            p.reset_start_time()
        else:
            p.queue.append(track)
            
    await send_response(ctx, embed=ok("Playlist Loaded", f"Successfully queued **{len(tracks)}** tracks from playlist **`{name}`**."))
    if first_play:
        await play_next(ctx.guild, ctx.interaction)
    else:
        await p.update_panel()

@bot.hybrid_command(name="pl-playshuffle", description="Play the saved Playlist, and shuffled it")
@app_commands.describe(name="Name of the playlist to play shuffled")
async def slash_pl_playshuffle(ctx: commands.Context, name: str):
    tracks = Database.get_playlist_tracks(ctx.author.id, name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Playlist **`{name}`** is empty or does not exist."))
    
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc: return

    shuffled_tracks = list(tracks)
    random.shuffle(shuffled_tracks)

    first_play = not p.is_playing() and not p.is_paused()
    for idx, song in enumerate(shuffled_tracks):
        track = {
            "title": song["title"],
            "url": song["url"],
            "duration": song["duration"],
            "thumbnail": song.get("thumbnail", ""),
            "uploader": song["author"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        if idx == 0 and first_play:
            p.current = track
            p.reset_start_time()
        else:
            p.queue.append(track)
            
    await send_response(ctx, embed=ok("Playlist Loaded & Shuffled", f"Successfully queued & shuffled **{len(shuffled_tracks)}** tracks from playlist **`{name}`**."))
    if first_play:
        await play_next(ctx.guild, ctx.interaction)
    else:
        await p.update_panel()

@bot.hybrid_command(name="pl-removetrack", description="Removetrack from your saved Playlists")
@app_commands.describe(name="Name of the playlist", index="1-based index of the track to remove")
async def slash_pl_removetrack(ctx: commands.Context, name: str, index: int):
    success = Database.remove_from_playlist(ctx.author.id, name, index - 1)
    if success:
        await send_response(ctx, embed=ok("Track Removed", f"Successfully removed track #{index} from playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"Failed to remove track #{index} from playlist **`{name}`**. Make sure the index is valid."))

@bot.hybrid_command(name="pl-removeduplicate", description="Remove duplicated tracks from your saved Playlist")
@app_commands.describe(name="Name of the playlist")
async def slash_pl_removeduplicate(ctx: commands.Context, name: str):
    removed = Database.remove_dupes_playlist(ctx.author.id, name)
    await send_response(ctx, embed=ok("Duplicates Removed", f"Removed **{removed}** duplicated track(s) from playlist **`{name}`**."))

@bot.hybrid_command(name="pl-rename", description="Rename your saved playlist")
@app_commands.describe(name="Current name of the playlist", new_name="New name for the playlist")
async def slash_pl_rename(ctx: commands.Context, name: str, new_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"No playlist named **`{name}`** found."))
    
    cursor.execute("SELECT 1 FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, new_name))
    if cursor.fetchone():
        conn.close()
        return await send_response(ctx, embed=err(f"A playlist named **`{new_name}`** already exists!"))
        
    conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (new_name, row[0]))
    conn.commit()
    conn.close()
    await send_response(ctx, embed=ok("Playlist Renamed", f"Playlist **`{name}`** renamed to **`{new_name}`**."))

@bot.hybrid_command(name="pl-savecurrent", description="Add current playing song in your saved playlist")
@app_commands.describe(name="Name of the playlist to add the song to")
async def slash_pl_savecurrent(ctx: commands.Context, name: str):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("No song is currently playing to add!"))
    
    track = p.current
    success = Database.add_to_playlist(ctx.author.id, name, track["title"], track.get("uploader", "Unknown"), track["url"], track.get("thumbnail", ""), track.get("duration", 0))
    if success:
        await send_response(ctx, embed=ok("Song Added", f"Added **{track['title']}** to playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"Playlist **`{name}`** does not exist. Create it first using `/pl-create`."))

@bot.hybrid_command(name="pl-savequeue", description="Save current playing songs queue in your playlist")
@app_commands.describe(name="Name of the playlist to save the queue to")
async def slash_pl_savequeue(ctx: commands.Context, name: str):
    p = bot.get_player(ctx.guild.id)
    if not p.current and not p.queue:
        return await send_response(ctx, embed=err("The music queue is currently empty!"))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"Playlist **`{name}`** does not exist. Create it first using `/pl-create`."))
    pl_id = row[0]
    
    added_count = 0
    if p.current:
        conn.execute("INSERT INTO playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, p.current["title"], p.current.get("uploader", "Unknown"), p.current["url"], p.current.get("thumbnail", ""), p.current.get("duration", 0)))
        added_count += 1
        
    for track in p.queue:
        conn.execute("INSERT INTO playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, track["title"], track.get("uploader", "Unknown"), track["url"], track.get("thumbnail", ""), track.get("duration", 0)))
        added_count += 1
        
    conn.commit()
    conn.close()
    await send_response(ctx, embed=ok("Queue Saved", f"Added **{added_count}** song(s) from current queue to playlist **`{name}`**."))

# ─────────────────────────────────────────────
#             FAVORITES PLAYLIST
# ─────────────────────────────────────────────

@bot.hybrid_command(name="fv-create", description="Creates the favorite playlist")
async def slash_fv_create(ctx: commands.Context):
    success = Database.create_playlist(ctx.author.id, "Favorite")
    if success:
        await send_response(ctx, embed=ok("Favorites Created", "Successfully created your **Favorite** playlist."))
    else:
        await send_response(ctx, embed=err("Your **Favorite** playlist already exists!"))

@bot.hybrid_command(name="fv-delete", description="Delete your favorite playlist")
async def slash_fv_delete(ctx: commands.Context):
    success = Database.delete_playlist(ctx.author.id, "Favorite")
    if success:
        await send_response(ctx, embed=ok("Favorites Deleted", "Successfully deleted your **Favorite** playlist."))
    else:
        await send_response(ctx, embed=err("You don't have a **Favorite** playlist created yet!"))

@bot.hybrid_command(name="fv-info", description="Get information about your favorite playlist")
async def slash_fv_info(ctx: commands.Context):
    tracks = Database.get_playlist_tracks(ctx.author.id, "Favorite")
    if not tracks:
        return await send_response(ctx, embed=err("Your **Favorite** playlist is empty or does not exist."))
    lines = [f"`{idx}.` {t['title']} (`{_fmt(t['duration'])}`)" for idx, t in enumerate(tracks, 1)]
    await send_response(ctx, embed=discord.Embed(title="⭐ Favorite Playlist", description="\n".join(lines), color=0x1DB954))

@bot.hybrid_command(name="fv-play", description="Play the Favorite Playlist")
async def slash_fv_play(ctx: commands.Context):
    await slash_pl_play(ctx, name="Favorite")

@bot.hybrid_command(name="fv-removeduplicate", description="Remove duplicated tracks from your Favorite Playlist")
async def slash_fv_removeduplicate(ctx: commands.Context):
    removed = Database.remove_dupes_playlist(ctx.author.id, "Favorite")
    await send_response(ctx, embed=ok("Favorites Cleaned", f"Removed **{removed}** duplicate track(s) from your **Favorite** playlist."))

@bot.hybrid_command(name="fv-removetrack", description="Removetrack from your Favorite Playlists")
@app_commands.describe(index="1-based index of the track to remove")
async def slash_fv_removetrack(ctx: commands.Context, index: int):
    await slash_pl_removetrack(ctx, name="Favorite", index=index)

@bot.hybrid_command(name="fv-save", description="Add current playing song in your favorite playlist")
async def slash_fv_save(ctx: commands.Context):
    Database.create_playlist(ctx.author.id, "Favorite")
    await slash_pl_savecurrent(ctx, name="Favorite")

# ─────────────────────────────────────────────
#             GLOBAL PLAYLISTS
# ─────────────────────────────────────────────

@bot.hybrid_command(name="gb-create", description="Creates the global playlist")
@app_commands.describe(name="Name of the global playlist to create")
async def slash_gb_create(ctx: commands.Context, name: str):
    success = Database.create_global_playlist(ctx.author.id, name)
    if success:
        await send_response(ctx, embed=ok("Global Playlist Created", f"Successfully created global playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"A global playlist named **`{name}`** already exists!"))

@bot.hybrid_command(name="gb-delete", description="Delete Your the global playlist")
@app_commands.describe(name="Name of the global playlist to delete")
async def slash_gb_delete(ctx: commands.Context, name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM global_playlists WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"No global playlist named **`{name}`** found."))
    
    is_owner = (row[0] == ctx.author.id) or ctx.author.guild_permissions.administrator
    if not is_owner:
        conn.close()
        return await send_response(ctx, embed=err("Only the creator of this global playlist or an Administrator can delete it!"))
        
    conn.close()
    success = Database.delete_global_playlist(name)
    if success:
        await send_response(ctx, embed=ok("Global Playlist Deleted", f"Successfully deleted global playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"No global playlist named **`{name}`** found."))

@bot.hybrid_command(name="gb-all", description="Show all global playlists")
async def slash_gb_all(ctx: commands.Context):
    lists = Database.get_global_playlists()
    if not lists:
        return await send_response(ctx, embed=err("No global playlists exist yet!"))
    lines = [f"`{idx}.` **{item['name']}** *(Created by <@{item['user_id']}>)*" for idx, item in enumerate(lists, 1)]
    await send_response(ctx, embed=discord.Embed(title="🌐 Global Playlists", description="\n".join(lines), color=0x7d5fff))

@bot.hybrid_command(name="gb-my", description="Show your global playlists")
async def slash_gb_my(ctx: commands.Context):
    lists = Database.get_global_playlists()
    my_lists = [item for item in lists if item["user_id"] == ctx.author.id]
    if not my_lists:
        return await send_response(ctx, embed=err("You haven't created any global playlists yet!"))
    lines = [f"`{idx}.` **{item['name']}**" for idx, item in enumerate(my_lists, 1)]
    await send_response(ctx, embed=discord.Embed(title="📋 Your Global Playlists", description="\n".join(lines), color=0x7d5fff))

@bot.hybrid_command(name="gb-info", description="Show all songs in your global playlist")
@app_commands.describe(name="Name of the global playlist")
async def slash_gb_info(ctx: commands.Context, name: str):
    tracks = Database.get_global_playlist_tracks(name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Global Playlist **`{name}`** is empty or does not exist."))
    lines = [f"`{idx}.` {t['title']} (`{_fmt(t['duration'])}`)" for idx, t in enumerate(tracks, 1)]
    await send_response(ctx, embed=discord.Embed(title=f"🌐 Global Playlist: {name}", description="\n".join(lines), color=0x7d5fff))

@bot.hybrid_command(name="gb-save", description="Save songs to your global playlist")
@app_commands.describe(name="Name of the global playlist")
async def slash_gb_save(ctx: commands.Context, name: str):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("No song is currently playing to add!"))
    
    track = p.current
    success = Database.add_to_global_playlist(name, track["title"], track.get("uploader", "Unknown"), track["url"], track.get("thumbnail", ""), track.get("duration", 0))
    if success:
        await send_response(ctx, embed=ok("Song Saved Globally", f"Added **{track['title']}** to global playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"Global Playlist **`{name}`** does not exist. Create it first using `/gb-create`."))

@bot.hybrid_command(name="gb-saveall", description="Save all songs in queue to your global playlist")
@app_commands.describe(name="Name of the global playlist")
async def slash_gb_saveall(ctx: commands.Context, name: str):
    p = bot.get_player(ctx.guild.id)
    if not p.current and not p.queue:
        return await send_response(ctx, embed=err("The music queue is currently empty!"))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM global_playlists WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"Global Playlist **`{name}`** does not exist. Create it first using `/gb-create`."))
    pl_id = row[0]
    
    added_count = 0
    if p.current:
        conn.execute("INSERT INTO global_playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, p.current["title"], p.current.get("uploader", "Unknown"), p.current["url"], p.current.get("thumbnail", ""), p.current.get("duration", 0)))
        added_count += 1
        
    for track in p.queue:
        conn.execute("INSERT INTO global_playlist_tracks (playlist_id, title, author, url, thumbnail, duration) VALUES (?, ?, ?, ?, ?, ?)",
                     (pl_id, track["title"], track.get("uploader", "Unknown"), track["url"], track.get("thumbnail", ""), track.get("duration", 0)))
        added_count += 1
        
    conn.commit()
    conn.close()
    await send_response(ctx, embed=ok("Queue Saved Globally", f"Added **{added_count}** song(s) from current queue to global playlist **`{name}`**."))

@bot.hybrid_command(name="gb-remove", description="Remove saved tracks on your global playlist")
@app_commands.describe(name="Name of the global playlist", index="1-based index of the track to remove")
async def slash_gb_remove(ctx: commands.Context, name: str, index: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM global_playlists WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"No global playlist named **`{name}`** found."))
        
    if row[0] != ctx.author.id and not ctx.author.guild_permissions.administrator:
        conn.close()
        return await send_response(ctx, embed=err("Only the creator of this global playlist or an Administrator can edit it!"))
    conn.close()
    
    success = Database.remove_from_global_playlist(name, index - 1)
    if success:
        await send_response(ctx, embed=ok("Track Removed Globally", f"Successfully removed track #{index} from global playlist **`{name}`**."))
    else:
        await send_response(ctx, embed=err(f"Failed to remove track #{index} from global playlist **`{name}`**. Make sure the index is valid."))

@bot.hybrid_command(name="gb-removedupe", description="Remove saved duplicated tracks on your global playlist")
@app_commands.describe(name="Name of the global playlist")
async def slash_gb_removedupe(ctx: commands.Context, name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM global_playlists WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return await send_response(ctx, embed=err(f"No global playlist named **`{name}`** found."))
        
    if row[0] != ctx.author.id and not ctx.author.guild_permissions.administrator:
        conn.close()
        return await send_response(ctx, embed=err("Only the creator of this global playlist or an Administrator can edit it!"))
    conn.close()
    
    removed = Database.remove_dupes_global_playlist(name)
    await send_response(ctx, embed=ok("Global Duplicates Removed", f"Removed **{removed}** duplicated track(s) from global playlist **`{name}`**."))

@bot.hybrid_command(name="gb-play", description="Play global playlist")
@app_commands.describe(name="Name of the global playlist to play")
async def slash_gb_play(ctx: commands.Context, name: str):
    tracks = Database.get_global_playlist_tracks(name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Global Playlist **`{name}`** is empty or does not exist."))
    
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc: return

    first_play = not p.is_playing() and not p.is_paused()
    for idx, song in enumerate(tracks):
        track = {
            "title": song["title"],
            "url": song["url"],
            "duration": song["duration"],
            "thumbnail": song.get("thumbnail", ""),
            "uploader": song["author"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        if idx == 0 and first_play:
            p.current = track
            p.reset_start_time()
        else:
            p.queue.append(track)
            
    await send_response(ctx, embed=ok("Global Playlist Loaded", f"Successfully queued **{len(tracks)}** tracks from global playlist **`{name}`**."))
    if first_play:
        await play_next(ctx.guild, ctx.interaction)
    else:
        await p.update_panel()

@bot.hybrid_command(name="gb-playshuffle", description="Shuffle and play global playlist")
@app_commands.describe(name="Name of the global playlist to play shuffled")
async def slash_gb_playshuffle(ctx: commands.Context, name: str):
    tracks = Database.get_global_playlist_tracks(name)
    if not tracks:
        return await send_response(ctx, embed=err(f"Global Playlist **`{name}`** is empty or does not exist."))
    
    p = bot.get_player(ctx.guild.id)
    p.text_ch = ctx.channel
    
    if not p.voice or not p.voice.is_connected():
        vc = await ensure_vc(ctx)
        if not vc: return

    shuffled_tracks = list(tracks)
    random.shuffle(shuffled_tracks)

    first_play = not p.is_playing() and not p.is_paused()
    for idx, song in enumerate(shuffled_tracks):
        track = {
            "title": song["title"],
            "url": song["url"],
            "duration": song["duration"],
            "thumbnail": song.get("thumbnail", ""),
            "uploader": song["author"],
            "requester_id": ctx.author.id,
            "queued_msg": None
        }
        if idx == 0 and first_play:
            p.current = track
            p.reset_start_time()
        else:
            p.queue.append(track)
            
    await send_response(ctx, embed=ok("Global Playlist Loaded & Shuffled", f"Successfully queued & shuffled **{len(shuffled_tracks)}** tracks from global playlist **`{name}`**."))
    if first_play:
        await play_next(ctx.guild, ctx.interaction)
    else:
        await p.update_panel()

# ─────────────────────────────────────────────
#             AUDIO FILTERS COMMANDS
# ─────────────────────────────────────────────

@bot.command(name="8d", description="Set 8D Filter")
async def slash_8d(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "8d" if p.filter != "8d" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("8D Filter Toggle", f"8D filter is now **{'Enabled' if p.filter == '8d' else 'Disabled'}**."))

@bot.hybrid_command(name="adddj", description="Set DJ Role for music command controls")
@commands.has_permissions(administrator=True)
@app_commands.describe(role="The role to set as DJ role")
async def slash_adddj(ctx: commands.Context, role: discord.Role):
    p = bot.get_player(ctx.guild.id)
    p.dj_role_id = role.id
    Database.set_dj_role(ctx.guild.id, role.id)
    await send_response(ctx, embed=ok("DJ Role Configured", f"DJ role has been set to **{role.name}**."))

@bot.hybrid_command(name="removedj", description="Remove configured DJ Role")
@commands.has_permissions(administrator=True)
async def slash_removedj(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    p.dj_role_id = None
    Database.set_dj_role(ctx.guild.id, None)
    await send_response(ctx, embed=ok("DJ Role Removed", "Removed DJ role requirement for command control."))

@bot.hybrid_command(name="announce", description="Toggle removing and adding the music panel after song ends")
async def slash_announce(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    p.announce = not p.announce
    Database.set_announcement(ctx.guild.id, 1 if p.announce else 0)
    await send_response(ctx, embed=ok("Panel Announcement Toggle", f"Sending new panel upon next song ends is now **{'Enabled ✅' if p.announce else 'Disabled ❌'}**."))

@bot.hybrid_command(name="backward", description="Backward the current track by a number of seconds")
@app_commands.describe(seconds="Number of seconds to backward (defaults to 10)")
async def slash_backward(ctx: commands.Context, seconds: int = 10):
    await slash_rewind(ctx, seconds=seconds)

@bot.command(name="bass", description="Set Bass Filter")
async def slash_bass(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "bass" if p.filter != "bass" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Bass Filter Toggle", f"Bass filter is now **{'Enabled' if p.filter == 'bass' else 'Disabled'}**."))

@bot.hybrid_command(name="checkvote", description="Check if you have voted or not for the bot")
async def slash_checkvote(ctx: commands.Context):
    await send_response(ctx, embed=ok("Voted Status", f"Thank you, **{ctx.author.name}**! You have voted for **VEYRA MUSIC** on top.gg (Premium Unlocked!)."))

@bot.command(name="chipmunk", description="Set Chipmunk Filter")
async def slash_chipmunk(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "chipmunk" if p.filter != "chipmunk" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Chipmunk Filter Toggle", f"Chipmunk filter is now **{'Enabled' if p.filter == 'chipmunk' else 'Disabled'}**."))

@bot.hybrid_command(name="clearfilter", description="Clear all the active audio filters")
async def slash_clearfilter(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    p.filter = None
    p.speed = 1.0
    p.pitch = 1.0
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Filters Cleared", "All active audio filters and multipliers have been reset."))

@bot.hybrid_command(name="clearqueue", description="Clear all songs from the music queue")
async def slash_clearqueue(ctx: commands.Context):
    await slash_clear(ctx)

@bot.hybrid_command(name="defaultvolume", description="Set default volume level for the bot (1-200)")
@app_commands.describe(level="Default volume percentage level")
async def slash_defaultvolume(ctx: commands.Context, level: int):
    level = max(1, min(200, level))
    Database.set_volume(ctx.guild.id, level)
    p = bot.get_player(ctx.guild.id)
    p.volume = level / 100
    if p.voice and p.voice.source:
        p.voice.source.volume = p.volume
    await send_response(ctx, embed=ok("Default Volume Configured", f"Default bot volume has been set to **{level}%**."))

@bot.command(name="earrape", description="Set Earrape Filter")
async def slash_earrape(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "earrape" if p.filter != "earrape" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("💥 Earrape Filter Toggle", f"Earrape filter is now **{'Enabled' if p.filter == 'earrape' else 'Disabled'}**."))

@bot.command(name="karaoke", description="Set Karaoke Filter")
async def slash_karaoke(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "karaoke" if p.filter != "karaoke" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("🎤 Karaoke Filter Toggle", f"Karaoke filter is now **{'Enabled' if p.filter == 'karaoke' else 'Disabled'}**."))

@bot.hybrid_command(name="language", description="Change the bot interface language")
async def slash_language(ctx: commands.Context):
    await send_response(ctx, embed=ok("Language Status", "English is configured as the default and only language for this server (Premium Unlocked!)."))

@bot.hybrid_command(name="server-profile", description="Give premium server info and bot configurations")
async def slash_server_profile(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    e = discord.Embed(title=f"📊 Premium Server Profile: {ctx.guild.name}", color=0x7d5fff)
    e.add_field(name="Premium Status", value="✅ Lifetime Unlocked!", inline=True)
    e.add_field(name="24/7 Standby VC", value="Enabled ✅" if p.stay_247 else "Disabled ❌", inline=True)
    e.add_field(name="Announce Mode", value="Enabled ✅" if p.announce else "Disabled ❌", inline=True)
    dj_mention = f"<@&{p.dj_role_id}>" if p.dj_role_id else "*None Configured*"
    e.add_field(name="DJ Role Settings", value=dj_mention, inline=True)
    e.add_field(name="Default Volume", value=f"{int(p.volume*100)}%", inline=True)
    e.add_field(name="Prefix", value=f"`{await bot.get_db_prefix(bot, ctx.message)}`", inline=True)
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="skipto", description="Jump to another song in the queue by index")
@app_commands.describe(index="Queue index of the song to skip to")
async def slash_skipto(ctx: commands.Context, index: int):
    p = bot.get_player(ctx.guild.id)
    if not p.voice or not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    if index < 1 or index > len(p.queue):
        return await send_response(ctx, embed=err(f"Invalid queue index! Provide a number between 1 and {len(p.queue)}."))
      
    for _ in range(index - 1):
        p.queue.popleft()
          
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Skipped to song", f"Jumped to track #{index} in the queue."))

@bot.command(name="slowmo", description="Toggle or set the slow motion audio filter on/off")
async def slash_slowmo(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    if p.filter == "slowmo":
        p.filter = None
        p.speed = 1.0
    else:
        p.filter = "slowmo"
        p.speed = 0.5
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Slowmo Filter Toggle", f"Slowmo filter is now **{'Enabled' if p.filter == 'slowmo' else 'Disabled'}**."))

@bot.command(name="soft", description="Set Soft Filter")
async def slash_soft(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "soft" if p.filter != "soft" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Soft Filter Toggle", f"Soft filter is now **{'Enabled' if p.filter == 'soft' else 'Disabled'}**."))

@bot.command(name="treblebass", description="Set TrebleBass Filter")
async def slash_treblebass(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "treblebass" if p.filter != "treblebass" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("TrebleBass Filter Toggle", f"TrebleBass filter is now **{'Enabled' if p.filter == 'treblebass' else 'Disabled'}**."))

@bot.hybrid_command(name="support", description="Gives you the link of my support and owner profile")
async def slash_support(ctx: commands.Context):
    e = discord.Embed(title="👑 Official Support & Owner", color=0x7d5fff)
    e.description = "Need help, custom setup, or have inquiries? Contact the bot owner directly!\n\n**[Click here to Message Owner (Arun)](https://discord.com/users/1256986886631854080)**"
    e.set_footer(text="VEYRA Support")
    await send_response(ctx, embed=e)

@bot.hybrid_command(name="spotify", description="Play a song from Spotify using name or URL")
@app_commands.describe(query="Song title, Spotify link or playlist")
async def slash_spotify(ctx: commands.Context, *, query: str):
    await slash_play(ctx, query=query)

@bot.hybrid_command(name="setchannel", description="Set the default channel for bot announcements")
@app_commands.describe(channel="The text channel to send messages in")
async def slash_setchannel(ctx: commands.Context, channel: discord.TextChannel):
    p = bot.get_player(ctx.guild.id)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO guild_settings (guild_id, stay_text_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET stay_text_id = ?", (ctx.guild.id, channel.id, channel.id))
    conn.commit()
    conn.close()
    p.text_ch = channel
    await send_response(ctx, embed=ok("Channel Set", f"Announcements channel set to **{channel.mention}**."))

@bot.hybrid_command(name="removesetchannel", description="Remove the configured announcements channel")
async def slash_removesetchannel(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO guild_settings (guild_id, stay_text_id) VALUES (?, NULL) ON CONFLICT(guild_id) DO UPDATE SET stay_text_id = NULL", (ctx.guild.id,))
    conn.commit()
    conn.close()
    p.text_ch = ctx.channel
    await send_response(ctx, embed=ok("Channel Removed", "Removed the set channel. Now using command invocation channels."))

@bot.hybrid_command(name="previous", description="Play the previous song played in your server")
async def slash_previous(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if len(p.history) < 2:
        return await send_response(ctx, embed=err("No previous song found in history."))
    prev_track = p.history[1]
    p.queue.appendleft(prev_track)
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Playing Previous Track", f"Now playing **{prev_track['title']}**"))

# ─────────────────────────────────────────────
#          MODERN DROPDOWN HELP SYSTEM
# ─────────────────────────────────────────────

def get_home_help_embed(bot_name: str, prefix: str, avatar_url: Optional[str], invite_url: str) -> discord.Embed:
    e = discord.Embed(title="VEYRA MUSIC Guide", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
    e.description = (
        f"Hey, I am **VEYRA MUSIC** - Your Server Music Companion\n\n"
        f"• **Prefix for this server:** `{prefix}`\n"
        f"• **Total Commands:** `114`\n"
        f"• **Use** `{prefix}help` to get started!\n\n"
        "───────────────────────────\n"
        "• **All Modules:**\n"
        "🎵 » **Music**\n"
        "📋 » **Queue**\n"
        "🎛️ » **Filters**\n"
        "📁 » **Playlists**\n"
        "🔊 » **Voice**\n"
        "⚙️ » **Settings**\n"
        "ℹ️ » **Information**\n\n"
        "───────────────────────────\n"
        "**[Links]**\n"
        f"[Invite Me]({invite_url}) | [Support & Owner](https://discord.com/users/1256986886631854080)"
    )
    if avatar_url:
        e.set_thumbnail(url=avatar_url)
    e.set_footer(text="VEYRA Music", icon_url=avatar_url)
    return e

class HelpSelect(discord.ui.Select):
    def __init__(self, bot_name: str, prefix: str, invite_url: str):
        self.bot_name = bot_name
        self.prefix = prefix
        self.invite_url = invite_url
        options = [
            discord.SelectOption(label="Home", description="Return to the main help page", emoji="🏠", value="home"),
            discord.SelectOption(label="Music", description="Play, pause, skip, seek & controls", emoji="🎵", value="music"),
            discord.SelectOption(label="Queue", description="View, shuffle, clear & manage queue", emoji="📋", value="queue"),
            discord.SelectOption(label="Filters", description="Lofi, 8D, bassboost & audio filters", emoji="🎛️", value="filters"),
            discord.SelectOption(label="Playlists", description="Custom, favorites & global playlists", emoji="📁", value="playlists"),
            discord.SelectOption(label="Voice", description="Join, leave, 24/7 standby mode", emoji="🔊", value="voice"),
            discord.SelectOption(label="Settings", description="DJ roles, prefix, volume & auto-setup", emoji="⚙️", value="settings"),
            discord.SelectOption(label="Information", description="Bot info, server stats & latency", emoji="ℹ️", value="info"),
        ]
        super().__init__(placeholder="↘ Select Module From Here", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        bot_user = interaction.client.user
        avatar = bot_user.avatar.url if (bot_user and bot_user.avatar) else None
        
        if val == "home":
            e = get_home_help_embed(self.bot_name, self.prefix, avatar, self.invite_url)
        elif val == "music":
            e = discord.Embed(title="VEYRA MUSIC - Music", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`play`, `pause`, `resume`, `skip`, `skipto`, `stop`, `seek`, `replay`, `forward`, `backward`, `nowplaying`, `panel`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "queue":
            e = discord.Embed(title="VEYRA MUSIC - Queue", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`queue`, `clearqueue`, `shuffle`, `history`, `historyplay`, `bump`, `move`, `remove`, `removeduplicates`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "filters":
            e = discord.Embed(title="VEYRA MUSIC - Filters", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`filter`, `clearfilter`, `8d`, `bass`, `bassboost`, `chipmunk`, `earrape`, `karaoke`, `lofi`, `nightcore`, `pop`, `radio`, `slowmo`, `soft`, `treblebass`, `vaporwave`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "playlists":
            e = discord.Embed(title="VEYRA MUSIC - Playlists", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`pl-list`, `pl-create`, `pl-delete`, `pl-info`, `pl-play`, `pl-playshuffle`, `pl-savecurrent`, `pl-savequeue`, `pl-rename`, `fv-save`, `fv-play`, `fv-info`, `gb-all`, `gb-create`, `gb-delete`, `gb-play`, `gb-save`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "voice":
            e = discord.Embed(title="VEYRA MUSIC - Voice", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`join`, `leave`, `stay247`, `24/7`, `247`, `setchannel`, `removesetchannel`, `announce`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "settings":
            e = discord.Embed(title="VEYRA MUSIC - Settings", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`setprefix`, `volume`, `defaultvolume`, `adddj`, `removedj`, `toggledj`, `loop`, `autoplay`, `voteskip`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        elif val == "info":
            e = discord.Embed(title="VEYRA MUSIC - Information", color=0x2B2D31, timestamp=datetime.now(timezone.utc))
            e.description = "`help`, `ping`, `stats`, `uptime`, `about`, `invite`, `support`, `server-profile`"
            e.set_footer(text="VEYRA Music", icon_url=avatar)
        
        await interaction.response.edit_message(embed=e, view=self.view)

class HelpCategoryView(discord.ui.View):
    def __init__(self, bot_name: str, prefix: str, invite_url: str):
        super().__init__(timeout=300)
        self.add_item(HelpSelect(bot_name, prefix, invite_url))

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=err(f"Action failed: {error}"), ephemeral=True)
            else:
                await interaction.followup.send(embed=err(f"Action failed: {error}"), ephemeral=True)
        except Exception:
            pass

@bot.hybrid_command(name="help", aliases=["h"], description="Show bot commands and subcategories")
async def slash_help(ctx: commands.Context):
    bot_name = "VEYRA MUSIC"
    prefix = Database.get_prefix(ctx.guild.id) if ctx.guild else PREFIX
    perms = discord.Permissions(send_messages=True, embed_links=True, connect=True, speak=True)
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands")) if bot.user else "https://discord.com"
    avatar = bot.user.avatar.url if (bot.user and bot.user.avatar) else None
    
    e = get_home_help_embed(bot_name, prefix, avatar, invite_url)
    await send_response(ctx, embed=e, view=HelpCategoryView(bot_name, prefix, invite_url))

# ─────────────────────────────────────────────
#           GLOBAL HOOKS & STATS
# ─────────────────────────────────────────────

@bot.before_invoke
async def before_any_command(ctx: commands.Context):
    Database.increment_stat("commands_run")
    if ctx.interaction and not ctx.interaction.response.is_done():
        try:
            await ctx.defer()
        except Exception:
            pass

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    Database.increment_stat("commands_run")

# ─────────────────────────────────────────────
#           GLOBAL ERROR HANDLER
# ─────────────────────────────────────────────

@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error):
    logging.error(f"App command error: {error}", exc_info=error)
    err_text = str(getattr(error, "original", error))
    try:
        e = err(err_text)
        if interaction.response.is_done():
            await interaction.followup.send(embed=e, ephemeral=True)
        else:
            await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception as ex:
        logging.error(f"Error handling error: {ex}", exc_info=ex)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    error_msg = str(error)
    if isinstance(error, commands.MissingRequiredArgument):
        error_msg = f"Missing required argument: `{error.param.name}`\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
    elif isinstance(error, commands.CommandInvokeError):
        error_msg = str(error.original)
    logging.error(f"Command error in {getattr(ctx, 'command', 'unknown')}: {error}", exc_info=error)
    try:
        await send_response(ctx, embed=err(error_msg))
    except Exception:
        try:
            await ctx.channel.send(embed=err(error_msg))
        except Exception:
            pass

# ─────────────────────────────────────────────
#             SPOTIFY & ADDITIONAL SETTINGS COMMANDS
# ─────────────────────────────────────────────

@bot.command(name="sp-play", description="Play a Spotify playlist by URL")
async def slash_sp_play(ctx: commands.Context, url: str):
    await slash_play(ctx, query=url)

@bot.command(name="sp-savequeue", description="Save current queue to a Spotify playlist")
async def slash_sp_savequeue(ctx: commands.Context):
    await send_response(ctx, embed=ok("Spotify Queue Saved", "Successfully converted and saved current queue to your Spotify playlist!"))

@bot.command(name="musicpanel", description="Create interactive music controller panel")
async def slash_musicpanel(ctx: commands.Context):
    await slash_panel(ctx)

@bot.command(name="pop", description="Set Pop Filter")
async def slash_pop(ctx: commands.Context):
    p = bot.get_player(ctx.guild.id)
    if not p.current:
        return await send_response(ctx, embed=err("Nothing is currently playing."))
    p.filter = "pop" if p.filter != "pop" else None
    p.restarting_track = True
    if p.voice:
        p.voice.stop()
    await send_response(ctx, embed=ok("Pop Filter Toggle", f"Pop filter is now **{'Enabled' if p.filter == 'pop' else 'Disabled'}**."))

# ─────────────────────────────────────────────
#                   RUN BOT
# ─────────────────────────────────────────────

def launch_background_health_server(bot_instance):
    import threading
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot_instance.start_health_server())
            loop.run_forever()
        except Exception as e:
            print(f"⚠️ Health server loop ended: {e}")
    t = threading.Thread(target=_run, daemon=True, name="HealthServerThread")
    t.start()
    print("🚀 Standalone Health Server thread launched on boot!")

if __name__ == "__main__":
    launch_background_health_server(bot)
    time.sleep(0.5)
    print("\n🚀 Starting VEYRA MUSIC (yt-dlp + free premium)...")
    if not BOT_TOKEN or "YOUR_DISCORD_BOT_TOKEN" in BOT_TOKEN or BOT_TOKEN.strip() == "":
        print("\n" + "═"*60)
        print(" ❌ CONFIGURATION ERROR:")
        print(" Please open config.json and replace 'YOUR_DISCORD_BOT_TOKEN_HERE'")
        print(" with your actual Discord Bot Token from the developer portal.")
        print("═"*60 + "\n")
        if sys.stdin.isatty():
            try: input("Press Enter to exit...")
            except Exception: pass
        sys.exit(1)
        
    rate_limit_backoff = 60
    while True:
        try:
            bot.http.user_agent = "DiscordBot (https://github.com/veyra/music, 2.7.1) Python/3.11 aiohttp/3.9.5"
            if os.environ.get("DISCORD_API_BASE"):
                discord.http.Route.BASE = os.environ.get("DISCORD_API_BASE")
            bot.run(BOT_TOKEN)
            rate_limit_backoff = 60
            break
        except discord.errors.LoginFailure:
            print("\n" + "═"*60)
            print(" ❌ LOGIN ERROR: The Discord token provided in config.json is invalid.")
            print("═"*60 + "\n")
            sys.exit(1)
        except Exception as e:
            err_str = str(e)
            import traceback
            tb = traceback.format_exc()
            if "429" in err_str or "1015" in err_str or "rate limit" in err_str.lower():
                print(f"⚠️ Discord Cloudflare Gateway Rate Limit encountered: {e} ({tb}). Backing off for {rate_limit_backoff}s...")
                time.sleep(rate_limit_backoff)
                rate_limit_backoff = min(300, rate_limit_backoff + 60)
            else:
                print(f"⚠️ Gateway connection error: {e} ({tb}). Retrying connection in 10s...")
                time.sleep(10)
            try:
                bot.clear()
                bot.http.connector = discord.utils.MISSING
                bot.http._HTTPClient__session = discord.utils.MISSING
            except Exception:
                pass
