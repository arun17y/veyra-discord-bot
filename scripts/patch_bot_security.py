import os
import re

bot_path = os.path.join(os.path.dirname(__file__), '../bot/bot.py')
with open(bot_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update is_whitelisted to check role & channel entries from whitelists table
old_is_wl_part = '''        # 2. Check legacy user whitelists table
        cursor.execute("SELECT 1 FROM whitelists WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
        if cursor.fetchone():
            conn.close()
            return True'''

new_is_wl_part = '''        # 2. Check whitelists table for user
        cursor.execute("SELECT 1 FROM whitelists WHERE guild_id = ? AND user_id = ? AND LOWER(COALESCE(type, 'user')) IN ('user', 'member')", (str(guild_id), str(user_id)))
        if cursor.fetchone():
            conn.close()
            return True

        # Check whitelists table for roles
        if check_roles:
            placeholders = ",".join("?" for _ in check_roles)
            cursor.execute(f"SELECT 1 FROM whitelists WHERE guild_id = ? AND user_id IN ({placeholders}) AND LOWER(type) = 'role'", [str(guild_id)] + check_roles)
            if cursor.fetchone():
                conn.close()
                return True

        # Check whitelists table for channel
        if channel_id:
            cursor.execute("SELECT 1 FROM whitelists WHERE guild_id = ? AND user_id = ? AND LOWER(type) = 'channel'", (str(guild_id), str(channel_id)))
            if cursor.fetchone():
                conn.close()
                return True'''

if old_is_wl_part in content:
    content = content.replace(old_is_wl_part, new_is_wl_part)
    print("Updated is_whitelisted with role & channel support!")
else:
    print("Warning: old_is_wl_part not found")

# 2. Update on_member_join Anti-Raid and Verification
old_join_sec = '''    # 0. Anti Raid check (Disabled)
    pass

    # 5. Verification System
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled, unverified_role FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
        v_row = cursor.fetchone()
        conn.close()
        if v_row and v_row[0] == 1 and v_row[1] and str(v_row[1]).isdigit():
            uv_role = guild.get_role(int(v_row[1]))
            if uv_role and uv_role < guild.me.top_role:
                await member.add_roles(uv_role, reason="VEYRA Verification Gate: Assign Unverified")
                print(f"✅ Assigned unverified role to {member.name}")
    except Exception as e:
        print(f"Failed to assign unverified role on join: {e}")'''

new_join_sec = '''    # --- 0. REAL-TIME ANTI-RAID ENFORCEMENT ---
    try:
        if not member.bot and not (is_whitelisted(guild.id, member.id) or member.id == guild.owner_id):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT enabled, invite_link_protection, join_rate_threshold, min_account_age, punishment_type FROM antiraid_settings WHERE guild_id = ?", (str(guild.id),))
            ar_row = cursor.fetchone()
            conn.close()
            
            if ar_row and ar_row[0] == 1:
                inv_prot = ar_row[1]
                rate_thresh = ar_row[2] or 10
                min_age_days = ar_row[3] or 3
                punish_type = (ar_row[4] or 'Kick').strip().capitalize()
                
                # Check 1: Minimum Account Age
                import datetime as _dt
                acc_age_days = (_dt.datetime.now(_dt.timezone.utc) - member.created_at).days
                if acc_age_days < min_age_days:
                    reason_msg = f"Account age ({acc_age_days}d) is below minimum threshold ({min_age_days}d)"
                    print(f"[ANTI-RAID] {punish_type} on {member.name} in {guild.name}: {reason_msg}")
                    
                    if punish_type == 'Ban':
                        await guild.ban(member, reason=f"VEYRA Anti-Raid: {reason_msg}")
                    elif punish_type == 'Kick':
                        await member.kick(reason=f"VEYRA Anti-Raid: {reason_msg}")
                    else:
                        await member.timeout(_dt.timedelta(days=7), reason=f"VEYRA Anti-Raid: {reason_msg}")
                        
                    await dispatch_discord_log(
                        guild, 'security',
                        "🛡️ Anti-Raid: Rogue Account Neutralized",
                        f"**Target:** {member.mention} (`{member.id}`)\\n**Reason:** {reason_msg}\\n**Action Executed:** `{punish_type}`",
                        color=0xEF4444
                    )
                    log_system_event(guild.id, "VEYRA Security", f"Anti-Raid {punish_type}", f"Neutralized {member.name}: {reason_msg}")
                    return

                # Check 2: Join Rate Sliding Window (in 10s)
                if not hasattr(bot, 'recent_guild_joins'):
                    bot.recent_guild_joins = {}
                join_list = bot.recent_guild_joins.setdefault(guild.id, [])
                now_mono = _time.monotonic()
                join_list = [t for t in join_list if now_mono - t < 10.0]
                join_list.append(now_mono)
                bot.recent_guild_joins[guild.id] = join_list
                
                if len(join_list) > rate_thresh:
                    reason_msg = f"Join rate surge ({len(join_list)} joins in 10s > threshold {rate_thresh})"
                    print(f"[ANTI-RAID LOCKDOWN] {guild.name}: {reason_msg}")
                    
                    if punish_type == 'Ban':
                        await guild.ban(member, reason=f"VEYRA Anti-Raid: {reason_msg}")
                    elif punish_type == 'Kick':
                        await member.kick(reason=f"VEYRA Anti-Raid: {reason_msg}")
                    else:
                        await member.timeout(_dt.timedelta(days=7), reason=f"VEYRA Anti-Raid: {reason_msg}")
                        
                    await dispatch_discord_log(
                        guild, 'security',
                        "🚨 Anti-Raid: Mass Join Surge Neutralized",
                        f"**Target:** {member.mention} (`{member.id}`)\\n**Reason:** {reason_msg}\\n**Action Executed:** `{punish_type}`",
                        color=0xDC2626
                    )
                    log_system_event(guild.id, "VEYRA Security", f"Anti-Raid Lockdown {punish_type}", f"Neutralized {member.name}: {reason_msg}")
                    return
    except Exception as ar_err:
        print(f"[Anti-Raid Error] {ar_err}")

    # --- 5. VERIFICATION GATE AUTO-QUARANTINE ---
    try:
        if not member.bot:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT enabled, unverified_role FROM verification_settings WHERE guild_id = ?", (str(guild.id),))
            v_row = cursor.fetchone()
            conn.close()
            if v_row and v_row[0] == 1 and v_row[1]:
                uv_spec = str(v_row[1]).strip()
                uv_role = None
                if uv_spec.isdigit():
                    uv_role = guild.get_role(int(uv_spec))
                if not uv_role:
                    uv_role = discord.utils.find(lambda r: r.name.lower() == uv_spec.lower(), guild.roles)
                if uv_role and uv_role < guild.me.top_role:
                    await member.add_roles(uv_role, reason="VEYRA Verification Gate: Automated Entry Quarantine")
                    print(f"✅ Assigned unverified quarantine role '{uv_role.name}' to {member.name}")
    except Exception as e:
        print(f"Failed to assign unverified role on join: {e}")'''

if old_join_sec in content:
    content = content.replace(old_join_sec, new_join_sec)
    print("Updated on_member_join with real-time Anti-Raid and Verification!")
else:
    print("Warning: old_join_sec not found")

# 3. Update verify_callback to log member verified to #security-logs
old_verify_cb_success = '''                print("DEBUG: roles applied successfully, sending success response...")
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)'''

new_verify_cb_success = '''                print("DEBUG: roles applied successfully, sending success response...")
                await interaction.response.send_message("✅ Verification successful! Welcome to the server.", ephemeral=True)
                try:
                    await dispatch_discord_log(
                        interaction.guild, 'security',
                        "✅ Member Verified",
                        f"**Member:** {interaction.user.mention} (`{interaction.user.id}`)\\n**Role Granted:** `{v_role.name}`" + (f"\\n**Role Removed:** `{uv_role.name}`" if uv_role else ""),
                        color=0x10B981
                    )
                    log_system_event(interaction.guild.id, interaction.user.name, "Member Verified", f"Verified role {v_role.name} granted")
                except Exception as log_ex:
                    print(f"Failed to log verification success: {log_ex}")'''

if old_verify_cb_success in content:
    content = content.replace(old_verify_cb_success, new_verify_cb_success)
    print("Updated verify_callback with real-time Discord embed logging!")
else:
    print("Warning: old_verify_cb_success not found")

with open(bot_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished patching bot/bot.py successfully!")
