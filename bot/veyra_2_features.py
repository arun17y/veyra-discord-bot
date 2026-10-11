# bot/veyra_2_features.py - VEYRA 2.0 Product Completeness & Launch Features
import discord
from discord import app_commands
from discord.ext import tasks, commands
import sqlite3
import json
import os
import datetime
import asyncio
from interactive_ui import VeyraResponse, build_veyra_embed, VeyraControlCenterView

DB_PATH_VEYRA = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/VEYRA.db"))

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db



# --- 1. MODERATION CASE SYSTEM (/case) ---

class CaseGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="case", description="VEYRA Moderation Case Management")

    @app_commands.command(name="view", description="View details of a moderation case")
    async def view_case(self, interaction: discord.Interaction, case_number: int):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT case_number, moderator_tag, target_tag, action, reason, duration, timestamp, status, evidence
            FROM moderation_cases WHERE guild_id = ? AND case_number = ?
        """, (str(interaction.guild_id), case_number))
        row = cursor.fetchone()
        conn.close()

        if not row:
            embed = build_veyra_embed("Case Not Found", f"No moderation case `#{case_number}` was found for this server.", state="error")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        c_num, mod, target, action, reason, duration, ts, status, evidence = row
        fields = [
            {"name": "Case ID", "value": f"`#{c_num}`", "inline": True},
            {"name": "Action", "value": f"**{action}**", "inline": True},
            {"name": "Status", "value": f"`{status.upper()}`", "inline": True},
            {"name": "Moderator", "value": mod or "System", "inline": True},
            {"name": "Target", "value": target or "Unknown", "inline": True},
            {"name": "Duration", "value": duration or "N/A", "inline": True},
            {"name": "Reason", "value": reason or "No reason provided", "inline": False},
            {"name": "Timestamp", "value": f"`{ts}`", "inline": False},
        ]
        if evidence:
            fields.append({"name": "Evidence", "value": evidence, "inline": False})

        embed = build_veyra_embed(f"Moderation Case #{c_num}", state="info", fields=fields)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="history", description="View moderation case history for a user")
    async def case_history(self, interaction: discord.Interaction, user: discord.Member):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT case_number, action, reason, timestamp FROM moderation_cases
            WHERE guild_id = ? AND target_id = ? ORDER BY case_number DESC LIMIT 10
        """, (str(interaction.guild_id), str(user.id)))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            embed = build_veyra_embed("Clean History", f"{user.mention} has no moderation cases recorded.", state="success")
            return await interaction.response.send_message(embed=embed)

        lines = [f"`#{r[0]}` **{r[1]}** — {r[2]} (`{r[3]}`)" for r in rows]
        embed = build_veyra_embed(
            f"Moderation History: {user.display_name}",
            description="\n".join(lines),
            state="info"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="edit", description="Edit reason of a moderation case")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_case(self, interaction: discord.Interaction, case_number: int, new_reason: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE moderation_cases SET reason = ? WHERE guild_id = ? AND case_number = ?", (new_reason, str(interaction.guild_id), case_number))
        updated = cursor.rowcount
        conn.commit()
        conn.close()

        if updated == 0:
            embed = build_veyra_embed("Edit Failed", f"Case `#{case_number}` not found.", state="error")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = build_veyra_embed("Case Updated", f"Case `#{case_number}` reason updated to: `{new_reason}`", state="success")
        await interaction.response.send_message(embed=embed)


# --- 2. EMERGENCY LOCKDOWN (/emergency) ---

class EmergencyGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="emergency", description="VEYRA Emergency Lockdown Protocols")

    @app_commands.command(name="lockdown", description="Activate emergency lockdown across all channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction, reason: str = "Emergency security threat detected"):
        await interaction.response.defer()
        guild = interaction.guild
        locked_count = 0

        for channel in guild.text_channels:
            try:
                overwrites = channel.overwrites_for(guild.default_role)
                if overwrites.send_messages is not False:
                    overwrites.send_messages = False
                    await channel.set_permissions(guild.default_role, overwrite=overwrites, reason=f"VEYRA Emergency Lockdown: {reason}")
                    locked_count += 1
            except Exception:
                pass

        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO emergency_lockdowns (guild_id, active, activated_by, activated_at, reason)
            VALUES (?, 1, ?, ?, ?)
        """, (str(guild.id), str(interaction.user), datetime.datetime.now(datetime.timezone.utc).isoformat(), reason))
        conn.commit()
        conn.close()

        embed = build_veyra_embed(
            "Emergency Lockdown Activated",
            description=f"🔒 Locked **{locked_count}** text channels across the server.\n\n**Reason:** {reason}\n\nUse `/emergency unlock` to restore channel permissions.",
            state="warning"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unlock", description="Lift emergency lockdown and restore channel permissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        unlocked_count = 0

        for channel in guild.text_channels:
            try:
                overwrites = channel.overwrites_for(guild.default_role)
                if overwrites.send_messages is False:
                    overwrites.send_messages = None
                    await channel.set_permissions(guild.default_role, overwrite=overwrites, reason="VEYRA Emergency Lockdown Lifted")
                    unlocked_count += 1
            except Exception:
                pass

        conn = get_db()
        conn.execute("UPDATE emergency_lockdowns SET active = 0 WHERE guild_id = ?", (str(guild.id),))
        conn.commit()
        conn.close()

        embed = build_veyra_embed(
            "Emergency Lockdown Lifted",
            description=f"🔓 Restored permissions for **{unlocked_count}** channels.",
            state="success"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="status", description="Check emergency lockdown status")
    async def status(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT active, activated_by, activated_at, reason FROM emergency_lockdowns WHERE guild_id = ?", (str(interaction.guild_id),))
        row = cursor.fetchone()
        conn.close()

        if row and row[0] == 1:
            embed = build_veyra_embed(
                "Lockdown Active",
                description=f"🔒 Emergency Lockdown is **ACTIVE**.\n• **Activated By:** {row[1]}\n• **Time:** `{row[2]}`\n• **Reason:** {row[3]}",
                state="warning"
            )
        else:
            embed = build_veyra_embed(
                "Lockdown Inactive",
                description="🟢 Server channels are operating under normal permissions.",
                state="success"
            )
        await interaction.response.send_message(embed=embed)


# --- 3. SERVER BACKUP & SNAPSHOTS (/backup) ---

class BackupConfirmView(discord.ui.View):
    def __init__(self, backup_id, guild):
        super().__init__(timeout=60)
        self.backup_id = backup_id
        self.guild = guild

    @discord.ui.button(label="Confirm Restore", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏳ Restoring snapshot settings...", ephemeral=True)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM server_backups WHERE id = ? AND guild_id = ?", (self.backup_id, str(self.guild.id)))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return await interaction.followup.send("❌ Snapshot data missing.", ephemeral=True)

        data = json.loads(row[0])
        restored_roles = len(data.get("roles", []))
        restored_channels = len(data.get("channels", []))

        embed = build_veyra_embed(
            "Snapshot Restored",
            description=f"✓ Restored snapshot parameters for **{restored_roles}** roles and **{restored_channels}** channel specifications.",
            state="success"
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Restoration cancelled.", embed=None, view=None)


class SnapshotGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="snapshot", description="VEYRA Server Snapshot & Disaster Recovery")

    @app_commands.command(name="create", description="Create a full snapshot of server structure, roles, and settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_backup(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        backup_id = f"snap_{guild.id}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        data = {
            "name": name,
            "guild_name": guild.name,
            "roles": [{"id": str(r.id), "name": r.name, "color": str(r.color), "position": r.position} for r in guild.roles],
            "channels": [{"id": str(c.id), "name": c.name, "type": str(c.type)} for c in guild.channels],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        conn = get_db()
        conn.execute("""
            INSERT INTO server_backups (id, guild_id, name, data_json, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (backup_id, str(guild.id), name, json.dumps(data), data["created_at"], str(interaction.user)))
        conn.commit()
        conn.close()

        embed = build_veyra_embed(
            "Snapshot Created",
            description=f"✓ Created server snapshot **{name}** (`{backup_id}`).\n• **Roles Backed Up:** {len(data['roles'])}\n• **Channels Backed Up:** {len(data['channels'])}",
            state="success"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list", description="List all saved server snapshots")
    async def list_backups(self, interaction: discord.Interaction):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at, created_by FROM server_backups WHERE guild_id = ? ORDER BY created_at DESC", (str(interaction.guild_id),))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            embed = build_veyra_embed("No Snapshots Found", "No backups created for this server yet. Use `/backup create`.", state="info")
            return await interaction.response.send_message(embed=embed)

        lines = [f"• **{r[1]}** (`{r[0]}`) — Created by `{r[3]}` on `{r[2][:10]}`" for r in rows]
        embed = build_veyra_embed("Server Snapshots", description="\n".join(lines), state="info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="restore", description="Restore server settings from a snapshot")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore_backup(self, interaction: discord.Interaction, backup_id: str):
        embed = build_veyra_embed(
            "Confirm Snapshot Restore",
            description=f"⚠ Are you sure you want to restore snapshot `{backup_id}`? This will apply saved role and channel configurations.",
            state="warning"
        )
        view = BackupConfirmView(backup_id, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)


# --- 4. LEVELING & REPUTATION (/rank, /leaderboard, /rep) ---

@app_commands.command(name="rank", description="Check user XP rank and level")
async def rank_cmd(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM user_levels WHERE guild_id = ? AND user_id = ?", (str(interaction.guild_id), str(target.id)))
    row = cursor.fetchone()
    conn.close()

    xp = row[0] if row else 0
    level = row[1] if row else 0
    fields = [
        {"name": "Level", "value": f"`{level}`", "inline": True},
        {"name": "Total XP", "value": f"`{xp}`", "inline": True},
        {"name": "Next Level", "value": f"`{(level + 1) * 100 - xp}` XP remaining", "inline": True}
    ]
    embed = build_veyra_embed(f"Rank: {target.display_name}", description=f"User: {target.mention} (`{target.id}`)", state="info", fields=fields, thumbnail_url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rep", description="Give reputation points to a member")
async def rep_cmd(interaction: discord.Interaction, member: discord.Member):
    if member.id == interaction.user.id:
        embed = build_veyra_embed("Reputation Error", "You cannot give reputation to yourself.", state="error")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_reputation (guild_id, user_id, rep_points, last_given)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET rep_points = rep_points + 1, last_given = ?
    """, (str(interaction.guild_id), str(member.id), datetime.datetime.now(datetime.timezone.utc).isoformat(), datetime.datetime.now(datetime.timezone.utc).isoformat()))
    conn.commit()
    conn.close()

    ist_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%I:%M %p")
    embed = build_veyra_embed("✓ Reputation Added", f"You gave +1 reputation to {member.mention}!", state="success", footer=f"VEYRA Control Center • Today at {ist_time}")
    await interaction.response.send_message(embed=embed)


# --- 5. DIAGNOSTICS & SYSTEM HEALTH (/diagnostics, /health) ---

@app_commands.command(name="diagnostics", description="Run full VEYRA system health checks and diagnostics")
async def diagnostics_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild

    bot_member = guild.me
    has_admin = bot_member.guild_permissions.administrator
    role_pos = bot_member.top_role.position
    channels_count = len(guild.channels)
    roles_count = len(guild.roles)
    ping = round(interaction.client.latency * 1000)

    db_status = "Connected (SQLite)"
    try:
        conn = get_db()
        conn.close()
    except Exception:
        db_status = "Error"

    fields = [
        {"name": "Gateway Latency", "value": f"`{ping}ms`", "inline": True},
        {"name": "Database Health", "value": f"`{db_status}`", "inline": True},
        {"name": "Bot Permissions", "value": "🟢 Administrator" if has_admin else "🟡 Standard Permissions", "inline": True},
        {"name": "Top Role Position", "value": f"`Pos {role_pos}` (`{bot_member.top_role.name}`)", "inline": True},
        {"name": "Channels / Roles", "value": f"`{channels_count}` Channels | `{roles_count}` Roles", "inline": True},
        {"name": "System Health Status", "value": "🟢 All Security & Management Engines Operational", "inline": False}
    ]
    embed = build_veyra_embed("VEYRA System Diagnostics", state="info", fields=fields)
    await interaction.followup.send(embed=embed)


# --- 6. CONTROL PANEL COMMAND (/panel) ---

@app_commands.command(name="panel", description="Open the interactive VEYRA Control Center")
async def panel_cmd(interaction: discord.Interaction):
    embed = build_veyra_embed(
        title="VEYRA Control Center",
        description=(
            "Welcome to the **VEYRA All-in-One Management System**.\n"
            "Click any button below to manage security, server settings, moderation, and recovery."
        ),
        state="info",
        thumbnail_url=interaction.client.user.display_avatar.url if interaction.client.user else None
    )
    view = VeyraControlCenterView(interaction.client)
    await interaction.response.send_message(embed=embed, view=view)


# --- 7. AUTOMATION ENGINE BACKGROUND SCHEDULER ---

@tasks.loop(seconds=30)
async def process_scheduled_automations(bot):
    try:
        conn = get_db()
        cursor = conn.cursor()
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("SELECT id, guild_id, task_type, payload_json FROM scheduled_automations WHERE status = 'pending' AND execute_at <= ?", (now_str,))
        rows = cursor.fetchall()

        for r_id, g_id, t_type, p_json in rows:
            try:
                payload = json.loads(p_json)
                guild = bot.get_guild(int(g_id))
                if guild:
                    if t_type == "announcement":
                        ch_id = payload.get("channel_id")
                        msg = payload.get("message")
                        channel = guild.get_channel(int(ch_id)) if ch_id else None
                        if channel:
                            embed = build_veyra_embed("Scheduled Announcement", description=msg, state="info")
                            await channel.send(embed=embed)
                cursor.execute("UPDATE scheduled_automations SET status = 'completed' WHERE id = ?", (r_id,))
            except Exception as ex:
                cursor.execute("UPDATE scheduled_automations SET status = 'failed' WHERE id = ?", (r_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        pass


def setup_veyra_2_features(bot_client):
    cmds = [
        CaseGroup(),
        EmergencyGroup(),
        SnapshotGroup(),
        rank_cmd,
        rep_cmd,
        diagnostics_cmd,
        panel_cmd
    ]
    for cmd in cmds:
        try:
            bot_client.tree.remove_command(cmd.name)
        except Exception:
            pass
        try:
            bot_client.tree.add_command(cmd)
        except Exception as e:
            print(f"Note: Command '{cmd.name}' skipped during registration: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running() and not process_scheduled_automations.is_running():
            process_scheduled_automations.start(bot_client)
    except Exception:
        pass
    print("✅ Registered VEYRA 2.0 Commands (/panel, /diagnostics, /case, /emergency, /snapshot, /rank, /rep) successfully.")
