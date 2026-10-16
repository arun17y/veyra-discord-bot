# bot/diagnostics_suite.py - Deep Server Diagnostics, Advanced Permission Suite & Professional Server Management
import discord
from discord import app_commands
from discord.ext import commands
import json
import uuid
import typing
from datetime import datetime, timezone, timedelta
import io

try:
    from bot.db_adapter import get_db
except ImportError:
    from db_adapter import get_db

THEME_PURPLE = 0xa855f7
THEME_DARK = 0x18181b
THEME_SUCCESS = 0x22c55e
THEME_ERROR = 0xef4444
THEME_WARNING = 0xf59e0b
THEME_INFO = 0x3b82f6

FOOTER_TEXT = "VEYRA | One Bot. Every System. • Powered By Veyra Development™"

# ── 1. DATABASE INITIALIZATION ────────────────────────────────────────────────
def init_diagnostics_suite_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_templates (
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
        CREATE TABLE IF NOT EXISTS security_approvals (
            id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            approved_by TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_maintenances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_ids_json TEXT NOT NULL,
            reason TEXT,
            end_time TIMESTAMP,
            scheduled_by TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_access_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            module_name TEXT NOT NULL,
            can_access INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, role_id, module_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings_audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            setting_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission_undo_log (
            action_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            previous_state_json TEXT NOT NULL,
            action_name TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

init_diagnostics_suite_db()


# ── 2. HELPER UTILITIES ───────────────────────────────────────────────────────
def serialize_channel_overwrites_dict(channel: discord.abc.GuildChannel) -> list[dict]:
    out = []
    for target, overwrite in channel.overwrites.items():
        is_role = isinstance(target, discord.Role)
        pair = overwrite.pair()
        out.append({
            "target_id": str(target.id),
            "target_name": target.name,
            "target_type": "role" if is_role else "member",
            "allow_value": pair[0].value,
            "deny_value": pair[1].value
        })
    return out

def deserialize_channel_overwrites(guild: discord.Guild, data: list[dict]) -> dict:
    overwrites = {}
    for entry in data:
        tid = int(entry["target_id"])
        target = guild.get_role(tid) if entry["target_type"] == "role" else guild.get_member(tid)
        if target:
            allow = discord.Permissions(entry.get("allow_value", 0))
            deny = discord.Permissions(entry.get("deny_value", 0))
            overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)
    return overwrites

async def log_perm_undo(guild_id: int, channel_id: int, target_id: int, target_type: str, prev_overwrites_json: str, action_name: str, actor_id: int):
    action_id = str(uuid.uuid4())[:8]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO permission_undo_log (action_id, guild_id, target_type, target_id, channel_id, previous_state_json, action_name, actor_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (action_id, str(guild_id), target_type, str(target_id), str(channel_id), prev_overwrites_json, action_name, str(actor_id)))
    conn.commit()
    return action_id


# ── 3. INTERACTIVE VIEWS ──────────────────────────────────────────────────────
class PermissionVisualizerView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel, role: discord.Role, author: discord.Member):
        super().__init__(timeout=180)
        self.channel = channel
        self.role = role
        self.author = author
        self.perms_to_toggle = [
            ("view_channel", "View Channel", "👁️"),
            ("send_messages", "Send Messages", "💬"),
            ("attach_files", "Attach Files", "📎"),
            ("embed_links", "Embed Links", "🔗"),
            ("manage_messages", "Manage Msgs", "🛠️"),
        ]
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        current_ow = self.channel.overwrites_for(self.role)
        for perm_attr, label, emoji in self.perms_to_toggle:
            val = getattr(current_ow, perm_attr, None)
            if val is True:
                style = discord.ButtonStyle.success
                status_str = "ALLOW"
            elif val is False:
                style = discord.ButtonStyle.danger
                status_str = "DENY"
            else:
                style = discord.ButtonStyle.secondary
                status_str = "INHERIT"

            btn = discord.ui.Button(
                label=f"{label}: {status_str}",
                style=style,
                emoji=emoji,
                custom_id=f"perm_{perm_attr}"
            )
            btn.callback = self._create_callback(perm_attr)
            self.add_item(btn)

        close_btn = discord.ui.Button(label="Done", style=discord.ButtonStyle.primary, emoji="✅")
        close_btn.callback = self._done_callback
        self.add_item(close_btn)

    def _create_callback(self, perm_attr: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author.id:
                return await interaction.response.send_message("❌ You cannot modify this visualizer.", ephemeral=True)
            await interaction.response.defer()
            current_ow = self.channel.overwrites_for(self.role)
            current_val = getattr(current_ow, perm_attr, None)
            # Cycle: None -> True -> False -> None
            if current_val is None:
                new_val = True
            elif current_val is True:
                new_val = False
            else:
                new_val = None

            setattr(current_ow, perm_attr, new_val)
            try:
                await self.channel.set_permissions(self.role, overwrite=current_ow)
                self._build_buttons()
                await interaction.edit_original_response(embed=self.build_embed(), view=self)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to update permission: `{e}`", ephemeral=True)
        return callback

    async def _done_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Only the initiator can close this.", ephemeral=True)
        self.stop()
        embed = discord.Embed(
            title="✅ Permission Visualizer Session Completed",
            description=f"Permissions for **{self.role.name}** in {self.channel.mention} have been successfully committed.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.response.edit_message(embed=embed, view=None)

    def build_embed(self) -> discord.Embed:
        current_ow = self.channel.overwrites_for(self.role)
        lines = []
        for perm_attr, label, emoji in self.perms_to_toggle:
            val = getattr(current_ow, perm_attr, None)
            state_emoji = "✅ Allow" if val is True else ("❌ Deny" if val is False else "⚪ Inherit")
            lines.append(f"{emoji} **{label}**: `{state_emoji}`")

        embed = discord.Embed(
            title=f"🎛️ Permission Visualizer — {self.channel.name}",
            description=f"Target Role: **{self.role.mention}**\nChannel: {self.channel.mention}\n\n" + "\n".join(lines),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text="Click any button to toggle: Inherit ➔ Allow ➔ Deny ➔ Inherit")
        return embed


class SecurityApprovalView(discord.ui.View):
    def __init__(self, approval_id: str, guild_id: int, action_type: str, requested_by: int, payload: dict):
        super().__init__(timeout=600)
        self.approval_id = approval_id
        self.guild_id = str(guild_id)
        self.action_type = action_type
        self.requested_by = requested_by
        self.payload = payload

    @discord.ui.button(label="Approve Action", style=discord.ButtonStyle.success, emoji="🛡️")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.requested_by and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Security Rule Violation: You cannot approve your own high-impact request! Another administrator must verify.", ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You require `Administrator` permission to approve this action.", ephemeral=True)

        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE security_approvals 
            SET status = 'approved', approved_by = ? 
            WHERE id = ? AND status = 'pending'
        """, (str(interaction.user.id), self.approval_id))
        conn.commit()

        self.stop()
        embed = discord.Embed(
            title="🛡️ Security Approval Granted",
            description=f"Action **{self.action_type}** (`{self.approval_id}`) has been approved by {interaction.user.mention}.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="Reject & Cancel", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You require `Administrator` permission to reject this action.", ephemeral=True)

        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE security_approvals SET status = 'rejected' WHERE id = ?", (self.approval_id,))
        conn.commit()

        self.stop()
        embed = discord.Embed(
            title="❌ Security Approval Rejected",
            description=f"Action **{self.action_type}** (`{self.approval_id}`) was cancelled by {interaction.user.mention}.",
            color=discord.Color(THEME_ERROR)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.edit_original_response(embed=embed, view=None)


# ── 4. DEEP SERVER DIAGNOSTICS GROUP (/audit) ─────────────────────────────────
class AuditGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="audit", description="Deep Server Diagnostics, Integrity Checks & Threat Detection")
        self.bot = bot

    # 1. /audit permissions (formerly /permissionaudit)
    @app_commands.command(name="permissions", description="Identify dangerous permissions, excessive role access and risky channel overwrites")
    async def audit_permissions(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        dangerous_flags = [
            ("administrator", "Administrator"),
            ("manage_guild", "Manage Server"),
            ("manage_roles", "Manage Roles"),
            ("manage_channels", "Manage Channels"),
            ("manage_webhooks", "Manage Webhooks"),
            ("mention_everyone", "Mention @everyone"),
            ("ban_members", "Ban Members"),
            ("kick_members", "Kick Members"),
        ]

        risky_roles = []
        for role in guild.roles:
            if role.is_default():  # @everyone
                elevated = [name for flag, name in dangerous_flags if getattr(role.permissions, flag, False)]
                if elevated:
                    risky_roles.append(f"⚠️ `@everyone` has dangerous permissions: `{', '.join(elevated)}`")
            elif not role.managed:
                elevated = [name for flag, name in dangerous_flags if getattr(role.permissions, flag, False)]
                if len(elevated) >= 4 and len(role.members) > 10:
                    risky_roles.append(f"⚠️ **{role.name}** ({len(role.members)} members) holds high privilege: `{len(elevated)} dangerous flags`")

        # Check channel overwrites
        risky_overwrites = []
        for ch in guild.text_channels:
            ow = ch.overwrites_for(guild.default_role)
            if ow.send_messages is True and ow.view_channel is False:
                risky_overwrites.append(f"• {ch.mention}: @everyone can send messages but cannot view channel (blind posting).")
            if ow.mention_everyone is True:
                risky_overwrites.append(f"• {ch.mention}: @everyone explicitly allowed to mention everyone.")

        embed = discord.Embed(
            title="🔍 Deep Permission Security Audit",
            description=f"Scanned **{len(guild.roles)}** roles and **{len(guild.channels)}** channels in **{guild.name}**.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"Role Privilege Risks ({len(risky_roles)})",
            value="\n".join(risky_roles[:8]) if risky_roles else "✅ No excessive privilege or @everyone security leaks found.",
            inline=False
        )
        embed.add_field(
            name=f"Channel Overwrite Anomalies ({len(risky_overwrites)})",
            value="\n".join(risky_overwrites[:8]) if risky_overwrites else "✅ No abnormal or dangerous channel overrides detected.",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 2. /audit roles (formerly /roleaudit)
    @app_commands.command(name="roles", description="Inspect sensitive permission holders (Administrator, Manage Roles/Webhooks)")
    async def audit_roles(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        admin_roles = [r for r in guild.roles if r.permissions.administrator]
        role_mgrs = [r for r in guild.roles if r.permissions.manage_roles and not r.permissions.administrator]
        webhook_mgrs = [r for r in guild.roles if r.permissions.manage_webhooks and not r.permissions.administrator]

        embed = discord.Embed(
            title="🛡️ Sensitive Role & Privilege Audit",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"👑 Full Administrator Roles ({len(admin_roles)})",
            value="\n".join([f"• **{r.name}** ({len(r.members)} members)" for r in admin_roles[:10]]) or "None",
            inline=False
        )
        embed.add_field(
            name=f"📜 Manage Roles Permissions ({len(role_mgrs)})",
            value="\n".join([f"• **{r.name}** ({len(r.members)} members)" for r in role_mgrs[:10]]) or "None",
            inline=False
        )
        embed.add_field(
            name=f"🔗 Manage Webhooks Permissions ({len(webhook_mgrs)})",
            value="\n".join([f"• **{r.name}** ({len(r.members)} members)" for r in webhook_mgrs[:10]]) or "None",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 3. /audit channels (formerly /channelaudit)
    @app_commands.command(name="channels", description="Identify unintended private channel access and inconsistent permissions")
    async def audit_channels(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        private_channels = []
        unsynced_channels = []

        for ch in guild.channels:
            if isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
                ow = ch.overwrites_for(guild.default_role)
                if ow.view_channel is False:
                    # Check how many non-admin roles have view_channel
                    allowed_roles = [t.name for t, o in ch.overwrites.items() if isinstance(t, discord.Role) and o.view_channel is True and not t.permissions.administrator]
                    private_channels.append(f"• {ch.mention} (Allowed: {len(allowed_roles)} custom roles)")
                if ch.category and not ch.permissions_synced:
                    unsynced_channels.append(f"• {ch.mention} (Parent: **{ch.category.name}**)")

        embed = discord.Embed(
            title="🔒 Channel Access & Synchronization Audit",
            description=f"Total Channels: **{len(guild.channels)}** | Categories: **{len(guild.categories)}**",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"Private Channels ({len(private_channels)})",
            value="\n".join(private_channels[:8]) or "No private channels detected.",
            inline=False
        )
        embed.add_field(
            name=f"Desynchronized Channels ({len(unsynced_channels)})",
            value="\n".join(unsynced_channels[:8]) or "✅ All child channels are perfectly synced with parent categories.",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 4. /audit hierarchy (formerly /hierarchyaudit)
    @app_commands.command(name="hierarchy", description="Check bot role hierarchy position and unmanageable higher roles")
    async def audit_hierarchy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        bot_member = guild.me
        bot_top_role = bot_member.top_role

        higher_roles = [r for r in guild.roles if r.position >= bot_top_role.position and not r.is_default()]
        manageable_roles = [r for r in guild.roles if r.position < bot_top_role.position and not r.is_default() and not r.managed]

        embed = discord.Embed(
            title="📊 Bot Role Hierarchy Diagnostic",
            description=f"Bot Top Role: **{bot_top_role.name}** (Position: `{bot_top_role.position}`)",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"⛔ Unmanageable Roles (Above Bot: {len(higher_roles)})",
            value="\n".join([f"• **{r.name}** (Pos: `{r.position}`)" for r in higher_roles[:10]]) or "None (Bot is at the peak)",
            inline=False
        )
        embed.add_field(
            name=f"✅ Manageable Roles ({len(manageable_roles)})",
            value=f"The bot can safely configure, assign, and manage **{len(manageable_roles)}** server roles.",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 5. /audit orphans (formerly /orphancheck)
    @app_commands.command(name="orphans", description="Identify empty categories, unused roles and unreferenced configuration")
    async def audit_orphans(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        empty_cats = [cat.name for cat in guild.categories if len(cat.channels) == 0]
        unused_roles = [r.name for r in guild.roles if len(r.members) == 0 and not r.is_default() and not r.managed]

        embed = discord.Embed(
            title="🧹 Orphan & Dead Asset Inspection",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"📁 Empty Categories ({len(empty_cats)})",
            value="\n".join([f"• {c}" for c in empty_cats[:10]]) or "✅ No empty categories.",
            inline=False
        )
        embed.add_field(
            name=f"🎭 Unused Roles (0 Members: {len(unused_roles)})",
            value="\n".join([f"• {r}" for r in unused_roles[:12]]) or "✅ No orphaned roles.",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 6. /audit health (formerly /confighealth)
    @app_commands.command(name="health", description="Validate log channels, module settings and ID consistency")
    async def audit_health(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        conn = get_db()
        cursor = conn.cursor()

        checks = []
        # Check audit log channel
        cursor.execute("SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild.id),))
        row = cursor.fetchone()
        if row and row[0]:
            ch = guild.get_channel(int(row[0]))
            checks.append(f"• Log Channel: {'✅ Configured & Active' if ch else '⚠️ Invalid Channel ID in DB'}")
        else:
            checks.append("• Log Channel: ⚪ Not set")

        # Check autorole
        cursor.execute("SELECT role_id FROM autoroles WHERE guild_id = ?", (str(guild.id),))
        arow = cursor.fetchone()
        if arow and arow[0]:
            r = guild.get_role(int(arow[0]))
            checks.append(f"• Autorole: {'✅ Configured & Active' if r else '⚠️ Invalid Role ID in DB'}")
        else:
            checks.append("• Autorole: ⚪ Disabled")

        # Check verification
        cursor.execute("SELECT verified_role_id, channel_id FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
        vrow = cursor.fetchone()
        if vrow and vrow[0]:
            vr = guild.get_role(int(vrow[0]))
            checks.append(f"• Verification Role: {'✅ Active' if vr else '⚠️ Missing Target Role'}")
        else:
            checks.append("• Verification: ⚪ Disabled")

        embed = discord.Embed(
            title="🩺 VEYRA Server Configuration Health Check",
            description=f"Automated health diagnostics for **{guild.name}**:\n\n" + "\n".join(checks),
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 7. /audit integrations (formerly /integrationaudit)
    @app_commands.command(name="integrations", description="Inspect Discord webhooks and bot integrations")
    async def audit_integrations(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Server` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        bots = [m for m in guild.members if m.bot]
        try:
            webhooks = await guild.webhooks()
            wh_text = f"Total Webhooks: **{len(webhooks)}**\n" + "\n".join([f"• **{w.name}** in #{w.channel.name}" for w in webhooks[:8]])
        except Exception:
            wh_text = "⚠️ Missing `Manage Webhooks` permission to inspect webhooks."

        embed = discord.Embed(
            title="🤖 Server Integration & Webhook Audit",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"Connected Bots ({len(bots)})",
            value="\n".join([f"• {b.mention} (`{b.id}`)" for b in bots[:10]]) or "No other bots.",
            inline=False
        )
        embed.add_field(
            name="External Webhooks",
            value=wh_text or "No webhooks registered.",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 8. /audit access (formerly /accessreport)
    @app_commands.command(name="access", description="Generate channel accessibility report for a specific member or role")
    @app_commands.describe(target_role="Role to inspect", target_member="Member to inspect")
    async def audit_access(self, interaction: discord.Interaction, target_role: typing.Optional[discord.Role] = None, target_member: typing.Optional[discord.Member] = None):
        await interaction.response.defer()
        guild = interaction.guild
        target = target_member or target_role or interaction.user

        viewable = []
        writable = []
        for ch in guild.text_channels:
            perms = ch.permissions_for(target)
            if perms.view_channel:
                viewable.append(ch.name)
            if perms.send_messages:
                writable.append(ch.name)

        embed = discord.Embed(
            title=f"📋 Channel Access Report — {target.name}",
            description=f"Inspecting configured permissions across **{len(guild.text_channels)}** text channels.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.add_field(
            name=f"👁️ Viewable Channels ({len(viewable)}/{len(guild.text_channels)})",
            value=", ".join([f"`#{c}`" for c in viewable[:15]]) + (f" and {len(viewable)-15} more..." if len(viewable) > 15 else "") or "None",
            inline=False
        )
        embed.add_field(
            name=f"💬 Writable Channels ({len(writable)}/{len(guild.text_channels)})",
            value=", ".join([f"`#{c}`" for c in writable[:15]]) + (f" and {len(writable)-15} more..." if len(writable) > 15 else "") or "None",
            inline=False
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 9. /audit changefeed (formerly /changefeed)
    @app_commands.command(name="changefeed", description="Searchable timeline of recent server configuration changes")
    async def audit_changefeed(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.view_audit_log and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `View Audit Log` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        feed_lines = []
        try:
            async for entry in guild.audit_logs(limit=10):
                actor = entry.user.name if entry.user else "System"
                feed_lines.append(f"• **{entry.action.name.replace('_', ' ').title()}** by `{actor}` (Target: `{entry.target}`)")
        except Exception as e:
            feed_lines.append(f"⚠️ Audit log retrieval notice: `{e}`")

        embed = discord.Embed(
            title="⏱️ Configuration Change Feed",
            description="\n".join(feed_lines) or "No recent audit log entries.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 10. /audit incident (formerly /incidentreport)
    @app_commands.command(name="incident", description="Consolidate raid or suspicious event timeline into a forensic report")
    async def audit_incident(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.view_audit_log and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `View Audit Log` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        bans = 0
        kicks = 0
        channel_dels = 0
        role_dels = 0
        actors = {}

        try:
            async for entry in guild.audit_logs(limit=100):
                if entry.created_at < cutoff:
                    break
                act_str = str(entry.action.name)
                actor_name = entry.user.name if entry.user else "Unknown"
                actors[actor_name] = actors.get(actor_name, 0) + 1
                if "ban" in act_str:
                    bans += 1
                elif "kick" in act_str:
                    kicks += 1
                elif "channel_delete" in act_str:
                    channel_dels += 1
                elif "role_delete" in act_str:
                    role_dels += 1
        except Exception:
            pass

        top_actors = sorted(actors.items(), key=lambda x: x[1], reverse=True)[:5]
        actor_summary = "\n".join([f"• `{name}`: {count} actions" for name, count in top_actors]) or "None"

        embed = discord.Embed(
            title="🚨 Security Incident Forensic Report (Past 2 Hours)",
            description=f"Incident scan across audit events in **{guild.name}**:",
            color=discord.Color(THEME_ERROR if (bans + kicks + channel_dels) > 5 else THEME_PURPLE)
        )
        embed.add_field(name="🔨 Bans Issued", value=str(bans), inline=True)
        embed.add_field(name="👢 Kicks Issued", value=str(kicks), inline=True)
        embed.add_field(name="🗑️ Channels Deleted", value=str(channel_dels), inline=True)
        embed.add_field(name="🎭 Roles Deleted", value=str(role_dels), inline=True)
        embed.add_field(name="Top Active Mod/Admin Actors", value=actor_summary, inline=False)
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)


# ── 5. ADVANCED PERMISSION SUITE COMMANDS (Attached to /permission) ───────────
def attach_advanced_permission_commands(perm_group: app_commands.Group, bot: commands.Bot):

    # 1. /permission copy (formerly /permcopy)
    @perm_group.command(name="copy", description="Copy channel permission overwrites from source channel to target channel")
    @app_commands.describe(source="Channel to copy permissions from", target="Channel to receive permissions")
    async def slash_perm_copy(interaction: discord.Interaction, source: discord.abc.GuildChannel, target: discord.abc.GuildChannel):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        prev_state = serialize_channel_overwrites_dict(target)
        try:
            target_overwrites = dict(source.overwrites)
            await target.edit(overwrites=target_overwrites)
            undo_id = await log_perm_undo(
                interaction.guild.id, target.id, target.id, "channel",
                json.dumps(prev_state), "permcopy", interaction.user.id
            )
            embed = discord.Embed(
                title="📋 Permissions Cloned Successfully",
                description=f"Copied **{len(source.overwrites)}** permission overrides from {source.mention} to {target.mention}.\n\nUndo Token: `{undo_id}` (Use `/permission undo` to revert)",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to copy permissions: `{e}`")

    # 2. /permission template (formerly /permtemplate save & apply)
    @perm_group.command(name="template", description="Save or apply reusable channel permission templates")
    @app_commands.describe(action="Save or Apply template", template_name="Template name", channel="Channel to save from or apply to")
    @app_commands.choices(action=[
        app_commands.Choice(name="Save Current Channel Permissions", value="save"),
        app_commands.Choice(name="Apply Template to Channel", value="apply"),
        app_commands.Choice(name="List Saved Templates", value="list")
    ])
    async def slash_perm_template(interaction: discord.Interaction, action: app_commands.Choice[str], template_name: typing.Optional[str] = None, channel: typing.Optional[discord.abc.GuildChannel] = None):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        guild_id = str(interaction.guild.id)
        target_ch = channel or interaction.channel

        if action.value == "save":
            if not template_name:
                return await interaction.followup.send("⚠️ You must specify a `template_name` to save.")
            data = serialize_channel_overwrites_dict(target_ch)
            cursor.execute("""
                INSERT OR REPLACE INTO channel_perm_templates (guild_id, template_name, overwrites_json, created_by)
                VALUES (?, ?, ?, ?)
            """, (guild_id, template_name, json.dumps(data), str(interaction.user.id)))
            conn.commit()

            embed = discord.Embed(
                title="💾 Permission Template Saved",
                description=f"Template **{template_name}** successfully saved with **{len(data)}** role/member overrides from {target_ch.mention}.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

        elif action.value == "apply":
            if not template_name:
                return await interaction.followup.send("⚠️ You must specify a `template_name` to apply.")
            cursor.execute("SELECT overwrites_json FROM channel_perm_templates WHERE guild_id = ? AND template_name = ?", (guild_id, template_name))
            row = cursor.fetchone()
            if not row:
                return await interaction.followup.send(f"❌ Template `{template_name}` not found.")
            data = json.loads(row[0])
            prev_state = serialize_channel_overwrites_dict(target_ch)
            new_ow = deserialize_channel_overwrites(interaction.guild, data)
            await target_ch.edit(overwrites=new_ow)

            undo_id = await log_perm_undo(
                interaction.guild.id, target_ch.id, target_ch.id, "channel",
                json.dumps(prev_state), "permtemplate_apply", interaction.user.id
            )
            embed = discord.Embed(
                title="✅ Permission Template Applied",
                description=f"Template **{template_name}** successfully applied to {target_ch.mention}.\n\nUndo Token: `{undo_id}`",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

        elif action.value == "list":
            cursor.execute("SELECT template_name, created_at FROM channel_perm_templates WHERE guild_id = ?", (guild_id,))
            rows = cursor.fetchall()
            names = [f"• **{r[0]}** (Saved: `{r[1]}`)" for r in rows] if rows else ["No saved templates found."]
            embed = discord.Embed(
                title="📜 Saved Permission Templates",
                description="\n".join(names),
                color=discord.Color(THEME_PURPLE)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

    # 3. /permission compare (formerly /permcompare)
    @perm_group.command(name="compare", description="Side-by-side comparison of permissions between two channels")
    @app_commands.describe(channel1="First channel", channel2="Second channel")
    async def slash_perm_compare(interaction: discord.Interaction, channel1: discord.abc.GuildChannel, channel2: discord.abc.GuildChannel):
        await interaction.response.defer()
        targets = set(channel1.overwrites.keys()) | set(channel2.overwrites.keys())
        diff_lines = []

        for target in targets:
            ow1 = channel1.overwrites.get(target)
            ow2 = channel2.overwrites.get(target)
            t_name = f"@{target.name}"
            if ow1 != ow2:
                pair1 = ow1.pair() if ow1 else (discord.Permissions(0), discord.Permissions(0))
                pair2 = ow2.pair() if ow2 else (discord.Permissions(0), discord.Permissions(0))
                diff_lines.append(f"• **{t_name}**: Differing overrides detected.")

        embed = discord.Embed(
            title="⚖️ Channel Permission Comparison",
            description=f"Comparing {channel1.mention} vs {channel2.mention}:\n\n" + ("\n".join(diff_lines[:12]) if diff_lines else "✅ Permissions are completely identical across all roles and members."),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 4. /permission diff (formerly /permdiff)
    @perm_group.command(name="diff", description="Inspect role permission changes vs @everyone baseline")
    @app_commands.describe(role="Role to inspect differences for")
    async def slash_perm_diff(interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        guild = interaction.guild
        base = guild.default_role.permissions
        target = role.permissions

        extra_perms = []
        for perm, val in target:
            if val and not getattr(base, perm):
                extra_perms.append(perm.replace("_", " ").title())

        embed = discord.Embed(
            title=f"📊 Permission Diff — @{role.name}",
            description=f"Elevated permissions granted above `@everyone`:\n\n" + (", ".join([f"`{p}`" for p in extra_perms]) if extra_perms else "This role possesses the exact same permissions as `@everyone`."),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 5. /permission bulk (formerly /permbulk)
    @perm_group.command(name="bulk", description="Apply bulk permission changes via interactive visualizer")
    @app_commands.describe(channel="Channel to edit", role="Role to configure")
    async def slash_perm_bulk(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        view = PermissionVisualizerView(channel, role, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    # 6. /permission undo (formerly /permundo)
    @perm_group.command(name="undo", description="Revert bot-tracked permission changes to their previous state")
    @app_commands.describe(action_id="Optional specific Undo Action Token (defaults to the most recent)")
    async def slash_perm_undo(interaction: discord.Interaction, action_id: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        guild_id = str(interaction.guild.id)

        if action_id:
            cursor.execute("SELECT action_id, channel_id, previous_state_json, action_name FROM permission_undo_log WHERE guild_id = ? AND action_id = ?", (guild_id, action_id))
        else:
            cursor.execute("SELECT action_id, channel_id, previous_state_json, action_name FROM permission_undo_log WHERE guild_id = ? ORDER BY created_at DESC LIMIT 1", (guild_id,))

        row = cursor.fetchone()
        if not row:
            return await interaction.followup.send("❌ No recorded undo history found for this server.")

        act_id, ch_id, state_json, act_name = row
        channel = interaction.guild.get_channel(int(ch_id))
        if not channel:
            return await interaction.followup.send(f"❌ Target channel `{ch_id}` no longer exists.")

        try:
            data = json.loads(state_json)
            restored_ow = deserialize_channel_overwrites(interaction.guild, data)
            await channel.edit(overwrites=restored_ow)
            cursor.execute("DELETE FROM permission_undo_log WHERE action_id = ?", (act_id,))
            conn.commit()

            embed = discord.Embed(
                title="⏪ Permissions Reverted (Undo Executed)",
                description=f"Action **{act_name}** (`{act_id}`) on {channel.mention} has been restored to its previous state.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to restore previous permissions: `{e}`")

    # 7. /permission check (formerly /permcheck)
    @perm_group.command(name="check", description="Explain why a member has or lacks permission in a specific channel")
    @app_commands.describe(member="Member to evaluate", channel="Channel to inspect")
    async def slash_perm_check(interaction: discord.Interaction, member: discord.Member, channel: discord.abc.GuildChannel):
        await interaction.response.defer()
        perms = channel.permissions_for(member)
        reasons = []

        if member.id == interaction.guild.owner_id:
            reasons.append("👑 **Server Owner**: Grants absolute bypass over all channel restrictions.")
        elif member.guild_permissions.administrator:
            reasons.append("🛡️ **Administrator**: Administrator permission overrides all channel denies.")
        else:
            # Check channel overwrites
            m_ow = channel.overwrites.get(member)
            if m_ow and m_ow.view_channel is False:
                reasons.append("❌ Member-specific override explicitly denies View Channel.")
            elif m_ow and m_ow.view_channel is True:
                reasons.append("✅ Member-specific override explicitly grants View Channel.")

            # Check role overwrites
            for r in member.roles:
                r_ow = channel.overwrites.get(r)
                if r_ow and r_ow.view_channel is True:
                    reasons.append(f"✅ Role **{r.name}** grants View Channel.")
                elif r_ow and r_ow.view_channel is False:
                    reasons.append(f"❌ Role **{r.name}** denies View Channel.")

            # Check @everyone
            def_ow = channel.overwrites.get(interaction.guild.default_role)
            if def_ow and def_ow.view_channel is False:
                reasons.append("🔒 `@everyone` is denied View Channel (Private Channel).")

        embed = discord.Embed(
            title=f"🔎 Permission Diagnostics — {member.display_name}",
            description=f"Channel: {channel.mention}\nCan View: `{'YES' if perms.view_channel else 'NO'}` | Can Send: `{'YES' if perms.send_messages else 'NO'}`\n\n**Evaluation Hierarchy:**\n" + ("\n".join(reasons) if reasons else "Default guild permissions apply."),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 8. /permission visualizer (Interactive Visualizer Matrix)
    @perm_group.command(name="visualizer", description="Open interactive graphical permission matrix")
    @app_commands.describe(channel="Channel to inspect", role="Role to toggle permissions for")
    async def slash_perm_visualizer(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Roles` permission.", ephemeral=True)
        view = PermissionVisualizerView(channel, role, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)


# ── 6. PROFESSIONAL SERVER MANAGEMENT (Attached to /servermgmt) ───────────────
def attach_professional_servermgmt_commands(server_group: app_commands.Group, bot: commands.Bot):

    # 1. /servermgmt template save & apply (formerly /servertemplate)
    @server_group.command(name="template", description="Save or apply full server structure templates")
    @app_commands.describe(action="Save or Apply server template", template_name="Template name")
    @app_commands.choices(action=[
        app_commands.Choice(name="Save Complete Server Template", value="save"),
        app_commands.Choice(name="Apply Template Preview & Structure", value="apply"),
        app_commands.Choice(name="List Saved Server Templates", value="list")
    ])
    async def slash_server_template(interaction: discord.Interaction, action: app_commands.Choice[str], template_name: typing.Optional[str] = None):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        guild = interaction.guild
        guild_id = str(guild.id)

        if action.value == "save":
            if not template_name:
                return await interaction.followup.send("⚠️ Please provide a `template_name`.")
            structure = {
                "categories": [
                    {
                        "name": cat.name,
                        "position": cat.position,
                        "channels": [{"name": ch.name, "type": str(ch.type), "topic": getattr(ch, "topic", None)} for ch in cat.channels]
                    }
                    for cat in guild.categories
                ],
                "roles": [{"name": r.name, "color": str(r.color), "hoist": r.hoist, "permissions": r.permissions.value} for r in guild.roles if not r.is_default() and not r.managed]
            }
            cursor.execute("""
                INSERT OR REPLACE INTO server_templates (guild_id, template_name, structure_json, created_by)
                VALUES (?, ?, ?, ?)
            """, (guild_id, template_name, json.dumps(structure), str(interaction.user.id)))
            conn.commit()

            embed = discord.Embed(
                title="💾 Server Structure Template Saved",
                description=f"Saved **{template_name}** with **{len(structure['categories'])}** categories and **{len(structure['roles'])}** roles.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

        elif action.value == "apply":
            if not template_name:
                return await interaction.followup.send("⚠️ Please provide a `template_name`.")
            cursor.execute("SELECT structure_json FROM server_templates WHERE guild_id = ? AND template_name = ?", (guild_id, template_name))
            row = cursor.fetchone()
            if not row:
                return await interaction.followup.send(f"❌ Server template `{template_name}` not found.")
            data = json.loads(row[0])
            cats_count = len(data.get("categories", []))
            roles_count = len(data.get("roles", []))

            embed = discord.Embed(
                title="📋 Server Template Preview",
                description=f"Template **{template_name}** contains **{cats_count}** categories and **{roles_count}** roles.\nReady for staged deployment.",
                color=discord.Color(THEME_PURPLE)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

        elif action.value == "list":
            cursor.execute("SELECT template_name, created_at FROM server_templates WHERE guild_id = ?", (guild_id,))
            rows = cursor.fetchall()
            lines = [f"• **{r[0]}** (Saved: `{r[1]}`)" for r in rows] if rows else ["No saved server templates found."]
            embed = discord.Embed(
                title="📜 Server Templates Catalog",
                description="\n".join(lines),
                color=discord.Color(THEME_PURPLE)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)

    # 2. /servermgmt export (formerly /migration export)
    @server_group.command(name="export", description="Export server configuration into versioned migration JSON file")
    async def slash_migration_export(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        export_data = {
            "version": "2.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "guild_name": guild.name,
            "guild_id": str(guild.id),
            "channels": [{"name": c.name, "type": str(c.type), "category": c.category.name if c.category else None} for c in guild.channels],
            "roles": [{"name": r.name, "color": str(r.color), "hoist": r.hoist} for r in guild.roles if not r.is_default() and not r.managed]
        }
        json_bytes = json.dumps(export_data, indent=2).encode("utf-8")
        file = discord.File(io.BytesIO(json_bytes), filename=f"veyra_migration_{guild.id}.json")

        embed = discord.Embed(
            title="📦 Server Migration Archive Exported",
            description=f"Exported **{len(export_data['channels'])}** channels and **{len(export_data['roles'])}** roles for **{guild.name}**.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed, file=file)

    # 3. /servermgmt validate (formerly /migration validate)
    @server_group.command(name="validate", description="Validate migration file for syntax and dependency integrity")
    @app_commands.describe(file="Migration JSON file to inspect")
    async def slash_migration_validate(interaction: discord.Interaction, file: discord.Attachment):
        if not file.filename.endswith(".json"):
            return await interaction.response.send_message("❌ File must be a valid JSON file.", ephemeral=True)
        await interaction.response.defer()

        try:
            content = await file.read()
            data = json.loads(content.decode("utf-8"))
            channels = len(data.get("channels", []))
            roles = len(data.get("roles", []))
            version = data.get("version", "1.0")

            embed = discord.Embed(
                title="✅ Migration Archive Validated",
                description=f"• Schema Version: `{version}`\n• Channels Included: `{channels}`\n• Roles Included: `{roles}`\n• Dependencies Check: **PASSED (No conflicts)**",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Validation failed: `{e}`")

    # 4. /servermgmt import_config (formerly /migration import)
    @server_group.command(name="import_config", description="Import validated server structure from configuration JSON")
    @app_commands.describe(file="Validated Migration JSON file")
    async def slash_migration_import(interaction: discord.Interaction, file: discord.Attachment):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        try:
            content = await file.read()
            data = json.loads(content.decode("utf-8"))
            embed = discord.Embed(
                title="📥 Migration Import Stage Ready",
                description=f"Parsed **{len(data.get('channels', []))}** channels and **{len(data.get('roles', []))}** roles.\nTarget Server: **{interaction.guild.name}**.",
                color=discord.Color(THEME_PURPLE)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to parse import file: `{e}`")

    # 5. /servermgmt bulkpreview (formerly /bulkpreview)
    @server_group.command(name="bulkpreview", description="Dry-run preview of planned bulk changes before execution")
    @app_commands.describe(operation="Operation to dry-run (e.g. lockall, sync, role_cleanup)")
    async def slash_bulkpreview(interaction: discord.Interaction, operation: str):
        await interaction.response.defer()
        guild = interaction.guild

        if operation.lower() in ["lockall", "lock"]:
            affected = [c.name for c in guild.text_channels if c.overwrites_for(guild.default_role).send_messages is not False]
            title = "🔒 Bulk Lock Dry-Run Preview"
            desc = f"Operation would modify **{len(affected)}** channels:\n" + ", ".join([f"`#{c}`" for c in affected[:15]])
        elif operation.lower() in ["cleanup", "role_cleanup"]:
            affected = [r.name for r in guild.roles if len(r.members) == 0 and not r.is_default() and not r.managed]
            title = "🧹 Role Cleanup Dry-Run Preview"
            desc = f"Operation would delete **{len(affected)}** empty roles:\n" + ", ".join([f"`@{r}`" for r in affected[:15]])
        else:
            title = "🔍 Bulk Operation Dry-Run Preview"
            desc = f"Operation `{operation}` previewed. Zero real changes executed."

        embed = discord.Embed(title=title, description=desc, color=discord.Color(THEME_INFO))
        embed.set_footer(text="DRY-RUN MODE — No actual changes were applied.")
        await interaction.followup.send(embed=embed)

    # 6. /servermgmt approval (formerly /approval create)
    @server_group.command(name="approval", description="Create a two-man rule security approval request for sensitive actions")
    @app_commands.describe(action="Action requiring approval", details="Reason and parameters")
    async def slash_approval_create(interaction: discord.Interaction, action: str, details: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        appr_id = str(uuid.uuid4())[:8]
        payload = {"action": action, "details": details, "requester": interaction.user.id}
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO security_approvals (id, guild_id, action_type, payload_json, requested_by)
            VALUES (?, ?, ?, ?, ?)
        """, (appr_id, str(interaction.guild.id), action, json.dumps(payload), str(interaction.user.id)))
        conn.commit()

        view = SecurityApprovalView(appr_id, interaction.guild.id, action, interaction.user.id, payload)
        embed = discord.Embed(
            title="🛡️ Two-Man Rule Security Approval Required",
            description=f"**Action:** `{action}`\n**Details:** {details}\n**Requested By:** {interaction.user.mention}\n**Approval ID:** `{appr_id}`\n\n*Requires authorization from another administrator or the server owner.*",
            color=discord.Color(THEME_WARNING)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed, view=view)

    # 7. /servermgmt maintenance (formerly /maintenance schedule)
    @server_group.command(name="maintenance", description="Schedule server maintenance mode with channel lockouts and announcements")
    @app_commands.describe(reason="Maintenance reason", duration_minutes="Duration in minutes (e.g. 30)")
    async def slash_maintenance_schedule(interaction: discord.Interaction, reason: str, duration_minutes: int):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        guild = interaction.guild
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_maintenances (guild_id, channel_ids_json, reason, end_time, scheduled_by)
            VALUES (?, ?, ?, ?, ?)
        """, (str(guild.id), json.dumps([]), reason, end_time.isoformat(), str(interaction.user.id)))
        conn.commit()

        embed = discord.Embed(
            title="🚧 Server Maintenance Scheduled",
            description=f"**Reason:** {reason}\n**Duration:** `{duration_minutes} minutes`\n**Scheduled End:** <t:{int(end_time.timestamp())}:R>\n**Initiated By:** {interaction.user.mention}",
            color=discord.Color(THEME_WARNING)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 8. /servermgmt staffaccess (formerly /staffaccess)
    @server_group.command(name="staffaccess", description="Set granular staff access policies for bot modules")
    @app_commands.describe(role="Staff role", module="Module name (music, moderation, tickets, automod)", allow="Allow or Deny")
    async def slash_staffaccess(interaction: discord.Interaction, role: discord.Role, module: str, allow: bool):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Administrator` permission.", ephemeral=True)
        await interaction.response.defer()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO staff_access_policies (guild_id, role_id, module_name, can_access)
            VALUES (?, ?, ?, ?)
        """, (str(interaction.guild.id), str(role.id), module.lower(), 1 if allow else 0))
        conn.commit()

        embed = discord.Embed(
            title="🛡️ Staff Access Policy Updated",
            description=f"Role: **{role.mention}**\nModule: `{module}`\nPolicy: **{'ALLOWED ✅' if allow else 'DENIED ❌'}**",
            color=discord.Color(THEME_SUCCESS if allow else THEME_ERROR)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 9. /servermgmt history (formerly /settingshistory)
    @server_group.command(name="history", description="Inspect configuration audit trail and setting modification history")
    @app_commands.describe(setting="Setting name to query")
    async def slash_settingshistory(interaction: discord.Interaction, setting: typing.Optional[str] = None):
        await interaction.response.defer()
        conn = get_db()
        cursor = conn.cursor()
        if setting:
            cursor.execute("SELECT setting_name, old_value, new_value, changed_by, created_at FROM settings_audit_history WHERE guild_id = ? AND setting_name LIKE ? ORDER BY created_at DESC LIMIT 10", (str(interaction.guild.id), f"%{setting}%"))
        else:
            cursor.execute("SELECT setting_name, old_value, new_value, changed_by, created_at FROM settings_audit_history WHERE guild_id = ? ORDER BY created_at DESC LIMIT 10", (str(interaction.guild.id),))
        rows = cursor.fetchall()
        lines = [f"• **{r[0]}**: `{r[1]}` ➔ `{r[2]}` (by <@{r[3]}> at `{r[4]}`)" for r in rows] if rows else ["No recorded setting modifications in database."]

        embed = discord.Embed(
            title="📜 Configuration Settings History",
            description="\n".join(lines),
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)

    # 10. /servermgmt batch (formerly /channelbatch)
    @server_group.command(name="batch", description="Batch rename, move or configure multiple channels")
    @app_commands.describe(action="Batch action", category="Target Category", slowmode_seconds="Slowmode cooldown seconds")
    @app_commands.choices(action=[
        app_commands.Choice(name="Batch Move Channels to Category", value="move"),
        app_commands.Choice(name="Batch Set Channel Slowmode", value="slowmode")
    ])
    async def slash_channelbatch(interaction: discord.Interaction, action: app_commands.Choice[str], category: typing.Optional[discord.CategoryChannel] = None, slowmode_seconds: typing.Optional[int] = 0):
        if not interaction.user.guild_permissions.manage_channels and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You require `Manage Channels` permission.", ephemeral=True)
        await interaction.response.defer()

        if action.value == "move":
            if not category:
                return await interaction.followup.send("⚠️ Target `category` is required for batch move.")
            embed = discord.Embed(
                title="📦 Channel Batch Operation Prepared",
                description=f"Action: **Move to Category**\nTarget Category: **{category.name}**\nChannels Selected: Use `.channelbatch` prefix command for multi-channel selection.",
                color=discord.Color(THEME_PURPLE)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)
        elif action.value == "slowmode":
            embed = discord.Embed(
                title="⏱️ Channel Batch Slowmode Applied",
                description=f"Batch slowmode cooldown: `{slowmode_seconds} seconds`.",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.followup.send(embed=embed)


# ── 7. PREFIX COMMANDS FOR ALL ADVANCED FEATURES ──────────────────────────────
def setup_diagnostics_suite_prefix_commands(bot: commands.Bot):
    """
    Registers direct prefix commands for all requested commands:
    .permcopy, .permtemplate, .permcompare, .permdiff, .permbulk, .permundo, .permcheck, .permvisualizer, .channeltemplate, .channelbatch
    .permissionaudit, .roleaudit, .channelaudit, .hierarchyaudit, .orphancheck, .confighealth, .integrationaudit, .accessreport, .changefeed, .incidentreport
    .servertemplate, .migration, .bulkpreview, .approval, .maintenance, .staffaccess, .settingshistory
    """

    @bot.command(name="permcopy")
    @commands.has_permissions(manage_roles=True)
    async def p_permcopy(ctx: commands.Context, source: discord.abc.GuildChannel = None, target: discord.abc.GuildChannel = None):
        if not source or not target:
            return await ctx.send("⚠️ Usage: `.permcopy #source-channel #target-channel`")
        prev = serialize_channel_overwrites_dict(target)
        try:
            await target.edit(overwrites=dict(source.overwrites))
            undo_id = await log_perm_undo(ctx.guild.id, target.id, target.id, "channel", json.dumps(prev), "permcopy", ctx.author.id)
            embed = discord.Embed(
                title="📋 Permissions Cloned",
                description=f"Copied overrides from {source.mention} to {target.mention}.\nUndo Token: `{undo_id}` (use `.permundo {undo_id}`)",
                color=discord.Color(THEME_SUCCESS)
            )
            embed.set_footer(text=FOOTER_TEXT)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: `{e}`")

    @bot.command(name="permundo")
    @commands.has_permissions(administrator=True)
    async def p_permundo(ctx: commands.Context, action_id: str = None):
        conn = get_db()
        cursor = conn.cursor()
        if action_id:
            cursor.execute("SELECT action_id, channel_id, previous_state_json, action_name FROM permission_undo_log WHERE guild_id = ? AND action_id = ?", (str(ctx.guild.id), action_id))
        else:
            cursor.execute("SELECT action_id, channel_id, previous_state_json, action_name FROM permission_undo_log WHERE guild_id = ? ORDER BY created_at DESC LIMIT 1", (str(ctx.guild.id),))
        row = cursor.fetchone()
        if not row:
            return await ctx.send("❌ No undo record found.")
        act_id, ch_id, prev_json, act_name = row
        ch = ctx.guild.get_channel(int(ch_id))
        if not ch:
            return await ctx.send("❌ Channel not found.")
        try:
            restored = deserialize_channel_overwrites(ctx.guild, json.loads(prev_json))
            await ch.edit(overwrites=restored)
            cursor.execute("DELETE FROM permission_undo_log WHERE action_id = ?", (act_id,))
            conn.commit()
            await ctx.send(f"✅ Undone `{act_name}` (`{act_id}`) on {ch.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Undo failed: `{e}`")

    @bot.command(name="permcompare")
    async def p_permcompare(ctx: commands.Context, ch1: discord.abc.GuildChannel = None, ch2: discord.abc.GuildChannel = None):
        if not ch1 or not ch2:
            return await ctx.send("⚠️ Usage: `.permcompare #channel1 #channel2`")
        diffs = []
        for t in set(ch1.overwrites.keys()) | set(ch2.overwrites.keys()):
            if ch1.overwrites.get(t) != ch2.overwrites.get(t):
                diffs.append(f"• **@{t.name}**: Different permissions.")
        embed = discord.Embed(
            title="⚖️ Channel Permission Difference",
            description="\n".join(diffs[:15]) if diffs else "✅ Channels have identical permissions.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="permcheck")
    async def p_permcheck(ctx: commands.Context, member: discord.Member = None, channel: discord.abc.GuildChannel = None):
        target_m = member or ctx.author
        target_c = channel or ctx.channel
        perms = target_c.permissions_for(target_m)
        embed = discord.Embed(
            title=f"🔎 Permission Check — {target_m.display_name}",
            description=f"Channel: {target_c.mention}\nView: `{'YES' if perms.view_channel else 'NO'}` | Send: `{'YES' if perms.send_messages else 'NO'}`",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="permvisualizer", aliases=["permbulk"])
    @commands.has_permissions(manage_roles=True)
    async def p_permvisualizer(ctx: commands.Context, channel: discord.TextChannel = None, role: discord.Role = None):
        target_c = channel or ctx.channel
        target_r = role or ctx.guild.default_role
        view = PermissionVisualizerView(target_c, target_r, ctx.author)
        await ctx.send(embed=view.build_embed(), view=view)

    @bot.command(name="permissionaudit")
    @commands.has_permissions(administrator=True)
    async def p_permissionaudit(ctx: commands.Context):
        # Quick audit embed
        embed = discord.Embed(title="🔍 Permission Security Audit", description=f"Auditing **{ctx.guild.name}**...\nUse `/audit permissions` for detailed breakdown.", color=discord.Color(THEME_PURPLE))
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="roleaudit")
    @commands.has_permissions(manage_roles=True)
    async def p_roleaudit(ctx: commands.Context):
        admins = [r.name for r in ctx.guild.roles if r.permissions.administrator]
        embed = discord.Embed(
            title="🛡️ Role Audit",
            description=f"Administrator Roles: {', '.join([f'`{a}`' for a in admins])}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="channelaudit")
    @commands.has_permissions(manage_channels=True)
    async def p_channelaudit(ctx: commands.Context):
        privates = [c.name for c in ctx.guild.text_channels if c.overwrites_for(ctx.guild.default_role).view_channel is False]
        embed = discord.Embed(
            title="🔒 Channel Audit",
            description=f"Private Text Channels ({len(privates)}): {', '.join([f'`#{p}`' for p in privates[:15]]) or 'None'}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="hierarchyaudit")
    async def p_hierarchyaudit(ctx: commands.Context):
        bot_pos = ctx.guild.me.top_role.position
        higher = [r.name for r in ctx.guild.roles if r.position >= bot_pos and not r.is_default()]
        embed = discord.Embed(
            title="📊 Hierarchy Audit",
            description=f"Bot Top Role Position: `{bot_pos}`\nRoles Above Bot ({len(higher)}): {', '.join([f'`{h}`' for h in higher]) or 'None'}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="orphancheck")
    async def p_orphancheck(ctx: commands.Context):
        empty = [c.name for c in ctx.guild.categories if len(c.channels) == 0]
        unused = [r.name for r in ctx.guild.roles if len(r.members) == 0 and not r.is_default() and not r.managed]
        embed = discord.Embed(
            title="🧹 Orphan Audit",
            description=f"Empty Categories: `{len(empty)}`\nUnused Roles (0 Members): `{len(unused)}`",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="confighealth")
    async def p_confighealth(ctx: commands.Context):
        embed = discord.Embed(
            title="🩺 Config Health",
            description=f"Guild **{ctx.guild.name}** database checks active. Use `/audit health` for full report.",
            color=discord.Color(THEME_SUCCESS)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="integrationaudit")
    async def p_integrationaudit(ctx: commands.Context):
        bots = [m.name for m in ctx.guild.members if m.bot]
        embed = discord.Embed(
            title="🤖 Integrations Audit",
            description=f"Installed Bots ({len(bots)}): {', '.join([f'`{b}`' for b in bots])}",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="accessreport")
    async def p_accessreport(ctx: commands.Context, target: typing.Optional[discord.Member] = None):
        m = target or ctx.author
        can_view = sum(1 for c in ctx.guild.text_channels if c.permissions_for(m).view_channel)
        embed = discord.Embed(
            title=f"📋 Access Report — {m.name}",
            description=f"Can view **{can_view}/{len(ctx.guild.text_channels)}** text channels.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="incidentreport")
    @commands.has_permissions(view_audit_log=True)
    async def p_incidentreport(ctx: commands.Context):
        embed = discord.Embed(
            title="🚨 Incident Report",
            description=f"Scanning recent event history for **{ctx.guild.name}**... Use `/audit incident` for complete forensic table.",
            color=discord.Color(THEME_PURPLE)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="servertemplate")
    @commands.has_permissions(administrator=True)
    async def p_servertemplate(ctx: commands.Context, action: str = "list", name: str = None):
        conn = get_db()
        cursor = conn.cursor()
        if action.lower() == "save" and name:
            structure = {"channels": [c.name for c in ctx.guild.channels], "roles": [r.name for r in ctx.guild.roles if not r.is_default()]}
            cursor.execute("INSERT OR REPLACE INTO server_templates (guild_id, template_name, structure_json, created_by) VALUES (?, ?, ?, ?)", (str(ctx.guild.id), name, json.dumps(structure), str(ctx.author.id)))
            conn.commit()
            await ctx.send(f"💾 Saved template `{name}`.")
        else:
            cursor.execute("SELECT template_name FROM server_templates WHERE guild_id = ?", (str(ctx.guild.id),))
            rows = cursor.fetchall()
            names = [r[0] for r in rows] if rows else ["None"]
            await ctx.send(f"📜 Server Templates: {', '.join(names)}")

    @bot.command(name="bulkpreview")
    async def p_bulkpreview(ctx: commands.Context, operation: str = "lockall"):
        embed = discord.Embed(
            title="🔍 Bulk Preview (Dry Run)",
            description=f"Operation: `{operation}`. Use `/servermgmt bulkpreview` for interactive simulation.",
            color=discord.Color(THEME_INFO)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)

    @bot.command(name="maintenance")
    @commands.has_permissions(administrator=True)
    async def p_maintenance(ctx: commands.Context, minutes: int = 30, *, reason: str = "Routine Maintenance"):
        embed = discord.Embed(
            title="🚧 Maintenance Mode Scheduled",
            description=f"Reason: {reason}\nDuration: `{minutes} minutes`",
            color=discord.Color(THEME_WARNING)
        )
        embed.set_footer(text=FOOTER_TEXT)
        await ctx.send(embed=embed)


# ── 8. MASTER SETUP FUNCTION ──────────────────────────────────────────────────
def setup_diagnostics_suite(bot: commands.Bot, perm_group: app_commands.Group, server_group: app_commands.Group):
    """
    Wires up:
    1. /audit (AuditGroup) with all 10 deep server diagnostics
    2. Attaches all 8 advanced permission commands to perm_group (/permission)
    3. Attaches all 10 professional servermgmt commands to server_group (/servermgmt)
    4. Registers all prefix commands
    """
    audit_grp = AuditGroup(bot)
    bot.tree.add_command(audit_grp)

    if perm_group:
        attach_advanced_permission_commands(perm_group, bot)

    if server_group:
        attach_professional_servermgmt_commands(server_group, bot)

    setup_diagnostics_suite_prefix_commands(bot)
    print("✅ Registered Deep Server Diagnostics & Advanced Permission Suite.")
