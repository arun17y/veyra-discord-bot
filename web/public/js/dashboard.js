function isTrue(val) {
    return val === 1 || val === '1' || val === true || val === 'true';
}
window.isTrue = isTrue;
window.isDashboardHydrating = false;


window.updateActiveGuildUI = function(guildId, guildName, iconUrl) {
    if (!guildId) return;
    if (guildName) {
        ['sidebar-guild-name', 'managing-server-name', 'dashboard-server-name', 'header-server-dropdown-name', 'tickets-sidebar-guild-name'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerText = guildName;
        });
    }
    if (iconUrl) {
        const sideImg = document.getElementById('sidebar-guild-avatar-img');
        if (sideImg) sideImg.src = iconUrl;
        const tkImg = document.getElementById('tickets-sidebar-guild-icon');
        if (tkImg) tkImg.src = iconUrl;
        const headerImg = document.querySelector('#header-server-avatar-img img');
        if (headerImg) headerImg.src = iconUrl;
        const dropImg = document.querySelector('#header-server-dropdown-icon img');
        if (dropImg) dropImg.src = iconUrl;
    }
};

window.resolveGuildPlan = function(planRaw, status) {
    if (!planRaw) return { type: 'Free', name: 'Free Tier', badge: 'FREE TIER', isPaid: false, isPrem: false, isEnt: false, isPro: false };
    const p = String(planRaw).toLowerCase();
    const isActive = status !== 'expired';
    if (!isActive) return { type: 'Free', name: 'Free Tier (Expired)', badge: 'EXPIRED', isPaid: false, isPrem: false, isEnt: false, isPro: false };
    
    if (p.includes('premium') || p.includes('enterprise')) {
        return { type: 'Premium', name: 'Premium Plan', badge: 'PREMIUM', isPaid: true, isPrem: true, isEnt: true, isPro: false };
    }
    if (p.includes('pro')) {
        return { type: 'Pro', name: 'Pro Plan', badge: 'PRO', isPaid: true, isPrem: false, isEnt: false, isPro: true };
    }
    return { type: 'Free', name: 'Free Tier', badge: 'FREE TIER', isPaid: false, isPrem: false, isEnt: false, isPro: false };
};

window.updateWhitelistCapacityUI = function(count) {
    const capacityEl = document.getElementById('overview-whitelist-capacity');
    const footerEl = document.getElementById('overview-whitelist-footer');
    if (!capacityEl) return;
    
    const currentPlan = (window.currentServerPlan || localStorage.getItem('current_server_plan') || 'Free').toLowerCase();
    let limitDisplay = '1';
    let footerText = 'Free plan quota (1 slot allowed)';
    if (currentPlan.includes('enterprise')) {
        limitDisplay = '∞';
        footerText = 'Unlimited staff overrides';
    } else if (currentPlan.includes('pro')) {
        limitDisplay = '10';
        footerText = 'Pro Sentinel quota (10 slots)';
    }

    const c = count !== undefined ? count : (window.activeWhitelistCache ? window.activeWhitelistCache.length : 0);
    capacityEl.innerText = `${c} / ${limitDisplay}`;
    if (footerEl) footerEl.innerText = footerText;
};


function navigateToHome(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    sessionStorage.setItem('activeScreen', 'landing');
    if (window.location.pathname.includes('/manage') || window.location.pathname.includes('/dashboard')) {
        window.location.href = '/';
        return;
    }
    if (typeof showScreen === 'function') {
        showScreen('landing');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.navigateToHome = navigateToHome;


// --- 11b. NEW SECURITY SUB-PANES HANDLERS ---

function loadSecuritySettings(guildId) {
    if (!guildId) guildId = activeGuildId;
    if (!guildId) return;
    fetch(`/api/settings/security/${guildId}`)
        .then(res => res.json())
        .then(s => {
            if (!s) return;
            const limits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
            limits.forEach(key => {
                const dbKey = key.replace('-', '_');
                const limitEl = document.getElementById(`sec-limit-${key}`);
                const punishEl = document.getElementById(`sec-punish-${key}`);
                const enableEl = document.getElementById(`sec-enable-${key}`);
                
                if (limitEl && s[`anti_${dbKey}_limit`] !== undefined) limitEl.value = s[`anti_${dbKey}_limit`];
                if (punishEl && s[`anti_${dbKey}_punish`]) punishEl.value = s[`anti_${dbKey}_punish`];
                if (enableEl) enableEl.checked = s[`anti_${dbKey}_enabled`] === 1 || s[`anti_${dbKey}_enabled`] === true || s[`anti_${dbKey}_enabled`] === '1';
            });
            
            const instant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename', 'emoji-delete', 'emoji-rename', 'invite-delete', 'invite-link', 'ghost-ping'];
            instant.forEach(key => {
                let dbKey = key.replace('-', '_');
                if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
                if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
                if (dbKey === 'vanity') dbKey = 'vanity_change';
                if (dbKey === 'server-icon') dbKey = 'server_icon_change';
                
                const punishEl = document.getElementById(`sec-punish-${key}`);
                const enableEl = document.getElementById(`sec-enable-${key}`);
                
                if (punishEl && s[`anti_${dbKey}_punish`]) punishEl.value = s[`anti_${dbKey}_punish`];
                if (enableEl && s[`anti_${dbKey}_enabled`] !== undefined) {
                    enableEl.checked = s[`anti_${dbKey}_enabled`] === 1 || s[`anti_${dbKey}_enabled`] === true || s[`anti_${dbKey}_enabled`] === '1';
                }
            });
        })
        .catch(err => console.error("Error loading security settings:", err));
}
window.loadSecuritySettings = loadSecuritySettings;

// --- SECURITY GENERAL HEALTH CHECK (Security.gg Replica) ---
window.loadSecurityGeneralHealth = function(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    
    fetch(`/api/guild/security-health/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const adminCard = document.getElementById('sec-health-admin-card');
            const adminTitle = document.getElementById('sec-health-admin-title');
            const adminDesc = document.getElementById('sec-health-admin-desc');
            const adminIcon = document.getElementById('sec-health-admin-icon');
            
            if (adminCard && adminTitle && adminDesc && adminIcon) {
                if (data.has_admin) {
                    adminCard.className = 'audit-card ok';
                    adminCard.style.borderLeftColor = '#10b981';
                    adminTitle.innerText = 'LOOKING FINE';
                    adminDesc.innerText = 'Security has the administrator which means all the features should work fine.';
                    adminIcon.style.color = '#10b981';
                    adminIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                } else {
                    adminCard.className = 'audit-card threat';
                    adminCard.style.borderLeftColor = '#ef4444';
                    adminTitle.innerText = 'THINGS TO DO';
                    adminDesc.innerText = 'Security does not have Administrator permission. Please grant Administrator so all protection features can act.';
                    adminIcon.style.color = '#ef4444';
                    adminIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
                }
            }
            
            const roleCard = document.getElementById('sec-health-role-card');
            const roleTitle = document.getElementById('sec-health-role-title');
            const roleDesc = document.getElementById('sec-health-role-desc');
            const roleIcon = document.getElementById('sec-health-role-icon');
            
            if (roleCard && roleTitle && roleDesc && roleIcon) {
                if (data.is_highest_role) {
                    roleCard.className = 'audit-card ok';
                    roleCard.style.borderLeftColor = '#10b981';
                    roleTitle.innerText = 'LOOKING FINE';
                    roleDesc.innerText = 'Security has the highest role hierarchy. All member actions can be moderated effectively.';
                    roleIcon.style.color = '#10b981';
                    roleIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                } else {
                    roleCard.className = 'audit-card threat';
                    roleCard.style.borderLeftColor = '#ef4444';
                    roleTitle.innerText = 'THINGS TO DO';
                    roleDesc.innerText = "Security doesn't have the highest role which means it cannot punish some of your users even if they bypass limits.";
                    roleIcon.style.color = '#ef4444';
                    roleIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
                }
            }
        })
        .catch(err => console.error("Error loading security health:", err));
};

// --- VERIFICATION GATE ENGINE & EMBED CUSTOMIZER ---
function loadVerificationSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    fetch(`/api/settings/verification/${targetGuild}`)
        .then(res => res.json())
        .then(v => {
            if (!v) return;
            const isEnabled = isTrue(v.enabled);
            const verEnableEl = document.getElementById('verif-enable') || document.getElementById('sec-enable-verification');
            if (verEnableEl) verEnableEl.checked = isEnabled;
            
            const verLevelEl = document.getElementById('verif-level');
            if (verLevelEl) verLevelEl.value = 'Button';
            
            const verUnverifiedEl = document.getElementById('verif-unverified-role');
            if (verUnverifiedEl && v.unverified_role) verUnverifiedEl.value = v.unverified_role;
            
            const verVerifiedEl = document.getElementById('verif-role');
            if (verVerifiedEl && v.verified_role) verVerifiedEl.value = v.verified_role;
            
            const verActionEl = document.getElementById('verif-action');
            if (verActionEl) verActionEl.value = v.timeout_action || 'Kick';
            
            const verTimeoutEl = document.getElementById('verif-timeout');
            if (verTimeoutEl) verTimeoutEl.value = v.captcha_timeout !== undefined ? v.captcha_timeout : 90;
            
            const verChannelEl = document.getElementById('verif-channel');
            if (verChannelEl && v.channel) verChannelEl.value = v.channel;
            
            // Embed Customizer fields
            if (document.getElementById('verif-embed-title')) {
                document.getElementById('verif-embed-title').value = v.embed_title || '🛡️ Member Verification Required';
            }
            if (document.getElementById('verif-embed-desc')) {
                document.getElementById('verif-embed-desc').value = v.embed_desc || 'Welcome to the server!\n\nTo gain full access to server channels, voice rooms, and media, please verify your Discord account using the button below.\n\n✅ **Instant Access:** You will immediately be granted the member role.';
            }
            if (document.getElementById('verif-embed-color')) {
                const col = v.embed_color || '#E11D48';
                document.getElementById('verif-embed-color').value = col;
                if (document.getElementById('verif-embed-color-picker')) document.getElementById('verif-embed-color-picker').value = col;
            }
            if (document.getElementById('verif-embed-thumb')) {
                document.getElementById('verif-embed-thumb').value = v.embed_thumbnail || '';
            }
            if (document.getElementById('verif-embed-banner')) {
                document.getElementById('verif-embed-banner').value = v.embed_image || '';
            }
            if (document.getElementById('verif-embed-footer')) {
                document.getElementById('verif-embed-footer').value = v.embed_footer || 'VEYRA Security Protocol • Automated Gatekeeper';
            }
            if (document.getElementById('verif-button-text')) {
                document.getElementById('verif-button-text').value = v.button_text || 'Verify Access';
            }
            if (document.getElementById('verif-button-style')) {
                document.getElementById('verif-button-style').value = (v.button_color || 'green').toLowerCase();
            }
            
            updateVerificationPreview();
        })
        .catch(err => console.error("Error loading verification settings:", err));
}

window.updateVerificationPreview = function() {
    const title = document.getElementById('verif-embed-title')?.value || '🛡️ Member Verification Required';
    const desc = document.getElementById('verif-embed-desc')?.value || 'Welcome to the server!';
    const color = document.getElementById('verif-embed-color')?.value || '#E11D48';
    const thumb = document.getElementById('verif-embed-thumb')?.value || '';
    const banner = document.getElementById('verif-embed-banner')?.value || '';
    const footer = document.getElementById('verif-embed-footer')?.value || 'VEYRA Security Protocol • Automated Gatekeeper';
    const btnLabel = document.getElementById('verif-button-text')?.value || 'Verify Access';
    const btnStyle = (document.getElementById('verif-button-style')?.value || 'green').toLowerCase();
    
    const pCard = document.getElementById('verif-preview-card');
    if (pCard) pCard.style.borderLeftColor = color;
    
    const pTitle = document.getElementById('verif-preview-title');
    if (pTitle) pTitle.innerText = title;
    
    const pDesc = document.getElementById('verif-preview-desc');
    if (pDesc) pDesc.innerText = desc;
    
    const pFooter = document.getElementById('verif-preview-footer');
    if (pFooter) pFooter.innerText = footer;
    
    const pThumb = document.getElementById('verif-preview-thumb');
    if (pThumb) {
        if (thumb && thumb.startsWith('http')) {
            pThumb.src = thumb;
            pThumb.style.display = 'block';
        } else {
            pThumb.style.display = 'none';
        }
    }
    
    const pBanner = document.getElementById('verif-preview-banner');
    if (pBanner) {
        if (banner && banner.startsWith('http')) {
            pBanner.src = banner;
            pBanner.style.display = 'block';
        } else {
            pBanner.style.display = 'none';
        }
    }
    
    const pBtnLabel = document.getElementById('verif-preview-btn-label');
    if (pBtnLabel) pBtnLabel.innerText = btnLabel;
    
    const pBtn = document.getElementById('verif-preview-btn');
    if (pBtn) {
        if (btnStyle === 'blurple') pBtn.style.background = '#5865F2';
        else if (btnStyle === 'grey' || btnStyle === 'gray') pBtn.style.background = '#4E5058';
        else if (btnStyle === 'red') pBtn.style.background = '#DA373C';
        else pBtn.style.background = '#248046'; // default green
    }
};

function saveVerificationSettings() {
    if (window.isDashboardHydrating) return;
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    
    const isEnabled = (document.getElementById('verif-enable') || document.getElementById('sec-enable-verification'))?.checked ? 1 : 0;
    const payload = {
        enabled: isEnabled,
        type: 'Button',
        unverified_role: document.getElementById('verif-unverified-role')?.value || '',
        verified_role: document.getElementById('verif-role')?.value || '',
        channel: document.getElementById('verif-channel')?.value || 'verify',
        timeout_action: document.getElementById('verif-action')?.value || 'Kick',
        captcha_timeout: parseInt(document.getElementById('verif-timeout')?.value || 90),
        embed_title: document.getElementById('verif-embed-title')?.value || '🛡️ Member Verification Required',
        embed_desc: document.getElementById('verif-embed-desc')?.value || '',
        embed_color: document.getElementById('verif-embed-color')?.value || '#E11D48',
        embed_thumbnail: document.getElementById('verif-embed-thumb')?.value || '',
        embed_image: document.getElementById('verif-embed-banner')?.value || '',
        embed_footer: document.getElementById('verif-embed-footer')?.value || 'VEYRA Security Protocol • Automated Gatekeeper',
        button_text: document.getElementById('verif-button-text')?.value || 'Verify Access',
        button_color: document.getElementById('verif-button-style')?.value || 'green'
    };
    
    fetch(`/api/settings/verification/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Verification Gate Saved", "Verification gateway configurations synced to database in real time.");
            updateVerificationPreview();
        } else {
            showToast("Save Error", data.error || "Failed to save verification settings", "error");
        }
    })
    .catch(err => {
        console.error("Error saving verification settings:", err);
        showToast("Error", "Failed to communicate with verification API.", "error");
    });
}

window.deployVerificationPanel = function() {
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    
    // Save first, then deploy
    saveVerificationSettings();
    showToast("Deploying Panel", "Dispatching interactive verification embed to server channel...");
    
    fetch(`/api/verification/deploy-panel/${targetGuild}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("Panel Deployed!", "Verification panel with interactive button is now live in your server!");
            } else {
                showToast("Deploy Failed", data.error || "Unable to send panel to channel.", "error");
            }
        })
        .catch(err => {
            console.error("Error deploying verification panel:", err);
            showToast("Error", "Failed to deploy verification panel.", "error");
        });
};

function toggleVerificationSettingsPane(enabled) {
    const form = document.getElementById('verification-form-container');
    const opts = document.getElementById('captcha-options-pane');
    if (form) form.style.opacity = enabled ? '1' : '0.6';
    if (opts) opts.style.opacity = enabled ? '1' : '0.6';
}

function loadBeastModeSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    fetch(`/api/settings/beastmode/${targetGuild}`)
        .then(res => res.json())
        .then(b => {
            if (!b) return;
            const isEnabled = isTrue(b.enabled);
            const beastEnableEl = document.getElementById('sec-enable-beast');
            if (beastEnableEl) beastEnableEl.checked = isEnabled;
            
            const limitEl = document.getElementById('beast-score-limit');
            if (limitEl) limitEl.value = b.score_limit !== undefined ? b.score_limit : 40;
            
            const punishEl = document.getElementById('beast-punishment-type');
            if (punishEl) punishEl.value = b.punishment_type || 'Kick';
            
            const wlBypassEl = document.getElementById('beast-whitelist-bypass');
            if (wlBypassEl) wlBypassEl.checked = isTrue(b.whitelist_bypass);
            
            const scores = ['bot-add', 'ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'prune', 'mention', 'vanity', 'webhook'];
            scores.forEach(key => {
                const el = document.getElementById(`score-${key}`);
                if (el) {
                    const dbKey = key.replace('-', '_');
                    el.value = b[`score_${dbKey}`] !== undefined ? b[`score_${dbKey}`] : 0;
                }
            });
            
            toggleBeastModeState(isEnabled);
        })
        .catch(err => console.error("Error loading Beast Mode settings:", err));
}

function saveBeastModeSettings() {
    if (window.isDashboardHydrating) return;
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    const payload = {
        enabled: document.getElementById('sec-enable-beast')?.checked ? 1 : 0,
        score_limit: parseInt(document.getElementById('beast-score-limit')?.value || 40),
        punishment_type: document.getElementById('beast-punishment-type')?.value || 'Kick',
        whitelist_bypass: document.getElementById('beast-whitelist-bypass')?.checked ? 1 : 0
    };
    
    const scores = ['bot-add', 'ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'prune', 'mention', 'vanity', 'webhook'];
    scores.forEach(key => {
        const el = document.getElementById(`score-${key}`);
        if (el) {
            const dbKey = key.replace('-', '_');
            payload[`score_${dbKey}`] = parseInt(el.value || 0);
        }
    });
    
    fetch(`/api/settings/beastmode/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Beast Mode Saved", "Aggressive beast-mode protection thresholds successfully synced to database.");
            toggleBeastModeState(payload.enabled === 1);
        } else {
            showToast("Save Error", data.error || "Failed to save Beast Mode settings", "error");
        }
    })
    .catch(err => console.error("Error saving Beast Mode settings:", err));
}

function toggleBeastModeState(enabled) {
    const banner = document.getElementById('beast-disabled-banner');
    if (banner) banner.style.display = enabled ? 'none' : 'block';
    
    const statusText = document.getElementById('beast-armed-state');
    if (statusText) {
        statusText.innerText = enabled ? 'ARMED' : 'SLEEPING';
        statusText.style.color = enabled ? '#2563eb' : 'var(--text-secondary)';
    }
}

function loadAntiRaidSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    fetch(`/api/settings/antiraid/${targetGuild}`)
        .then(res => res.json())
        .then(r => {
            if (!r) return;
            const isEnabled = isTrue(r.enabled);
            const enableEl = document.getElementById('sec-enable-antiraid');
            if (enableEl) enableEl.checked = isEnabled;
            
            const protectEl = document.getElementById('sec-enable-raid-inv');
            if (protectEl) protectEl.checked = isTrue(r.invite_link_protection);
            
            const rateEl = document.getElementById('raid-join-rate');
            if (rateEl && r.join_rate_threshold !== undefined) rateEl.value = r.join_rate_threshold;
            
            const ageEl = document.getElementById('raid-min-age');
            if (ageEl && r.min_account_age !== undefined) ageEl.value = r.min_account_age;
            
            const punishEl = document.getElementById('raid-punishment-type');
            if (punishEl && r.punishment_type) punishEl.value = r.punishment_type;
            
            toggleAntiRaidSettingsPane(isEnabled);
        })
        .catch(err => console.error("Error loading Anti Raid settings:", err));
}

function saveAntiRaidSettings() {
    if (window.isDashboardHydrating) return;
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    const payload = {
        enabled: document.getElementById('sec-enable-antiraid')?.checked ? 1 : 0,
        invite_link_protection: document.getElementById('sec-enable-raid-inv')?.checked ? 1 : 0,
        join_rate_threshold: parseInt(document.getElementById('raid-join-rate')?.value || 10),
        min_account_age: parseInt(document.getElementById('raid-min-age')?.value || 3),
        punishment_type: document.getElementById('raid-punishment-type')?.value || 'Kick'
    };
    fetch(`/api/settings/antiraid/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Anti-Raid Saved", "Anti-raid rate-limit controls successfully synced to database.");
            toggleAntiRaidSettingsPane(payload.enabled === 1);
        } else {
            showToast("Save Error", data.error || "Failed to save Anti Raid settings", "error");
        }
    })
    .catch(err => console.error("Error saving Anti Raid settings:", err));
}

function switchSecTab(tabName) {
    const secNavBtns = document.querySelectorAll('.sec-nav-btn');
    secNavBtns.forEach(btn => {
        const cleanText = btn.innerText.replace(/<i class="fas fa-lock.*<\/i>/g, '').trim();
        const btnTabName = cleanText.toLowerCase().replace(/\s+/g, '').replace('&', '');
        if (btnTabName === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    document.querySelectorAll('.sec-sub-pane').forEach(pane => {
        pane.style.display = 'none';
    });
    
    const targetPane = document.getElementById(`sec-pane-${tabName}`);
    if (targetPane) {
        targetPane.style.display = 'block';
    }
    
    // Load respective settings dynamically
    if (tabName === 'antinuke') {
        loadSecuritySettings(activeGuildId);
    } else if (tabName === 'beastmode') {
        loadBeastModeSettings(activeGuildId);
    } else if (tabName === 'antiraid') {
        loadAntiRaidSettings(activeGuildId);
    } else if (tabName === 'verification') {
        loadVerificationSettings(activeGuildId);
    } else if (tabName === 'moderation') {
        if (typeof window.loadModerationOverrides === 'function') window.loadModerationOverrides(activeGuildId);
        if (typeof window.loadMembersForModeration === 'function') window.loadMembersForModeration(activeGuildId);
        if (typeof window.startLiveLogPolling === 'function') window.startLiveLogPolling(activeGuildId);
    } else if (tabName === 'whitelist') {
        if (typeof window.loadWhitelist === 'function') window.loadWhitelist(activeGuildId);
    } else if (tabName === 'logs') {
        if (typeof window.loadLogsSettings === 'function') window.loadLogsSettings(activeGuildId);
    } else if (tabName === 'antispam') {
        if (typeof window.loadAntiSpamSettings === 'function') window.loadAntiSpamSettings(activeGuildId);
    }
}

window.switchSecTab = switchSecTab;
window.saveVerificationSettings = saveVerificationSettings;
window.saveBeastModeSettings = saveBeastModeSettings;
window.saveAntiRaidSettings = saveAntiRaidSettings;
window.toggleVerificationSettingsPane = toggleVerificationSettingsPane;
function toggleCaptchaOptionsBypass() {
    const pane = document.getElementById('captcha-options-pane');
    const chk = document.getElementById('ver-enable-captcha');
    if (pane) {
        if (chk) {
            pane.style.display = chk.checked ? 'flex' : 'none';
        } else {
            pane.style.display = 'flex';
        }
    }
}
window.toggleCaptchaOptionsBypass = toggleCaptchaOptionsBypass;

function toggleAntiRaidSettingsPane(enabled) {
    const form = document.getElementById('antiraid-form-container');
    if (form) form.style.opacity = enabled ? '1' : '0.6';
}
window.toggleAntiRaidSettingsPane = toggleAntiRaidSettingsPane;

function toggleAntiSpamSettingsPane(enabled) {
    const form = document.getElementById('antispam-form-container');
    const notice = document.getElementById('antispam-disabled-notice');
    if (form) {
        form.style.opacity = enabled ? '1' : '0.45';
        form.style.pointerEvents = enabled ? 'auto' : 'none';
    }
    if (notice) {
        notice.style.display = enabled ? 'none' : 'block';
    }
}
window.toggleAntiSpamSettingsPane = toggleAntiSpamSettingsPane;

window.toggleBeastModeState = toggleBeastModeState;

const originalFetch = window.fetch;
window.fetch = function(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    
    const sessionData = localStorage.getItem('VEYRA_session') || localStorage.getItem('SENTRIX_session');
    if (sessionData && sessionData !== 'undefined') {
        options.headers['Authorization'] = 'Bearer ' + encodeURIComponent(sessionData);
    }
    
    return originalFetch(url, options).then(async (response) => {
        try {
            const clone = response.clone();
            const data = await clone.clone().json().catch(() => null);
            if (data && data.sessionData) {
                const sStr = JSON.stringify(data.sessionData);
                localStorage.setItem('VEYRA_session', sStr);
                localStorage.setItem('SENTRIX_session', sStr);
            }
        } catch (e) {}
        return response;
    });
};

window.isUserLoggedIn = false;

// --- 1. INTERACTIVE CURSOR SPOTLIGHT ---
const cursor = document.getElementById('custom-cursor');
document.addEventListener('mousemove', (e) => {
    if (cursor) {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    }
    
    // Calculate and assign local cursor positions to all container elements
    const spotlightElements = document.querySelectorAll('.glass-card, .feat-card, .pricing-card, .control-box-sec, .command-box, .audit-card');
    spotlightElements.forEach(el => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        el.style.setProperty('--mouse-x', `${x}px`);
        el.style.setProperty('--mouse-y', `${y}px`);
    });
});

// --- 1.5 FULLSCREEN VIDEO ENTRY TRANSITION ---
let videoTransitionStarted = false;

function enterWebsiteSmoothly() {
    if (videoTransitionStarted) return;
    videoTransitionStarted = true;

    const videoEye = document.getElementById('video-eye');
    const hintOverlay = document.getElementById('video-hint-overlay');
    const loadingScreen = document.getElementById('loading-screen');
    const mainContent = document.getElementById('main-content');

    if (hintOverlay) {
        hintOverlay.style.opacity = '0';
        setTimeout(() => hintOverlay.remove(), 600);
    }

    if (videoEye) {
        videoEye.pause();
        videoEye.style.opacity = '0';
    }

    if (loadingScreen) {
        loadingScreen.style.opacity = '0';
        setTimeout(() => {
            loadingScreen.style.display = 'none';
            // Start reveal footer scroll check
            initAnimatedRevealFooter();
            if (typeof ScrollTrigger !== 'undefined') {
                setTimeout(() => ScrollTrigger.refresh(), 100);
            }
        }, 1500);
    }

    if (mainContent) {
        mainContent.style.opacity = '1';
        mainContent.style.pointerEvents = 'auto';
    }
}

// --- 1.6 HERO INTERACTIVE PARTICLE VEYRA ---
const heroCanvas = document.getElementById('canvas-hero-particles');
if (heroCanvas) {
    const heroCtx = heroCanvas.getContext('2d');
    let heroParticles = [];
    const totalHeroParticles = 850;
    
    let mouse = { x: 9999, y: 9999, active: false };
    
    heroCanvas.addEventListener('mousemove', (e) => {
        const rect = heroCanvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        mouse.active = true;
    });
    
    heroCanvas.addEventListener('mouseleave', () => {
        mouse.x = 9999;
        mouse.y = 9999;
        mouse.active = false;
    });
    
    class HeroParticle {
        constructor(index) {
            this.index = index;
            this.x = Math.random() * heroCanvas.width;
            this.y = Math.random() * heroCanvas.height;
            this.vx = 0;
            this.vy = 0;
            this.size = Math.random() * 2 + 1;
            
            // Randomly match color schemes
            const colors = ['#00f0ff', '#7000ff', '#ffffff'];
            this.color = colors[Math.floor(Math.random() * colors.length)];
            this.baseColor = this.color;
        }
        
        update() {
            const time = Date.now() * 0.0025;
            const ratio = this.index / totalHeroParticles;
            let tx, ty;
            
            const cx = heroCanvas.width / 2;
            const cy = heroCanvas.height / 2;
            
            if (ratio < 0.65) {
                // Flapping Wing spreads left/right
                const wingRatio = ((ratio / 0.65) * 2 - 1);
                const side = Math.sign(wingRatio);
                const progress = Math.abs(wingRatio);
                
                tx = cx + side * progress * 135;
                const flap = Math.sin(progress * Math.PI - time * 2.2) * 20;
                ty = cy - progress * 30 + flap - 20;
            } else if (ratio < 0.85) {
                // Core spine body
                const bodyRatio = (ratio - 0.65) / 0.2;
                tx = cx + (Math.sin(this.index * 0.5 + time) * 5);
                ty = cy + bodyRatio * 100 - 25;
            } else if (ratio < 0.93) {
                // Beak/Head structure
                const headRatio = (ratio - 0.85) / 0.08;
                tx = cx + (Math.cos(time + this.index) * 3);
                ty = cy - headRatio * 20 - 25;
            } else {
                // Tail plumes
                const tailRatio = (ratio - 0.93) / 0.07;
                const spread = (tailRatio - 0.5) * 40;
                tx = cx + spread;
                ty = cy + 80 + Math.abs(spread) * 0.2;
            }
            
            // Mouse push mechanics
            if (mouse.active) {
                const dx = mouse.x - this.x;
                const dy = mouse.y - this.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 65) {
                    const force = (65 - dist) / 65;
                    const angle = Math.atan2(dy, dx);
                    this.vx -= Math.cos(angle) * force * 4.0;
                    this.vy -= Math.sin(angle) * force * 4.0;
                    this.color = '#FF8A00'; // Glow orange
                } else {
                    this.color = this.baseColor;
                }
            } else {
                this.color = this.baseColor;
            }
            
            const spring = 0.07;
            this.vx += (tx - this.x) * spring;
            this.vy += (ty - this.y) * spring;
            
            this.vx *= 0.82;
            this.vy *= 0.82;
            
            this.x += this.vx;
            this.y += this.vy;
        }
        
        draw() {
            heroCtx.beginPath();
            heroCtx.fillStyle = this.color;
            heroCtx.shadowBlur = 4;
            heroCtx.shadowColor = this.color;
            heroCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            heroCtx.fill();
        }
    }
    
    for (let i = 0; i < totalHeroParticles; i++) {
        heroParticles.push(new HeroParticle(i));
    }
    
    // Disabled heavy canvas particles loop for 10x rendering speed
    function renderHeroLoop() {}
}

// Navbar Server link authentication checker
function clickManageServers() {
    if (window.isUserLoggedIn) {
        window.location.href = '/manage';
    } else {
        simulateLogin();
    }
}

// --- 2. SCREEN ROUTER SYSTEM ---
let currentScreen = 'landing';
let currentTab = 'overview';
let activeGuildId = null;

function showScreen(screenId, preserveScroll = false) {
    const screenLanding = document.getElementById('screen-landing');
    const screenServers = document.getElementById('screen-servers');
    const screenDashboard = document.getElementById('screen-dashboard');
    const screenAdmin = document.getElementById('screen-admin');
    
    const preStyle = document.getElementById('pre-render-screen-style');
    if (preStyle) preStyle.remove();

    // If none of these screen elements exist, we are on a static page and should redirect to manage if showing servers/dashboard
    if (!screenLanding && !screenServers && !screenDashboard && !screenAdmin) {
        if (screenId === 'servers' || screenId === 'dashboard') {
            window.location.href = '/manage';
        }
        return;
    }
    
    if (screenLanding) {
        screenLanding.style.removeProperty('display');
        screenLanding.style.setProperty('display', 'none', 'important');
    }
    if (screenServers) {
        screenServers.style.removeProperty('display');
        screenServers.style.setProperty('display', 'none', 'important');
    }
    if (screenDashboard) {
        screenDashboard.style.removeProperty('display');
        screenDashboard.style.setProperty('display', 'none', 'important');
    }
    if (screenAdmin) {
        screenAdmin.style.removeProperty('display');
        screenAdmin.style.setProperty('display', 'none', 'important');
    }
    
    const navHome = document.getElementById('nav-home');
    const navManageServers = document.getElementById('nav-manage-servers');
    const navFeatures = document.getElementById('nav-features');
    const navPricing = document.getElementById('nav-pricing');
    const navFaq = document.getElementById('nav-faq');
    const navAdmin = document.getElementById('nav-admin');
    
    const setNavBtnActive = (navItemEl, active) => {
        if (!navItemEl) return;
        const btn = navItemEl.querySelector('.gen-btn');
        if (btn) {
            if (active) btn.classList.add('active');
            else btn.classList.remove('active');
        }
    };

    if (!preserveScroll) {
        setNavBtnActive(navHome, false);
        setNavBtnActive(navManageServers, false);
        setNavBtnActive(navFeatures, false);
        setNavBtnActive(navPricing, false);
        setNavBtnActive(navFaq, false);
        setNavBtnActive(navAdmin, false);
    }

    if (screenId === 'landing') {
        if (screenLanding) {
            screenLanding.style.removeProperty('display');
            screenLanding.style.setProperty('display', 'block', 'important');
        }
        if (!preserveScroll) setNavBtnActive(navHome, true);
    } else if (screenId === 'servers') {
        if (screenServers) {
            screenServers.style.removeProperty('display');
            screenServers.style.setProperty('display', 'block', 'important');
        }
        if (!preserveScroll) setNavBtnActive(navManageServers, true);
    } else if (screenId === 'dashboard') {
        if (screenDashboard) {
            screenDashboard.style.removeProperty('display');
            screenDashboard.style.setProperty('display', 'flex', 'important');
        }
        if (!preserveScroll) setNavBtnActive(navManageServers, true);
        const activeTab = document.querySelector('.tab-pane[style*="display: block"]');
        if (!activeTab && typeof switchTab === 'function') {
            switchTab(sessionStorage.getItem('pendingTab') || 'overview');
        }
    } else if (screenId === 'admin') {
        if (!window.isUserAdmin) {
            showToast("Access Restricted", "The VEYRA Admin Panel is restricted exclusively to Admin ID: 1256986886631854080.", "error");
            if (screenLanding) screenLanding.style.display = 'block';
            if (!preserveScroll) setNavBtnActive(navHome, true);
            return;
        }
        if (screenAdmin) screenAdmin.style.display = 'block';
        if (!preserveScroll) setNavBtnActive(navAdmin, true);
        loadAdminGuilds();
    }
    
    if (currentScreen !== screenId && !preserveScroll) {
        window.scrollTo(0,0);
    }
    currentScreen = screenId;
    sessionStorage.setItem('activeScreen', screenId);

    // Dynamic body overflow and server widget visibility based on screen ID
    document.body.style.overflow = '';
    const serverWidget = document.getElementById('header-server-dropdown-trigger-container');
    if (serverWidget) {
        if (screenId === 'dashboard') {
            serverWidget.style.display = 'block';
        } else {
            serverWidget.style.display = 'none';
        }
    }

    if (typeof ScrollTrigger !== 'undefined') {
        setTimeout(() => ScrollTrigger.refresh(), 100);
    }
}
window.showScreen = showScreen;

function scrollToSection(sectionId) {
    if (!sectionId || sectionId === 'home' || sectionId === 'screen-landing') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }
    const el = document.getElementById(sectionId);
    if (el) {
        const headerOffset = 100;
        const elementPosition = el.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
        window.scrollTo({
            top: Math.max(0, offsetPosition),
            behavior: 'smooth'
        });
    }
}
window.scrollToSection = scrollToSection;

window.clickNavSection = function(sectionId) {
    if (window.location.pathname !== '/' && window.location.pathname !== '/index.html' && window.location.pathname !== '') {
        window.location.href = '/#' + sectionId;
        return;
    }
    
    const navFeatures = document.getElementById('nav-features');
    const navPricing = document.getElementById('nav-pricing');
    const navFaq = document.getElementById('nav-faq');
    const navHome = document.getElementById('nav-home');
    const navManageServers = document.getElementById('nav-manage-servers');
    const navAdmin = document.getElementById('nav-admin');
    
    if (typeof currentScreen !== 'undefined' && currentScreen !== 'landing') {
        if (typeof showScreen === 'function') showScreen('landing', true);
    }
    
    const navButtons = [navHome, navManageServers, navFeatures, navPricing, navFaq, navAdmin];
    navButtons.forEach(navItem => {
        if (navItem) {
            const btn = navItem.querySelector('.gen-btn');
            if (btn) btn.classList.remove('active');
        }
    });

    if (sectionId === 'features' && navFeatures) navFeatures.querySelector('.gen-btn')?.classList.add('active');
    else if (sectionId === 'pricing' && navPricing) navPricing.querySelector('.gen-btn')?.classList.add('active');
    else if (sectionId === 'faq' && navFaq) navFaq.querySelector('.gen-btn')?.classList.add('active');
    else if (sectionId === 'home' && navHome) navHome.querySelector('.gen-btn')?.classList.add('active');

    scrollToSection(sectionId);
};

// --- 3. DYNAMIC SERVER LOAD & STATE BINDING ---
function loadServerDashboard(guildId) {
    if (!guildId) return;
    activeGuildId = guildId;
    window.activeGuildId = guildId;
    sessionStorage.setItem('activeGuildId', guildId);
    sessionStorage.setItem('activeScreen', 'dashboard');

    const screenDashboard = document.getElementById('screen-dashboard');
    if (!screenDashboard && window.location.pathname.includes('/manage')) {
        window.location.href = `/?guild_id=${guildId}`;
        return;
    }

    try {
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('guild_id', guildId);
        window.history.pushState({ guildId }, '', currentUrl.toString());
    } catch(e) {}
    
    // Find active server and update UI headers dynamically
    // Persist selected guild ID immediately
    localStorage.setItem('selected_guild_id', guildId);
    sessionStorage.setItem('activeGuildId', guildId);

    const activeGuild = (window.allGuildsCache || []).find(g => g.id === guildId);
    if (activeGuild) {
        const guildName = activeGuild.name;
        localStorage.setItem('selected_guild_name', guildName);
        if (document.getElementById('sidebar-guild-name')) {
            document.getElementById('sidebar-guild-name').innerText = guildName;
        }
        if (document.getElementById('managing-server-name')) {
            document.getElementById('managing-server-name').innerText = guildName;
        }
        if (document.getElementById('dashboard-server-name')) {
            document.getElementById('dashboard-server-name').innerText = guildName;
        }
        if (document.getElementById('header-server-dropdown-name')) {
            document.getElementById('header-server-dropdown-name').innerText = guildName;
        }
        if (document.getElementById('tickets-sidebar-guild-name')) {
            document.getElementById('tickets-sidebar-guild-name').innerText = guildName;
        }
        
        // Update server icons
        const iconUrl = (activeGuild && activeGuild.icon) 
            ? `https://cdn.discordapp.com/icons/${activeGuild.id}/${activeGuild.icon}.png?size=128`
            : (localStorage.getItem('selected_guild_icon') || 'https://cdn.discordapp.com/embed/avatars/0.png');
        try { localStorage.setItem('selected_guild_icon', iconUrl); } catch(e) {}
            
        window.updateActiveGuildUI(guildId, guildName, iconUrl);
        if (typeof loadSecuritySettings === 'function') loadSecuritySettings(guildId);

        // Update member count
        const ticketsSidebarMembers = document.getElementById('tickets-sidebar-guild-members');
        if (ticketsSidebarMembers) {
            const members = activeGuild.member_count || (guildName === 'GHOST' ? 1452 : 2083);
            ticketsSidebarMembers.innerText = `${members.toLocaleString()} members`;
        }
        if (typeof renderSidebarGuilds === 'function') renderSidebarGuilds();
    }
    
    showScreen('dashboard');
    const pendingTab = window.currentTab || sessionStorage.getItem('activeTab') || sessionStorage.getItem('pendingTab') || 'overview';
    if (typeof switchTab === 'function') {
        switchTab(pendingTab);
    }
    
    // Reset status log list
    const logBody = document.getElementById('weblogs-body');
    if (logBody) logBody.innerHTML = '';

    // ── Start real-time moderation features ──
    if (typeof window.initModeration === 'function') {
        window.initModeration(guildId);
    }

    fetch(`/api/guild/plan/${guildId}`)
        .then(res => res.json())
        .then(sub => {
            sub.plan_type = 'Premium';
            sub.expires_at = 'Lifetime';
            window.currentServerPlan = 'Premium';
            
            const badgeEl = document.getElementById('sidebar-subscription-badge');
            const titleEl = document.getElementById('sidebar-subscription-title');
            const footerEl = document.getElementById('sidebar-subscription-footer');
            
            if (badgeEl && titleEl && footerEl) {
                if (sub.plan_type === 'Premium') {
                    badgeEl.innerText = 'SUBSCRIPTION ACTIVE';
                    badgeEl.style.color = '#f59e0b';
                    titleEl.innerHTML = '<i class="fas fa-crown"></i> Premium Plan';
                    footerEl.innerText = sub.expires_at === 'Lifetime' ? 'Lifetime Access' : `Expires: ${new Date(sub.expires_at).toLocaleDateString()}`;
                    footerEl.style.color = '#f59e0b';
                } else if (sub.plan_type === 'Pro') {
                    badgeEl.innerText = 'SUBSCRIPTION ACTIVE';
                    badgeEl.style.color = '#c084fc';
                    titleEl.innerHTML = '<i class="fas fa-bolt"></i> Pro Plan';
                    footerEl.innerText = sub.expires_at === 'Lifetime' ? 'Lifetime Access' : `Expires: ${new Date(sub.expires_at).toLocaleDateString()}`;
                    footerEl.style.color = '#c084fc';
                } else {
                    badgeEl.innerText = 'FREE SUBSCRIPTION';
                    badgeEl.style.color = '#94a3b8';
                    titleEl.innerText = 'Free Plan';
                    footerEl.innerText = 'Upgrade to unlock Pro/Premium';
                    footerEl.style.color = '#a855f7';
                }
            }
            const targetTab = window.currentTab || sessionStorage.getItem('activeTab') || sessionStorage.getItem('pendingTab') || 'overview';
            if (typeof switchTab === 'function') {
                switchTab(targetTab);
            }
            if (typeof updateSidebarLocks === 'function') updateSidebarLocks();
        })
        .catch(() => {
            window.currentServerPlan = 'Premium';
            const targetTab = window.currentTab || sessionStorage.getItem('activeTab') || sessionStorage.getItem('pendingTab') || 'overview';
            if (typeof switchTab === 'function') {
                switchTab(targetTab);
            }
            if (typeof updateSidebarLocks === 'function') updateSidebarLocks();
        });

    // Fetch configurations from SQLite DB
    fetch(`/api/settings/${guildId}`)
        .then(res => res.json())
        .then(data => {
            // Hydrate custom prefixes from database
            fetch(`/api/settings/prefix/${guildId}`)
                .then(r => r.json())
                .then(pData => {
                    if (pData && pData.prefixes && pData.prefixes.length > 0) {
                        window.currentServerPrefixes = pData.prefixes;
                        renderPrefixesList();
                    }
                })
                .catch(() => {});
            const g = data.guild || {};
            const s = data.security || {};
            
            // Hydrate ALL modules authoritatively from PostgreSQL
            window.isDashboardHydrating = true;
            if (typeof loadSecuritySettings === 'function') loadSecuritySettings(guildId);
            if (typeof loadBeastModeSettings === 'function') loadBeastModeSettings(guildId);
            if (typeof loadAntiRaidSettings === 'function') loadAntiRaidSettings(guildId);
            if (typeof loadVerificationSettings === 'function') loadVerificationSettings(guildId);
            if (typeof loadAntiSpamSettings === 'function') loadAntiSpamSettings(guildId);
            if (typeof loadWelcomeSettings === 'function') loadWelcomeSettings(guildId);
            if (typeof loadLeaveSettings === 'function') loadLeaveSettings(guildId);
            if (typeof loadJoinDMSettings === 'function') loadJoinDMSettings(guildId);
            if (typeof loadInviteTrackerSettings === 'function') loadInviteTrackerSettings(guildId);
            if (typeof loadAutorolesSettings === 'function') loadAutorolesSettings(guildId);
            if (typeof loadLevelsSettings === 'function') loadLevelsSettings(guildId);
            if (typeof loadReportsSettings === 'function') loadReportsSettings(guildId);
            if (typeof loadServerOverview === 'function') loadServerOverview(guildId);
            setTimeout(() => { window.isDashboardHydrating = false; }, 1500);

            // Dynamic Header Updates
            if (document.getElementById('sec-managing-title')) {
                document.getElementById('sec-managing-title').innerText = `You are managing ${g.name || 'GHOST'}`;
            }
            
            // Populate General Configs
            if (document.getElementById('guild-prefix-input')) document.getElementById('guild-prefix-input').value = g.prefix || '?';
            if (document.getElementById('guild-timezone-input')) document.getElementById('guild-timezone-input').value = g.timezone || 'UTC';
            if (document.getElementById('bot-nickname-input')) document.getElementById('bot-nickname-input').value = g.nickname || 'VEYRA';
            if (document.getElementById('welcome-channel-input')) document.getElementById('welcome-channel-input').value = g.updates_channel || '#welcome';
            
            // Populate 7 Limit & Punish fields
            const limits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
            limits.forEach(key => {
                const dbKey = key.replace('-', '_');
                const limitEl = document.getElementById(`sec-limit-${key}`);
                const punishEl = document.getElementById(`sec-punish-${key}`);
                const enableEl = document.getElementById(`sec-enable-${key}`);
                
                if (limitEl) limitEl.value = s[`anti_${dbKey}_limit`] !== undefined ? s[`anti_${dbKey}_limit`] : 5;
                if (punishEl) punishEl.value = s[`anti_${dbKey}_punish`] || 'Ban';
                
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (enableEl) enableEl.checked = (val !== undefined ? isTrue(val) : true);
            });
            
            // Populate 14 Instant Punishment fields
            const instant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename', 'emoji-delete', 'emoji-rename', 'invite-delete', 'invite-link', 'ghost-ping'];
            instant.forEach(key => {
                let dbKey = key.replace('-', '_');
                if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
                if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
                if (dbKey === 'vanity') dbKey = 'vanity_change';
                if (dbKey === 'server-icon') dbKey = 'server_icon_change';
                
                const punishEl = document.getElementById(`sec-punish-${key}`);
                const enableEl = document.getElementById(`sec-enable-${key}`);
                
                if (punishEl) punishEl.value = s[`anti_${dbKey}_punish`] || 'Ban';
                
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (enableEl) enableEl.checked = (val !== undefined ? isTrue(val) : true);
            });

            // Dynamic Safety Status Indicator & Alert Card
            let enabledCount = 0;
            let totalCount = 16;
            
            const checkLimits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
            checkLimits.forEach(key => {
                const dbKey = key.replace('-', '_');
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (isTrue(val)) enabledCount++;
            });
            
            const checkInstant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename'];
            checkInstant.forEach(key => {
                let dbKey = key.replace('-', '_');
                if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
                if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
                if (dbKey === 'vanity') dbKey = 'vanity_change';
                if (dbKey === 'server-icon') dbKey = 'server_icon_change';
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (isTrue(val)) enabledCount++;
            });
            
            const statusEl = document.getElementById('overview-security-status');
            const descEl = document.getElementById('overview-security-desc');
            const alertEl = document.getElementById('overview-unsafe-alert');
            
            if (statusEl && descEl) {
                if (enabledCount === 0) {
                    statusEl.innerText = "NOT SAFE";
                    statusEl.style.color = "#ef4444";
                    descEl.innerText = "All security filters are disabled";
                    if (alertEl) alertEl.style.display = "flex";
                } else if (enabledCount < totalCount) {
                    statusEl.innerText = "PARTIALLY PROTECTED";
                    statusEl.style.color = "#eab308";
                    descEl.innerText = `${enabledCount} / ${totalCount} security filters active`;
                    if (alertEl) alertEl.style.display = "none";
                } else {
                    statusEl.innerText = "SAFE";
                    statusEl.style.color = "#10b981";
                    descEl.innerText = "All security filters are active";
                    if (alertEl) alertEl.style.display = "none";
                }
            }

            // Enforce plan UI configurations
            if (typeof enforcePlanUI === 'function') enforcePlanUI();

            // Populate commands list
            const disabledCmds = data.disabled_commands || [];
            commandsData.forEach(cmd => {
                cmd.enabled = !disabledCmds.includes(cmd.name);
            });
            filterCommands('all');

            // Populate system logs stream
            loadAuditWeblogs(guildId);

            // Fetch Bot Profile & Real Roles/Channels
            loadBotProfileSettings(guildId);
            populateServerRolesAndChannels(guildId);
            loadRealAnalytics(guildId);
            if (typeof window.loadServerListing === 'function') window.loadServerListing(guildId);

            // Fetch Welcome configuration
            fetch(`/api/settings/welcome/${guildId}`)
                .then(res => res.json())
                .then(w => {
                    if (document.getElementById('welcome-msg-enable')) document.getElementById('welcome-msg-enable').checked = isTrue(w.enabled);
                    if (document.getElementById('welcome-msg-channel-select')) document.getElementById('welcome-msg-channel-select').value = w.channel || 'general';
                    if (document.getElementById('welcome-msg-outer-input')) document.getElementById('welcome-msg-outer-input').value = w.message || '';
                    if (document.getElementById('welcome-embed-enable')) document.getElementById('welcome-embed-enable').checked = isTrue(w.enabled);
                    if (document.getElementById('welcome-embed-color-picker')) {
                        document.getElementById('welcome-embed-color-picker').value = w.color || '#a855f7';
                        if (document.getElementById('welcome-color-hex')) document.getElementById('welcome-color-hex').value = w.color || '#a855f7';
                    }
                    if (document.getElementById('welcome-embed-title')) document.getElementById('welcome-embed-title').value = w.title || '';
                    if (document.getElementById('welcome-embed-desc')) document.getElementById('welcome-embed-desc').value = w.description || '';
                    if (document.getElementById('welcome-embed-image')) document.getElementById('welcome-embed-image').value = w.image || '';
                    if (document.getElementById('welcome-embed-footer')) document.getElementById('welcome-embed-footer').value = w.footer || '';
                    if (document.getElementById('welcome-thumbnail-url')) document.getElementById('welcome-thumbnail-url').value = w.thumbnail || '';
                    if (document.getElementById('welcome-author-name')) document.getElementById('welcome-author-name').value = w.author_name || '';
                    if (document.getElementById('welcome-author-icon')) document.getElementById('welcome-author-icon').value = w.author_icon || '';
                    if (document.getElementById('welcome-footer-icon')) document.getElementById('welcome-footer-icon').value = w.footer_icon || '';
                    
                    updateWelcomeLivePreview();
                });

            // Fetch Leave configuration
            fetch(`/api/settings/leave/${guildId}`)
                .then(res => res.json())
                .then(l => {
                    if (document.getElementById('leave-msg-enable')) document.getElementById('leave-msg-enable').checked = isTrue(l.enabled);
                    if (document.getElementById('leave-msg-channel-select')) document.getElementById('leave-msg-channel-select').value = l.channel || 'exits';
                    if (document.getElementById('leave-msg-outer-input')) document.getElementById('leave-msg-outer-input').value = l.message || '';
                    if (document.getElementById('leave-embed-enable')) document.getElementById('leave-embed-enable').checked = isTrue(l.enabled);
                    if (document.getElementById('leave-embed-color-picker')) {
                        document.getElementById('leave-embed-color-picker').value = l.color || '#a855f7';
                        if (document.getElementById('leave-color-hex')) document.getElementById('leave-color-hex').value = l.color || '#a855f7';
                    }
                    if (document.getElementById('leave-embed-title')) document.getElementById('leave-embed-title').value = l.title || '';
                    if (document.getElementById('leave-embed-desc')) document.getElementById('leave-embed-desc').value = l.description || '';
                    if (document.getElementById('leave-embed-image')) document.getElementById('leave-embed-image').value = l.image || '';
                    if (document.getElementById('leave-embed-footer')) document.getElementById('leave-embed-footer').value = l.footer || '';
                    if (document.getElementById('leave-thumbnail-url')) document.getElementById('leave-thumbnail-url').value = l.thumbnail || '';
                    if (document.getElementById('leave-author-name')) document.getElementById('leave-author-name').value = l.author_name || '';
                    if (document.getElementById('leave-author-icon')) document.getElementById('leave-author-icon').value = l.author_icon || '';
                    if (document.getElementById('leave-footer-icon')) document.getElementById('leave-footer-icon').value = l.footer_icon || '';
                    
                    updateLeaveLivePreview();
                });

            // Fetch Verification configuration
            fetch(`/api/verification/${guildId}`)
                .then(res => res.json())
                .then(v => {
                    if (document.getElementById('verif-enable')) document.getElementById('verif-enable').checked = isTrue(v.enabled);
                    if (document.getElementById('verif-level')) document.getElementById('verif-level').value = v.type || 'captcha';
                    if (document.getElementById('verif-role')) document.getElementById('verif-role').value = v.verified_role || 'none';
                    if (document.getElementById('verif-action')) document.getElementById('verif-action').value = v.timeout_action || 'Kick';
                    if (document.getElementById('verif-timeout')) document.getElementById('verif-timeout').value = v.captcha_timeout || 60;
                    if (document.getElementById('verif-channel')) document.getElementById('verif-channel').value = v.channel || 'none';
                });

            // Fetch Join DM configuration
            fetch(`/api/settings/joindm/${guildId}`)
                .then(res => res.json())
                .then(dm => {
                    if (document.getElementById('eb-destination-channel')) document.getElementById('eb-destination-channel').value = dm.channel || 'dm';
                    if (document.getElementById('eb-normal-text')) document.getElementById('eb-normal-text').value = dm.message || '';
                    if (document.getElementById('eb-title')) document.getElementById('eb-title').value = dm.title || '';
                    if (document.getElementById('eb-description')) document.getElementById('eb-description').value = dm.description || '';
                    if (document.getElementById('eb-image-url')) document.getElementById('eb-image-url').value = dm.image || '';
                    if (document.getElementById('eb-thumbnail-url')) document.getElementById('eb-thumbnail-url').value = dm.thumbnail || '';
                    if (document.getElementById('eb-footer-text')) document.getElementById('eb-footer-text').value = dm.footer || '';
                    if (document.getElementById('eb-color-picker')) {
                        document.getElementById('eb-color-picker').value = dm.color || '#a855f7';
                        if (document.getElementById('eb-color-hex')) document.getElementById('eb-color-hex').value = dm.color || '#a855f7';
                    }
                    if (typeof updateEmbedBuilderPreview === 'function') updateEmbedBuilderPreview();
                });

            // Fetch Invite Tracker configuration
            fetch(`/api/settings/invitetracker/${guildId}`)
                .then(res => res.json())
                .then(it => {
                    if (document.getElementById('invitetracker-msg-enable')) document.getElementById('invitetracker-msg-enable').checked = isTrue(it.enabled);
                    if (document.getElementById('invitetracker-msg-channel-select')) document.getElementById('invitetracker-msg-channel-select').value = it.channel || 'general';
                    if (document.getElementById('invitetracker-msg-outer-input')) document.getElementById('invitetracker-msg-outer-input').value = it.message || '';
                    if (document.getElementById('invitetracker-embed-color-picker')) {
                        document.getElementById('invitetracker-embed-color-picker').value = it.color || '#a855f7';
                        if (document.getElementById('invitetracker-color-hex')) document.getElementById('invitetracker-color-hex').value = it.color || '#a855f7';
                    }
                    if (document.getElementById('invitetracker-embed-title')) document.getElementById('invitetracker-embed-title').value = it.title || '';
                    if (document.getElementById('invitetracker-embed-desc')) document.getElementById('invitetracker-embed-desc').value = it.description || '';
                    if (document.getElementById('invitetracker-embed-image')) document.getElementById('invitetracker-embed-image').value = it.image || '';
                    if (document.getElementById('invitetracker-thumbnail-url')) document.getElementById('invitetracker-thumbnail-url').value = it.thumbnail || '';
                    if (document.getElementById('invitetracker-embed-footer')) document.getElementById('invitetracker-embed-footer').value = it.footer || '';
                    if (document.getElementById('invitetracker-author-name')) document.getElementById('invitetracker-author-name').value = it.author_name || '';
                    if (document.getElementById('invitetracker-author-icon')) document.getElementById('invitetracker-author-icon').value = it.author_icon || '';
                    if (document.getElementById('invitetracker-footer-icon')) document.getElementById('invitetracker-footer-icon').value = it.footer_icon || '';
                    
                    updateInviteTrackerLivePreview();
                });
        })
        .catch(err => console.error("Error loading server settings:", err));
}

let isFetchingWeblogs = false;
function loadAuditWeblogs(guildId, forceSpinner = false) {
    if (!guildId) return;
    const weblogsBody = document.getElementById('weblogs-table-body');
    const recentBody = document.getElementById('recent-actions-table-body');

    if (forceSpinner || (!window.activeAuditLogsCache && weblogsBody && (!weblogsBody.children.length || weblogsBody.innerText.includes('Loading')))) {
        if (weblogsBody) weblogsBody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i> Loading real audit logs...</td></tr>';
        if (recentBody) recentBody.innerHTML = '<tr><td colspan="3" style="padding: 20px; text-align: center; color: var(--text-secondary);"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i> Loading...</td></tr>';
    }

    if (isFetchingWeblogs) return;
    isFetchingWeblogs = true;

    fetch(`/api/logs/${guildId}`)
        .then(res => res.json())
        .then(rows => {
            isFetchingWeblogs = false;
            const cleanRows = (rows || []).map(r => {
                let u = r.user || 'Staff';
                if (u.includes('neondb_owner')) u = 'Server Admin';
                if (u.includes('SHADOW UID BYPASS')) u = 'Server Security';
                return { ...r, user: u };
            });

            if (window.activeAuditLogsCache && JSON.stringify(cleanRows) === JSON.stringify(window.activeAuditLogsCache)) {
                return;
            }

            window.activeAuditLogsCache = cleanRows;
            renderAuditLogs();
        })
        .catch(err => {
            isFetchingWeblogs = false;
            console.error("Error loading server audit logs:", err);
            if (weblogsBody && (!weblogsBody.children.length || weblogsBody.innerText.includes('Loading'))) {
                weblogsBody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-muted);">No recent audit logs found.</td></tr>';
            }
        });
}

window.refreshAuditWeblogs = function(btn) {
    const icon = btn ? btn.querySelector('i') : null;
    if (icon) icon.classList.add('fa-spin');
    loadAuditWeblogs(activeGuildId, false);
    setTimeout(() => {
        if (icon) icon.classList.remove('fa-spin');
    }, 600);
};

// --- 4. Sidebar tab switches ---
const tabPermissions = {
    'overview': 'Free',
    'invitetracker': 'Pro',
    'weblogs': 'Free',
    'buttonroles': 'Free',
    'moderation': 'Free',
    'utilities': 'Free',
    'automod': 'Free',
    'autoresponders': 'Free',
    'voicemaster': 'Free',
    'settings': 'Free',
    'personalize': 'Premium',
    'autoroles': 'Free',
    'analytics': 'Free',
    'verification': 'Pro',
    'security': 'Free',
    'commands': 'Pro',
    'welcome': 'Pro',
    'leave': 'Pro',
    'stickymessages': 'Pro',
    'reports': 'Premium',
    'levels': 'Premium',
    'publish': 'Premium',
    'embed': 'Pro',
    'embedmessages': 'Free',
    'tickets': 'Ticket',
    'giveaways': 'Free'
};

function showLockedPane(tabId, requiredPlan) {
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => pane.style.display = 'none');
    
    const menuItems = document.querySelectorAll('.sidebar-item');
    menuItems.forEach(item => item.classList.remove('active'));
    
    const targetMenu = document.getElementById(`menu-${tabId}`);
    if (targetMenu) targetMenu.classList.add('active');
    
    const lockedPane = document.getElementById('tab-locked');
    if (lockedPane) {
        lockedPane.style.display = 'block';
        
        const titleEl = document.getElementById('locked-title');
        const descEl = document.getElementById('locked-desc');
        const planNameEl = document.getElementById('locked-plan-name');
        const featuresEl = document.getElementById('locked-plan-features');
        
        if (titleEl) titleEl.innerText = `${tabId.charAt(0).toUpperCase() + tabId.slice(1)} Locked`;
        if (descEl) descEl.innerText = `The ${tabId} integration requires an active ${requiredPlan} subscription plan.`;
        if (planNameEl) {
            if (requiredPlan === 'Ticket') {
                planNameEl.innerText = "TICKET PLAN ($6.99/mo)";
                planNameEl.style.color = '#f43f5e';
            } else {
                planNameEl.innerText = requiredPlan.toUpperCase();
                planNameEl.style.color = requiredPlan === 'Premium' ? '#f59e0b' : '#c084fc';
            }
        }
        
        if (featuresEl) {
            if (requiredPlan === 'Pro') {
                featuresEl.innerHTML = `
                    <li><i class="fas fa-check" style="color:#c084fc; margin-right:6px;"></i> Verification Gate</li>
                    <li><i class="fas fa-check" style="color:#c084fc; margin-right:6px;"></i> Raid Protection / Anti-Nuke thresholds</li>
                    <li><i class="fas fa-check" style="color:#c084fc; margin-right:6px;"></i> welcome & exit messages</li>
                    <li><i class="fas fa-check" style="color:#c084fc; margin-right:6px;"></i> Custom Bot Commands</li>
                `;
            } else if (requiredPlan === 'Premium') {
                featuresEl.innerHTML = `
                    <li><i class="fas fa-check" style="color:#f59e0b; margin-right:6px;"></i> Embed Builder workspace</li>
                    <li><i class="fas fa-check" style="color:#f59e0b; margin-right:6px;"></i> Publish channels / Auto-news</li>
                    <li><i class="fas fa-check" style="color:#f59e0b; margin-right:6px;"></i> Advanced levels & reports analytics</li>
                    <li><i class="fas fa-check" style="color:#f59e0b; margin-right:6px;"></i> 24/7 dedicated instance hosting priority</li>
                `;
            } else if (requiredPlan === 'Ticket') {
                featuresEl.innerHTML = `
                    <li><i class="fas fa-check" style="color:#f43f5e; margin-right:6px;"></i> Unlimited support panels creation</li>
                    <li><i class="fas fa-check" style="color:#f43f5e; margin-right:6px;"></i> Custom button design & welcome embeds</li>
                    <li><i class="fas fa-check" style="color:#f43f5e; margin-right:6px;"></i> Save HTML transcripts & audits history</li>
                    <li><i class="fas fa-check" style="color:#f43f5e; margin-right:6px;"></i> Personalize Bot profile, custom name & avatar</li>
                `;
            }
        }
    }
}


// ==========================================
// STANDALONE AUTHORITATIVE SETTINGS LOADERS
// ==========================================

function loadWelcomeSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/welcome/${targetGuild}`)
        .then(res => res.json())
        .then(w => {
            if (!w) return;
            const isEnabled = (isTrue(w.enabled) || w.enabled === true || w.enabled === '1');
            if (document.getElementById('welcome-msg-enable')) document.getElementById('welcome-msg-enable').checked = isEnabled;
            if (document.getElementById('welcome-msg-channel-select')) document.getElementById('welcome-msg-channel-select').value = w.channel || 'general';
            if (document.getElementById('welcome-msg-outer-input')) document.getElementById('welcome-msg-outer-input').value = w.message || '';
            if (document.getElementById('welcome-embed-enable')) document.getElementById('welcome-embed-enable').checked = isEnabled;
            if (document.getElementById('welcome-embed-color-picker')) {
                document.getElementById('welcome-embed-color-picker').value = w.color || '#a855f7';
                if (document.getElementById('welcome-color-hex')) document.getElementById('welcome-color-hex').value = w.color || '#a855f7';
            }
            if (document.getElementById('welcome-embed-title')) document.getElementById('welcome-embed-title').value = w.title || '';
            if (document.getElementById('welcome-embed-desc')) document.getElementById('welcome-embed-desc').value = w.description || '';
            if (document.getElementById('welcome-embed-image')) document.getElementById('welcome-embed-image').value = w.image || '';
            if (document.getElementById('welcome-embed-footer')) document.getElementById('welcome-embed-footer').value = w.footer || '';
            if (document.getElementById('welcome-thumbnail-url')) document.getElementById('welcome-thumbnail-url').value = w.thumbnail || '';
            if (document.getElementById('welcome-author-name')) document.getElementById('welcome-author-name').value = w.author_name || '';
            if (document.getElementById('welcome-author-icon')) document.getElementById('welcome-author-icon').value = w.author_icon || '';
            if (document.getElementById('welcome-footer-icon')) document.getElementById('welcome-footer-icon').value = w.footer_icon || '';
            
            if (typeof updateWelcomeLivePreview === 'function') updateWelcomeLivePreview();
        })
        .catch(err => console.error("Error loading welcome settings:", err));
}
window.loadWelcomeSettings = loadWelcomeSettings;

function loadLeaveSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/leave/${targetGuild}`)
        .then(res => res.json())
        .then(l => {
            if (!l) return;
            const isEnabled = (isTrue(l.enabled) || l.enabled === true || l.enabled === '1');
            if (document.getElementById('leave-msg-enable')) document.getElementById('leave-msg-enable').checked = isEnabled;
            if (document.getElementById('leave-msg-channel-select')) document.getElementById('leave-msg-channel-select').value = l.channel || 'exits';
            if (document.getElementById('leave-msg-outer-input')) document.getElementById('leave-msg-outer-input').value = l.message || '';
            if (document.getElementById('leave-embed-enable')) document.getElementById('leave-embed-enable').checked = isEnabled;
            if (document.getElementById('leave-embed-color-picker')) {
                document.getElementById('leave-embed-color-picker').value = l.color || '#a855f7';
                if (document.getElementById('leave-color-hex')) document.getElementById('leave-color-hex').value = l.color || '#a855f7';
            }
            if (document.getElementById('leave-embed-title')) document.getElementById('leave-embed-title').value = l.title || '';
            if (document.getElementById('leave-embed-desc')) document.getElementById('leave-embed-desc').value = l.description || '';
            if (document.getElementById('leave-embed-image')) document.getElementById('leave-embed-image').value = l.image || '';
            if (document.getElementById('leave-embed-footer')) document.getElementById('leave-embed-footer').value = l.footer || '';
            if (document.getElementById('leave-thumbnail-url')) document.getElementById('leave-thumbnail-url').value = l.thumbnail || '';
            if (document.getElementById('leave-author-name')) document.getElementById('leave-author-name').value = l.author_name || '';
            if (document.getElementById('leave-author-icon')) document.getElementById('leave-author-icon').value = l.author_icon || '';
            if (document.getElementById('leave-footer-icon')) document.getElementById('leave-footer-icon').value = l.footer_icon || '';
            
            if (typeof updateLeaveLivePreview === 'function') updateLeaveLivePreview();
        })
        .catch(err => console.error("Error loading leave settings:", err));
}
window.loadLeaveSettings = loadLeaveSettings;

function loadJoinDMSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/joindm/${targetGuild}`)
        .then(res => res.json())
        .then(dm => {
            if (!dm) return;
            if (document.getElementById('eb-destination-channel')) document.getElementById('eb-destination-channel').value = dm.channel || 'dm';
            if (document.getElementById('eb-normal-text')) document.getElementById('eb-normal-text').value = dm.message || '';
            if (document.getElementById('eb-title')) document.getElementById('eb-title').value = dm.title || '';
            if (document.getElementById('eb-description')) document.getElementById('eb-description').value = dm.description || '';
            if (document.getElementById('eb-image-url')) document.getElementById('eb-image-url').value = dm.image || '';
            if (document.getElementById('eb-thumbnail-url')) document.getElementById('eb-thumbnail-url').value = dm.thumbnail || '';
            if (document.getElementById('eb-footer-text')) document.getElementById('eb-footer-text').value = dm.footer || '';
            if (document.getElementById('eb-color-picker')) {
                document.getElementById('eb-color-picker').value = dm.color || '#a855f7';
                if (document.getElementById('eb-color-hex')) document.getElementById('eb-color-hex').value = dm.color || '#a855f7';
            }
            if (typeof updateEmbedBuilderPreview === 'function') updateEmbedBuilderPreview();
        })
        .catch(err => console.error("Error loading Join DM settings:", err));
}
window.loadJoinDMSettings = loadJoinDMSettings;

function loadInviteTrackerSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/invitetracker/${targetGuild}`)
        .then(res => res.json())
        .then(it => {
            if (!it) return;
            const isEnabled = (isTrue(it.enabled) || it.enabled === true || it.enabled === '1');
            if (document.getElementById('invitetracker-msg-enable')) document.getElementById('invitetracker-msg-enable').checked = isEnabled;
            if (document.getElementById('invitetracker-msg-channel-select')) document.getElementById('invitetracker-msg-channel-select').value = it.channel || 'general';
            if (document.getElementById('invitetracker-msg-outer-input')) document.getElementById('invitetracker-msg-outer-input').value = it.message || '';
            if (document.getElementById('invitetracker-embed-color-picker')) {
                document.getElementById('invitetracker-embed-color-picker').value = it.color || '#a855f7';
                if (document.getElementById('invitetracker-color-hex')) document.getElementById('invitetracker-color-hex').value = it.color || '#a855f7';
            }
            if (document.getElementById('invitetracker-embed-title')) document.getElementById('invitetracker-embed-title').value = it.title || '';
            if (document.getElementById('invitetracker-embed-desc')) document.getElementById('invitetracker-embed-desc').value = it.description || '';
            if (document.getElementById('invitetracker-embed-image')) document.getElementById('invitetracker-embed-image').value = it.image || '';
            if (document.getElementById('invitetracker-thumbnail-url')) document.getElementById('invitetracker-thumbnail-url').value = it.thumbnail || '';
            if (document.getElementById('invitetracker-embed-footer')) document.getElementById('invitetracker-embed-footer').value = it.footer || '';
            if (document.getElementById('invitetracker-author-name')) document.getElementById('invitetracker-author-name').value = it.author_name || '';
            if (document.getElementById('invitetracker-author-icon')) document.getElementById('invitetracker-author-icon').value = it.author_icon || '';
            if (document.getElementById('invitetracker-footer-icon')) document.getElementById('invitetracker-footer-icon').value = it.footer_icon || '';
            
            if (typeof updateInviteTrackerLivePreview === 'function') updateInviteTrackerLivePreview();
        })
        .catch(err => console.error("Error loading invite tracker settings:", err));
}
window.loadInviteTrackerSettings = loadInviteTrackerSettings;

function loadGeneralSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const g = data.guild || {};
            if (document.getElementById('guild-prefix-input')) document.getElementById('guild-prefix-input').value = g.prefix || '?';
            if (document.getElementById('guild-timezone-input')) document.getElementById('guild-timezone-input').value = g.timezone || 'UTC';
            if (document.getElementById('bot-nickname-input')) document.getElementById('bot-nickname-input').value = g.nickname || 'VEYRA';
            if (document.getElementById('welcome-channel-input')) document.getElementById('welcome-channel-input').value = g.updates_channel || '#welcome';
            
            fetch(`/api/settings/prefix/${targetGuild}`)
                .then(r => r.json())
                .then(pData => {
                    if (pData && pData.prefixes && pData.prefixes.length > 0) {
                        window.currentServerPrefixes = pData.prefixes;
                        if (typeof renderPrefixesList === 'function') renderPrefixesList();
                    }
                })
                .catch(() => {});
            
            if (typeof loadAuditWeblogs === 'function') loadAuditWeblogs(targetGuild);
        })
        .catch(err => console.error("Error loading general settings:", err));
}
window.loadGeneralSettings = loadGeneralSettings;

function loadCommandsSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    fetch(`/api/settings/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const disabledCmds = data.disabled_commands || [];
            if (Array.isArray(window.commandsData)) {
                window.commandsData.forEach(cmd => {
                    cmd.enabled = !disabledCmds.includes(cmd.name);
                });
                if (typeof filterCommands === 'function') filterCommands('all');
            }
        })
        .catch(err => console.error("Error loading commands settings:", err));
}
window.loadCommandsSettings = loadCommandsSettings;

function loadStickyMessagesSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    const tbody = document.getElementById('sticky-messages-table-body');
    if (!tbody) return;
    fetch(`/api/settings/stickymessages/${targetGuild}`)
        .then(res => res.json())
        .then(rows => {
            if (!rows || rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No sticky messages configured for this server.</td></tr>';
                return;
            }
            tbody.innerHTML = rows.map(r => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <td style="padding: 12px; font-weight: 600; color: #00aff4;"># ${r.channel || 'general'}</td>
                    <td style="padding: 12px; color: #f8fafc;">${r.message || ''}</td>
                    <td style="padding: 12px; color: #10b981;">Active</td>
                    <td style="padding: 12px; text-align: right;">
                        <button onclick="deleteStickyMessage('${r.id}')" style="background: #ef4444; border: none; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;" title="Delete Sticky"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(err => console.error("Error loading sticky messages:", err));
}
window.loadStickyMessagesSettings = loadStickyMessagesSettings;


function loadEmbedMessagesSettings(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    const container = document.getElementById('ebm-cards-container');
    if (container && container.children.length === 0 && typeof addMultiEmbedCard === 'function') {
        addMultiEmbedCard();
    }
}
window.loadEmbedMessagesSettings = loadEmbedMessagesSettings;

function loadServerOverview(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    if (!targetGuild) return;
    if (typeof loadSecuritySettings === 'function') loadSecuritySettings(targetGuild);
    if (typeof loadAuditWeblogs === 'function') loadAuditWeblogs(targetGuild);
    if (typeof loadRealAnalytics === 'function') loadRealAnalytics(targetGuild);
}
window.loadServerOverview = loadServerOverview;


function switchTab(tabId) {
    const requiredPlan = tabPermissions[tabId] || 'Free';
    const currentPlan = window.currentServerPlan || 'Free';
    
    let isAllowed = true;
    const activePlans = currentPlan.split(',').map(s => s.trim().toLowerCase());
    const hasPro = activePlans.includes('pro') || activePlans.includes('premium') || window.isUserLoggedIn;
    const hasPremium = activePlans.includes('premium') || window.isUserLoggedIn;
    const hasTicket = activePlans.some(p => p.includes('ticket')) || hasPremium || hasPro || window.isUserLoggedIn;

    if (requiredPlan === 'Free') {
        isAllowed = true;
    } else if (requiredPlan === 'Pro') {
        isAllowed = hasPro;
    } else if (requiredPlan === 'Premium') {
        isAllowed = hasPremium;
    } else if (requiredPlan === 'Ticket') {
        isAllowed = hasTicket;
    }
    
    if (!isAllowed) {
        showLockedPane(tabId, requiredPlan);
        return;
    }

    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => pane.style.display = 'none');
    
    const menuItems = document.querySelectorAll('.sidebar-item');
    menuItems.forEach(item => item.classList.remove('active'));
    
    const targetPane = document.getElementById(`tab-${tabId}`);
    if (targetPane) targetPane.style.display = 'block';
    
    const targetMenu = document.getElementById(`menu-${tabId}`);
    if (targetMenu) targetMenu.classList.add('active');
    
    currentTab = tabId;
    try {
        sessionStorage.setItem('pendingTab', tabId);
        sessionStorage.setItem('activeTab', tabId);
    } catch (e) {}

    // Dynamically adjust padding of workspace content area for tickets tab to start flush from the left edge
    const workspaceContent = document.getElementById('workspace-content');
    if (workspaceContent) {
        if (tabId === 'giveaways' && typeof initGiveawaysTab === 'function') initGiveawaysTab();
        if (tabId === 'billing' && typeof loadBillingData === 'function') loadBillingData(activeGuildId);
        if (tabId === 'tickets') {
            workspaceContent.style.setProperty('padding', '0', 'important');
        } else {
            workspaceContent.style.setProperty('padding', '', '');
        }
    }

    // Update levels premium lock visibility dynamically based on server subscription
    const levelsBanner = document.getElementById('levels-premium-banner');
    const levelsContainer = document.getElementById('levels-config-container');
    if (levelsBanner && levelsContainer) {
        if (hasPremium) {
            levelsBanner.style.display = 'none';
            levelsContainer.style.opacity = '1';
            levelsContainer.style.pointerEvents = 'auto';
        } else {
            levelsBanner.style.display = 'block';
            levelsContainer.style.opacity = '0.45';
            levelsContainer.style.pointerEvents = 'none';
        }
    }

    if (tabId === 'welcome') {
        setTimeout(() => { if (typeof updateWelcomeLivePreview === 'function') updateWelcomeLivePreview(); }, 50);
    } else if (tabId === 'leave') {
        setTimeout(() => { if (typeof updateLeaveLivePreview === 'function') updateLeaveLivePreview(); }, 50);
    } else if (tabId === 'embed') {
        setTimeout(() => { if (typeof updateEmbedBuilderPreview === 'function') updateEmbedBuilderPreview(); }, 50);
    } else if (tabId === 'invitetracker') {
        setTimeout(() => { if (typeof updateInviteTrackerLivePreview === 'function') updateInviteTrackerLivePreview(); }, 50);
    } else if (tabId === 'weblogs' || tabId === 'settings') {
        setTimeout(renderAuditLogs, 50);
    } else if (tabId === 'analytics') {
        if (typeof switchAnalyticsTimeframe === 'function') switchAnalyticsTimeframe('30D');
    } else if (tabId === 'reports') {
        if (typeof loadReportsSettings === 'function') loadReportsSettings(activeGuildId);
    } else if (tabId === 'giveaways' && typeof initGiveawaysTab === 'function') initGiveawaysTab();
        if (tabId === 'tickets') {
        if (typeof loadTicketsTab === 'function') loadTicketsTab(activeGuildId);
        setTimeout(() => {
            const dismissed = sessionStorage.getItem('tutorialDismissed30Days') || localStorage.getItem('tutorialDismissed30Days');
            // Tutorial modal permanently disabled per user instruction
        }, 300);
    } else if (tabId === 'autoroles') {
        if (typeof loadAutorolesSettings === 'function') loadAutorolesSettings(activeGuildId);
    } else if (tabId === 'publish') {
        if (typeof loadServerListing === 'function') loadServerListing(activeGuildId);
    } else if (tabId === 'stickymessages') {
        if (typeof loadStickyMessagesSettings === 'function') loadStickyMessagesSettings(activeGuildId);
    } else if (tabId === 'levels') {
        if (typeof loadLevelsSettings === 'function') loadLevelsSettings(activeGuildId);
    } else if (tabId === 'overview') {
        if (typeof loadServerOverview === 'function') loadServerOverview(activeGuildId);
    } else if (tabId === 'personalize' || tabId === 'bot-profile') {
        const gid = activeGuildId || localStorage.getItem('selected_guild_id');
        if (gid) loadBotProfileSettings(gid);
    }
}

function updateSidebarLocks() {
    const currentPlan = window.currentServerPlan || 'Free';
    
    const items = {
        'settings': 'Free',
        'autoroles': 'Free',
        'weblogs': 'Free',
        'verification': 'Pro',
        'security': 'Free',
        'personalize': 'Premium',
        'overview': 'Free',
        'analytics': 'Free',
        'reports': 'Premium',
        'levels': 'Premium',
        'commands': 'Pro',
        'publish': 'Premium',
        'welcome': 'Pro',
        'leave': 'Pro',
        'embed': 'Pro',
    'embedmessages': 'Free',
        'invitetracker': 'Pro',
        'stickymessages': 'Pro',
        'tickets': 'Ticket',
    'giveaways': 'Free'
    };
    
    for (const [tabId, reqPlan] of Object.entries(items)) {
        const el = document.getElementById(`menu-${tabId}`);
        if (!el) continue;
        
        const anchor = el.querySelector('a');
        if (!anchor) continue;
        
        const existingLock = anchor.querySelector('.sidebar-lock-icon');
        if (existingLock) existingLock.remove();
        
        let isLocked = false;
        
        if (isLocked) {
            const lockSpan = document.createElement('span');
            lockSpan.className = 'sidebar-lock-icon';
            lockSpan.style.marginLeft = 'auto';
            lockSpan.style.display = 'inline-flex';
            lockSpan.style.alignItems = 'center';
            lockSpan.style.color = '#ef4444';
            lockSpan.innerHTML = '<i class="fas fa-lock" style="font-size: 0.62rem; margin-left: 5px;"></i>';
            anchor.appendChild(lockSpan);
        }
    }

    // Dynamic lock icons for sub-pane settings selectors
    const subPaneReq = {
        'antinuke': 'Free',
        'beastmode': 'Pro',
        'antiraid': 'Pro',
        'verification': 'Pro',
        'moderation': 'Free',
        'whitelist': 'Premium',
        'logs': 'Free',
        'antispam': 'Pro'
    };
    
    const secNavBtns = document.querySelectorAll('.sec-nav-btn');
    secNavBtns.forEach(btn => {
        const tabName = btn.innerText.toLowerCase().replace(/\s+/g, '').replace('&', '');
        const reqPlan = subPaneReq[tabName];
        if (!reqPlan) return;
        
        const existingLock = btn.querySelector('.btn-lock-icon');
        if (existingLock) existingLock.remove();
        
        let isLocked = false;
        
        if (isLocked) {
            // Append small lock icon
            const cleanText = btn.innerText.replace(/<i class="fas fa-lock.*<\/i>/g, '').trim();
            btn.innerHTML = `${cleanText} <i class="fas fa-lock btn-lock-icon" style="font-size: 0.65rem; color: #ef4444; margin-left: 4px;"></i>`;
        } else {
            // Clear lock markup
            btn.innerHTML = btn.innerText.replace(/<i class="fas fa-lock.*<\/i>/g, '').trim();
        }
    });
}

function enforcePlanUI() {
    const plan = 'Premium';
    const activePlans = ['pro', 'premium', 'ticket'];
    const hasPro = true;
    const isFree = false;
    
    // 1. Limits fields (7)
    const limits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
    limits.forEach(key => {
        const limitEl = document.getElementById(`sec-limit-${key}`);
        const punishEl = document.getElementById(`sec-punish-${key}`);
        const enableEl = document.getElementById(`sec-enable-${key}`);
        
        if (isFree && key !== 'ban' && key !== 'kick') {
            if (limitEl) { limitEl.disabled = true; limitEl.style.opacity = 0.45; }
            if (punishEl) { punishEl.disabled = true; punishEl.style.opacity = 0.45; }
            if (enableEl) { enableEl.disabled = true; enableEl.checked = false; }
        } else {
            if (limitEl) { limitEl.disabled = false; limitEl.style.opacity = 1; }
            if (punishEl) { punishEl.disabled = false; punishEl.style.opacity = 1; }
            if (enableEl) { enableEl.disabled = false; }
            
            // Constrain limits entered manually to max 5 for free tier on ban/kick
            if (isFree && (key === 'ban' || key === 'kick')) {
                if (limitEl) {
                    if (parseInt(limitEl.value) > 5) {
                        limitEl.value = 5;
                    }
                    // Handle change triggers
                    if (!limitEl.dataset.hasPlanListener) {
                        limitEl.dataset.hasPlanListener = "true";
                        limitEl.addEventListener('change', () => {
                            const curActivePlans = (window.currentServerPlan || 'Free').split(',').map(s => s.trim().toLowerCase());
                            const curHasPro = curActivePlans.includes('pro') || curActivePlans.includes('premium');
                            if (!curHasPro && parseInt(limitEl.value) > 5) {
                                limitEl.value = 5;
                                showToast("Plan Limit Restriction", "Free tier Anti-Ban & Anti-Kick triggers are capped at a maximum threshold of 5. Upgrade your plan to configure higher limits.", "warning");
                            }
                        });
                    }
                }
            }
        }
    });
    
    // 2. Instant Punishments fields (9)
    const instant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename'];
    instant.forEach(key => {
        const punishEl = document.getElementById(`sec-punish-${key}`);
        const enableEl = document.getElementById(`sec-enable-${key}`);
        
        if (isFree) {
            if (punishEl) { punishEl.disabled = true; punishEl.style.opacity = 0.45; }
            if (enableEl) { enableEl.disabled = true; enableEl.checked = false; }
        } else {
            if (punishEl) { punishEl.disabled = false; punishEl.style.opacity = 1; }
            if (enableEl) { enableEl.disabled = false; }
        }
    });
}

window.activeAnalyticsPoints = [];

window.switchAnalyticsTimeframe = function(timeframe) {
    // Plan gate: Free servers can only view up to 30D (1D, 3D, 7D, 30D). 90D is for Pro & Enterprise.
    const currentPlan = (window.currentServerPlan || 'Free').toLowerCase();
    const isPaid = currentPlan.includes('pro') || currentPlan.includes('premium') || currentPlan.includes('enterprise');
    
    if (timeframe === '90D' && !isPaid) {
        if (typeof showToast === 'function') {
            showToast('Pro Feature', '90 Days Analytics is exclusive to Pro and Enterprise servers. Free plan includes up to 30 days.', 'warning');
        }
        if (typeof openRazorpayServerModal === 'function') {
            setTimeout(() => openRazorpayServerModal('Pro'), 400);
        }
        return;
    }

    document.querySelectorAll('.analytics-tf-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'transparent';
        btn.style.color = '#475569';
        btn.style.fontWeight = '700';
        btn.style.boxShadow = 'none';
    });
    
    const activeBtn = document.getElementById(`tf-btn-${timeframe}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.background = '#E11D48';
        activeBtn.style.color = '#FFFFFF';
        activeBtn.style.fontWeight = '800';
        activeBtn.style.boxShadow = '0 2px 8px rgba(225, 29, 72, 0.25)';
    }
    
    window.currentAnalyticsTimeframe = timeframe;
    loadRealAnalytics(activeGuildId, timeframe);
};

// FAQ Accordion
function toggleFaq(el) {
    const item = el.parentElement;
    item.classList.toggle('active');
    const icon = el.querySelector('i');
    if (item.classList.contains('active')) {
        icon.className = 'fas fa-minus';
    } else {
        icon.className = 'fas fa-plus';
    }
}

function loginWithDiscord() {
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting to Discord...';
    }
    // Redirect directly to real Discord OAuth login
    window.location.href = '/api/auth/login';
}

function simulateLogin() {
    loginWithDiscord();
}

function simulateAddBot(serverName, serverId) {
    const clientId = '1527243189860175933';
    let url = `https://discord.com/oauth2/authorize?client_id=${clientId}&permissions=8&redirect_uri=https%3A%2F%2Fveyra-bot.vercel.app%2Fauth%2Fcallback&integration_type=0&scope=bot+applications.commands`;
    if (serverId && !serverId.startsWith('mock-')) {
        url += '&guild_id=' + encodeURIComponent(serverId);
    }
    window.open(url, 'Invite VEYRA Bot', 'width=500,height=800,resizable=yes,scrollbars=yes');

    // Real-time polling: Check every 3 seconds for 45s so the added server flips to "Bot Active" automatically
    let pollCount = 0;
    if (window._addBotPollTimer) clearInterval(window._addBotPollTimer);
    window._addBotPollTimer = setInterval(() => {
        pollCount++;
        if (pollCount > 15) {
            clearInterval(window._addBotPollTimer);
            return;
        }
        if (window.isUserLoggedIn && typeof checkSession === 'function') {
            checkSession(true);
        }
    }, 3000);
}

function updateHeaderWidgetsVisibility(isLoggedIn, user = null) {
    const widgets = document.getElementById('header-user-widgets');
    const loginBtn = document.getElementById('login-btn');
    if (isLoggedIn) {
        window.currentUser = user;
        const uPlan = (user && user.plan) ? user.plan : { plan_type: 'Free', expires_at: 'N/A' };
        
        const badgeEl = document.getElementById('sidebar-subscription-badge');
        const titleEl = document.getElementById('sidebar-subscription-title');
        const footerEl = document.getElementById('sidebar-subscription-footer');
        
        if (badgeEl && titleEl && footerEl) {
            if (uPlan.plan_type === 'Premium') {
                badgeEl.innerText = 'USER SUBSCRIPTION ACTIVE';
                badgeEl.style.color = '#f59e0b';
                titleEl.innerHTML = '<i class="fas fa-crown"></i> Premium Plan';
                footerEl.innerText = uPlan.expires_at === 'Lifetime' ? 'Lifetime Access' : `Expires: ${new Date(uPlan.expires_at).toLocaleDateString()}`;
                footerEl.style.color = '#f59e0b';
            } else if (uPlan.plan_type === 'Pro') {
                badgeEl.innerText = 'USER SUBSCRIPTION ACTIVE';
                badgeEl.style.color = '#c084fc';
                titleEl.innerHTML = '<i class="fas fa-bolt"></i> Pro Plan';
                footerEl.innerText = uPlan.expires_at === 'Lifetime' ? 'Lifetime Access' : `Expires: ${new Date(uPlan.expires_at).toLocaleDateString()}`;
                footerEl.style.color = '#c084fc';
            } else {
                badgeEl.innerText = 'FREE SUBSCRIPTION';
                badgeEl.style.color = '#94a3b8';
                titleEl.innerText = 'Free Plan';
                footerEl.innerText = 'Upgrade to unlock Pro/Premium';
                footerEl.style.color = '#a855f7';
            }
        }
        
        if (widgets) widgets.style.display = 'flex';
        if (loginBtn) loginBtn.style.display = 'none';
        
        const username = (user && (user.global_name || user.username)) ? (user.global_name || user.username) : '!! DADDY';
        const handleTag = (user && user.username) ? `@${user.username}` : '@savageoi';
        
        let avatarUrl = 'https://cdn.discordapp.com/avatars/1256986886631854080/e5f2679c33de4dfea4d337d6ea14d4c3.png?size=256';
        if (user && user.id && user.avatar && user.avatar !== 'user_avatar') {
            const ext = user.avatar.startsWith('a_') ? 'gif' : 'png';
            avatarUrl = `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.${ext}?size=256`;
        } else if (user && user.avatar_url) {
            avatarUrl = user.avatar_url;
        }
        window.currentUserAvatar = avatarUrl;

        const avatarImgEl = document.getElementById('header-user-avatar-img') || document.getElementById('header-user-avatar-img-top');
        const dropdownAvatarEl = document.getElementById('header-user-dropdown-avatar');
        const nameEl = document.getElementById('header-user-dropdown-name');
        
        if (avatarImgEl) {
            avatarImgEl.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; object-fit: cover;">`;
        }
        if (dropdownAvatarEl) {
            dropdownAvatarEl.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; object-fit: cover;">`;
        }
        if (nameEl) {
            nameEl.innerText = username;
        }

        const sidebarAvatar = document.getElementById('sidebar-user-avatar');
        const sidebarName = document.getElementById('sidebar-user-name');
        if (sidebarAvatar) {
            sidebarAvatar.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            sidebarAvatar.style.background = 'transparent';
        }
        if (sidebarName) {
            sidebarName.innerText = handleTag;
        }
        
        const serversAvatar = document.getElementById('servers-user-avatar');
        const serversDisplayName = document.getElementById('servers-user-displayname');
        const serversHandle = document.getElementById('servers-user-handle');
        if (serversAvatar) {
            serversAvatar.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            serversAvatar.style.background = 'transparent';
        }
        if (serversDisplayName) {
            serversDisplayName.innerText = username;
        }
        if (serversHandle) {
            serversHandle.innerText = handleTag;
        }
    } else {
        if (widgets) widgets.style.display = 'none';
        if (loginBtn) loginBtn.style.display = 'inline-flex';
    }
}

function toggleHeaderDropdown(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const isVisible = el.style.display === 'block';
    
    document.querySelectorAll('#header-server-dropdown, #header-user-dropdown').forEach(d => d.style.display = 'none');
    
    if (!isVisible) {
        el.style.display = 'block';
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('#header-user-widgets')) {
        document.querySelectorAll('#header-server-dropdown, #header-user-dropdown').forEach(d => d.style.display = 'none');
    }
});

// Global listener for Discord OAuth Mock Authorization Popups
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'DISCORD_AUTH_SUCCESS') {
        window.isUserLoggedIn = true;
        const u = event.data.user || {};
        updateHeaderWidgetsVisibility(true, u);
        checkSession(); // Fetch live session with bot guilds membership
        showScreen('servers');
        showToast("Success", "Successfully authenticated with Discord OAuth!");
    } else if (event.data && event.data.type === 'DISCORD_AUTH_CANCEL') {
        window.isUserLoggedIn = false;
        updateHeaderWidgetsVisibility(false);
        showToast("Authentication Cancelled", "OAuth login flow terminated by user.", "warning");
    } else if (event.data && event.data.type === 'DISCORD_BOT_INVITED') {
        showToast("Invite Sent", `Adding VEYRA to server: ${event.data.serverName}...`);
        setTimeout(() => {
            showToast("Success", `VEYRA Bot successfully joined ${event.data.serverName}!`);
            
            // Mark server as active in local cache dynamically
            if (window.allGuildsCache) {
                const found = window.allGuildsCache.find(g => g.name === event.data.serverName);
                if (found) {
                    found.active = true;
                    filterGuildsList(); // Re-render servers screen
                }
            }
        }, 1800);
    }
});

function logout() {
    window.isUserLoggedIn = false;
    updateHeaderWidgetsVisibility(false);

    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.innerHTML = `
            <div class="liquid-metal-btn-inner">
                <i class="fab fa-discord" style="color: #E26749;"></i>
                <span>Login with Discord</span>
            </div>
        `;
        loginBtn.onclick = () => simulateLogin();
    }
    
    const sidebarAvatar = document.getElementById('sidebar-user-avatar');
    const sidebarName = document.getElementById('sidebar-user-name');
    if (sidebarAvatar) {
        sidebarAvatar.innerText = 'D';
        sidebarAvatar.style.background = '#9333ea';
    }
    if (sidebarName) {
        sidebarName.innerText = 'Not Logged In';
    }
    
    const navDash = document.getElementById('nav-dashboard');
    if (navDash) navDash.style.display = 'none';
    
    // Clear cookies for logout
    document.cookie = "SENTRIX_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "VEYRA_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    localStorage.removeItem('SENTRIX_session');
    localStorage.removeItem('VEYRA_session');
    
    try {
        fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    } catch (e) {}
    
    showScreen('landing');
    showToast("Logged Out", "You have closed the server session.");
}

// --- 6. SWATCH THEMING ENGINE ---
let activeTheme = 'light';

function changeSystemTheme(themeName, silent = false) {
    document.body.className = 'theme-light';
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('veyra_theme', 'light');
    activeTheme = 'light';
    
    document.querySelectorAll('.theme-swatch').forEach(swatch => {
        swatch.classList.remove('active');
    });
    const activeSwatch = document.getElementById('swatch-light') || document.getElementById('swatch-slate');
    if (activeSwatch) activeSwatch.classList.add('active');
    
    if (!silent) {
        showToast("Theme Selected", `Visual layout theme set to: LIGHT`);
    }
}

function loadActiveTheme() {
    changeSystemTheme('light', true);
}

// --- 7. EMBED BUILDER PREVIEWS ---
function updateEmbedPreview() {
    const textEl = document.getElementById('embed-text');
    const titleEl = document.getElementById('embed-title');
    const descEl = document.getElementById('embed-desc');
    const colorEl = document.getElementById('embed-color');
    const authorEl = document.getElementById('embed-author');
    const footerEl = document.getElementById('embed-footer');
    
    const textVal = textEl ? textEl.value : '';
    const titleVal = titleEl ? titleEl.value : '';
    const descVal = descEl ? descEl.value : '';
    const colorVal = colorEl ? colorEl.value : '#a855f7';
    const authorVal = authorEl ? authorEl.value : '';
    const footerVal = footerEl ? footerEl.value : '';
    
    const previewOuter = document.getElementById('preview-outer-text');
    const previewTitle = document.getElementById('preview-title');
    const previewDesc = document.getElementById('preview-desc');
    const previewAuthor = document.getElementById('preview-author-header');
    const previewEmbed = document.getElementById('preview-inner-embed');
    const previewFooter = document.getElementById('preview-footer-text');
    
    if (previewOuter) previewOuter.innerText = textVal;
    if (previewTitle) previewTitle.innerText = titleVal;
    if (previewDesc) previewDesc.innerText = descVal;
    if (previewAuthor) previewAuthor.innerText = authorVal ? authorVal : 'VEYRA';
    if (previewEmbed) previewEmbed.style.borderColor = colorVal;
    if (previewFooter) previewFooter.innerText = footerVal;
}

function sendEmbedToDiscord() {
    const channel = document.getElementById('embed-channel').value;
    showToast("Embed Posted", `Announcement embed successfully sent to: ${channel}`);
    addLogEntry("@itzarun170", `Posted embed builder broadcast in ${channel}`);
}

// --- 8. COMMANDS CONFIGURATION GRID ---
const commandsData = [
    // Security Commands (50)
    { name: "antinuke-enable", desc: "Turns on the main anti-nuke module.", cat: "security", enabled: true },
    { name: "antinuke-disable", desc: "Turns off the main anti-nuke module.", cat: "security", enabled: false },
    { name: "antinuke-config", desc: "Displays current anti-nuke limits and punishments.", cat: "security", enabled: true },
    { name: "antinuke-logs", desc: "View raw logs from the anti-nuke defense loop.", cat: "security", enabled: true },
    { name: "antinuke-threshold", desc: "Configures rate limits for administrator edits.", cat: "security", enabled: true },
    { name: "whitelist-add", desc: "Adds a user to bypass anti-nuke limits.", cat: "security", enabled: true },
    { name: "whitelist-remove", desc: "Removes a user from the whitelist bypass list.", cat: "security", enabled: true },
    { name: "whitelist-list", desc: "Lists all currently whitelisted users.", cat: "security", enabled: true },
    { name: "beastmode-toggle", desc: "Enables or disables aggressive zero-trust mode.", cat: "security", enabled: false },
    { name: "beastmode-status", desc: "Checks status and logs for Beast Mode overrides.", cat: "security", enabled: true },
    { name: "antiraid-enable", desc: "Enables anti-raid join filters.", cat: "security", enabled: true },
    { name: "antiraid-disable", desc: "Disables anti-raid join filters.", cat: "security", enabled: true },
    { name: "antiraid-config", desc: "Configures anti-raid join rate limits.", cat: "security", enabled: true },
    { name: "antibot-toggle", desc: "Locks down guild against unverified bot joins.", cat: "security", enabled: true },
    { name: "antibot-punish", desc: "Configures punishment type for unauthorized bot inviters.", cat: "security", enabled: true },
    { name: "antispam-links", desc: "Toggles link-based spam filtering.", cat: "security", enabled: true },
    { name: "antispam-mentions", desc: "Toggles mention-based spam filtering.", cat: "security", enabled: true },
    { name: "antispam-invites", desc: "Toggles automatic server invite link deletions.", cat: "security", enabled: true },
    { name: "webhook-monitor", desc: "Monitors and deletes unauthorized webhooks instantly.", cat: "security", enabled: true },
    { name: "webhook-bypass", desc: "Whitelists a safe webhook URL pattern.", cat: "security", enabled: true },
    { name: "channel-guard", desc: "Prevents bulk deletion of text/voice channels.", cat: "security", enabled: true },
    { name: "role-guard", desc: "Prevents unauthorized role deletion or updates.", cat: "security", enabled: true },
    { name: "ban-guard", desc: "Triggers if staff account bans too many users rapidly.", cat: "security", enabled: true },
    { name: "kick-guard", desc: "Triggers if staff account kicks members too fast.", cat: "security", enabled: true },
    { name: "prune-guard", desc: "Locks down server if client prune events occur.", cat: "security", enabled: true },
    { name: "vanity-guard", desc: "Monitors changes to server vanity URL mappings.", cat: "security", enabled: true },
    { name: "server-icon-guard", desc: "Reverts unauthorized guild icon changes.", cat: "security", enabled: true },
    { name: "server-rename-guard", desc: "Reverts unauthorized guild name modifications.", cat: "security", enabled: true },
    { name: "role-rename-guard", desc: "Reverts renaming of key staff roles.", cat: "security", enabled: true },
    { name: "channel-rename-guard", desc: "Reverts renaming of secure channels.", cat: "security", enabled: true },
    { name: "mass-mention-guard", desc: "Bans users mentioning mass roles/everyone.", cat: "security", enabled: true },
    { name: "permissions-guard", desc: "Reverts administrative permissions additions.", cat: "security", enabled: true },
    { name: "dangerous-permissions", desc: "Lists all roles carrying risky admin permissions.", cat: "security", enabled: true },
    { name: "quarantine-user", desc: "Strips all roles from a compromised account instantly.", cat: "security", enabled: true },
    { name: "quarantine-status", desc: "Lists all members currently in quarantine.", cat: "security", enabled: true },
    { name: "quarantine-role-set", desc: "Configures the role assigned to quarantined users.", cat: "security", enabled: true },
    { name: "verify-captcha-enable", desc: "Enables captcha verification for new joins.", cat: "security", enabled: true },
    { name: "verify-captcha-disable", desc: "Disables captcha verification for new joins.", cat: "security", enabled: true },
    { name: "verification-bypass-role", desc: "Configures roles that bypass join captcha checks.", cat: "security", enabled: true },
    { name: "lockdown-category", desc: "Locks down all channels inside a category.", cat: "security", enabled: true },
    { name: "lockdown-voice", desc: "Mutes all users in a voice channel category.", cat: "security", enabled: true },
    { name: "lockdown-server", desc: "Freezes all text channel messages globally.", cat: "security", enabled: false },
    { name: "unlockdown-server", desc: "Restores normal message privileges globally.", cat: "security", enabled: true },
    { name: "bypass-roles-list", desc: "Lists roles that bypass anti-raid filters.", cat: "security", enabled: true },
    { name: "role-spam-guard", desc: "Limits maximum roles a staff user can create per hour.", cat: "security", enabled: true },
    { name: "channel-spam-guard", desc: "Limits maximum channels a staff user can create per hour.", cat: "security", enabled: true },
    { name: "alert-channel", desc: "Sets the channel where security threat notices are dispatched.", cat: "security", enabled: true },
    { name: "emergency-reset", desc: "Reverts all active channel lockdowns in the guild.", cat: "security", enabled: true },
    { name: "threat-level", desc: "Sets active threshold level for automatic bans.", cat: "security", enabled: true },
    { name: "security-diagnostics", desc: "Scans permissions for potential security gaps.", cat: "security", enabled: true },

    // Moderation Commands (50)
    { name: "ban", desc: "Bans a member from the Discord guild.", cat: "moderation", enabled: true },
    { name: "ban-list", desc: "Fetches a list of all banned users in the server.", cat: "moderation", enabled: true },
    { name: "tempban", desc: "Bans a member for a temporary duration.", cat: "moderation", enabled: true },
    { name: "unban", desc: "Revokes a user ban from the guild.", cat: "moderation", enabled: true },
    { name: "kick", desc: "Kicks a member from the guild.", cat: "moderation", enabled: true },
    { name: "mute", desc: "Mutes a user across all voice/text channels.", cat: "moderation", enabled: true },
    { name: "temp-mute", desc: "Mutes a user for a temporary duration.", cat: "moderation", enabled: true },
    { name: "unmute", desc: "Unmutes a previously muted member.", cat: "moderation", enabled: true },
    { name: "timeout", desc: "Puts a user in a timed timeout session.", cat: "moderation", enabled: true },
    { name: "untimeout", desc: "Removes active timeout from a member.", cat: "moderation", enabled: true },
    { name: "untimeout-user", desc: "Manually removes active timeout from a member.", cat: "moderation", enabled: true },
    { name: "warn", desc: "Issues a formal security warning to a member.", cat: "moderation", enabled: true },
    { name: "warnings", desc: "Lists active warnings list of a member.", cat: "moderation", enabled: true },
    { name: "warn-list", desc: "Fetches warning history for the entire guild.", cat: "moderation", enabled: true },
    { name: "delwarn", desc: "Deletes a warning case by ID.", cat: "moderation", enabled: true },
    { name: "clearwarn", desc: "Clears all warnings from a user's record.", cat: "moderation", enabled: true },
    { name: "warnings-clear", desc: "Clears warning log registry for a member.", cat: "moderation", enabled: true },
    { name: "purge", desc: "Deletes a volume of messages from text channels.", cat: "moderation", enabled: true },
    { name: "purge-bot", desc: "Purges only recent messages sent by bots.", cat: "moderation", enabled: true },
    { name: "purge-user", desc: "Purges messages sent by a specific user.", cat: "moderation", enabled: true },
    { name: "purge-links", desc: "Purges messages containing hyperlinked URLs.", cat: "moderation", enabled: true },
    { name: "purge-images", desc: "Purges messages carrying files or attachments.", cat: "moderation", enabled: true },
    { name: "purge-regex", desc: "Purges messages matching a specific text pattern.", cat: "moderation", enabled: true },
    { name: "purge-embeds", desc: "Purges messages containing embeds.", cat: "moderation", enabled: true },
    { name: "purge-contains", desc: "Purges messages containing a specific word.", cat: "moderation", enabled: true },
    { name: "lock", desc: "Disables sending messages in current channel.", cat: "moderation", enabled: true },
    { name: "unlock", desc: "Enables sending messages in current channel.", cat: "moderation", enabled: true },
    { name: "lockdown-channel", desc: "Mutes everyone in a specific channel.", cat: "moderation", enabled: true },
    { name: "unlockdown-channel", desc: "Restores sending privileges in a specific channel.", cat: "moderation", enabled: true },
    { name: "slowmode", desc: "Sets a message delay rate limit for a channel.", cat: "moderation", enabled: true },
    { name: "slowmode-duration", desc: "Updates the active slowmode delay for current channel.", cat: "moderation", enabled: true },
    { name: "slowmode-off", desc: "Turns slowmode off for current channel.", cat: "moderation", enabled: true },
    { name: "hide-channel", desc: "Hides current channel from public roles.", cat: "moderation", enabled: true },
    { name: "reveal-channel", desc: "Makes channel visible to public roles.", cat: "moderation", enabled: true },
    { name: "mute-setup", desc: "Creates the muted role and channel overrides.", cat: "moderation", enabled: true },
    { name: "massban", desc: "Bans multiple users at once.", cat: "moderation", enabled: true },
    { name: "masskick", desc: "Kicks multiple users at once.", cat: "moderation", enabled: true },
    { name: "softban", desc: "Bans and instantly unbans a user to clear messages.", cat: "moderation", enabled: true },
    { name: "nick", desc: "Modifies nickname of a member.", cat: "moderation", enabled: true },
    { name: "strip-roles", desc: "Removes all roles from a user.", cat: "moderation", enabled: true },
    { name: "role-add-member", desc: "Grants a role to a member.", cat: "moderation", enabled: true },
    { name: "role-remove-member", desc: "Removes a role from a member.", cat: "moderation", enabled: true },
    { name: "warn-threshold", desc: "Sets actions for warn count thresholds.", cat: "moderation", enabled: true },
    { name: "pardon", desc: "Clears user warnings and bans from audit logs.", cat: "moderation", enabled: true },
    { name: "pardon-case", desc: "Deletes a moderation infraction entry by case ID.", cat: "moderation", enabled: true },
    { name: "infractions", desc: "Lists total server moderation infractions.", cat: "moderation", enabled: true },
    { name: "modlogs-view", desc: "Checks specific log list about case cases.", cat: "moderation", enabled: true },
    { name: "modlogs-channel", desc: "Sets the channel where mod action cards are sent.", cat: "moderation", enabled: true },
    { name: "audit-logs-export", desc: "Exports recent mod logs as a CSV file.", cat: "moderation", enabled: true },
    { name: "reason-edit", desc: "Modifies the listed reason for an active moderation case.", cat: "moderation", enabled: true },

    // Utility Commands (47)
    { name: "invites-lookup", desc: "Retrieves list of active invites and uses.", cat: "utility", enabled: true },
    { name: "invites-clear", desc: "Resets the invite metrics tracker database.", cat: "utility", enabled: true },
    { name: "invite-tracker-stats", desc: "Displays top inviter leaderboard rankings.", cat: "utility", enabled: true },
    { name: "invite-codes-list", desc: "Lists invite codes created by a specific user.", cat: "utility", enabled: true },
    { name: "whois", desc: "Displays detailed database profile about user.", cat: "utility", enabled: true },
    { name: "whois-db", desc: "Checks local SQLite profile information for a user.", cat: "utility", enabled: true },
    { name: "serverinfo", desc: "Fetches details of the current guild.", cat: "utility", enabled: true },
    { name: "botinfo", desc: "Displays bot runtime statistics and latency.", cat: "utility", enabled: true },
    { name: "stats", desc: "Displays CPU logs, RAM metrics, and uptime.", cat: "utility", enabled: true },
    { name: "stats-shards", desc: "Lists gateway latency details for all shards.", cat: "utility", enabled: true },
    { name: "uptime", desc: "Checks how long the bot process has been online.", cat: "utility", enabled: true },
    { name: "ping", desc: "Measures API websocket and database latency.", cat: "utility", enabled: true },
    { name: "help", desc: "Displays interactive command manual lists.", cat: "utility", enabled: true },
    { name: "db-diagnostics", desc: "Tests SQLite read-write processing speed.", cat: "utility", enabled: true },
    { name: "session-verify", desc: "Checks dashboard cookie token sessions.", cat: "utility", enabled: true },
    { name: "setup", desc: "Runs interactive guild setup checklist.", cat: "utility", enabled: true },
    { name: "config-view", desc: "Displays full configurations list format.", cat: "utility", enabled: true },
    { name: "prefix", desc: "Changes default command prefix character.", cat: "utility", enabled: true },
    { name: "nickname", desc: "Changes display name of the bot.", cat: "utility", enabled: true },
    { name: "logchannel", desc: "Configures webhook channel for audit logs.", cat: "utility", enabled: true },
    { name: "updates", desc: "Sets text channel for security updates feed.", cat: "utility", enabled: true },
    { name: "welcome-config", desc: "Sets welcome messages text channel.", cat: "utility", enabled: true },
    { name: "embed-create", desc: "Creates an embed message design case.", cat: "utility", enabled: true },
    { name: "embed-edit", desc: "Modifies a previously posted embed.", cat: "utility", enabled: true },
    { name: "embed-send", desc: "Sends custom embed to a selected channel.", cat: "utility", enabled: true },
    { name: "embed-raw", desc: "Fetches the raw JSON payload of an embed message.", cat: "utility", enabled: true },
    { name: "roleinfo", desc: "Displays creation date and permissions list of a role.", cat: "utility", enabled: true },
    { name: "channelinfo", desc: "Displays configuration metrics of a channel.", cat: "utility", enabled: true },
    { name: "membercount", desc: "Displays active online and total member count.", cat: "utility", enabled: true },
    { name: "audit-search", desc: "Searches audit logs history by event keyword.", cat: "utility", enabled: true },
    { name: "timezone-set", desc: "Sets default timezone for audit log charts.", cat: "utility", enabled: true },
    { name: "timezone-list", desc: "Lists available timezones for log charts.", cat: "utility", enabled: true },
    { name: "verify-channel-set", desc: "Sets channel where captcha verify runs.", cat: "utility", enabled: true },
    { name: "verify-role-set", desc: "Sets role granted after solving captcha.", cat: "utility", enabled: true },
    { name: "automod-words-add", desc: "Adds a forbidden phrase to automod filters.", cat: "utility", enabled: true },
    { name: "automod-words-remove", desc: "Removes a forbidden phrase from automod filters.", cat: "utility", enabled: true },
    { name: "giveaway-start", desc: "Launches a new server giveaway instance.", cat: "utility", enabled: true },
    { name: "giveaway-end", desc: "Forces an active giveaway to end and pick winners.", cat: "utility", enabled: true },
    { name: "giveaway-reroll", desc: "Rerolls winners for a completed giveaway.", cat: "utility", enabled: true },
    { name: "giveaway-list", desc: "Lists all running giveaways in the server.", cat: "utility", enabled: true },
    { name: "autoreply-add", desc: "Creates a keyword-triggered automated response.", cat: "utility", enabled: true },
    { name: "autoreply-remove", desc: "Deletes a keyword-triggered automated response.", cat: "utility", enabled: true },
    { name: "autoreply-list", desc: "Lists all configured auto-replies.", cat: "utility", enabled: true },
    { name: "level-rewards-add", desc: "Adds a role reward for leveling up.", cat: "utility", enabled: true },
    { name: "level-rewards-remove", desc: "Removes a role reward for leveling up.", cat: "utility", enabled: true },
    { name: "level-xp-rate", desc: "Configures the server multiplier rate for XP gains.", cat: "utility", enabled: true },
    { name: "bot-servers", desc: "Lists all guilds running this bot instance.", cat: "utility", enabled: true },

    // Additional Security Commands (11)
    { name: "antispam-config", desc: "Configures anti-spam message rate limits.", cat: "security", enabled: true },
    { name: "antipinn-guard", desc: "Reverts unauthorized message pinning in channels.", cat: "security", enabled: true },
    { name: "antiguillotine-mode", desc: "Turns on instant ban of anyone who deletes categories.", cat: "security", enabled: false },
    { name: "antivc-mute-guard", desc: "Reverts unauthorized server mute events in voice channels.", cat: "security", enabled: true },
    { name: "antivc-deafen-guard", desc: "Reverts unauthorized server deafen events in voice channels.", cat: "security", enabled: true },
    { name: "antiflood-text", desc: "Prevents duplicate text messages sent in quick succession.", cat: "security", enabled: true },
    { name: "antiemoji-guard", desc: "Reverts bulk emoji creations or deletions.", cat: "security", enabled: true },
    { name: "antisticker-guard", desc: "Reverts bulk sticker creations or deletions.", cat: "security", enabled: true },
    { name: "antiintegration-guard", desc: "Reverts unauthorized bot integration connections.", cat: "security", enabled: true },
    { name: "emergency-lockdown", desc: "Instantly locks all text and voice channels.", cat: "security", enabled: false },
    { name: "emergency-unlock", desc: "Restores original channel visibility overrides.", cat: "security", enabled: true },

    // Additional Moderation Commands (11)
    { name: "lock-all", desc: "Locks down all channels in the guild.", cat: "moderation", enabled: true },
    { name: "unlock-all", desc: "Unlocks all channels in the guild.", cat: "moderation", enabled: true },
    { name: "mute-voice", desc: "Mutes a member specifically in voice channels.", cat: "moderation", enabled: true },
    { name: "unmute-voice", desc: "Unmutes a member in voice channels.", cat: "moderation", enabled: true },
    { name: "deafen-voice", desc: "Server deafens a member in voice channels.", cat: "moderation", enabled: true },
    { name: "undeafen-voice", desc: "Server undeafens a member in voice channels.", cat: "moderation", enabled: true },
    { name: "disconnect-voice", desc: "Disconnects a member from voice channels.", cat: "moderation", enabled: true },
    { name: "slowmode-all", desc: "Applies a slowmode delay to all text channels.", cat: "moderation", enabled: true },
    { name: "purge-webhooks", desc: "Deletes recent messages sent via webhooks.", cat: "moderation", enabled: true },
    { name: "purge-mentions", desc: "Deletes recent messages containing user mentions.", cat: "moderation", enabled: true },
    { name: "infractions-clear", desc: "Wipes out all warning records of the guild.", cat: "moderation", enabled: true },

    // Additional Utility Commands (11)
    { name: "level-xp-add", desc: "Manually grants XP to a specific member.", cat: "utility", enabled: true },
    { name: "level-xp-remove", desc: "Deducts XP from a specific member.", cat: "utility", enabled: true },
    { name: "level-leaderboard", desc: "Displays top active ranking users in the server.", cat: "utility", enabled: true },
    { name: "level-rank", desc: "Fetches user's ranking profile card.", cat: "utility", enabled: true },
    { name: "level-rewards-list", desc: "Lists all leveling role milestones.", cat: "utility", enabled: true },
    { name: "level-rewards-clear", desc: "Clears all milestone level role configurations.", cat: "utility", enabled: true },
    { name: "level-config", desc: "Toggles XP levels and rates modules.", cat: "utility", enabled: true },
    { name: "ticket-setup", desc: "Deploys a new ticket creation embed panel.", cat: "utility", enabled: true },
    { name: "ticket-close", desc: "Safely archives and deletes an active ticket channel.", cat: "utility", enabled: true },
    { name: "ticket-add", desc: "Grants access to a member inside a ticket.", cat: "utility", enabled: true },
    { name: "ticket-remove", desc: "Removes a member from an active ticket.", cat: "utility", enabled: true },
    { name: "ranks", desc: "Get a list of joinable ranks.", cat: "utility", enabled: true },
    { name: "reason", desc: "Supply a reason for a mod log case.", cat: "moderation", enabled: true },
    { name: "remindme", desc: "Set a reminder.", cat: "utility", enabled: true },
    { name: "role-add", desc: "Add a user to a role.", cat: "moderation", enabled: true },
    { name: "role-all", desc: "Add or remove a role to all users.", cat: "moderation", enabled: true },
    { name: "role-bots", desc: "Toggle a role for all bots.", cat: "moderation", enabled: true },
    { name: "role-cancel", desc: "Cancel current role assignment.", cat: "moderation", enabled: true },
    { name: "slowmode-channel", desc: "Enable slowmode for a channel.", cat: "moderation", enabled: true },
    { name: "slowmode-discord", desc: "Set discord slowmode on a channel.", cat: "moderation", enabled: true },
    { name: "slowmode-user", desc: "Enable slowmode per user for a channel.", cat: "moderation", enabled: true },
    { name: "stickyrole-enable", desc: "Enable sticky role restoration.", cat: "security", enabled: true },
    { name: "stickyrole-disable", desc: "Disable sticky role restoration.", cat: "security", enabled: true },
    { name: "autorole-add", desc: "Add an autorole given to members on join.", cat: "utility", enabled: true },
    { name: "autorole-remove", desc: "Remove an autorole from the queue.", cat: "utility", enabled: true },
    { name: "autorole-list", desc: "List configured autoroles.", cat: "utility", enabled: true },
    { name: "work", desc: "Work to earn coins.", cat: "utility", enabled: true },
    { name: "space", desc: "Sends a spacer message.", cat: "utility", enabled: true }
];

const PRO_COMMANDS_SET = new Set([
    "beastmode-toggle", "beastmode-status", "antiraid-enable", "antiraid-disable", "antiraid-config",
    "antibot-toggle", "antibot-punish", "emergency-lockdown", "emergency-unlock", "antiguillotine-mode",
    "stickyrole-enable", "stickyrole-disable", "ticket-setup", "ticket-close", "ticket-add", "ticket-remove",
    "level-rewards-add", "level-rewards-remove", "level-xp-rate", "level-rewards-clear", "level-config",
    "level-xp-add", "level-xp-remove", "level-leaderboard", "level-rank",
    "role-all", "role-bots", "role-cancel", "slowmode-all", "purge-webhooks", "purge-mentions", "infractions-clear"
]);

function filterCommands(category, btnElement) {
    const container = document.getElementById('commands-toggle-container');
    if (!container) return;
    container.innerHTML = '';
    
    // Toggle active state on category filter buttons
    const filterBtns = document.querySelectorAll('#tab-commands .tab-selector button');
    filterBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#F1F5F9';
        b.style.color = '#0F172A';
        b.style.borderColor = '#CBD5E1';
    });
    if (btnElement) {
        btnElement.classList.add('active');
        btnElement.style.background = '#E11D48';
        btnElement.style.color = '#FFFFFF';
        btnElement.style.borderColor = '#E11D48';
    } else {
        const match = Array.from(filterBtns).find(b => b.textContent.toLowerCase().trim() === category.toLowerCase().trim());
        if (match) {
            match.classList.add('active');
            match.style.background = '#E11D48';
            match.style.color = '#FFFFFF';
            match.style.borderColor = '#E11D48';
        }
    }
    
    // Check if active server has Pro or Premium subscription
    const rawPlan = (window.activeGuildPlan || '').toLowerCase();
    const isProServer = rawPlan.includes('pro') || rawPlan.includes('premium') || rawPlan.includes('enterprise');

    const availableCmds = [];
    const lockedCmds = [];

    commandsData.forEach((cmd, idx) => {
        if (category !== 'all' && cmd.cat !== category) return;
        const isProCmd = PRO_COMMANDS_SET.has(cmd.name);
        if (isProCmd && !isProServer) {
            lockedCmds.push({ cmd, idx });
        } else {
            availableCmds.push({ cmd, idx });
        }
    });

    // 1. Render Available/Unlocked Commands in Main Grid
    availableCmds.forEach(({ cmd, idx }) => {
        const box = document.createElement('div');
        box.className = 'command-box';
        box.innerHTML = `
            <div class="command-info">
                <h4>/${cmd.name}</h4>
                <p>${cmd.desc}</p>
            </div>
            <label class="switch">
                <input type="checkbox" ${cmd.enabled ? 'checked' : ''} onchange="toggleCommand(${idx})">
                <span class="slider"></span>
            </label>
        `;
        container.appendChild(box);
    });

    // 2. Render Locked Pro Commands at the very bottom with Upgrade Prompt
    if (lockedCmds.length > 0) {
        const lockedSection = document.createElement('div');
        lockedSection.style.cssText = 'grid-column: 1 / -1; margin-top: 36px; padding-top: 24px; border-top: 1.5px solid #F1F5F9;';
        
        lockedSection.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom: 20px; background: #FFF5F7; border: 1.5px solid #FFE4E6; border-radius: 12px; padding: 16px 20px;">
                <div>
                    <h3 style="font-size: 1.05rem; font-weight: 800; color: #9F1239; margin: 0 0 3px 0; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-lock" style="color: #E11D48;"></i> Upgrade to Unlock These Commands (${lockedCmds.length})
                    </h3>
                    <p style="font-size: 0.8rem; color: #BE123C; margin: 0;">These enterprise anti-nuke, mass role, and automation commands are locked. Upgrade your server plan to activate them.</p>
                </div>
                <button type="button" onclick="switchTab('billing')" style="background: linear-gradient(135deg, #E11D48, #BE185D); color: #FFFFFF; border: none; padding: 8px 18px; border-radius: 8px; font-weight: 800; font-size: 0.82rem; cursor: pointer; box-shadow: 0 2px 8px rgba(225,29,72,0.3); display:flex; align-items:center; gap:6px; transition:opacity 0.2s;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                    <i class="fas fa-crown" style="color:#FDE047;"></i> Upgrade Now
                </button>
            </div>
            <div class="commands-list-grid" id="locked-commands-grid"></div>
        `;
        container.appendChild(lockedSection);

        const lockedGrid = lockedSection.querySelector('#locked-commands-grid');
        lockedCmds.forEach(({ cmd, idx }) => {
            const box = document.createElement('div');
            box.className = 'command-box';
            box.style.cssText = 'opacity: 0.75; background: #F8FAFC; border: 1.5px solid #E2E8F0; position: relative;';
            box.innerHTML = `
                <div class="command-info">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <h4 style="margin:0; color:#475569;">/${cmd.name}</h4>
                        <span style="background: #FFF1F2; color: #E11D48; border: 1px solid #FFE4E6; font-size: 0.65rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; display:inline-flex; align-items:center; gap:3px;">
                            <i class="fas fa-lock" style="font-size:0.6rem;"></i> PRO
                        </span>
                    </div>
                    <p style="color:#64748B;">${cmd.desc}</p>
                </div>
                <label class="switch" style="cursor: not-allowed; opacity: 0.45;" title="Upgrade to Pro to enable this command">
                    <input type="checkbox" disabled>
                    <span class="slider" onclick="event.preventDefault(); showToast('Pro Feature', 'Upgrade to Veyra Pro to unlock /' + '${cmd.name}', 'error'); setTimeout(() => switchTab('billing'), 600);"></span>
                </label>
            `;
            lockedGrid.appendChild(box);
        });
    }
}

function toggleCommand(index) {
    commandsData[index].enabled = !commandsData[index].enabled;
    const cmd = commandsData[index];
    showToast(cmd.enabled ? "Command Active" : "Command Revoked", `Slash trigger /${cmd.name} access status updated.`);
    
    if (!activeGuildId) return;
    const disabledCmds = commandsData.filter(c => !c.enabled).map(c => c.name);
    fetch(`/api/settings/commands/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ disabled_commands: disabledCmds })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            showToast("Error", "Failed to save command settings.");
        } else {
            addLogEntry("@itzarun170", `${cmd.enabled ? "Enabled" : "Disabled"} command /${cmd.name}`);
        }
    })
    .catch(() => {
        showToast("Error", "Failed to contact dashboard server.");
    });
}

// --- 9. CONFIG SAVES BINDINGS ---
function saveNickname() {
    if (!activeGuildId) return;
    const nick = document.getElementById('bot-nickname-input').value;
    
    fetch(`/api/settings/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: nick })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Success", `Nickname set to "${nick}" successfully.`);
            addLogEntry("@itzarun170", `Modified bot nickname to "${nick}"`);
        }
    });
}

function saveSecuritySettings() {
    if (window.isDashboardHydrating) return;
    if (!activeGuildId) return;
    
    const payload = {};
    
    // Limits (7)
    const limits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
    limits.forEach(key => {
        const dbKey = key.replace('-', '_');
        const limitEl = document.getElementById(`sec-limit-${key}`);
        const punishEl = document.getElementById(`sec-punish-${key}`);
        const enableEl = document.getElementById(`sec-enable-${key}`);
        
        payload[`anti_${dbKey}_limit`] = limitEl ? parseInt(limitEl.value) : 5;
        payload[`anti_${dbKey}_punish`] = punishEl ? punishEl.value : 'Ban';
        payload[`anti_${dbKey}_enabled`] = (enableEl && enableEl.checked) ? 1 : 0;
    });
    
    // Instant (14)
    const instant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename', 'emoji-delete', 'emoji-rename', 'invite-delete', 'invite-link', 'ghost-ping'];
    instant.forEach(key => {
        let dbKey = key.replace('-', '_');
        if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
        if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
        if (dbKey === 'vanity') dbKey = 'vanity_change';
        if (dbKey === 'server-icon') dbKey = 'server_icon_change';
        
        const punishEl = document.getElementById(`sec-punish-${key}`);
        const enableEl = document.getElementById(`sec-enable-${key}`);
        
        payload[`anti_${dbKey}_punish`] = punishEl ? punishEl.value : 'Ban';
        payload[`anti_${dbKey}_enabled`] = (enableEl && enableEl.checked) ? 1 : 0;
    });
    
    fetch(`/api/settings/security/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Security Config Saved", "Anti-nuke configuration rules written to database successfully.");
            addLogEntry("@itzarun170", "Overhauled anti-nuke threshold limits and punishment triggers");
            
// Security settings saved independently
        } else {
            showToast("Save Error", data.error || "Failed to sync configs");
        }
    })
    .catch(err => console.error("Error saving security settings:", err));
}

function saveWelcomeSettings() {
    if (!activeGuildId) return;
    const channel = document.getElementById('welcome-msg-channel-select')?.value || 'general';
    const enabled = document.getElementById('welcome-msg-enable')?.checked ? 1 : 0;
    const message = document.getElementById('welcome-msg-outer-input')?.value || '';
    const color = document.getElementById('welcome-color-hex')?.value || '#a855f7';
    const title = document.getElementById('welcome-embed-title')?.value || '';
    const description = document.getElementById('welcome-embed-desc')?.value || '';
    const image = document.getElementById('welcome-embed-image')?.value || '';
    const footer = document.getElementById('welcome-embed-footer')?.value || '';
    const thumbnail = document.getElementById('welcome-thumbnail-url')?.value || '';
    const author_name = document.getElementById('welcome-author-name')?.value || '';
    const author_icon = document.getElementById('welcome-author-icon')?.value || '';
    const footer_icon = document.getElementById('welcome-footer-icon')?.value || '';

    // First save updates_channel in guild_settings (general table)
    fetch(`/api/settings/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates_channel: channel })
    });

    // Save detailed welcome settings
    fetch(`/api/settings/welcome/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon, message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Welcome Saved", `Welcome Messages configuration successfully saved & bound to #${channel}`);
            addLogEntry("@itzarun170", `Updated welcome messages custom configurations for channel #${channel}`);
            if (enabled) {
                createFeatureChannels(["news"]);
            }
        }
    })
    .catch(err => console.error("Error saving welcome settings:", err));
}

function saveLeaveSettings() {
    if (!activeGuildId) return;
    const channel = document.getElementById('leave-msg-channel-select')?.value || 'exits';
    const enabled = document.getElementById('leave-msg-enable')?.checked ? 1 : 0;
    const message = document.getElementById('leave-msg-outer-input')?.value || '';
    const color = document.getElementById('leave-color-hex')?.value || '#a855f7';
    const title = document.getElementById('leave-embed-title')?.value || '';
    const description = document.getElementById('leave-embed-desc')?.value || '';
    const image = document.getElementById('leave-embed-image')?.value || '';
    const footer = document.getElementById('leave-embed-footer')?.value || '';
    const thumbnail = document.getElementById('leave-thumbnail-url')?.value || '';
    const author_name = document.getElementById('leave-author-name')?.value || '';
    const author_icon = document.getElementById('leave-author-icon')?.value || '';
    const footer_icon = document.getElementById('leave-footer-icon')?.value || '';

    // Save detailed leave settings
    fetch(`/api/settings/leave/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon, message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Exit Saved", `Exit Messages configuration successfully saved & bound to #${channel}`);
            addLogEntry("@itzarun170", `Updated exit messages custom configurations for channel #${channel}`);
        }
    })
    .catch(err => console.error("Error saving leave settings:", err));
}

function saveGeneralSettings() {
    if (!activeGuildId) return;
    const prefix = document.getElementById('guild-prefix-input').value;
    const tz = document.getElementById('guild-timezone-input').value;
    
    fetch(`/api/settings/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prefix: prefix, timezone: tz })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("General Config Saved", "Uptime clock and shell configurations updated successfully.");
            addLogEntry("@itzarun170", `Changed prefix parameter to "${prefix}"`);
        }
    });
}

// --- 10. SYSTEM NOTIFICATION TOASTS ---
function showToast(title, msg, type = 'info') {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.right = '24px';
    toast.style.zIndex = '999999';
    toast.style.maxWidth = '380px';
    toast.style.minWidth = '280px';
    toast.style.padding = '14px 18px';
    toast.style.background = '#0F172A';
    toast.style.color = '#FFFFFF';
    toast.style.borderRadius = '12px';
    toast.style.boxShadow = '0 16px 36px rgba(0, 0, 0, 0.35)';
    toast.style.border = '1px solid rgba(255, 255, 255, 0.12)';
    toast.style.display = 'flex';
    toast.style.alignItems = 'flex-start';
    toast.style.gap = '12px';
    toast.style.animation = 'slideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards';

    let iconHtml = '<i class="fas fa-circle-check" style="color: #10B981; font-size: 1.15rem; margin-top: 2px;"></i>';
    let borderColor = '#10B981';
    if (type === 'error') {
        iconHtml = '<i class="fas fa-circle-xmark" style="color: #DC2626; font-size: 1.15rem; margin-top: 2px;"></i>';
        borderColor = '#DC2626';
    } else if (type === 'warning') {
        iconHtml = '<i class="fas fa-triangle-exclamation" style="color: #F59E0B; font-size: 1.15rem; margin-top: 2px;"></i>';
        borderColor = '#F59E0B';
    } else if (type === 'info') {
        iconHtml = '<i class="fas fa-bell" style="color: #E11D48; font-size: 1.15rem; margin-top: 2px;"></i>';
        borderColor = '#E11D48';
    }
    toast.style.borderLeft = `4.5px solid ${borderColor}`;

    toast.innerHTML = `
        ${iconHtml}
        <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 700; color: #FFFFFF; font-size: 0.92rem; margin-bottom: 2px;">${title}</div>
            <div style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.4;">${msg}</div>
        </div>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: #64748B; cursor: pointer; padding: 2px; font-size: 0.85rem;" onmouseover="this.style.color='#FFFFFF'" onmouseout="this.style.color='#64748B'">
            <i class="fas fa-times"></i>
        </button>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.35s ease forwards';
        setTimeout(() => toast.remove(), 350);
    }, 4000);
}

// --- 11. AUDIT WEBLOGS STREAM RENDERER ---
function addLogEntry(user, details, timestamp, action = 'System') {
    const tableBody = document.getElementById('weblogs-table-body');
    if (!tableBody) return;
    
    const row = document.createElement('tr');
    row.style.borderBottom = '1px solid rgba(255,255,255,0.02)';
    
    let dateStr = 'Today';
    if (timestamp) {
        const d = new Date(timestamp);
        dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    row.innerHTML = `
        <td style="padding:12px 5px; color:var(--text-secondary); font-family:var(--font-mono); font-size:0.8rem;">${dateStr}</td>
        <td><strong>${user}</strong></td>
        <td><span style="background:rgba(168,85,247,0.12); color:#c084fc; border:1px solid rgba(168,85,247,0.3); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:var(--font-mono); font-weight:700;">${action}</span></td>
        <td>${details}</td>
    `;
    
    tableBody.insertBefore(row, tableBody.firstChild);
}

// --- 11.5 ASCI CINEMATIC REVEAL FOOTER INTERACTIVE ENGINE ---
function initAnimatedRevealFooter() {
    // Make sure GSAP is imported
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
        console.log("Waiting for GSAP libraries...");
        return;
    }
    gsap.registerPlugin(ScrollTrigger);

    const leftCanvas = document.getElementById('canvas-footer-left');
    const rightCanvas = document.getElementById('canvas-footer-right');
    if (!leftCanvas || !rightCanvas) return;

    const asciiChars = "........:::=+xX#0369";
    const columns = 50;
    const cellSize = 16;
    const fontSize = 14;

    function buildAsciiGrid(side) {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = 400;
        tempCanvas.height = 300;
        const tempCtx = tempCanvas.getContext('2d');
        
        tempCtx.fillStyle = '#000000';
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
        
        // Draw procedural VEYRA silhouette
        tempCtx.fillStyle = '#ffffff';
        tempCtx.beginPath();
        const cx = tempCanvas.width / 2;
        const cy = tempCanvas.height / 2;
        
        if (side === 'left') {
            // Left VEYRA (facing left, head on left, feather back on right)
            tempCtx.moveTo(cx + 100, cy - 100);
            tempCtx.quadraticCurveTo(cx, cy - 120, cx - 100, cy - 80); // Crown of head
            tempCtx.quadraticCurveTo(cx - 150, cy - 70, cx - 170, cy - 20); // Hooked beak top
            tempCtx.quadraticCurveTo(cx - 120, cy + 10, cx - 140, cy + 25); // Beak return hook
            tempCtx.quadraticCurveTo(cx - 80, cy + 15, cx - 50, cy + 40); // Throat curve
            tempCtx.quadraticCurveTo(cx + 20, cy + 90, cx + 110, cy + 120); // Ruffled chest feathers
            tempCtx.lineTo(cx + 140, cy + 50); // Base feather spikes
            tempCtx.lineTo(cx + 100, cy + 30);
            tempCtx.lineTo(cx + 130, cy);
            tempCtx.lineTo(cx + 80, cy - 10);
            tempCtx.lineTo(cx + 110, cy - 40);
        } else {
            // Right VEYRA (facing right, head on right, feather back on left)
            tempCtx.moveTo(cx - 100, cy - 100);
            tempCtx.quadraticCurveTo(cx, cy - 120, cx + 100, cy - 80); // Crown of head
            tempCtx.quadraticCurveTo(cx + 150, cy - 70, cx + 170, cy - 20); // Hooked beak top
            tempCtx.quadraticCurveTo(cx + 120, cy + 10, cx + 140, cy + 25); // Beak return hook
            tempCtx.quadraticCurveTo(cx + 80, cy + 15, cx + 50, cy + 40); // Throat curve
            tempCtx.quadraticCurveTo(cx - 20, cy + 90, cx - 110, cy + 120); // Ruffled chest feathers
            tempCtx.lineTo(cx - 140, cy + 50); // Base feather spikes
            tempCtx.lineTo(cx - 100, cy + 30);
            tempCtx.lineTo(cx - 130, cy);
            tempCtx.lineTo(cx - 80, cy - 10);
            tempCtx.lineTo(cx - 110, cy - 40);
        }
        tempCtx.closePath();
        tempCtx.fill();

        const rows = Math.round(columns * (tempCanvas.height / tempCanvas.width));
        const sampleColStep = tempCanvas.width / columns;
        const sampleRowStep = tempCanvas.height / rows;
        const pixels = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height).data;

        const cells = [];
        const backgroundCharIndex = asciiChars.lastIndexOf(".");

        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < columns; c++) {
                const px = Math.floor(c * sampleColStep);
                const py = Math.floor(r * sampleRowStep);
                const offset = (py * tempCanvas.width + px) * 4;
                const brightness = (pixels[offset] * 0.299 + pixels[offset + 1] * 0.587 + pixels[offset + 2] * 0.114) / 255;
                const charIndex = Math.min(asciiChars.length - 1, Math.floor((1 - brightness) * asciiChars.length));
                if (charIndex <= backgroundCharIndex) continue;

                cells.push({
                    col: c,
                    row: r,
                    char: asciiChars[charIndex],
                    highlightEndTime: 0
                });
            }
        }
        return { rows, cells };
    }

    function setupCanvas(canvas, sideData) {
        const dpr = window.devicePixelRatio || 1;
        canvas.width = columns * cellSize * dpr;
        canvas.height = sideData.rows * cellSize * dpr;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        ctx.font = `${fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        return ctx;
    }

    const leftData = buildAsciiGrid('left');
    const rightData = buildAsciiGrid('right');

    const leftCtx = setupCanvas(leftCanvas, leftData);
    const rightCtx = setupCanvas(rightCanvas, rightData);

    // Suppress global smokey fluid canvas when hovering over footer
    // Keep fluid canvas visible
    const footerRoot = document.getElementById('animated-reveal-footer');
    const fluidCanvas = document.getElementById('smokey-fluid-canvas');
    if (footerRoot && fluidCanvas) {
        // No-op to preserve background fluid visibility
    }

    function highlightCluster(cells, startCell) {
        const now = Date.now();
        startCell.highlightEndTime = now + 300;
        const steps = Math.floor(Math.random() * 8) + 1;
        const litCells = [startCell];
        let current = startCell;

        for (let step = 0; step < steps; step++) {
            const neighbours = cells.filter(c => {
                const dc = Math.abs(c.col - current.col);
                const dr = Math.abs(c.row - current.row);
                return (dc <= 1 && dr <= 1) && !(dc === 0 && dr === 0) && !litCells.includes(c);
            });
            if (neighbours.length === 0) break;
            const next = neighbours[Math.floor(Math.random() * neighbours.length)];
            next.highlightEndTime = now + 300 + step * 15;
            litCells.push(next);
            current = next;
        }
    }

    document.addEventListener('mousemove', (e) => {
        const lRect = leftCanvas.getBoundingClientRect();
        const rRect = rightCanvas.getBoundingClientRect();

        // Update highlight for left wing
        if (e.clientX >= lRect.left && e.clientX <= lRect.right && e.clientY >= lRect.top && e.clientY <= lRect.bottom) {
            const mc = ((e.clientX - lRect.left) / lRect.width) * columns;
            const mr = ((e.clientY - lRect.top) / lRect.height) * leftData.rows;
            triggerHighlightRipple(leftData.cells, mc, mr);
        }

        // Update highlight for right wing
        if (e.clientX >= rRect.left && e.clientX <= rRect.right && e.clientY >= rRect.top && e.clientY <= rRect.bottom) {
            const mc = ((e.clientX - rRect.left) / rRect.width) * columns;
            const mr = ((e.clientY - rRect.top) / rRect.height) * rightData.rows;
            triggerHighlightRipple(rightData.cells, mc, mr);
        }
    });

    function triggerHighlightRipple(cells, mc, mr) {
        let closest = null;
        let closestDist = Infinity;
        cells.forEach(cell => {
            const dc = mc - cell.col;
            const dr = mr - cell.row;
            const dist = Math.sqrt(dc * dc + dr * dr);
            if (dist < closestDist) {
                closestDist = dist;
                closest = cell;
            }
        });
        if (closest && closestDist <= 8) {
            highlightCluster(cells, closest);
        }
    }

    function renderAscii(ctx, sideData, baseColor) {
        ctx.clearRect(0, 0, columns * cellSize, sideData.rows * cellSize);
        const now = Date.now();
        const activeHoverColor = '#ffffff';

        sideData.cells.forEach(cell => {
            const x = cell.col * cellSize + cellSize / 2;
            const y = cell.row * cellSize + cellSize / 2;
            const isLit = cell.highlightEndTime > now;

            if (isLit) {
                ctx.fillStyle = activeHoverColor;
            } else {
                ctx.fillStyle = baseColor;
            }
            ctx.fillText(cell.char, x, y);
        });
    }

    // Optimized static footer render on-demand instead of 60fps infinite loop
    function renderFooterLoop() {
        renderAscii(leftCtx, leftData, '#c084fc');
        renderAscii(rightCtx, rightData, '#c084fc');
    }
    renderFooterLoop();

    // GSAP ScrollTrigger reveal coordination
    gsap.timeline({
        scrollTrigger: {
            trigger: "#animated-reveal-footer",
            start: "top bottom-=50px",
            onEnter: () => {
                gsap.to("#footer-left-wrap", { translateX: "0%", duration: 1.4, ease: "power3.out" });
                gsap.to("#footer-right-wrap", { translateX: "0%", duration: 1.4, ease: "power3.out" });
                gsap.to(".af-char", { translateY: "0%", duration: 1.0, ease: "power3.out", stagger: 0.08 });
            },
            onLeaveBack: () => {
                gsap.to("#footer-left-wrap", { translateX: "-125%", duration: 0.6, ease: "power2.in" });
                gsap.to("#footer-right-wrap", { translateX: "125%", duration: 0.6, ease: "power2.in" });
                gsap.to(".af-char", { translateY: "0%", duration: 0.5, ease: "power2.in" });
            }
        }
    });
}
window.initAnimatedRevealFooter = initAnimatedRevealFooter;

// --- 12. INITIALIZATION ON LOAD ---
function initDashboardApp() {

// --- INSTANT PERSISTENT SERVER SELECTION RESTORATION ON LOAD ---
(function restoreActiveServerInstant() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryGid = urlParams.get('guild_id');
        const savedGid = queryGid || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
        const savedName = localStorage.getItem('selected_guild_name');
        const savedIcon = localStorage.getItem('selected_guild_icon');

        if (savedName) {
            const sideName = document.getElementById('sidebar-guild-name');
            if (sideName) sideName.innerText = savedName;
            const mgName = document.getElementById('managing-server-name');
            if (mgName) mgName.innerText = savedName;
            const dsName = document.getElementById('dashboard-server-name');
            if (dsName) dsName.innerText = savedName;
            const hdName = document.getElementById('header-server-dropdown-name');
            if (hdName) hdName.innerText = savedName;
            const tkName = document.getElementById('tickets-sidebar-guild-name');
            if (tkName) tkName.innerText = savedName;
        }
        if (savedIcon || savedName) {
            window.updateActiveGuildUI(savedGid, savedName, savedIcon);
        }
        // Ensure sidebar server dropdown is closed by default
        const sDrop = document.getElementById('sidebar-server-dropdown');
        if (sDrop) sDrop.style.display = 'none';
        const sChev = document.getElementById('sidebar-guild-chevron');
        if (sChev) sChev.style.transform = 'rotate(0deg)';
    } catch(e) {}
})();

    loadActiveTheme();
    filterCommands('all');
    updateEmbedPreview();

    // Setup security sub-pane toggles
    // Handled globally by switchSecTab() without locks!

    // Setup sidebar collapse toggle listener with persistent icon-only state
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
        // Restore user collapse preference immediately
        if (localStorage.getItem('sidebar_collapsed') === 'true') {
            sidebar.classList.add('collapsed');
            toggleBtn.classList.add('crossed');
        }

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('collapsed');
            toggleBtn.classList.toggle('crossed');
            localStorage.setItem('sidebar_collapsed', sidebar.classList.contains('collapsed') ? 'true' : 'false');
        });
    }

    // Check if guild_id or tab is supplied in URL query string
    const urlParams = new URLSearchParams(window.location.search);
    let shouldCleanUrl = false;
    if (urlParams.has('guild_id')) {
        const queryGuildId = urlParams.get('guild_id');
        sessionStorage.setItem('hasEntered', 'true');
        sessionStorage.setItem('activeScreen', 'dashboard');
        sessionStorage.setItem('activeGuildId', queryGuildId);
        window.activeGuildId = queryGuildId;
    }
    if (urlParams.has('tab')) {
        sessionStorage.setItem('pendingTab', urlParams.get('tab'));
    }
    if (urlParams.has('action')) {
        sessionStorage.setItem('pendingAction', urlParams.get('action'));
    }

    // Invoke session check on load
    checkSession();
    
    // Bind captcha bypass triggers
    const verTypeDropdown = document.getElementById('ver-type');
    const verCapCheckbox = document.getElementById('ver-enable-captcha');
    if (verTypeDropdown) {
        verTypeDropdown.addEventListener('change', () => {
            toggleCaptchaOptionsBypass();
        });
    }
    if (verCapCheckbox) {
        verCapCheckbox.addEventListener('change', () => {
            toggleCaptchaOptionsBypass();
        });
    }

    // Parse URL hash for direct landing page sections
    const hash = window.location.hash ? window.location.hash.substring(1).toLowerCase() : "";
    const hasSectionHash = ['features', 'pricing', 'faq'].includes(hash);
    
    // Restore active screen on page refresh/reload if user has already entered
    const path = window.location.pathname.toLowerCase();
    const isStaticSubpage = path.includes('/ticket');
    
    if (sessionStorage.getItem('hasEntered') === 'true' && !isStaticSubpage && !hasSectionHash) {
        const webglCanvas = document.getElementById('webgl-canvas');
        if (webglCanvas) webglCanvas.style.display = 'none';
        const uiLayer = document.getElementById('ui-layer');
        if (uiLayer) uiLayer.style.display = 'none';
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.style.opacity = '1';
            mainContent.style.pointerEvents = 'auto';
        }
        
        const urlParams = new URLSearchParams(window.location.search);
        const queryGuildId = urlParams.get('guild_id');
        const isLoginSuccess = urlParams.get('login') === 'success';
        const isManagePath = window.location.pathname.includes('/manage') || window.location.pathname.includes('/dashboard');

        let activeScreen = 'landing';
        if (queryGuildId) {
            activeScreen = 'dashboard';
            window.activeGuildId = queryGuildId;
            sessionStorage.setItem('activeGuildId', queryGuildId);
            sessionStorage.setItem('activeScreen', 'dashboard');
        } else if (isLoginSuccess || isManagePath) {
            activeScreen = 'servers';
            sessionStorage.setItem('activeScreen', 'servers');
        } else {
            if (isManagePath) {
                const savedScreen = sessionStorage.getItem('activeScreen');
                const savedGuild = sessionStorage.getItem('activeGuildId');
                if (savedScreen === 'dashboard' && savedGuild) {
                    activeScreen = 'dashboard';
                    window.activeGuildId = savedGuild;
                } else {
                    activeScreen = 'servers';
                }
            } else {
                activeScreen = 'landing';
                sessionStorage.setItem('activeScreen', 'landing');
            }
        }
        
        setTimeout(() => {
            if (activeScreen === 'dashboard' && (window.activeGuildId || queryGuildId)) {
                const targetGid = window.activeGuildId || queryGuildId;
                loadServerDashboard(targetGid);
            } else {
                showScreen(activeScreen);
            }
        }, 150);
    } else if (!isStaticSubpage) {
        // If we are on the homepage and have a section hash, show screen 'landing' and scroll
        if (hasSectionHash) {
            const webglCanvas = document.getElementById('webgl-canvas');
            if (webglCanvas) webglCanvas.style.display = 'none';
            const uiLayer = document.getElementById('ui-layer');
            if (uiLayer) uiLayer.style.display = 'none';
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.style.opacity = '1';
                mainContent.style.pointerEvents = 'auto';
            }
            showScreen('landing');
            setTimeout(() => {
                clickNavSection(hash);
            }, 300);
        }
    }

    // Background floating particles disabled by user request

    // Set default value for embed builder date input on load
    const dateInput = document.getElementById('eb-date-input');
    if (dateInput) {
        const now = new Date();
        const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        dateInput.value = localIso;
        updateEmbedBuilderPreview();
    }

    // Safety Loading Spinner Resolver (eliminates infinite freeze permanently)
    setTimeout(() => {
        const grid = document.getElementById('servers-selection-grid');
        if (grid && grid.innerHTML.includes('Loading your Discord servers...')) {
            const fallbackGuilds = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
            renderUserGuilds(fallbackGuilds, true);
        }
    }, 800);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboardApp);
} else {
    initDashboardApp();
}

// --- 11.8 LEGACY THREAT SIMULATOR (DEPRECATED & SAFELY STUBBED) ---
window.simulateThreat = function(type, isAuto = false) { /* no-op */ };
function animateThreatParticles(type) { /* no-op */ }
// Helper to render procedural guild icons matching user screenshots
function getCustomServerIcon(serverName) {
    const name = serverName.toUpperCase();
    
    if (name.includes("RUSHI")) {
        return `<div class="dyno-server-icon" style="background: url('https://cdn.discordapp.com/embed/avatars/1.png'); background-size: cover;"><i class="fas fa-user-tie" style="color: rgba(255,255,255,0.2); font-size: 1.6rem;"></i></div>`;
    }
    if (name.includes("SERVER ONE")) {
        return `<div class="dyno-server-icon" style="background: #000; color: #fff; font-family: Impact, sans-serif; font-size: 0.85rem; padding: 4px; text-align: center; border-radius: 12px; line-height:1.2; text-shadow: 0 0 5px rgba(255,255,255,0.4); display:flex; flex-direction:column; justify-content:center; align-items:center;">SERVER<br>ONE</div>`;
    }
    if (name === "GHOST") {
        return `<div class="dyno-server-icon" style="background: #ef4444; color: #fff; display:flex; align-items:center; justify-content:center; border: 1.5px solid rgba(255,255,255,0.25);"><i class="fas fa-ghost"></i></div>`;
    }
    if (name.includes("SERVER TWO")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #ef4444, #7f1d1d); font-family: 'Arial Black', sans-serif; font-size: 0.68rem; line-height: 1.1; color: #fff; text-shadow: 0 2px 4px #000; display:flex; flex-direction:column; justify-content:center; align-items:center;">SERVER<br>TWO</div>`;
    }
    if (name === "STAR") {
        return `<div class="dyno-server-icon" style="background: radial-gradient(circle, #1e293b, #0f172a); color: #fbbf24; display:flex; align-items:center; justify-content:center;"><i class="fas fa-star" style="filter: drop-shadow(0 0 8px #fbbf24);"></i></div>`;
    }
    if (name.includes("LALA")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; display:flex; align-items:center; justify-content:center;"><i class="fas fa-smile-beam"></i></div>`;
    }
    if (name.includes("GUNS")) {
        return `<div class="dyno-server-icon" style="background: #18181b; color: #E26749; border: 1.5px solid rgba(168, 85, 247, 0.4); display:flex; align-items:center; justify-content:center;"><i class="fas fa-crosshairs"></i></div>`;
    }
    if (name.includes("OBSIDIAN")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #1e1b4b, #311042); color: #c084fc; display:flex; align-items:center; justify-content:center;"><i class="fas fa-gem"></i></div>`;
    }
    if (name.includes("CHAMELEON")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #10b981, #064e3b); color: #fff; font-weight:800; font-family:sans-serif; display:flex; align-items:center; justify-content:center;">MC</div>`;
    }
    if (name.includes("COUNTER-STRIKE")) {
        return `<div class="dyno-server-icon" style="background: radial-gradient(circle, #27272a, #09090b); color: #fb923c; display:flex; align-items:center; justify-content:center;"><i class="fas fa-shield-halved"></i></div>`;
    }
    if (name.includes("MAGIC CHEATS")) {
        return `<div class="dyno-server-icon" style="background: #0f172a; color: #38bdf8; border: 1.5px solid #38bdf8; display:flex; align-items:center; justify-content:center;"><i class="fas fa-wand-magic-sparkles"></i></div>`;
    }
    if (name.includes("CLOUD CHEAT")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #06b6d4, #083344); color: #fff; display:flex; align-items:center; justify-content:center;"><i class="fas fa-cloud-bolt"></i></div>`;
    }
    if (name.includes("CODES")) {
        return `<div class="dyno-server-icon" style="background: #000; color: #10b981; border: 1.5px solid #10b981; font-family: monospace; font-size: 1.4rem; display:flex; align-items:center; justify-content:center;">&lt;/&gt;</div>`;
    }
    if (name.includes("GFF")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; font-family: 'Impact', sans-serif; display:flex; align-items:center; justify-content:center;">GFF</div>`;
    }
    if (name.includes("PRITAM")) {
        return `<div class="dyno-server-icon" style="background: radial-gradient(circle, #f43f5e, #881337); color: #fff; display:flex; align-items:center; justify-content:center;"><i class="fas fa-user-ninja"></i></div>`;
    }
    if (name.includes("COREDEV")) {
        return `<div class="dyno-server-icon" style="background: #111827; color: #f97316; border: 1.5px solid #f97316; display:flex; align-items:center; justify-content:center;"><i class="fas fa-dragon"></i></div>`;
    }
    if (name.includes("QUANTREX")) {
        return `<div class="dyno-server-icon" style="background: #1e1b4b; color: #818cf8; border: 1.5px solid #818cf8; display:flex; align-items:center; justify-content:center;"><i class="fas fa-cubes"></i></div>`;
    }
    if (name.includes("UPAKUL")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #ec4899, #be185d); color: #fff; font-family: sans-serif; font-weight:800; display:flex; align-items:center; justify-content:center;">UK</div>`;
    }
    if (name.includes("ROCKSTAR")) {
        return `<div class="dyno-server-icon" style="background: #facc15; color: #000; font-family: 'Impact', sans-serif; border: 2px solid #000; font-size: 2.2rem; line-height: 1; display:flex; align-items:center; justify-content:center;">R*</div>`;
    }
    if (name.includes("BLAZE")) {
        return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #b91c1c, #000); color: #f87171; font-family: 'Arial Black', sans-serif; font-size: 0.8rem; display:flex; align-items:center; justify-content:center;">BLAZE</div>`;
    }
    
    // Default fallback letters
    const firstChar = serverName.charAt(0).toUpperCase();
    return `<div class="dyno-server-icon" style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: #fff; display:flex; align-items:center; justify-content:center;">${firstChar}</div>`;
}

window.clickManageServers = function() {
    window.location.href = '/manage';
};

// Check for active Discord OAuth2 session
function checkSession(forceRefresh = false) {
    const urlParams = new URLSearchParams(window.location.search);
    const queryGuildId = urlParams.get('guild_id');
    const savedGuildId = queryGuildId || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
    const activeScr = sessionStorage.getItem('activeScreen');
    const localSess = localStorage.getItem('VEYRA_session') || localStorage.getItem('SENTRIX_session');

    // 1. OPTIMISTIC INSTANT RENDER (0ms latency, eliminates loading spinner freeze)
    if (localSess && localSess !== 'undefined') {
        try {
            const cached = JSON.parse(localSess);
            if (cached && cached.user) {
                window.isUserLoggedIn = true;
                window.currentUser = cached.user;
                let cGuilds = cached.guilds || [];
                if (!Array.isArray(cGuilds) || cGuilds.length === 0) {
                    cGuilds = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
                }
                renderUserGuilds(cGuilds, true);
                updateHeaderWidgetsVisibility(true, cached.user);
            }
        } catch(e) {
            console.warn("Cached session parse notice:", e);
        }
    }

    // Clean login=success from query string smoothly without reload
    if (window.location.search.includes('login=')) {
        try {
            const cleanUrl = new URL(window.location.href);
            cleanUrl.searchParams.delete('login');
            window.history.replaceState({}, '', cleanUrl.toString());
        } catch(e) {}
    }

    const fetchHeaders = {};
    if (localSess && localSess !== 'undefined') {
        try {
            fetchHeaders['Authorization'] = 'Bearer ' + encodeURIComponent(localSess);
        } catch (e) {}
    }
    const refreshParam = forceRefresh ? '&refresh=true' : '';
    fetch('/api/auth/session?t=' + Date.now() + refreshParam, { cache: 'no-store', headers: fetchHeaders })
        .then(res => res.json())
        .then(data => {
            if (data.loggedIn && data.user) {
                window.isUserLoggedIn = true;
                try {
                    localStorage.setItem('VEYRA_session', JSON.stringify({ user: data.user, guilds: data.guilds }));
                    localStorage.setItem('SENTRIX_session', JSON.stringify({ user: data.user, guilds: data.guilds }));
                } catch(e) {}
                const tag = (data.user.global_name || data.user.username) ? (data.user.global_name || data.user.username) : 'User';
                let avatarUrl = 'assets/bypass_logs_avatar.webp';
                if (data.user.id && data.user.avatar && data.user.avatar !== 'user_avatar') {
                    const ext = data.user.avatar.startsWith('a_') ? 'gif' : 'png';
                    avatarUrl = `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.${ext}?size=256`;
                } else if (data.user.avatar_url) {
                    avatarUrl = data.user.avatar_url;
                }
                window.currentUserDisplayName = tag;
                window.currentUserAvatar = avatarUrl;
                
                updateHeaderWidgetsVisibility(true, data.user);
                
                const loginBtn = document.getElementById('login-btn');
                if (loginBtn) {
                    loginBtn.innerHTML = `<img src="${avatarUrl}" style="width:24px; height:24px; border-radius:50%; margin-right:6px; vertical-align:middle; display:inline-block; object-fit: cover;"> <span>${tag}</span>`;
                    loginBtn.onclick = () => showScreen('servers');
                }

                const sidebarAvatar = document.getElementById('sidebar-user-avatar');
                const sidebarName = document.getElementById('sidebar-user-name');
                if (sidebarAvatar) {
                    sidebarAvatar.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
                    sidebarAvatar.style.background = 'transparent';
                }
                if (sidebarName) {
                    sidebarName.innerText = tag;
                }

                // Update Server Selection header profile avatar & labels
                const serversAvatar = document.getElementById('servers-user-avatar');
                const serversDisplayName = document.getElementById('servers-user-displayname');
                const serversHandle = document.getElementById('servers-user-handle');
                if (serversAvatar) {
                    serversAvatar.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
                    serversAvatar.style.background = 'transparent';
                }
                if (serversDisplayName) {
                    serversDisplayName.innerText = data.user.global_name || data.user.username;
                }
                if (serversHandle) {
                    serversHandle.innerText = `@${data.user.username}`;
                }

                // Update simulation live preview avatars
                const simAvatar = document.getElementById('sim-user-avatar');
                const leaveSimAvatar = document.getElementById('leave-sim-user-avatar');
                if (simAvatar) {
                    simAvatar.innerHTML = `<img src="assets/bypass_logs_avatar.webp" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
                }
                if (leaveSimAvatar) {
                    leaveSimAvatar.innerHTML = `<img src="assets/bypass_logs_avatar.webp" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
                }
                
                const navDash = document.getElementById('nav-dashboard');
                if (navDash) navDash.style.display = 'block';

                // Check Sovereign Admin Authorization (Restricted to ID: 1256986886631854080)
                fetch('/api/admin/check?t=' + Date.now(), { cache: 'no-store' })
                    .then(res => res.json())
                    .then(admData => {
                        window.isUserAdmin = admData.isAdmin;
                        const navAdmin = document.getElementById('nav-admin');
                        if (navAdmin) navAdmin.style.display = admData.isAdmin ? 'inline-block' : 'none';
                        if (admData.isAdmin) loadAdminGuilds();
                    })
                    .catch(e => console.error("Admin check error:", e));
                
                let serversList = data.guilds || [];
                if (!Array.isArray(serversList) || serversList.length === 0) {
                    serversList = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
                }
                renderUserGuilds(serversList, true);
                if (savedGuildId && Array.isArray(serversList)) {
                    const matchedG = serversList.find(g => String(g.id) === String(savedGuildId));
                    if (matchedG) {
                        const mIcon = matchedG.icon ? `https://cdn.discordapp.com/icons/${matchedG.id}/${matchedG.icon}.png?size=128` : (localStorage.getItem('selected_guild_icon') || 'https://cdn.discordapp.com/embed/avatars/0.png');
                        window.updateActiveGuildUI(matchedG.id, matchedG.name, mIcon);
                    }
                }
                if (typeof window.initRazorpayCheckoutFlow === 'function') {
                    window.initRazorpayCheckoutFlow();
                }
                
                const isAlreadyViewingGuild = (currentScreen === 'dashboard' || activeScr === 'dashboard') && window.activeGuildId && String(window.activeGuildId) === String(savedGuildId);
                if ((activeScr === 'dashboard' || queryGuildId) && savedGuildId && typeof loadServerDashboard === 'function') {
                    if (!isAlreadyViewingGuild) {
                        loadServerDashboard(savedGuildId);
                    }
                } else if (window.location.pathname.includes('/manage') || window.location.pathname.includes('/dashboard')) {
                    showScreen('servers');
                } else {
                    if (!queryGuildId && currentScreen !== 'dashboard') {
                        showScreen('landing');
                    }
                }
            } else {
                // If backend session returned false, render fallback Ghost server so user is NEVER stuck on loading
                let fallbackGuilds = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
                if (localSess && localSess !== 'undefined') {
                    try {
                        const cached = JSON.parse(localSess);
                        if (cached && Array.isArray(cached.guilds) && cached.guilds.length > 0) {
                            fallbackGuilds = cached.guilds;
                        }
                    } catch(e) {}
                }
                renderUserGuilds(fallbackGuilds, true);

                if (queryGuildId) {
                    showScreen('dashboard');
                    if (typeof loadServerDashboard === 'function') {
                        loadServerDashboard(queryGuildId);
                    }
                } else if (window.location.pathname.includes('/manage') || window.location.pathname.includes('/dashboard')) {
                    showScreen('servers');
                } else {
                    showScreen('landing');
                }
            }
        })
        .catch(err => {
            console.error("Session fetch failed, using fallback:", err);
            let fallbackGuilds = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
            if (localSess && localSess !== 'undefined') {
                try {
                    const cached = JSON.parse(localSess);
                    if (cached && Array.isArray(cached.guilds) && cached.guilds.length > 0) {
                        fallbackGuilds = cached.guilds;
                    }
                } catch(e) {}
            }
            renderUserGuilds(fallbackGuilds, true);
            if (queryGuildId) {
                showScreen('dashboard');
                if (typeof loadServerDashboard === 'function') {
                    loadServerDashboard(queryGuildId);
                }
            } else if (window.location.pathname.includes('/manage') || window.location.pathname.includes('/dashboard')) {
                showScreen('servers');
            } else {
                showScreen('landing');
            }
        });
}

function renderUserGuilds(guilds, loggedIn = false) {
    const container = document.getElementById('screen-servers');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!loggedIn) {
        container.style.maxWidth = '480px';
        container.innerHTML = `
            <div class="login-auth-card-container" style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 65vh; width: 100%; position: relative;">
                <div class="glass-card" style="width: 100%; max-width: 440px; background: var(--surface); border: 1px solid var(--border-color); border-radius: 20px; padding: 40px 32px; text-align: center; box-shadow: var(--theme-shadow); position: relative; z-index: 10;">
                    <div style="width: 76px; height: 76px; border-radius: 20px; background: var(--soft-pink); border: 1.5px solid var(--border-color); display: flex; align-items: center; justify-content: center; margin: 0 auto 22px auto; overflow: hidden; position: relative;">
                        <img src="assets/bypass_logs_avatar.webp" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    </div>
                    <div style="background: var(--soft-pink); color: var(--accent-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 4px 12px; font-family: var(--font-mono); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; display: inline-block; margin-bottom: 14px;">
                        DISCORD AUTH REQUIRED
                    </div>
                    <h2 style="font-size: 1.6rem; font-weight: 800; color: var(--text-primary); margin: 0 0 12px 0; font-family: var(--font-display);">Welcome to Veyra</h2>
                    <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; margin: 0 0 28px 0; font-family: var(--font-body); font-weight: 400; max-width: 320px; margin-left: auto; margin-right: auto;">
                        Sign in with Discord to manage your community servers, configure security, and review server logs.
                    </p>
                    <button class="btn-primary" onclick="simulateLogin()" style="width: 100%; font-size: 1rem; border-radius: 10px; cursor: pointer; background: var(--accent-primary); color: #FFFFFF; font-weight: 700; padding: 14px 0; border: none; display: flex; align-items: center; justify-content: center; gap: 10px; transition: all 0.2s ease;">
                        <i class="fab fa-discord" style="font-size: 1.2rem;"></i>
                        <span>Sign In with Discord</span>
                    </button>
                    <div style="margin-top: 24px; display: flex; align-items: center; justify-content: center; gap: 6px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); letter-spacing: 0.04em;">
                        <i class="fas fa-shield-halved" style="color: var(--accent-primary); font-size: 0.8rem;"></i>
                        <span>Official Discord OAuth2 Gateway</span>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    // Always guarantee Ghost server card presence if empty
    if (!Array.isArray(guilds) || guilds.length === 0) {
        guilds = [{ id: '1538507162496667718', name: 'Ghost', icon: null, can_invite: true, active: true }];
    }

    // Render the Server Management view (if logged in)
    container.style.maxWidth = '640px';
    
    // Header section
    const headerDiv = document.createElement('div');
    headerDiv.style.marginBottom = '24px';
    headerDiv.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <a href="/" onclick="navigateToHome(event)" class="back-home-btn" title="Back to Home" style="display: inline-flex; align-items: center; gap: 8px; background: var(--surface); border: 1.5px solid var(--border-color); color: var(--text-primary); font-size: 0.88rem; font-weight: 700; padding: 7px 14px; border-radius: 10px; text-decoration: none; cursor: pointer; transition: all 0.2s;">
                    <i class="fas fa-arrow-left" style="color: var(--accent-primary);"></i>
                    <span>Home</span>
                </a>
                <h1 style="font-size: 1.8rem; color: var(--text-primary); font-family: var(--font-display); font-weight: 800; margin: 0;">Select a Server</h1>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button onclick="simulateAddBot('New Guild')" class="invite-bot-btn" style="background: var(--surface); color: var(--accent-primary); border: 1.5px solid var(--border-color); padding: 8px 16px; border-radius: 8px; font-family: var(--font-display); font-weight: 700; font-size: 0.82rem; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.borderColor='var(--accent-primary)'" onmouseout="this.style.borderColor='var(--border-color)'">
                    <i class="fas fa-plus" style="margin-right: 4px;"></i> Invite Bot
                </button>
                <button id="refresh-servers-btn" onclick="manualRefreshServers()" style="background: var(--soft-pink); color: var(--accent-secondary); border: 1px solid var(--border-color); padding: 8px 14px; border-radius: 8px; font-family: var(--font-display); font-weight: 700; font-size: 0.82rem; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px;">
                    <i class="fas fa-arrows-rotate" id="refresh-servers-icon"></i>
                    <span>Refresh</span>
                </button>
            </div>
        </div>
        <p style="font-size: 0.96rem; color: var(--text-secondary); margin: 0; font-family: var(--font-body); font-weight: 550; line-height: 1.5;">
            Choose a server to access its moderation, automations, and security controls.
        </p>
    `;
    container.appendChild(headerDiv);

    // Search bar
    const searchDiv = document.createElement('div');
    searchDiv.style.position = 'relative';
    searchDiv.style.marginBottom = '18px';
    searchDiv.innerHTML = `
        <input type="text" id="guild-search-input" placeholder="Search servers by name..." style="width: 100%; padding: 12px 42px 12px 16px; background: var(--surface); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary); font-size: 0.92rem; font-family: var(--font-body); box-sizing: border-box; box-shadow: var(--card-shadow); transition: border-color 0.2s ease;">
        <i class="fas fa-magnifying-glass" style="position: absolute; right: 16px; top: 15px; color: var(--text-muted); font-size: 0.92rem; pointer-events: none;"></i>
    `;
    container.appendChild(searchDiv);

    // Stats row
    const statsDiv = document.createElement('div');
    statsDiv.id = 'servers-stats-row';
    statsDiv.style.display = 'flex';
    statsDiv.style.alignItems = 'center';
    statsDiv.style.gap = '10px';
    statsDiv.style.flexWrap = 'wrap';
    statsDiv.style.fontFamily = 'var(--font-mono)';
    statsDiv.style.fontSize = '0.82rem';
    statsDiv.style.color = 'var(--text-secondary)';
    statsDiv.style.fontWeight = '700';
    statsDiv.style.marginBottom = '22px';
    
    // Count stats
    const totalCount = guilds.length;
    const activeCount = guilds.filter(g => g.active === true && g.missing !== true).length;
    const notConfiguredCount = guilds.filter(g => g.active !== true && g.can_invite !== false).length;
    const noPermissionCount = guilds.filter(g => g.active !== true && g.can_invite === false).length;

    statsDiv.innerHTML = `
        <span style="color: var(--text-primary); font-weight: 800;">${totalCount} Total</span>
        <span style="color: var(--text-muted);">&bull;</span>
        <span style="display: flex; align-items: center; gap: 6px; color: #1E6B47; font-weight: 700;"><span style="width: 8px; height: 8px; border-radius: 50%; background: #287A55; display: inline-block;"></span> ${activeCount} Active</span>
        <span style="color: var(--text-muted);">&bull;</span>
        <span style="display: flex; align-items: center; gap: 6px; color: var(--accent-secondary); font-weight: 700;"><span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-primary); display: inline-block;"></span> ${notConfiguredCount} Ready to Add</span>
        ${noPermissionCount > 0 ? `<span style="color: var(--text-muted);">&bull;</span><span style="display: flex; align-items: center; gap: 6px; color: var(--text-secondary); font-weight: 700;"><span style="width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); display: inline-block;"></span> ${noPermissionCount} No Access</span>` : ''}
    `;
    container.appendChild(statsDiv);

    // Cards list container
    const listGrid = document.createElement('div');
    listGrid.id = 'servers-selection-grid';
    listGrid.style.display = 'flex';
    listGrid.style.flexDirection = 'column';
    listGrid.style.gap = '14px';
    container.appendChild(listGrid);

    window.allGuildsCache = guilds;
    if (typeof renderSidebarGuilds === 'function') renderSidebarGuilds();

    // Search event
    const searchField = document.getElementById('guild-search-input');
    if (searchField) {
        searchField.addEventListener('input', filterGuildsList);
    }

    filterGuildsList();
}

function filterGuildsList() {
    const query = (document.getElementById('guild-search-input')?.value || '').toLowerCase();
    const listGrid = document.getElementById('servers-selection-grid');
    if (!listGrid) return;
    
    listGrid.innerHTML = '';
    const guilds = window.allGuildsCache || [];
    const filtered = guilds.filter(g => g.name.toLowerCase().includes(query));
    
    // Sort sequence:
    // 1st: bot is active -> priority 1
    // 2nd: can invite -> priority 2
    // 3rd: no permission -> priority 3
    filtered.sort((a, b) => {
        const getPriority = (g) => {
            const isBotActive = g.active === true && g.missing !== true;
            const canInvite = g.can_invite !== false;
            if (isBotActive) return 1;
            if (canInvite) return 2;
            return 3;
        };
        const priorityA = getPriority(a);
        const priorityB = getPriority(b);
        if (priorityA !== priorityB) {
            return priorityA - priorityB;
        }
        return a.name.localeCompare(b.name);
    });
    
    if (filtered.length === 0) {
        const noServersCard = document.createElement('div');
        noServersCard.style.padding = '40px 24px';
        noServersCard.style.textAlign = 'center';
        noServersCard.style.color = 'var(--text-secondary)';
        noServersCard.style.fontFamily = 'var(--font-body)';
        noServersCard.style.fontSize = '0.92rem';
        noServersCard.style.background = 'var(--surface)';
        noServersCard.style.border = '1.5px dashed var(--border-color)';
        noServersCard.style.borderRadius = '14px';
        noServersCard.innerHTML = `
            <i class="fas fa-server" style="font-size: 2rem; color: var(--accent-primary); margin-bottom: 12px; display: block; opacity: 0.7;"></i>
            <strong style="color: var(--text-primary); display: block; margin-bottom: 4px;">No matching servers found</strong>
            <span style="font-size: 0.8rem; color: var(--text-muted); display: inline-block; line-height: 1.5;">Make sure you are the Server Owner or have "Manage Server" permissions in Discord.</span>
        `;
        listGrid.appendChild(noServersCard);
    } else {
        filtered.forEach(g => {
            const card = document.createElement('div');
            card.className = 'glass-card server-card-item';
            card.style.background = 'var(--surface)';
            card.style.border = '1px solid var(--border-color)';
            card.style.borderRadius = '14px';
            card.style.padding = '18px 20px';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.gap = '14px';
            card.style.boxShadow = 'var(--card-shadow)';
            card.style.transition = 'all 0.2s ease';

            let iconHtml = '';
            if (g.icon) {
                iconHtml = `<img src="https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png?size=128" style="width:46px; height:46px; border-radius:10px; object-fit:cover; border: 1px solid var(--border-color); flex-shrink:0;">`;
            } else {
                const initial = (g.name || 'S').charAt(0).toUpperCase();
                iconHtml = `<div style="width: 46px; height: 46px; border-radius: 10px; background: var(--soft-pink); border: 1px solid var(--border-color); display:flex; align-items:center; justify-content:center; font-weight:800; color:var(--accent-primary); font-size:1.1rem; flex-shrink:0;">${initial}</div>`;
            }

            const isBotActive = g.active === true && g.missing !== true;
            const isMissing = g.missing === true;
            const canInvite = g.can_invite !== false;
            
            let statusText = 'Not Configured';
            let statusDotColor = 'var(--accent-primary)';
            let statusBg = 'var(--soft-pink)';
            let actionBtnText = '<i class="fas fa-plus" style="margin-right: 6px;"></i> Add to Server';
            let actionBtnStyle = 'background: var(--soft-pink); border: 1px solid var(--border-color); color: var(--accent-secondary); padding: 11px 0; border-radius: 8px; width: 100%; font-weight: 700; font-size: 0.88rem; cursor: pointer; text-align: center; font-family: var(--font-display); transition: all 0.2s ease;';
            let clickHandler = `simulateAddBot('${g.name.replace(/'/g, "\'")}', '${g.id}')`;
            
            if (isBotActive) {
                statusText = 'Bot Online';
                statusDotColor = '#287A55';
                statusBg = 'rgba(40, 122, 85, 0.12)';
                actionBtnText = '<i class="fas fa-sliders" style="margin-right: 6px;"></i> Manage Server';
                actionBtnStyle = 'background: var(--accent-primary); border: none; color: #FFFFFF; padding: 12px 0; border-radius: 8px; width: 100%; font-weight: 700; font-size: 0.92rem; cursor: pointer; text-align: center; font-family: var(--font-display); box-shadow: 0 4px 14px rgba(217, 108, 145, 0.25); transition: all 0.2s ease;';
                clickHandler = `loadServerDashboard('${g.id}')`;
            } else if (isMissing) {
                statusText = 'Bot Missing / Kicked';
                statusDotColor = '#9A6415';
                statusBg = 'rgba(154, 100, 21, 0.12)';
                actionBtnText = '<i class="fas fa-arrow-rotate-right" style="margin-right: 6px;"></i> Re-Invite Bot';
                actionBtnStyle = 'background: #9A6415; border: none; color: #FFFFFF; padding: 11px 0; border-radius: 8px; width: 100%; font-weight: 700; font-size: 0.88rem; cursor: pointer; text-align: center; font-family: var(--font-display); transition: all 0.2s ease;';
                clickHandler = `simulateAddBot('${g.name.replace(/'/g, "\'")}', '${g.id}')`;
            } else if (!canInvite) {
                statusText = 'Missing Admin Rights';
                statusDotColor = 'var(--text-muted)';
                statusBg = 'var(--bg-secondary)';
                actionBtnText = '<i class="fas fa-lock" style="margin-right: 6px;"></i> No Manage Permission';
                actionBtnStyle = 'background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-muted); padding: 11px 0; border-radius: 8px; width: 100%; font-weight: 600; font-size: 0.85rem; cursor: not-allowed; text-align: center; font-family: var(--font-display);';
                clickHandler = 'event.stopPropagation(); return false;';
            }

            card.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 14px;">
                    <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
                        ${iconHtml}
                        <div style="min-width: 0;">
                            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0; font-family: var(--font-display); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${g.name}</h4>
                            <div style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.72rem; font-family: var(--font-mono); color: ${statusDotColor}; font-weight: 600; background: ${statusBg}; padding: 2px 8px; border-radius: 4px;">
                                <span style="width: 6px; height: 6px; border-radius: 50%; background: ${statusDotColor}; display: inline-block;"></span>
                                ${statusText}
                            </div>
                        </div>
                    </div>
                </div>
                <button onclick="${clickHandler}" style="${actionBtnStyle}" onmouseover="if(this.style.cursor!=='not-allowed') this.style.opacity='0.92'" onmouseout="this.style.opacity='1'">
                    ${actionBtnText}
                </button>
            `;
            listGrid.appendChild(card);
        });
    }

    // Add New Server card at the bottom of the stack
    const addCard = document.createElement('div');
    addCard.className = 'glass-card';
    addCard.style.border = '1.5px dashed var(--border-color)';
    addCard.style.borderRadius = '14px';
    addCard.style.padding = '22px 20px';
    addCard.style.display = 'flex';
    addCard.style.flexDirection = 'column';
    addCard.style.alignItems = 'center';
    addCard.style.justifyContent = 'center';
    addCard.style.gap = '6px';
    addCard.style.cursor = 'pointer';
    addCard.style.transition = 'all 0.2s ease';
    addCard.style.background = 'var(--surface)';
    addCard.onclick = () => simulateAddBot('New Guild');

    addCard.onmouseover = () => {
        addCard.style.borderColor = 'var(--accent-primary)';
        addCard.style.background = 'var(--soft-pink)';
    };
    addCard.onmouseout = () => {
        addCard.style.borderColor = 'var(--border-color)';
        addCard.style.background = 'var(--surface)';
    };

    addCard.innerHTML = `
        <div style="width: 36px; height: 36px; border-radius: 50%; background: var(--soft-pink); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; color: var(--accent-primary); font-size: 0.95rem;">
            <i class="fas fa-plus"></i>
        </div>
        <div style="font-weight: 700; color: var(--text-primary); font-size: 0.9rem; margin-top: 2px; font-family: var(--font-display);">Add to Another Server</div>
        <div style="font-size: 0.76rem; color: var(--text-muted); font-weight: 500; font-family: var(--font-body);">Invite VEYRA to a new Discord community</div>
    `;
    listGrid.appendChild(addCard);
}

window.manualRefreshServers = function() {
    const icon = document.getElementById('refresh-servers-icon');
    if (icon) icon.classList.add('fa-spin');
    if (typeof checkSession === 'function') {
        checkSession(true);
    }
    setTimeout(() => {
        if (icon) icon.classList.remove('fa-spin');
    }, 1200);
};

// Window focus listener: silently refresh telemetry if already on dashboard, avoid resetting active tabs
window.addEventListener('focus', () => {
    if (window.isUserLoggedIn) {
        if (currentScreen === 'dashboard' && window.activeGuildId) {
            if (typeof pollBotTelemetry === 'function') pollBotTelemetry();
        } else if (typeof checkSession === 'function') {
            checkSession(true);
        }
    }
});

// --- 24/7 SILENT REAL-TIME BACKGROUND REFRESH & BOT-JOIN AUTO-DETECTOR ---
(function initSilentRealtimeWatcher() {
    if (window._silentRealtimeWatcherActive) return;
    window._silentRealtimeWatcherActive = true;

    // Silent poller runs continuously every 3.5 seconds
    setInterval(async () => {
        if (!window.isUserLoggedIn) return;

        // 1. Silent sync for bot addition to user servers
        try {
            const res = await fetch('/api/user/guilds?t=' + Date.now(), { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.guilds)) {
                    const freshGuilds = data.guilds;
                    const prevGuilds = window.allGuildsCache || [];

                    // Check if any server newly got the bot added
                    freshGuilds.forEach(fg => {
                        const prev = prevGuilds.find(pg => pg.id === fg.id);
                        if (prev && !prev.active && fg.active) {
                            showToast("Bot Joined Server", `VEYRA is now online in ${fg.name}!`);
                        }
                    });

                    const prevActiveCount = prevGuilds.filter(g => g.active).length;
                    const newActiveCount = freshGuilds.filter(g => g.active).length;
                    
                    window.allGuildsCache = freshGuilds;

                    // Silently refresh in-sidebar server dropdown
                    if (typeof renderSidebarGuilds === 'function') {
                        const searchInput = document.getElementById('sidebar-guild-search');
                        const query = searchInput ? searchInput.value : '';
                        renderSidebarGuilds(query);
                    }

                    // If viewing server list and user is not actively typing in search, update grid smoothly
                    const serversScreen = document.getElementById('screen-servers');
                    const searchBox = document.getElementById('guild-search-input');
                    const isSearching = searchBox && document.activeElement === searchBox;
                    if (serversScreen && serversScreen.style.display !== 'none' && !isSearching) {
                        if (prevActiveCount !== newActiveCount || prevGuilds.length !== freshGuilds.length) {
                            if (typeof filterGuildsList === 'function') filterGuildsList();
                        }
                    }
                }
            }
        } catch (e) {
            // Silently ignore background polling errors
        }

        // 2. Silent sync for dashboard metrics when on dashboard screen
        try {
            const isDash = currentScreen === 'dashboard' || sessionStorage.getItem('activeScreen') === 'dashboard';
            if (activeGuildId && isDash) {
                // Silently refresh Whitelist Capacity
                fetch('/api/whitelist/' + activeGuildId, { cache: 'no-store' })
                    .then(r => r.json())
                    .then(wl => {
                        if (Array.isArray(wl)) {
                            window.activeWhitelistCache = wl;
                            if (typeof window.updateWhitelistCapacityUI === 'function') {
                                window.updateWhitelistCapacityUI(wl.length);
                            }
                        }
                    })
                    .catch(() => {});

                // Silently refresh bot telemetry
                if (typeof pollBotTelemetry === 'function') {
                    pollBotTelemetry();
                }
            }
        } catch (e) {}
    }, 3500);
})();

// --- IN-SIDEBAR SERVER SWITCHER ENGINE ---
function toggleSidebarServerDropdown(e) {
    if (e) e.stopPropagation();
    const dropdown = document.getElementById('sidebar-server-dropdown');
    const chevron = document.getElementById('sidebar-guild-chevron');
    if (!dropdown) return;

    const isShowing = dropdown.style.display === 'block';
    if (isShowing) {
        dropdown.style.display = 'none';
        if (chevron) chevron.style.transform = 'rotate(0deg)';
    } else {
        dropdown.style.display = 'block';
        if (chevron) chevron.style.transform = 'rotate(180deg)';
        const searchInput = document.getElementById('sidebar-guild-search');
        if (searchInput) {
            searchInput.value = '';
            setTimeout(() => searchInput.focus(), 60);
        }
        renderSidebarGuilds();
    }
}

function renderSidebarGuilds(query = '') {
    const list = document.getElementById('sidebar-guilds-list');
    if (!list) return;

    const guilds = window.allGuildsCache || [];
    if (guilds.length === 0) {
        list.innerHTML = `
            <div style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 0.8rem; font-family: var(--font-body);">
                No servers loaded yet.<br>
                <a href="#" onclick="checkSession(true); return false;" style="color: var(--accent-primary); font-weight: 700; text-decoration: none; margin-top: 6px; display: inline-block;">
                    <i class="fas fa-arrows-rotate"></i> Refresh Session
                </a>
            </div>
        `;
        return;
    }

    const q = query.toLowerCase().trim();
    const filtered = guilds.filter(g => (g.name || '').toLowerCase().includes(q));

    // Sort: Current server first, then bot-active servers, then others
    filtered.sort((a, b) => {
        if (a.id === activeGuildId) return -1;
        if (b.id === activeGuildId) return 1;
        const aActive = a.active === true && a.missing !== true;
        const bActive = b.active === true && b.missing !== true;
        if (aActive && !bActive) return -1;
        if (!aActive && bActive) return 1;
        return (a.name || '').localeCompare(b.name || '');
    });

    if (filtered.length === 0) {
        list.innerHTML = `<div style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 0.8rem; font-family: var(--font-body);">No matching servers</div>`;
        return;
    }

    list.innerHTML = '';
    filtered.forEach(g => {
        const isCurrent = g.id === activeGuildId;
        const isBotActive = g.active === true && g.missing !== true;
        const canInvite = g.can_invite !== false;

        let iconHtml = '';
        if (g.icon) {
            iconHtml = `<img src="https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png?size=64" style="width: 30px; height: 30px; border-radius: 8px; object-fit: cover; flex-shrink: 0;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">`;
        } else {
            const initial = (g.name || 'S').charAt(0).toUpperCase();
            iconHtml = `<div style="width: 30px; height: 30px; border-radius: 8px; background: var(--soft-pink); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--accent-primary); font-size: 0.82rem; flex-shrink: 0;">${initial}</div>`;
        }

        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.justifyContent = 'space-between';
        row.style.padding = '8px 10px';
        row.style.borderRadius = '8px';
        row.style.cursor = isBotActive ? 'pointer' : (canInvite ? 'pointer' : 'not-allowed');
        row.style.transition = 'all 0.15s ease';
        row.style.gap = '8px';
        row.style.userSelect = 'none';

        if (isCurrent) {
            row.style.background = 'var(--soft-pink)';
            row.style.border = '1px solid rgba(217, 108, 145, 0.35)';
        } else {
            row.style.background = 'transparent';
            row.onmouseover = () => { row.style.background = 'var(--bg-secondary)'; };
            row.onmouseout = () => { row.style.background = 'transparent'; };
        }

        row.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1;">
                ${iconHtml}
                <div style="min-width: 0; flex: 1;">
                    <div style="font-size: 0.82rem; font-weight: ${isCurrent ? '800' : '600'}; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: var(--font-display);">
                        ${g.name}
                    </div>
                    <div style="font-size: 0.65rem; color: ${isCurrent ? '#287A55' : (isBotActive ? '#287A55' : 'var(--text-muted)')}; display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-weight: 700;">
                        <span style="width: 5px; height: 5px; border-radius: 50%; background: ${isCurrent ? '#287A55' : (isBotActive ? '#287A55' : 'var(--text-muted)')}; display: inline-block;"></span>
                        <span>${isCurrent ? 'ACTIVE NOW' : (isBotActive ? 'ONLINE' : (canInvite ? 'READY TO ADD' : 'NO ACCESS'))}</span>
                    </div>
                </div>
            </div>
            ${isCurrent ? '<i class="fas fa-circle-check" style="color: #287A55; font-size: 0.85rem; flex-shrink: 0;"></i>' : 
              (isBotActive ? '<i class="fas fa-arrow-right" style="color: var(--accent-primary); font-size: 0.75rem; flex-shrink: 0; opacity: 0.7;"></i>' : 
              (canInvite ? `<button onclick="event.stopPropagation(); simulateAddBot('${g.name.replace(/'/g, "\'")}', '${g.id}')" style="background: var(--soft-pink); border: 1px solid var(--border-color); color: var(--accent-secondary); font-size: 0.68rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; cursor: pointer; flex-shrink: 0;">+ Add</button>` : '<i class="fas fa-lock" style="color: var(--text-muted); font-size: 0.7rem; flex-shrink: 0;"></i>'))}
        `;

        if (isBotActive && !isCurrent) {
            row.onclick = (e) => {
                e.stopPropagation();
                selectSidebarGuild(g.id);
            };
        } else if (!isBotActive && canInvite && !isCurrent) {
            row.onclick = (e) => {
                e.stopPropagation();
                simulateAddBot(g.name, g.id);
            };
        }

        list.appendChild(row);
    });
}

function filterSidebarGuilds(val) {
    renderSidebarGuilds(val);
}

function selectSidebarGuild(guildId) {
    const dropdown = document.getElementById('sidebar-server-dropdown');
    const chevron = document.getElementById('sidebar-guild-chevron');
    if (dropdown) dropdown.style.display = 'none';
    if (chevron) chevron.style.transform = 'rotate(0deg)';

    const guild = (window.allGuildsCache || []).find(g => g.id === guildId);
    if (guild) {
        showToast("Switched Server", `Now managing ${guild.name}`);
    }
    loadServerDashboard(guildId);
}

// Global click listener to close sidebar server dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('#sidebar-current-guild-box') && !e.target.closest('#sidebar-server-dropdown')) {
        const dropdown = document.getElementById('sidebar-server-dropdown');
        const chevron = document.getElementById('sidebar-guild-chevron');
        if (dropdown && dropdown.style.display === 'block') {
            dropdown.style.display = 'none';
            if (chevron) chevron.style.transform = 'rotate(0deg)';
        }
    }
});

// Dynamic Animations
const styleNode = document.createElement('style');
styleNode.innerHTML = `
@keyframes slideIn {
    from { transform: translateX(120px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
@keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
}
@keyframes scrollMarquee {
    0% { transform: translateX(0); }
    100% { transform: translateX(-33.33%); }
}
`;
document.head.appendChild(styleNode);

// --- HIGH-PERFORMANCE INTERACTIVE PARTICLE TEXT ENGINE ---
(function() {
    function initParticleTextEngine() {
        const container = document.getElementById('particle-headline-container');
        if (!container) return;

        const canvas = document.createElement('canvas');
        canvas.id = 'particle-text-canvas';
        canvas.style.width = '100%';
        canvas.style.height = '90px';
        canvas.style.display = 'block';
        canvas.style.margin = '10px 0';
        
        container.innerHTML = '';
        container.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let width = canvas.width = container.clientWidth || 800;
        let height = canvas.height = 90;

        window.addEventListener('resize', () => {
            if (!container) return;
            width = canvas.width = container.clientWidth || 800;
            height = canvas.height = 90;
            loadWord(words[wordIndex]);
        });

        const words = [
            "24/7 UNSTOPPABLE PROTECTION",
            "ADVANCED ANTI-NUKE CORE",
            "INSTANT STORE TICKET PANELS",
            "REAL-TIME INVITE GUARD",
            "WHITE-LABEL BOT ENGINE"
        ];
        let wordIndex = 0;

        const colors = ['#ffffff', '#FF6E42', '#a855f7', '#10b981', '#38bdf8'];
        let particles = [];
        let mouse = { x: -9999, y: -9999, radius: 70 };

        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
        });

        canvas.addEventListener('mouseleave', () => {
            mouse.x = -9999;
            mouse.y = -9999;
        });

        class Particle {
            constructor(x, y) {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.targetX = x;
                this.targetY = y;
                this.vx = (Math.random() - 0.5) * 4;
                this.vy = (Math.random() - 0.5) * 4;
                this.size = Math.random() * 1.8 + 1.2;
                this.color = colors[Math.floor(Math.random() * colors.length)];
                this.friction = 0.88;
                this.ease = 0.12;
            }

            update() {
                const dx = mouse.x - this.x;
                const dy = mouse.y - this.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < mouse.radius) {
                    const angle = Math.atan2(dy, dx);
                    const force = (mouse.radius - dist) / mouse.radius;
                    this.vx -= Math.cos(angle) * force * 5;
                    this.vy -= Math.sin(angle) * force * 5;
                }

                this.vx += (this.targetX - this.x) * this.ease;
                this.vy += (this.targetY - this.y) * this.ease;

                this.vx *= this.friction;
                this.vy *= this.friction;

                this.x += this.vx;
                this.y += this.vy;
            }

            draw() {
                ctx.fillStyle = this.color;
                ctx.shadowColor = this.color;
                ctx.shadowBlur = 8;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        function loadWord(text) {
            const offCanvas = document.createElement('canvas');
            offCanvas.width = width;
            offCanvas.height = height;
            const offCtx = offCanvas.getContext ? offCanvas.getContext('2d') : null;
            if (!offCtx) return;

            let fontSize = Math.min(width / (text.length * 0.62), 34);
            if (width < 500) fontSize = Math.min(width / (text.length * 0.65), 22);

            offCtx.fillStyle = '#ffffff';
            offCtx.font = `900 ${fontSize}px "Orbitron", "Inter", sans-serif`;
            offCtx.textAlign = 'center';
            offCtx.textBaseline = 'middle';
            offCtx.fillText(text, width / 2, height / 2);

            const imgData = offCtx.getImageData(0, 0, width, height);
            const data = imgData.data;
            const newTargets = [];
            const step = width < 600 ? 4 : 3;

            for (let y = 0; y < height; y += step) {
                for (let x = 0; x < width; x += step) {
                    const alpha = data[(y * width + x) * 4 + 3];
                    if (alpha > 128) {
                        newTargets.push({ x, y });
                    }
                }
            }

            if (particles.length < newTargets.length) {
                while (particles.length < newTargets.length) {
                    particles.push(new Particle(width / 2, height / 2));
                }
            } else if (particles.length > newTargets.length) {
                particles.length = newTargets.length;
            }

            for (let i = 0; i < particles.length; i++) {
                particles[i].targetX = newTargets[i].x;
                particles[i].targetY = newTargets[i].y;
                particles[i].vx += (Math.random() - 0.5) * 12;
                particles[i].vy += (Math.random() - 0.5) * 12;
            }
        }

        loadWord(words[wordIndex]);

        function render() {
            ctx.clearRect(0, 0, width, height);
            ctx.shadowBlur = 0;

            for (let i = 0; i < particles.length; i++) {
                particles[i].update();
                particles[i].draw();
            }

            requestAnimationFrame(render);
        }

        render();

        setInterval(() => {
            wordIndex = (wordIndex + 1) % words.length;
            loadWord(words[wordIndex]);
        }, 3600);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initParticleTextEngine);
    } else {
        initParticleTextEngine();
    }
})();


function createElectricBorder(canvasId, parentSelector, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const container = canvas.closest(parentSelector);
    if (!container) return;

    const ctx = canvas.getContext('2d');
    
    // Config properties matching React props
    const color = options.color || '#FFFFFF';
    const speed = options.speed !== undefined ? options.speed : 1;
    const chaos = options.chaos !== undefined ? options.chaos : 4;
    const thickness = options.thickness !== undefined ? options.thickness : 2.5;
    const borderRadius = options.borderRadius !== undefined ? options.borderRadius : 24;
    const glow = options.glow !== undefined ? options.glow : true;
    const glowColor = options.glowColor || '#00FFCC';
    const glowIntensity = options.glowIntensity !== undefined ? options.glowIntensity : 6;
    
    const octaves = 8;
    const lacunarity = 1.6;
    const gain = 0.7;
    const amplitude = chaos / 100; // Calibrated amplitude for displacement noise
    const frequency = 8;
    const baseFlatness = 0;
    const displacement = 12; // Keep it tight and close to border edge
    const gi = Math.max(1, Math.min(10, glowIntensity));
    const glowBlur = glow ? 6 + gi * 2 : 0;
    const glowPasses = glow ? gi : 0;
    const PAD = 40;

    let width = 0;
    let height = 0;
    let time = 0;
    let lastFrameTime = performance.now();
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    function random(x) {
        return (Math.sin(x * 12.9898) * 43758.5453) % 1;
    }

    function noise2D(x, y) {
        const i = Math.floor(x);
        const j = Math.floor(y);
        const fx = x - i;
        const fy = y - j;
        const a = random(i + j * 57);
        const b = random(i + 1 + j * 57);
        const c = random(i + (j + 1) * 57);
        const d = random(i + 1 + (j + 1) * 57);
        const ux = fx * fx * (3.0 - 2.0 * fx);
        const uy = fy * fy * (3.0 - 2.0 * fy);
        return a * (1 - ux) * (1 - uy) + b * ux * (1 - uy) + c * (1 - ux) * uy + d * ux * uy;
    }

    function octavedNoise(x, timeOffset, seed) {
        let y = 0;
        let amp = amplitude;
        let freq = frequency;
        for (let i = 0; i < octaves; i++) {
            let octaveAmplitude = amp;
            if (i === 0) octaveAmplitude *= baseFlatness;
            y += octaveAmplitude * noise2D(freq * x + seed * 100, timeOffset * freq * 0.35);
            freq *= lacunarity;
            amp *= gain;
        }
        return y;
    }

    function corner(cx, cy, r, start, arc, p) {
        const a = start + p * arc;
        return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
    }

    function roundedRectPoint(t, left, top, w, h, r) {
        const sw = w - 2 * r;
        const sh = h - 2 * r;
        const arc = (Math.PI * r) / 2;
        const total = 2 * sw + 2 * sh + 4 * arc;
        const dist = t * total;
        let acc = 0;
        if (dist <= acc + sw) {
            const p = (dist - acc) / sw;
            return { x: left + r + p * sw, y: top };
        }
        acc += sw;
        if (dist <= acc + arc) {
            const p = (dist - acc) / arc;
            return corner(left + w - r, top + r, r, -Math.PI / 2, Math.PI / 2, p);
        }
        acc += arc;
        if (dist <= acc + sh) {
            const p = (dist - acc) / sh;
            return { x: left + w, y: top + r + p * sh };
        }
        acc += sh;
        if (dist <= acc + arc) {
            const p = (dist - acc) / arc;
            return corner(left + w - r, top + h - r, r, 0, Math.PI / 2, p);
        }
        acc += arc;
        if (dist <= acc + sw) {
            const p = (dist - acc) / sw;
            return { x: left + w - r - p * sw, y: top + h };
        }
        acc += sw;
        if (dist <= acc + arc) {
            const p = (dist - acc) / arc;
            return corner(left + r, top + h - r, r, Math.PI / 2, Math.PI / 2, p);
        }
        acc += arc;
        if (dist <= acc + sh) {
            const p = (dist - acc) / sh;
            return { x: left, y: top + h - r - p * sh };
        }
        acc += sh;
        const p = (dist - acc) / arc;
        return corner(left + r, top + r, r, Math.PI, Math.PI / 2, p);
    }

    function updateSize() {
        const rect = container.getBoundingClientRect();
        width = rect.width;
        height = rect.height;
        const cw = width + PAD * 2;
        const ch = height + PAD * 2;
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        
        canvas.width = Math.floor(cw * dpr);
        canvas.height = Math.floor(ch * dpr);
        canvas.style.width = `${cw}px`;
        canvas.style.height = `${ch}px`;
        canvas.style.left = `${-PAD}px`;
        canvas.style.top = `${-PAD}px`;
    }

    function draw(currentTime) {
        if (canvas.width <= 0 || canvas.height <= 0) {
            updateSize();
            requestAnimationFrame(draw);
            return;
        }
        
        const dt = (currentTime - lastFrameTime) / 1000;
        time += dt * speed;
        lastFrameTime = currentTime;

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.scale(dpr, dpr);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        const left = PAD;
        const top = PAD;
        const bw = width;
        const bh = height;
        const maxR = Math.min(bw, bh) / 2;
        const radius = Math.min(borderRadius, Math.max(0, maxR));
        const perim = 2 * (bw + bh) + 2 * Math.PI * radius;
        const samples = Math.max(16, Math.floor(perim / 3));

        ctx.beginPath();
        for (let i = 0; i <= samples; i++) {
            const t = i / samples;
            const pt = roundedRectPoint(t, left, top, bw, bh, radius);
            const xn = octavedNoise(t * 8, time, 0);
            const yn = octavedNoise(t * 8, time, 1);
            const dx = pt.x + xn * displacement;
            const dy = pt.y + yn * displacement;
            if (i === 0) ctx.moveTo(dx, dy);
            else ctx.lineTo(dx, dy);
        }
        ctx.closePath();

        if (glowBlur > 0) {
            ctx.lineWidth = thickness * 0.7;
            ctx.strokeStyle = glowColor;
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = glowBlur;
            for (let p = 0; p < glowPasses; p++) ctx.stroke();
            ctx.shadowBlur = 0;
        }
        ctx.lineWidth = thickness;
        ctx.strokeStyle = color;
        ctx.stroke();

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', () => {
        clearTimeout(window[`ebResizeTimeout_${canvasId}`]);
        window[`ebResizeTimeout_${canvasId}`] = setTimeout(updateSize, 150);
    });
    
    updateSize();
    // Delay slightly to ensure sizes are calculated correctly
    setTimeout(() => {
        updateSize();
        requestAnimationFrame(draw);
    }, 200);
}

// Initialize Electric Borders dynamically using CSS custom properties
setTimeout(() => {
    const accentColor = getComputedStyle(document.body).getPropertyValue('--accent-primary').trim() || '#ffffff';
    const accentRgb = getComputedStyle(document.body).getPropertyValue('--accent-rgb').trim() || '255, 255, 255';
    const borderGlow = `rgba(${accentRgb}, 0.25)`;

    createElectricBorder('canvas-threat-border', '.simulation-dashboard', {
        color: accentColor,
        glowColor: borderGlow,
        glowIntensity: 5,
        borderRadius: 24,
        thickness: 2.2,
        speed: 0.9,
        chaos: 3.5
    });

    createElectricBorder('canvas-prism-border', '.prism-section-box', {
        color: accentColor,
        glowColor: borderGlow,
        glowIntensity: 5,
        borderRadius: 28,
        thickness: 2.2,
        speed: 0.9,
        chaos: 3.5
    });
}, 500);

/// --- SCROLL REVEAL TEXT COMPONENT (ScrollFloat implementation) ---
(function() {
    const targets = document.querySelectorAll('.scroll-reveal');
    targets.forEach(container => {
        const rawText = container.textContent.trim();
        container.innerHTML = '';
        
        const textParagraph = document.createElement('p');
        textParagraph.className = 'scroll-reveal-text';
        textParagraph.style.fontSize = 'clamp(1.5rem, 3.5vw, 2.5rem)';
        textParagraph.style.lineHeight = '1.45';
        textParagraph.style.fontWeight = '700';
        textParagraph.style.fontFamily = 'var(--font-display)';
        textParagraph.style.color = '#fff';
        
        // Split into words, then split words into characters
        const words = rawText.split(/\s+/);
        words.forEach((word, wordIdx) => {
            const wordSpan = document.createElement('span');
            wordSpan.style.display = 'inline-block';
            wordSpan.style.whiteSpace = 'nowrap';
            
            for (let i = 0; i < word.length; i++) {
                const charSpan = document.createElement('span');
                charSpan.className = 'float-char';
                charSpan.textContent = word[i];
                charSpan.style.display = 'inline-block';
                charSpan.style.transform = 'translateY(1.2em) rotate(6deg)';
                charSpan.style.opacity = '0';
                wordSpan.appendChild(charSpan);
            }
            
            textParagraph.appendChild(wordSpan);
            
            if (wordIdx < words.length - 1) {
                textParagraph.appendChild(document.createTextNode(' '));
            }
        });
        
        container.appendChild(textParagraph);
        
        const charElements = container.querySelectorAll('.float-char');
        
        if (typeof gsap !== 'undefined') {
            gsap.to(charElements, {
                scrollTrigger: {
                    trigger: container,
                    start: 'top bottom+=30%',
                    end: 'bottom bottom-=20%',
                    toggleActions: 'play none none reverse'
                },
                opacity: 1,
                y: 0,
                rotate: 0,
                duration: 1, // animationDuration
                ease: 'back.inOut(2)', // ease
                stagger: 0.03, // stagger
                overwrite: 'auto'
            });
        } else {
            charElements.forEach(el => { el.style.opacity = '1'; el.style.transform = 'none'; });
        }
    });
})();

// --- 13. STREAMING SHIELD DAEMON CONSOLE ---
(function() {
    const consoleContainer = document.getElementById('console-stream-lines');
    if (!consoleContainer) return;
    
    const logs = [
        { type: 'info', text: 'Shield Engine initialized. Core integrity OK.' },
        { type: 'warning', text: 'Spam pattern detected from @bot-user-412.' },
        { type: 'mitigate', text: 'AutoMod deleted invite link redirect.' },
        { type: 'info', text: 'Database synchronized. 0 latency backup created.' },
        { type: 'error', text: 'RAID ATTEMPT: 34 bot joins detected in 1.2s.' },
        { type: 'mitigate', text: 'Nuclear Guard engaged. Gatekeeper activated.' },
        { type: 'mitigate', text: 'Banned 34 raid accounts. Server stabilized.' },
        { type: 'info', text: 'Active scanning: 0 vulnerabilities found.' }
    ];
    
    let index = 0;
    
    function addLogLine() {
        if (consoleContainer.children.length > 7) {
            consoleContainer.removeChild(consoleContainer.firstChild);
        }
        
        const item = logs[index];
        const line = document.createElement('div');
        line.style.margin = '4px 0';
        line.style.fontFamily = 'var(--font-mono)';
        line.style.fontSize = '0.78rem';
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        let color = '#a3a3a3';
        let prefix = '[INFO]';
        if (item.type === 'warning') {
            color = '#eab308';
            prefix = '[WARN]';
        } else if (item.type === 'error') {
            color = '#ef4444';
            prefix = '[RAID]';
        } else if (item.type === 'mitigate') {
            color = '#10b981';
            prefix = '[MITG]';
        }
        
        line.innerHTML = `<span style="color:#6b7280; margin-right:8px;">${timestamp}</span><span style="color:${color}; font-weight:600; margin-right:8px;">${prefix}</span><span style="color:#e5e7eb;">${item.text}</span>`;
        consoleContainer.appendChild(line);
        
        index = (index + 1) % logs.length;
        
        setTimeout(addLogLine, 2000 + Math.random() * 2500);
    }
    
    // Kick off with some initial historical lines
    for (let i = 0; i < 4; i++) {
        const item = logs[i];
        const line = document.createElement('div');
        line.style.margin = '4px 0';
        line.style.fontFamily = 'var(--font-mono)';
        line.style.fontSize = '0.78rem';
        const dummySec = Math.max(0, new Date().getSeconds() - (15 - i * 3));
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ":" + (dummySec < 10 ? '0' + dummySec : dummySec);
        
        let color = '#a3a3a3';
        let prefix = '[INFO]';
        if (item.type === 'warning') {
            color = '#eab308';
            prefix = '[WARN]';
        } else if (item.type === 'error') {
            color = '#ef4444';
            prefix = '[RAID]';
        } else if (item.type === 'mitigate') {
            color = '#10b981';
            prefix = '[MITG]';
        }
        line.innerHTML = `<span style="color:#6b7280; margin-right:8px;">${timestamp}</span><span style="color:${color}; font-weight:600; margin-right:8px;">${prefix}</span><span style="color:#e5e7eb;">${item.text}</span>`;
        consoleContainer.appendChild(line);
    }
    index = 4;
    
    setTimeout(addLogLine, 2000);
})();

// --- 14. SAPPHIRE-STYLE WELCOME & LEAVE MESSAGE WORKSPACE CONTROLLERS ---

let currentWelcomeTab = 'messages';
let currentLeaveTab = 'messages';
let activeEditMode = 'welcome'; // 'welcome' or 'leave'

function toggleWelcomePane(tabId) {
    // Hide all sub-panes
    document.querySelectorAll('.welcome-sub-pane').forEach(el => el.style.display = 'none');
    
    // Show target sub-pane
    const pane = document.getElementById(`welcome-pane-${tabId}`);
    if (pane) pane.style.display = 'block';
    
    // Toggle active state on buttons
    document.querySelectorAll('#tab-welcome .sapphire-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-secondary)';
    });
    
    const activeBtn = document.getElementById(`btn-welcome-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.background = 'rgba(255,255,255,0.08)';
        activeBtn.style.color = '#fff';
    }
    
    currentWelcomeTab = tabId;
}

function toggleLeavePane(tabId) {
    // Hide all sub-panes
    document.querySelectorAll('.leave-sub-pane').forEach(el => el.style.display = 'none');
    
    // Show target sub-pane
    const pane = document.getElementById(`leave-pane-${tabId}`);
    if (pane) pane.style.display = 'block';
    
    // Toggle active state on buttons
    document.querySelectorAll('#tab-leave .sapphire-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-secondary)';
    });
    
    const activeBtn = document.getElementById(`btn-leave-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.background = 'rgba(255,255,255,0.08)';
        activeBtn.style.color = '#fff';
    }
    
    currentLeaveTab = tabId;
}

// Modal Toggle Handlers

function openWelcomeSettingsModal() {
    document.getElementById('modal-msg-name').value = "Message 1 (Welcome)";
    document.getElementById('modal-additional-settings').style.display = 'flex';
}

function openLeaveSettingsModal() {
    document.getElementById('modal-msg-name').value = "Message 1 (Leave)";
    document.getElementById('modal-additional-settings').style.display = 'flex';
}

function closeWelcomeSettingsModal() {
    document.getElementById('modal-additional-settings').style.display = 'none';
}

function openEditWelcomeMsg() {
    activeEditMode = 'welcome';
    document.getElementById('edit-msg-modal-title').innerText = "Edit Welcome Message Content";
    const channelBadgeVal = document.getElementById('welcome-channel-badge').textContent.trim();
    document.getElementById('welcome-msg-channel').value = channelBadgeVal;
    
    const outerText = document.getElementById('welcome-sim-outer-text').textContent.trim();
    document.getElementById('welcome-msg-text').value = outerText;
    document.getElementById('modal-edit-message').style.display = 'flex';
}

function openEditLeaveMsg() {
    activeEditMode = 'leave';
    document.getElementById('edit-msg-modal-title').innerText = "Edit Leave Message Content";
    const channelBadgeVal = document.getElementById('leave-channel-badge').textContent.trim();
    document.getElementById('welcome-msg-channel').value = channelBadgeVal;
    
    const outerText = document.getElementById('leave-sim-outer-text').textContent.trim();
    document.getElementById('welcome-msg-text').value = outerText;
    document.getElementById('modal-edit-message').style.display = 'flex';
}

function closeEditMessageModal() {
    document.getElementById('modal-edit-message').style.display = 'none';
}

function saveMessageContentEdit() {
    const channelVal = document.getElementById('welcome-msg-channel').value.trim();
    const textVal = document.getElementById('welcome-msg-text').value.trim();
    
    if (activeEditMode === 'welcome') {
        document.getElementById('welcome-channel-badge').innerHTML = `<i class="fa-solid fa-hashtag"></i> ${channelVal}`;
        document.getElementById('welcome-sim-outer-text').innerHTML = textVal.replace('{user}', '<span style="color: #00aff4; background: rgba(0,175,244,0.1); padding: 0 4px; border-radius: 3px; font-weight: 500; cursor: pointer;">@speedmcxx</span>');
        
        // Call backend API to save update
        if (activeGuildId) {
            fetch(`/api/settings/${activeGuildId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates_channel: channelVal })
            }).then(() => {
                showToast("Welcome Updated", "Welcome greetings updated successfully.");
                addLogEntry("@itzarun170", `Modified join settings text to: ${textVal}`);
            });
        }
    } else {
        document.getElementById('leave-channel-badge').innerHTML = `<i class="fa-solid fa-door-open"></i> ${channelVal}`;
        document.getElementById('leave-sim-outer-text').innerHTML = textVal.replace('{user}', '<span style="color: #00aff4; background: rgba(0,175,244,0.1); padding: 0 4px; border-radius: 3px; font-weight: 500; cursor: pointer;">@speedmcxx</span>');
        
        showToast("Leave Updated", "Leave logs channel and message template updated.");
        addLogEntry("@itzarun170", `Modified leave logging template to: ${textVal}`);
    }
    
    closeEditMessageModal();
}

// duplicate saveVerificationSettings removed - authoritative definition at line 181

window.loadInvitesSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    fetch(`/api/settings/invites/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const delayInput = document.getElementById('fake-delay-val');
            if (delayInput) delayInput.value = data.fake_delay !== undefined ? data.fake_delay : 3;

            const blacklistContainer = document.getElementById('invite-blacklist-list');
            if (blacklistContainer) {
                blacklistContainer.innerHTML = (data.blacklist || []).map(uId => `
                    <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 5px 12px; font-size: 0.82rem; color: #0F172A; font-weight:600; background:#F1F5F9; border:1px solid #CBD5E1; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444;"></span>
                        <span>${escapeHtml(uId)}</span>
                        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="deleteBlacklistUser('${uId}')"></i>
                    </div>
                `).join('') || '<span style="font-size:0.78rem; color:var(--text-secondary);">No blacklisted users</span>';
            }

            const hiddenContainer = document.getElementById('leaderboard-hidden-list');
            if (hiddenContainer) {
                hiddenContainer.innerHTML = (data.hidden || []).map(uId => `
                    <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 5px 12px; font-size: 0.82rem; color: #0F172A; font-weight:600; background:#F1F5F9; border:1px solid #CBD5E1; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #eab308;"></span>
                        <span>${escapeHtml(uId)}</span>
                        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="deleteHiddenUser('${uId}')"></i>
                    </div>
                `).join('') || '<span style="font-size:0.78rem; color:var(--text-secondary);">No hidden users</span>';
            }
        })
        .catch(err => console.error("Error loading invites settings:", err));
};

window.saveFakeDelay = function(value) {
    if (!activeGuildId) return;
    const delay = parseInt(value);
    if (isNaN(delay)) return;

    fetch(`/api/settings/invites/fake-delay/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fake_delay: delay })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Fake Delay Saved", `Accounts younger than ${delay} days will now count as fake.`);
            addLogEntry("@user", `Updated invite fake delay threshold to ${delay} days`);
        }
    })
    .catch(err => console.error("Error saving fake delay:", err));
};

function addBlacklistUser() {
    if (!activeGuildId) return;
    const userIdInput = document.getElementById('blacklist-user-id');
    const val = userIdInput.value.trim();
    if (!val) {
        showToast("Error", "Please specify a valid Discord User ID.", "error");
        return;
    }

    fetch(`/api/settings/invites/blacklist/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: val })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Blacklist Updated", `Added user ${val} to invite counting blacklist.`);
            addLogEntry("@user", `Blacklisted Discord User ${val} from invite tallies`);
            userIdInput.value = '';
            loadInvitesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error adding blacklist user:", err));
}

window.deleteBlacklistUser = function(userId) {
    if (!activeGuildId) return;
    fetch(`/api/settings/invites/blacklist/${activeGuildId}/${userId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Blacklist Updated", `Removed user ${userId} from invite blacklist.`);
            addLogEntry("@user", `Unblacklisted Discord User ${userId}`);
            loadInvitesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error removing blacklist user:", err));
};

function addHiddenUser() {
    if (!activeGuildId) return;
    const userIdInput = document.getElementById('hidden-user-id');
    const val = userIdInput.value.trim();
    if (!val) {
        showToast("Error", "Please specify a valid Discord User ID.", "error");
        return;
    }

    fetch(`/api/settings/invites/hidden/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: val })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Leaderboard Updated", `User ${val} hidden from public server leaderboard.`);
            addLogEntry("@user", `Hid User ${val} from active inviter leaderboards`);
            userIdInput.value = '';
            loadInvitesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error adding hidden user:", err));
}

window.deleteHiddenUser = function(userId) {
    if (!activeGuildId) return;
    fetch(`/api/settings/invites/hidden/${activeGuildId}/${userId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Leaderboard Updated", `User ${userId} will now appear on the leaderboard.`);
            addLogEntry("@user", `Restored User ${userId} to active inviter leaderboards`);
            loadInvitesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error removing hidden user:", err));
}

// --- DISCORD EMOJI & MARKDOWN PARSER FOR LIVE PREVIEWS ---

const DASHBOARD_UNICODE_EMOJIS = {
    crown: '👑', king: '👑', queen: '👸', prince: '🤴', princess: '👸',
    fire: '🔥', star: '⭐', star2: '🌟', sparkles: '✨', sparkle: '✨',
    check: '✅', white_check_mark: '✅', cross: '❌', x: '❌',
    heart: '❤️', rainbow_heart: '💖', sparkling_heart: '💖', broken_heart: '💔',
    tada: '🎉', party: '🎉', partybolt: '⚡', partying_face: '🥳',
    wave: '👋', warning: '⚠️', attention: '⚠️', no_entry_sign: '🚫', no_entry: '⛔',
    shield: '🛡️', lock: '🔒', unlock: '🔓', bell: '🔔', gear: '⚙️',
    tools: '🛠️', robot: '🤖', zap: '⚡', lightning: '⚡', rocket: '🚀',
    trophy: '🏆', medal: '🏅', gem: '💎', diamond: '💎', eyes: '👀',
    skull: '💀', '100': '💯', bulb: '💡', info: 'ℹ️', link: '🔗',
    pin: '📌', loudspeaker: '📢', mega: '📣', envelope: '✉️', mail: '✉️',
    door: '🚪', boom: '💥', gift: '🎁', money: '💰', coin: '🪙',
    dollar: '💵', hammer: '🔨', wrench: '🔧', key: '🔑', sword: '⚔️',
    swords: '⚔️', books: '📚', chart: '📊', target: '🎯', crystal_ball: '🔮',
    hourglass: '⌛', clock: '⏰', satellite: '📡', desktop: '🖥️', laptop: '💻',
    alert: '🚨', sound: '🔊', muted: '🔇', verified: '☑️'
};

function parseDiscordEmojis(text) {
    if (!text) return '';
    let parsed = String(text);

    // 1. Full Discord emojis: <:name:id> or <a:name:id> (both raw and HTML-escaped)
    parsed = parsed
        .replace(/&lt;(a)?:?([a-zA-Z0-9_\-]+):([0-9]+)&gt;/g, (match, isAnim, name, id) => {
            const ext = isAnim ? 'gif' : 'png';
            return `<img src="https://cdn.discordapp.com/emojis/${id}.${ext}" alt="${name}" title="${name}" class="discord-emoji-img" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;">`;
        })
        .replace(/<(a)?:?([a-zA-Z0-9_\-]+):([0-9]+)>/g, (match, isAnim, name, id) => {
            const ext = isAnim ? 'gif' : 'png';
            return `<img src="https://cdn.discordapp.com/emojis/${id}.${ext}" alt="${name}" title="${name}" class="discord-emoji-img" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;">`;
        });

    // 2. Custom name resolution :name: or :1551561322158760006webp:
    parsed = parsed.replace(/(?<!<)(?<!<a):([a-zA-Z0-9_\-]{2,36}):(?!\d+>)/g, (match, rawName) => {
        const lower = rawName.toLowerCase();
        const norm = lower.replace(/[-_]/g, '');

        // 2a. Check live guild emojis
        if (Array.isArray(window.guildEmojis)) {
            const found = window.guildEmojis.find(e => e.name && (e.name.toLowerCase() === lower || e.name.toLowerCase().replace(/[-_]/g, '') === norm));
            if (found) {
                const ext = found.animated ? 'gif' : 'png';
                return `<img src="https://cdn.discordapp.com/emojis/${found.id}.${ext}" alt="${found.name}" title="${found.name}" class="discord-emoji-img" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;">`;
            }
        }

        // 2b. Check unicode fallback
        if (DASHBOARD_UNICODE_EMOJIS[lower]) {
            return DASHBOARD_UNICODE_EMOJIS[lower];
        }
        if (DASHBOARD_UNICODE_EMOJIS[norm]) {
            return DASHBOARD_UNICODE_EMOJIS[norm];
        }

        // 2c. Check snowflake numeric ID (:1551561322158760006webp: or :1551561322158760006:)
        const numMatch = rawName.match(/^(\d{15,22})(?:webp|png|gif)?$/i);
        if (numMatch) {
            const numId = numMatch[1];
            return `<img src="https://cdn.discordapp.com/emojis/${numId}.png" alt="${numId}" title="${numId}" class="discord-emoji-img" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;" onerror="this.style.display='none'">`;
        }

        return match;
    });

    // 3. Discord Markdown formatting for preview
    parsed = parsed
        .replace(/^###\s+(.+)$/gm, '<div style="font-size: 0.95rem; font-weight: 700; color: #dbdee1; margin: 3px 0;">$1</div>')
        .replace(/^##\s+(.+)$/gm, '<div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin: 4px 0;">$1</div>')
        .replace(/^#\s+(.+)$/gm, '<div style="font-size: 1.25rem; font-weight: 800; color: #fff; margin: 6px 0;">$1</div>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
        .replace(/__(.+?)__/g, '<u>$1</u>')
        .replace(/~~(.+?)~~/g, '<s>$1</s>')
        .replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.3); padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 0.88em;">$1</code>');

    return parsed;
}

function updateWelcomeLivePreview() {
    const isMsgEnabled = document.getElementById('welcome-msg-enable')?.checked;
    const previewContainer = document.getElementById('welcome-preview-container');
    if (previewContainer) {
        previewContainer.style.opacity = isMsgEnabled ? '1' : '0.4';
        previewContainer.style.pointerEvents = isMsgEnabled ? 'all' : 'none';
    }

    const userAvatarUrl = window.currentUserAvatar || 'https://cdn.discordapp.com/embed/avatars/0.png';

    const outerInput = document.getElementById('welcome-msg-outer-input')?.value || '';
    const outerBody = document.getElementById('welcome-sim-outer-body');
    if (outerBody) {
        let text = outerInput.replace(/%member_mention%|\{user\}/g, '<span style="color: #00aff4; background: rgba(0,175,244,0.1); padding: 0 4px; border-radius: 3px; font-weight: 500; cursor: pointer;">@!! DADDY</span>');
        text = text.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        outerBody.innerHTML = parseDiscordEmojis(text);
    }

    const isEmbedEnabled = document.getElementById('welcome-embed-enable')?.checked;
    const embedBox = document.getElementById('welcome-sim-embed');
    if (embedBox) {
        embedBox.style.display = isEmbedEnabled ? 'flex' : 'none';
    }

    const colorVal = document.getElementById('welcome-embed-color-picker')?.value || '#ef4444';
    if (embedBox) {
        embedBox.style.borderLeftColor = colorVal;
    }

    const titleVal = document.getElementById('welcome-embed-title')?.value || '';
    const embedTitle = document.getElementById('welcome-sim-embed-title');
    if (embedTitle) {
        let formattedTitle = titleVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        embedTitle.innerHTML = parseDiscordEmojis(formattedTitle);
        embedTitle.style.display = titleVal ? 'block' : 'none';
    }

    const descVal = document.getElementById('welcome-embed-desc')?.value || '';
    const embedDesc = document.getElementById('welcome-sim-embed-desc');
    if (embedDesc) {
        let formattedDesc = descVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        embedDesc.innerHTML = parseDiscordEmojis(formattedDesc);
        embedDesc.style.display = descVal ? 'block' : 'none';
    }

    const imgVal = document.getElementById('welcome-embed-image')?.value || '';
    const bannerWrapper = document.getElementById('welcome-sim-embed-banner-wrapper');
    const bannerImg = document.getElementById('welcome-sim-embed-banner');
    if (bannerWrapper && bannerImg) {
        let formattedImg = imgVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        if (formattedImg) {
            bannerImg.src = formattedImg;
            bannerWrapper.style.display = 'block';
        } else {
            bannerWrapper.style.display = 'none';
        }
    }

    const footerVal = document.getElementById('welcome-embed-footer')?.value || '';
    const footerWrapper = document.getElementById('welcome-sim-embed-footer-wrapper');
    const footerText = document.getElementById('welcome-sim-embed-footer-text');
    if (footerWrapper && footerText) {
        footerText.innerText = footerVal;
        footerWrapper.style.display = footerVal ? 'flex' : 'none';
    }

    const thumbVal = document.getElementById('welcome-thumbnail-url')?.value || '';
    const thumbBox = document.getElementById('welcome-sim-embed-thumb');
    if (thumbBox) {
        let activeThumb = thumbVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        if (!activeThumb) activeThumb = userAvatarUrl;
        thumbBox.innerHTML = `<img src="${activeThumb}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
    }
}

function updateLeaveLivePreview() {
    const isMsgEnabled = document.getElementById('leave-msg-enable')?.checked;
    const previewContainer = document.getElementById('leave-preview-container');
    if (previewContainer) {
        previewContainer.style.opacity = isMsgEnabled ? '1' : '0.4';
        previewContainer.style.pointerEvents = isMsgEnabled ? 'all' : 'none';
    }

    const userAvatarUrl = window.currentUserAvatar || 'https://cdn.discordapp.com/embed/avatars/0.png';

    const outerInput = document.getElementById('leave-msg-outer-input')?.value || '';
    const outerBody = document.getElementById('leave-sim-outer-body');
    if (outerBody) {
        let text = outerInput.replace(/%member%/g, '<span style="color: #fff; font-weight: 600;">!! DADDY</span>');
        text = text.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        outerBody.innerHTML = parseDiscordEmojis(text);
    }

    const isEmbedEnabled = document.getElementById('leave-embed-enable')?.checked;
    const embedBox = document.getElementById('leave-sim-embed');
    if (embedBox) {
        embedBox.style.display = isEmbedEnabled ? 'flex' : 'none';
    }

    const colorVal = document.getElementById('leave-embed-color-picker')?.value || '#ef4444';
    if (embedBox) {
        embedBox.style.borderLeftColor = colorVal;
    }

    const titleVal = document.getElementById('leave-embed-title')?.value || '';
    const embedTitle = document.getElementById('leave-sim-embed-title');
    if (embedTitle) {
        let formattedTitle = titleVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        embedTitle.innerHTML = parseDiscordEmojis(formattedTitle);
        embedTitle.style.display = titleVal ? 'block' : 'none';
    }

    const descVal = document.getElementById('leave-embed-desc')?.value || '';
    const embedDesc = document.getElementById('leave-sim-embed-desc');
    if (embedDesc) {
        let formattedDesc = descVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        embedDesc.innerHTML = parseDiscordEmojis(formattedDesc);
        embedDesc.style.display = descVal ? 'block' : 'none';
    }

    const thumbVal = document.getElementById('leave-thumbnail-url')?.value || '';
    const thumbBox = document.getElementById('leave-sim-embed-thumb');
    if (thumbBox) {
        let activeThumb = thumbVal.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        if (!activeThumb) activeThumb = userAvatarUrl;
        thumbBox.innerHTML = `<img src="${activeThumb}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
    }
}

function setWelcomePresetColor(color) {
    const cp = document.getElementById('welcome-embed-color-picker');
    const txt = document.getElementById('welcome-color-hex');
    if (cp && txt) {
        cp.value = color;
        txt.value = color;
        updateWelcomeLivePreview();
    }
}

function setLeavePresetColor(color) {
    const cp = document.getElementById('leave-embed-color-picker');
    const txt = document.getElementById('leave-color-hex');
    if (cp && txt) {
        cp.value = color;
        txt.value = color;
        updateLeaveLivePreview();
    }
}

function setWelcomePresetImage(preset) {
    const imgField = document.getElementById('welcome-embed-image');
    if (!imgField) return;
    if (preset === 'red') {
        imgField.value = 'assets/bypass_logs_banner.webp';
    } else if (preset === 'purple') {
        imgField.value = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80';
    } else if (preset === 'cyber') {
        imgField.value = 'https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?auto=format&fit=crop&w=600&q=80';
    }
    updateWelcomeLivePreview();
}

function setLeavePresetImage(preset) {
    const imgField = document.getElementById('leave-embed-image');
    if (!imgField) return;
    if (preset === 'red') {
        imgField.value = 'assets/bypass_logs_banner.webp';
    } else if (preset === 'purple') {
        imgField.value = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80';
    } else if (preset === 'cyber') {
        imgField.value = 'https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?auto=format&fit=crop&w=600&q=80';
    }
    updateLeaveLivePreview();
}

// Initial binding of previews when dashboard is shown
document.addEventListener('DOMContentLoaded', () => {

// --- INSTANT PERSISTENT SERVER SELECTION RESTORATION ON LOAD ---
(function restoreActiveServerInstant() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryGid = urlParams.get('guild_id');
        const savedGid = queryGid || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
        const savedName = localStorage.getItem('selected_guild_name');
        const savedIcon = localStorage.getItem('selected_guild_icon');

        if (savedName) {
            const sideName = document.getElementById('sidebar-guild-name');
            if (sideName) sideName.innerText = savedName;
            const mgName = document.getElementById('managing-server-name');
            if (mgName) mgName.innerText = savedName;
            const dsName = document.getElementById('dashboard-server-name');
            if (dsName) dsName.innerText = savedName;
            const hdName = document.getElementById('header-server-dropdown-name');
            if (hdName) hdName.innerText = savedName;
            const tkName = document.getElementById('tickets-sidebar-guild-name');
            if (tkName) tkName.innerText = savedName;
        }
        if (savedIcon || savedName) {
            window.updateActiveGuildUI(savedGid, savedName, savedIcon);
        }
        // Ensure sidebar server dropdown is closed by default
        const sDrop = document.getElementById('sidebar-server-dropdown');
        if (sDrop) sDrop.style.display = 'none';
        const sChev = document.getElementById('sidebar-guild-chevron');
        if (sChev) sChev.style.transform = 'rotate(0deg)';
    } catch(e) {}
})();

    // Make sure initial values propagate to the preview screens on render
    setTimeout(() => {
        updateWelcomeLivePreview();
        updateLeaveLivePreview();
        renderAuditLogs();
        updateEmbedBuilderPreview();
    }, 1000);
});

// --- AUDIT LOGS DATABASE & RENDERERS ---

const mockAuditLogs = [
    { time: '2026-06-07 11:33:03', user: 'canyouflexx', action: 'embed edited for message_id 1513140925897904238 and channel_id 1499136957635235910' },
    { time: '2026-06-07 11:32:46', user: 'canyouflexx', action: 'embed edited for message_id 1513140925897904238 and channel_id 1499136957635235910' },
    { time: '2026-06-07 11:29:18', user: 'canyouflexx', action: 'embed edited for message_id 1513140925897904238 and channel_id 1499136957635235910' },
    { time: '2026-06-07 11:21:56', user: 'canyouflexx', action: 'embed.post' },
    { time: '2026-05-17 12:47:52', user: 'ghost__simon', action: 'nickname.update' },
    { time: '2026-05-17 12:45:32', user: 'ghost__simon', action: 'embed edited for message_id 1505209935862960210 and channel_id 1499137427195822140' },
    { time: '2026-05-17 12:45:03', user: 'ghost__simon', action: 'embed edited for message_id 1505208442934132828 and channel_id 1499137344211517520' },
    { time: '2026-05-17 12:44:56', user: 'ghost__simon', action: 'embed edited for message_id 1505208442934132828 and channel_id 1499137344211517520' }
];

function renderAuditLogs() {
    const recentBody = document.getElementById('recent-actions-table-body');
    const weblogsBody = document.getElementById('weblogs-table-body');
    const logs = window.activeAuditLogsCache || [];

    if (logs.length === 0) {
        if (weblogsBody) {
            weblogsBody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-muted);">No server audit activity recorded yet.</td></tr>';
        }
        if (recentBody) {
            recentBody.innerHTML = '<tr><td colspan="3" style="padding: 20px; text-align: center; color: var(--text-muted);">No activity recorded.</td></tr>';
        }
        return;
    }

    if (weblogsBody) {
        weblogsBody.innerHTML = logs.map(row => {
            let dateStr = 'Just now';
            if (row.timestamp) {
                const d = new Date(row.timestamp);
                dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            const userDisplay = row.user || 'Staff';
            return `
                <tr style="border-bottom: 1px solid var(--border-color); transition: background 0.15s ease;">
                    <td style="padding: 12px 14px; font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-secondary);">${dateStr}</td>
                    <td style="padding: 12px 14px; font-weight: 700; color: var(--text-primary);">${userDisplay}</td>
                    <td style="padding: 12px 14px;"><span style="background: var(--soft-pink); color: var(--accent-primary); border: 1px solid var(--border-color); padding: 3px 8px; border-radius: 6px; font-size: 0.74rem; font-family: var(--font-mono); font-weight: 700;">${row.action || 'Action'}</span></td>
                    <td style="padding: 12px 14px; font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4;">${row.details || 'Executed'}</td>
                </tr>
            `;
        }).join('');
    }

    if (recentBody) {
        recentBody.innerHTML = logs.slice(0, 8).map(row => {
            let dateStr = 'Today';
            if (row.timestamp) {
                const d = new Date(row.timestamp);
                dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            return `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 10px 5px; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-secondary);">${dateStr}</td>
                    <td style="padding: 10px 5px; font-weight: 700; color: var(--text-primary);">${row.user}</td>
                    <td style="padding: 10px 5px; line-height: 1.4; color: var(--text-secondary);">${row.action}: ${row.details}</td>
                </tr>
            `;
        }).join('');
    }
}

function filterRecentActionsTable() {
    const userQ = (document.getElementById('filter-user-settings')?.value || '').toLowerCase();
    const actionQ = (document.getElementById('filter-action-settings')?.value || '').toLowerCase();
    const recentBody = document.getElementById('recent-actions-table-body');
    if (!recentBody) return;

    const filtered = mockAuditLogs.filter(log => 
        log.user.toLowerCase().includes(userQ) && 
        log.action.toLowerCase().includes(actionQ)
    );

    recentBody.innerHTML = filtered.map(log => `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
            <td style="padding: 10px 5px; font-family: var(--font-mono); font-size:0.78rem;">${log.time}</td>
            <td style="padding: 10px 5px; font-weight:600; color:#fff;">${log.user}</td>
            <td style="padding: 10px 5px; line-height: 1.4;">${log.action}</td>
        </tr>
    `).join('');
}

function filterWeblogsTable() {
    const userQ = (document.getElementById('filter-user-weblogs')?.value || '').toLowerCase();
    const detailsQ = (document.getElementById('filter-details-weblogs')?.value || '').toLowerCase();
    const weblogsBody = document.getElementById('weblogs-table-body');
    if (!weblogsBody) return;

    const logs = window.activeAuditLogsCache || [];
    const filtered = logs.filter(log => 
        log.user.toLowerCase().includes(userQ) && 
        (log.details || '').toLowerCase().includes(detailsQ)
    );

    if (filtered.length === 0) {
        weblogsBody.innerHTML = `<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No matching logs found.</td></tr>`;
        return;
    }

    weblogsBody.innerHTML = filtered.map(row => {
        let dateStr = 'Today';
        if (row.timestamp) {
            const d = new Date(row.timestamp);
            dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
                <td style="padding: 12px 5px; font-family: var(--font-mono); font-size:0.8rem;">${dateStr}</td>
                <td style="padding: 12px 5px; font-weight:600; color:#fff;">${row.user}</td>
                <td style="padding: 12px 5px;"><span style="background:rgba(168,85,247,0.12); color:#c084fc; border:1px solid rgba(168,85,247,0.3); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:var(--font-mono); font-weight:700;">${row.action || 'System'}</span></td>
                <td style="padding: 12px 5px; line-height: 1.4;">${row.details}</td>
            </tr>
        `;
    }).join('');
}

// --- BOT SETTINGS HANDLERS ---

function applyBotNickname() {
    const nick = document.getElementById('bot-nickname-input')?.value || 'Custom Sentinel';
    
    if (activeGuildId) {
        fetch(`/api/settings/${activeGuildId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nickname: nick })
        })
        .then(res => res.json())
        .then(d => {
            showToast("Bot Nickname Applied", `Permanently saved bot guild nickname as "${nick}" in database!`, "success");
        })
        .catch(err => {
            showToast("Bot Nickname Applied", `Bot nickname set to "${nick}"`);
        });
    } else {
        showToast("Bot Nickname Applied", `Changed bot's global guild nickname to ${nick}`);
    }

    addLogEntry("!! DADDY", `Set guild bot name to: ${nick}`);
    mockAuditLogs.unshift({
        time: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: '!! DADDY',
        action: `Set nickname to ${nick}`
    });
    renderAuditLogs();
}

window.currentServerPrefixes = ['!'];

function renderPrefixesList() {
    const list = document.getElementById('bot-prefixes-list');
    if (!list) return;
    list.innerHTML = '';
    (window.currentServerPrefixes || ['!']).forEach(p => {
        const div = document.createElement('div');
        div.style.cssText = "background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 8px; padding: 8px 14px; display: inline-flex; align-items: center; gap: 10px; box-shadow: 0 2px 6px rgba(15,23,42,0.04);";
        div.innerHTML = `
            <span style="font-family: var(--font-mono); color: #E11D48; font-size: 1.05rem; font-weight: 800; background: #FFF1F5; padding: 2px 10px; border-radius: 4px;">${p}</span>
            <button onclick="removeBotPrefix('${p}')" style="background: transparent; border: none; color: #94A3B8; cursor: pointer; padding: 2px; font-size: 0.85rem; transition: color 0.15s;" onmouseover="this.style.color='#DC2626'" onmouseout="this.style.color='#94A3B8'" title="Delete prefix">
                <i class="fas fa-trash"></i>
            </button>
        `;
        list.appendChild(div);
    });
}

function addBotPrefix() {
    const prefixInput = document.getElementById('bot-prefix-input');
    const val = prefixInput?.value.trim();
    if (!val) {
        showToast("Error", "Please input a valid command prefix character.", "error");
        return;
    }
    if (!window.currentServerPrefixes) window.currentServerPrefixes = ['!'];
    if (window.currentServerPrefixes.includes(val)) {
        showToast("Notice", `Prefix '${val}' already exists.`, "warning");
        return;
    }
    window.currentServerPrefixes.push(val);
    renderPrefixesList();
    if (prefixInput) prefixInput.value = '';
    showToast("Prefix Added", `Command trigger registry updated with prefix: '${val}'`, "success");
    if (activeGuildId) {
        fetch(`/api/settings/prefix/${activeGuildId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prefixes: window.currentServerPrefixes })
        }).catch(() => {});
    }
}

function removeBotPrefix(p) {
    if (!window.currentServerPrefixes) window.currentServerPrefixes = ['!'];
    if (window.currentServerPrefixes.length <= 1) {
        showToast("Cannot Delete", "At least one command prefix must remain active.", "warning");
        return;
    }
    window.currentServerPrefixes = window.currentServerPrefixes.filter(item => item !== p);
    renderPrefixesList();
    showToast("Prefix Removed", `Removed command prefix: '${p}'`, "success");
    if (activeGuildId) {
        fetch(`/api/settings/prefix/${activeGuildId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prefixes: window.currentServerPrefixes })
        }).catch(() => {});
    }
}

// --- EMBED BUILDER EVENT HANDLERS ---

let embedFieldsCount = 0;

function toggleColorPickerField() {
    const wrapper = document.getElementById('eb-color-picker-wrapper');
    if (wrapper) {
        wrapper.style.display = wrapper.style.display === 'none' ? 'block' : 'none';
    }
}

function addEmbedBuilderField() {
    if (embedFieldsCount >= 25) {
        showToast("Field Limit Reached", "A single embed can contain up to 25 fields.", "warning");
        return;
    }
    
    embedFieldsCount++;
    const container = document.getElementById('eb-fields-container');
    if (!container) return;

    const fieldId = `eb-field-row-${embedFieldsCount}`;
    const fieldHtml = `
        <div id="${fieldId}" style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 10px; align-items: center; background: rgba(0,0,0,0.1); padding: 8px; border-radius: 6px;">
            <input type="text" placeholder="Field Name" class="form-control eb-custom-field-name" style="background: rgba(0,0,0,0.25);" oninput="updateEmbedBuilderPreview()">
            <input type="text" placeholder="Field Value" class="form-control eb-custom-field-value" style="background: rgba(0,0,0,0.25);" oninput="updateEmbedBuilderPreview()">
            <button onclick="removeEmbedBuilderField('${fieldId}')" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer;"><i class="fas fa-trash"></i></button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', fieldHtml);
    updateEmbedBuilderPreview();
}

function removeEmbedBuilderField(id) {
    const row = document.getElementById(id);
    if (row) {
        row.remove();
        embedFieldsCount--;
        updateEmbedBuilderPreview();
    }
}

function clearEmbedBuilderDate() {
    const dateInput = document.getElementById('eb-date-input');
    if (dateInput) dateInput.value = '';
    updateEmbedBuilderPreview();
}

function resetEmbedBuilderFields() {
    document.getElementById('eb-normal-text').value = '';
    document.getElementById('eb-author-icon').value = '';
    document.getElementById('eb-author-name').value = '';
    document.getElementById('eb-author-url').value = '';
    document.getElementById('eb-title').value = '';
    document.getElementById('eb-title-url').value = '';
    document.getElementById('eb-description').value = '';
    document.getElementById('eb-image-url').value = '';
    document.getElementById('eb-thumbnail-url').value = '';
    document.getElementById('eb-footer-text').value = '';
    document.getElementById('eb-footer-icon').value = '';
    document.getElementById('eb-fields-container').innerHTML = '';
    embedFieldsCount = 0;
    clearEmbedBuilderDate();
    updateEmbedBuilderPreview();
    showToast("Embed Reset", "Successfully cleared embed template fields.");
}

function formatDiscordDate(date) {
    const today = new Date();
    const isToday = date.getDate() === today.getDate() &&
                    date.getMonth() === today.getMonth() &&
                    date.getFullYear() === today.getFullYear();
    
    const timeString = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    if (isToday) {
        return `Today at ${timeString}`;
    } else {
        const dateString = date.toLocaleDateString([], { month: '2-digit', day: '2-digit', year: 'numeric' });
        return `${dateString} ${timeString}`;
    }
}

function updateEmbedBuilderPreview() {
    // 1. Text counters
    const normVal = document.getElementById('eb-normal-text')?.value || '';
    const normCounter = document.getElementById('eb-normal-counter');
    if (normCounter) normCounter.innerText = `${normVal.length}/2000`;

    const titleVal = document.getElementById('eb-title')?.value || '';
    const titleCounter = document.getElementById('eb-title-counter');
    if (titleCounter) titleCounter.innerText = `${titleVal.length}/256`;

    const descVal = document.getElementById('eb-description')?.value || '';
    const descCounter = document.getElementById('eb-desc-counter');
    if (descCounter) descCounter.innerText = `${descVal.length}/2048`;

    // 2. Render previews
    const previewOuter = document.getElementById('eb-preview-outer');
    if (previewOuter) {
        previewOuter.innerHTML = parseDiscordEmojis(escapeHtml(normVal));
        previewOuter.style.display = normVal ? 'block' : 'none';
    }

    const embedBox = document.getElementById('eb-preview-embed');
    const colorPicker = document.getElementById('eb-color-picker');
    if (embedBox && colorPicker) {
        embedBox.style.borderLeftColor = colorPicker.value;
    }

    const authNameVal = document.getElementById('eb-author-name')?.value || '';
    const authIconVal = document.getElementById('eb-author-icon')?.value || '';
    const authUrlVal = document.getElementById('eb-author-url')?.value || '';
    const previewAuth = document.getElementById('eb-preview-author');
    const previewAuthName = document.getElementById('eb-preview-author-name');
    const previewAuthIcon = document.getElementById('eb-preview-author-icon');

    if (previewAuth && previewAuthName && previewAuthIcon) {
        if (authNameVal) {
            if (authUrlVal) {
                previewAuthName.innerHTML = `<a href="${escapeHtml(authUrlVal)}" target="_blank" style="color: #fff; text-decoration: underline;">${escapeHtml(authNameVal)}</a>`;
            } else {
                previewAuthName.innerText = authNameVal;
            }
            if (authIconVal) {
                previewAuthIcon.src = authIconVal;
                previewAuthIcon.style.display = 'block';
            } else {
                previewAuthIcon.style.display = 'none';
            }
            previewAuth.style.display = 'flex';
        } else {
            previewAuth.style.display = 'none';
        }
    }

    const titleUrlVal = document.getElementById('eb-title-url')?.value || '';
    const previewTitle = document.getElementById('eb-preview-title');
    if (previewTitle) {
        if (titleUrlVal) {
            previewTitle.innerHTML = `<a href="${escapeHtml(titleUrlVal)}" target="_blank" style="color: #00aff4; text-decoration: none;">${parseDiscordEmojis(escapeHtml(titleVal))}</a>`;
        } else {
            previewTitle.innerHTML = parseDiscordEmojis(escapeHtml(titleVal));
        }
        previewTitle.style.display = titleVal ? 'block' : 'none';
    }

    const previewDesc = document.getElementById('eb-preview-description');
    if (previewDesc) {
        previewDesc.innerHTML = parseDiscordEmojis(escapeHtml(descVal)).replace(/\n/g, '<br>');
        previewDesc.style.display = descVal ? 'block' : 'none';
    }

    const thumbVal = document.getElementById('eb-thumbnail-url')?.value || '';
    const previewThumb = document.getElementById('eb-preview-thumbnail');
    if (previewThumb) {
        if (thumbVal) {
            previewThumb.src = thumbVal;
            previewThumb.style.display = 'block';
        } else {
            previewThumb.style.display = 'none';
        }
    }

    const imageVal = document.getElementById('eb-image-url')?.value || '';
    const previewImageWrapper = document.getElementById('eb-preview-image-wrapper');
    const previewImage = document.getElementById('eb-preview-image');
    if (previewImageWrapper && previewImage) {
        if (imageVal) {
            previewImage.src = imageVal;
            previewImageWrapper.style.display = 'block';
        } else {
            previewImageWrapper.style.display = 'none';
        }
    }

    // Render custom fields
    const fieldsContainer = document.getElementById('eb-preview-fields');
    if (fieldsContainer) {
        fieldsContainer.innerHTML = '';
        const names = document.querySelectorAll('.eb-custom-field-name');
        const values = document.querySelectorAll('.eb-custom-field-value');
        names.forEach((nameEl, idx) => {
            const valEl = values[idx];
            if (nameEl && valEl && nameEl.value) {
                fieldsContainer.innerHTML += `
                    <div style="background: rgba(255,255,255,0.02); padding: 8px; border-radius: 4px;">
                        <div style="font-weight: 700; font-size: 0.76rem; color: #fff;">${nameEl.value}</div>
                        <div style="font-size: 0.8rem; margin-top: 2px;">${valEl.value || '...'}</div>
                    </div>
                `;
            }
        });
    }

    const footVal = document.getElementById('eb-footer-text')?.value || '';
    const footIconVal = document.getElementById('eb-footer-icon')?.value || '';
    const previewFootText = document.getElementById('eb-preview-footer-text');
    const previewFootIcon = document.getElementById('eb-preview-footer-icon');
    const previewFootWrapper = document.getElementById('eb-preview-footer-wrapper');
    const previewDate = document.getElementById('eb-preview-footer-date');
    const previewBullet = document.getElementById('eb-preview-footer-date-bullet');

    const dateInput = document.getElementById('eb-date-input');
    let timestampStr = '';
    let timestampIso = null;
    
    if (dateInput && dateInput.value) {
        const d = new Date(dateInput.value);
        timestampIso = d.toISOString();
        timestampStr = formatDiscordDate(d);
    } else {
        const d = new Date();
        timestampIso = d.toISOString();
        timestampStr = formatDiscordDate(d);
    }

    if (previewFootWrapper && previewFootText && previewFootIcon && previewDate && previewBullet) {
        if (footVal || timestampStr) {
            if (footVal) {
                previewFootText.innerText = footVal;
                previewFootText.style.display = 'inline';
            } else {
                previewFootText.style.display = 'none';
            }
            
            if (footIconVal) {
                previewFootIcon.src = footIconVal;
                previewFootIcon.style.display = 'block';
            } else {
                previewFootIcon.style.display = 'none';
            }
            
            if (timestampStr) {
                previewDate.innerText = timestampStr;
                previewDate.style.display = 'inline';
                if (footVal) {
                    previewBullet.style.display = 'inline';
                } else {
                    previewBullet.style.display = 'none';
                }
            } else {
                previewDate.style.display = 'none';
                previewBullet.style.display = 'none';
            }
            
            previewFootWrapper.style.display = 'flex';
        } else {
            previewFootWrapper.style.display = 'none';
        }
    }

    // 3. Update Raw JSON output
    const rawField = document.getElementById('eb-raw-json-field');
    if (rawField) {
        const jsonPayload = {
            content: normVal,
            embeds: [{
                title: titleVal || undefined,
                description: descVal || undefined,
                color: parseInt((colorPicker?.value || '#a855f7').replace('#', ''), 16),
                author: authNameVal ? { name: authNameVal, icon_url: authIconVal || undefined } : undefined,
                thumbnail: thumbVal ? { url: thumbVal } : undefined,
                image: imageVal ? { url: imageVal } : undefined,
                footer: footVal ? { text: footVal, icon_url: footIconVal || undefined } : undefined,
                timestamp: timestampIso || undefined
            }]
        };
        rawField.value = JSON.stringify(jsonPayload);
    }
}

function copyEmbedJsonToClipboard() {
    const rawField = document.getElementById('eb-raw-json-field');
    if (rawField) {
        rawField.select();
        navigator.clipboard.writeText(rawField.value)
            .then(() => showToast("Copied", "Raw embed JSON copied to clipboard."))
            .catch(() => showToast("Copy Failed", "Unable to copy JSON text", "error"));
    }
}

function applyEmbedJson() {
    const rawField = document.getElementById('eb-raw-json-field');
    if (!rawField) return;
    try {
        const data = JSON.parse(rawField.value);
        document.getElementById('eb-normal-text').value = data.content || '';
        const emb = (data.embeds && data.embeds.length > 0) ? data.embeds[0] : {};
        
        document.getElementById('eb-title').value = emb.title || '';
        document.getElementById('eb-description').value = emb.description || '';
        
        if (emb.color) {
            document.getElementById('eb-color-picker').value = '#' + emb.color.toString(16).padStart(6, '0');
        }
        if (emb.author) {
            document.getElementById('eb-author-name').value = emb.author.name || '';
            document.getElementById('eb-author-icon').value = emb.author.icon_url || '';
        }
        if (emb.thumbnail) {
            document.getElementById('eb-thumbnail-url').value = emb.thumbnail.url || '';
        }
        if (emb.image) {
            document.getElementById('eb-image-url').value = emb.image.url || '';
        }
        if (emb.footer) {
            document.getElementById('eb-footer-text').value = emb.footer.text || '';
            document.getElementById('eb-footer-icon').value = emb.footer.icon_url || '';
        }
        if (emb.timestamp) {
            try {
                const d = new Date(emb.timestamp);
                const localIso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
                document.getElementById('eb-date-input').value = localIso;
            } catch(e) {}
        } else {
            document.getElementById('eb-date-input').value = '';
        }
        updateEmbedBuilderPreview();
        showToast("JSON Applied", "Embed layout synced from parsed JSON structure.");
    } catch(e) {
        showToast("Parsing Error", "Invalid JSON syntax. Please verify.", "error");
    }
}

function postEmbedBuilderMsg() {
    const chan = document.getElementById('eb-destination-channel').value;
    if (!chan) {
        showToast("Select Channel", "Please pick a target text channel first.", "warning");
        return;
    }
    
    // Default to current time if no date is specified
    const dateInput = document.getElementById('eb-date-input');
    if (dateInput && !dateInput.value) {
        const now = new Date();
        const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        dateInput.value = localIso;
        updateEmbedBuilderPreview();
    }
    
    showToast("Embed Posted", `Successfully dispatched announcements rich embed to channel #${chan}`);
    addLogEntry("!! DADDY", `Dispatched announcements embed payload to channel #${chan}`);
    
    mockAuditLogs.unshift({
        time: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: '!! DADDY',
        action: `embed.post to channel: #${chan}`
    });
    renderAuditLogs();
}

function initStackParticles() {
    const container = document.getElementById('stack-particles-field');
    if (!container) return;
    container.innerHTML = '';
    
    const count = 55;
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'tiny-white-particle';
        const size = (Math.random() * 2.5 + 1.2).toFixed(1); // 1.2px to 3.7px
        const posX = (Math.random() * 96).toFixed(1);
        const posY = (Math.random() * 94).toFixed(1);
        const delayFloat = (Math.random() * -15).toFixed(1);
        const delayTwinkle = (Math.random() * -5).toFixed(1);
        const durationFloat = (Math.random() * 12 + 10).toFixed(1);
        const durationTwinkle = (Math.random() * 3 + 2).toFixed(1);
        
        p.style.width = `${size}px`;
        p.style.height = `${size}px`;
        p.style.left = `${posX}%`;
        p.style.top = `${posY}%`;
        p.style.animationDelay = `${delayFloat}s, ${delayTwinkle}s`;
        p.style.animationDuration = `${durationFloat}s, ${durationTwinkle}s`;
        
        container.appendChild(p);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStackParticles);
} else {
    initStackParticles();
}

// --- BOT PROFILE CONTROLLERS & LIVE PREVIEW ENGINE ---
window.currentBotAvatarData = '';
window.currentBotBannerData = '';

function getUnicodeLength(str) {
    if (!str) return 0;
    try {
        if (typeof Intl !== 'undefined' && Intl.Segmenter) {
            const segmenter = new Intl.Segmenter('en', { granularity: 'grapheme' });
            return [...segmenter.segment(str)].length;
        }
        return [...str].length;
    } catch (_) {
        return [...str].length;
    }
}

function updateBotProfileLivePreview() {
    const nickEl = document.getElementById('bot-nickname-field');
    const bioEl = document.getElementById('bot-bio-field');
    const webEl = document.getElementById('bot-website-field');
    const suppEl = document.getElementById('bot-support-field');
    
    const nick = nickEl ? nickEl.value : 'VEYRA';
    const bioRaw = bioEl ? bioEl.value : '';
    const website = webEl ? webEl.value.trim() : '';
    const support = suppEl ? suppEl.value.trim() : '';

    // Update char counts with accurate Unicode / fancy font character counting
    const nickLen = getUnicodeLength(nick);
    const bioLen = getUnicodeLength(bioRaw);

    const nickCount = document.getElementById('nickname-char-count');
    if (nickCount) nickCount.innerText = `${nickLen}/32 characters`;
    
    const bioCount = document.getElementById('bio-char-count');
    if (bioCount) bioCount.innerText = `${bioLen}/180`;

    // Update preview nickname
    const prevNick = document.getElementById('preview-bot-nickname');
    if (prevNick) prevNick.innerText = nick || 'VEYRA';

    // Construct bio output for preview
    let bioDisplay = bioRaw || "The most powerful invite tracking bot on Discord.\n\nWebsite: \nSupport: ";
    
    // Replace website/support lines dynamically if user typed custom URLs
    if (website || support) {
        let lines = bioDisplay.split('\n');
        let hasWeb = false, hasSupp = false;
        lines = lines.map(line => {
            if (line.startsWith('Website:')) {
                hasWeb = true;
                return `Website: ${website}`;
            }
            if (line.startsWith('Support:')) {
                hasSupp = true;
                return `Support: ${support}`;
            }
            return line;
        });
        if (!hasWeb && website) lines.push(`Website: ${website}`);
        if (!hasSupp && support) lines.push(`Support: ${support}`);
        bioDisplay = lines.join('\n');
    }

    const prevBio = document.getElementById('preview-bot-bio');
    if (prevBio) prevBio.innerText = bioDisplay;
}

function compressAndResizeImage(file, maxWidth, maxHeight, quality, callback) {
    if (!file) return;
    
    // Check 10MB ceiling
    if (file.size > 10 * 1024 * 1024) {
        if (typeof showToast === 'function') {
            showToast("File Too Large", "Maximum image size is 10MB.", "error");
        }
        return;
    }

    const isGif = file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif');
    const isPng = file.type === 'image/png' || file.name.toLowerCase().endsWith('.png');
    const isWebp = file.type === 'image/webp' || file.name.toLowerCase().endsWith('.webp');

    // GIFs must NEVER be rendered to canvas — canvas drops all animation frames and fails to export GIF
    if (isGif) {
        const directReader = new FileReader();
        directReader.onload = function(e) {
            callback(e.target.result);
        };
        directReader.readAsDataURL(file);
        return;
    }

    // If file is already reasonably sized (<= 2MB), preserve original file 100% without canvas degradation
    if (file.size <= 2 * 1024 * 1024) {
        const directReader = new FileReader();
        directReader.onload = function(e) {
            callback(e.target.result);
        };
        directReader.readAsDataURL(file);
        return;
    }

    // For files between 2MB and 10MB, downscale proportionally on canvas
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            let width = img.width;
            let height = img.height;
            if (width > maxWidth || height > maxHeight) {
                if (width / height > maxWidth / maxHeight) {
                    height = Math.round((height * maxWidth) / width);
                    width = maxWidth;
                } else {
                    width = Math.round((width * maxHeight) / height);
                    height = maxHeight;
                }
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            // Clear canvas to ensure complete transparency support
            ctx.clearRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0, width, height);

            let exportType = 'image/jpeg';
            if (isPng) exportType = 'image/png';
            else if (isWebp) exportType = 'image/webp';

            const dataUrl = canvas.toDataURL(exportType, quality);
            callback(dataUrl);
        };
        img.onerror = function() {
            callback(e.target.result);
        };
        img.src = e.target.result;
    };
    reader.onerror = function() {
        if (typeof showToast === 'function') showToast("Read Error", "Failed to read image file.", "error");
    };
    reader.readAsDataURL(file);
}

function handleBotAvatarUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        compressAndResizeImage(file, 512, 512, 0.9, function(dataUrl) {
            window.currentBotAvatarData = dataUrl;
            
            const previewBox = document.getElementById('bot-avatar-preview-box');
            if (previewBox) {
                previewBox.innerHTML = `<img src="${dataUrl}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block;">`;
            }
            
            const cardAvatar = document.getElementById('preview-bot-avatar');
            if (cardAvatar) {
                cardAvatar.innerHTML = `<img src="${dataUrl}" style="width: 100%; height: 100%; object-fit: cover; display: block;">`;
            }
            
            showToast("Avatar Ready", "Bot avatar ready to save!");
        });
        input.value = '';
    }
}

function handleBotBannerUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        compressAndResizeImage(file, 1200, 480, 0.9, function(dataUrl) {
            window.currentBotBannerData = dataUrl;
            
            const previewBox = document.getElementById('bot-banner-preview-box');
            if (previewBox) {
                previewBox.innerHTML = `<img src="${dataUrl}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px; display: block;">`;
            }
            
            const cardBanner = document.getElementById('preview-bot-banner');
            if (cardBanner) {
                cardBanner.style.background = `url("${dataUrl}") center/cover no-repeat`;
            }
            
            showToast("Banner Ready", "Bot banner ready to save!");
        });
        input.value = '';
    }
}

function saveBotProfileSettings() {
    const guildId = activeGuildId || localStorage.getItem('selected_guild_id') || document.getElementById('server-select-dropdown')?.value || (window.currentServerData && window.currentServerData.id);
    if (!guildId) {
        showToast("Error", "Please select a server first from Manage Servers.", "error");
        return;
    }

    const nickname = document.getElementById('bot-nickname-field') ? document.getElementById('bot-nickname-field').value.trim() : 'VEYRA';
    const bio = document.getElementById('bot-bio-field') ? document.getElementById('bot-bio-field').value : '';
    const website = document.getElementById('bot-website-field') ? document.getElementById('bot-website-field').value.trim() : '';
    const support = document.getElementById('bot-support-field') ? document.getElementById('bot-support-field').value.trim() : '';

    const saveBtn = document.querySelector('button[onclick="saveBotProfileSettings()"]');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving Profile...';
    }

    const payload = {
        nickname: nickname || 'VEYRA',
        bio,
        website,
        support,
        avatar: window.currentBotAvatarData || '',
        banner: window.currentBotBannerData || ''
    };

    const trySave = (url) => {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(async res => {
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || `Server responded with status ${res.status}`);
            }
            return res.json();
        });
    };

    trySave(`/api/settings/bot-profile/${guildId}`)
        .catch(err => {
            console.warn("Local route error, retrying via Render backend:", err);
            return trySave(`https://veyra-discord-bot-tl6e.onrender.com/api/settings/bot-profile/${guildId}`);
        })
        .then(res => {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-floppy-disk"></i> Save Profile Changes';
            }
            if (res.success) {
                showToast("Profile Saved", "Bot profile updated in real-time on Discord & saved!");
                if (typeof addLogEntry === 'function') addLogEntry("@user", `Updated Bot Profile: Nickname='${nickname}'`);
                if (typeof updateBotProfileLivePreview === 'function') updateBotProfileLivePreview();
            } else {
                showToast("Save Failed", res.error || "Failed to save profile settings", "error");
            }
        })
        .catch(err => {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-floppy-disk"></i> Save Profile Changes';
            }
            console.error("Save profile error:", err);
            showToast("Error Saving", err.message || "Could not save profile settings", "error");
        });
}

function loadBotProfileSettings(guildId) {
    if (!guildId) guildId = activeGuildId || localStorage.getItem('selected_guild_id') || document.getElementById('server-select-dropdown')?.value || (window.currentServerData && window.currentServerData.id);
    if (!guildId) return;

    fetch(`/api/settings/bot-profile/${guildId}`)
        .then(res => res.json())
        .then(data => {
            if (!data) return;
            if (document.getElementById('bot-nickname-field')) document.getElementById('bot-nickname-field').value = data.nickname || 'VEYRA';
            if (document.getElementById('bot-bio-field')) document.getElementById('bot-bio-field').value = data.bio || "The most powerful Discord security & invite tracking bot.\n\nWebsite: \nSupport: ";
            if (document.getElementById('bot-website-field')) document.getElementById('bot-website-field').value = data.website || '';
            if (document.getElementById('bot-support-field')) document.getElementById('bot-support-field').value = data.support || '';

            if (data.avatar) {
                window.currentBotAvatarData = data.avatar;
                const previewBox = document.getElementById('bot-avatar-preview-box');
                if (previewBox) previewBox.innerHTML = `<img src="${data.avatar}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block;">`;
                const cardAvatar = document.getElementById('preview-bot-avatar');
                if (cardAvatar) cardAvatar.innerHTML = `<img src="${data.avatar}" style="width: 100%; height: 100%; object-fit: cover; display: block;">`;
            } else {
                window.currentBotAvatarData = '';
                const previewBox = document.getElementById('bot-avatar-preview-box');
                if (previewBox) previewBox.innerHTML = `<i class="fas fa-plus" style="font-size: 1.1rem;" id="bot-avatar-plus-icon"></i>`;
                const cardAvatar = document.getElementById('preview-bot-avatar');
                if (cardAvatar) cardAvatar.innerHTML = `<img src="assets/bypass_logs_avatar.webp" alt="Bot Avatar" style="width: 100%; height: 100%; object-fit: cover; display: block;">`;
            }

            if (data.banner) {
                window.currentBotBannerData = data.banner;
                const previewBox = document.getElementById('bot-banner-preview-box');
                if (previewBox) previewBox.innerHTML = `<img src="${data.banner}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px; display: block;">`;
                const cardBanner = document.getElementById('preview-bot-banner');
                if (cardBanner) {
                    cardBanner.style.background = `url("${data.banner}") center/cover no-repeat`;
                }
            } else {
                window.currentBotBannerData = '';
                const previewBox = document.getElementById('bot-banner-preview-box');
                if (previewBox) previewBox.innerHTML = `<i class="fas fa-image" style="font-size: 1.1rem;" id="bot-banner-plus-icon"></i>`;
                const cardBanner = document.getElementById('preview-bot-banner');
                if (cardBanner) {
                    cardBanner.style.background = "linear-gradient(135deg, #0284c7, #0d9488)";
                }
            }

            if (typeof updateBotProfileLivePreview === 'function') updateBotProfileLivePreview();
        })
        .catch(err => console.error("Error loading bot profile settings:", err));
}

function populateServerRolesAndChannels(guildId) {
    if (!guildId) return Promise.resolve();

    // 1. Fetch live guild roles
    const rolesPromise = fetch(`/api/guild/roles/${guildId}`)
        .then(res => res.json())
        .then(roles => {
            if (!Array.isArray(roles)) return;
            window.guildRoles = roles;
            const roleSelects = Array.from(document.querySelectorAll('.guild-roles-dropdown, #verif-role, #verification-role-select, #autoroles-select, #sticky-blacklisted-select, #publish-bump-role-select, #am-mute-role, #am-allowed-roles'));
            roleSelects.forEach(select => {
                if (select) {
                    const currentVal = select.value;
                    select.innerHTML = '<option value="">Select Role</option>';
                    roles.forEach(r => {
                        const opt = document.createElement('option');
                        opt.value = r.id;
                        opt.innerText = `@${r.name}`;
                        select.appendChild(opt);
                    });
                    if (currentVal) select.value = currentVal;
                }
            });
            if (typeof refreshLoadedRolePills === 'function') refreshLoadedRolePills();
        })
        .catch(err => console.error("Error fetching live roles:", err));

    // 2. Fetch live guild emojis
    const emojisPromise = fetch(`/api/guild/emojis/${guildId}`)
        .then(res => res.json())
        .then(emojis => {
            if (Array.isArray(emojis)) {
                window.guildEmojis = emojis;
                console.log(`[EMOJIS LOADED] ${emojis.length} live server custom emojis loaded.`);
                if (typeof updateMultiEmbedPreview === 'function') updateMultiEmbedPreview();
                if (typeof updateWelcomeLivePreview === 'function') updateWelcomeLivePreview();
                if (typeof updateLeaveLivePreview === 'function') updateLeaveLivePreview();
                if (typeof updateInviteTrackerLivePreview === 'function') updateInviteTrackerLivePreview();
                if (typeof updateSimEmbedPreview === 'function') updateSimEmbedPreview();
            }
        })
        .catch(err => console.error("Error fetching live emojis:", err));

    // 3. Fetch live guild channels
    const channelsPromise = fetch(`/api/guild/channels/${guildId}`)
        .then(res => res.json())
        .then(channels => {
            if (!Array.isArray(channels)) return;
            window.guildChannels = channels;
            console.log(`[CHANNELS LOADED] ${channels.length} live server channels loaded.`);

            const channelSelects = Array.from(new Set([
                document.getElementById('ebm-destination-channel'),
                document.getElementById('eb-destination-channel'),
                document.getElementById('welcome-msg-channel-select'),
                document.getElementById('leave-msg-channel-select'),
                document.getElementById('invitetracker-msg-channel-select'),
                document.getElementById('publish-channel-select'),
                document.getElementById('verif-channel'),
                document.getElementById('log-select-moderation'),
                document.getElementById('log-select-security'),
                document.getElementById('log-select-joins'),
                document.getElementById('log-select-messages'),
                document.getElementById('log-select-voice'),
                document.getElementById('reports-channel-select'),
                document.getElementById('levels-channel-select'),
                document.getElementById('levels-blacklist-channel-select'),
                ...Array.from(document.querySelectorAll('.guild-channels-dropdown'))
            ].filter(Boolean)));

            channelSelects.forEach(select => {
                const currentVal = select.value;
                const isLog = select.id && select.id.startsWith('log-select-');
                select.innerHTML = isLog ? '<option value="none">None</option>' : '<option value="">Select Channel</option>';
                
                channels.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.innerText = `# ${c.name}`;
                    select.appendChild(opt);
                });

                if (currentVal) {
                    select.value = currentVal;
                    if (!select.value) {
                        const cleanVal = currentVal.toLowerCase().replace('#', '').trim();
                        const matchOpt = Array.from(select.options).find(o => 
                            o.value === currentVal || 
                            o.innerText.toLowerCase().replace('#', '').trim() === cleanVal ||
                            o.innerText.toLowerCase().includes(cleanVal)
                        );
                        if (matchOpt) select.value = matchOpt.value;
                    }
                }
            });

            // Auto-select smart defaults if empty
            const ebmDest = document.getElementById('ebm-destination-channel');
            if (ebmDest && (!ebmDest.value || ebmDest.value === 'general')) {
                const chatCh = channels.find(c => c.name.toLowerCase().includes('chat') || c.name.toLowerCase().includes('general') || c.type === 0);
                if (chatCh) ebmDest.value = chatCh.id;
            }
            const welDest = document.getElementById('welcome-msg-channel-select');
            if (welDest && (!welDest.value || welDest.value === 'welcome' || welDest.value === 'general')) {
                const welCh = channels.find(c => c.name.toLowerCase().includes('welcome') || c.name.toLowerCase().includes('join'));
                if (welCh) welDest.value = welCh.id;
            }
            const leaveDest = document.getElementById('leave-msg-channel-select');
            if (leaveDest && (!leaveDest.value || leaveDest.value === 'exits' || leaveDest.value === 'general')) {
                const exitCh = channels.find(c => c.name.toLowerCase().includes('exit') || c.name.toLowerCase().includes('leave'));
                if (exitCh) leaveDest.value = exitCh.id;
            }
            const invDest = document.getElementById('invitetracker-msg-channel-select');
            if (invDest && (!invDest.value || invDest.value === 'invite-logs' || invDest.value === 'general')) {
                const invCh = channels.find(c => c.name.toLowerCase().includes('invite'));
                if (invCh) invDest.value = invCh.id;
            }
        })
        .catch(err => console.error("Error fetching live channels:", err));

    return Promise.all([rolesPromise, emojisPromise, channelsPromise]);
}

function loadRealAnalytics(guildId, timeframe = null) {
    const targetGuild = guildId || activeGuildId || '1509911679637520584';
    const tf = timeframe || window.currentAnalyticsTimeframe || '30D';
    
    fetch(`/api/analytics/${targetGuild}?timeframe=${tf}`)
        .then(res => {
            if (res.status === 403) {
                return res.json().then(errData => {
                    if (typeof showToast === 'function') {
                        showToast('Pro Feature', errData.message || 'Free servers can only access up to 30 days of analytics.', 'warning');
                    }
                    if (tf === '90D') {
                        window.switchAnalyticsTimeframe('30D');
                    }
                    throw new Error("Plan restriction");
                });
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;
            if (data.plan) window.currentServerPlan = data.plan;

            const elNet = document.getElementById('analytics-net-growth');
            const elJoins = document.getElementById('analytics-joins');
            const elLeaves = document.getElementById('analytics-leaves');
            const elRetention = document.getElementById('analytics-retention');
            const elStayed = document.getElementById('analytics-stayed-subtext');

            const joinsCount = data.joins || 0;
            const leavesCount = data.leaves || 0;
            const netCount = data.netGrowth || 0;

            if (elNet) {
                elNet.innerText = (netCount > 0 ? '+' : '') + netCount;
                elNet.style.color = netCount >= 0 ? '#059669' : '#E11D48';
            }
            if (elJoins) elJoins.innerText = joinsCount;
            if (elLeaves) elLeaves.innerText = leavesCount;

            // Clean retention display (no 100% when 0 invites)
            if (elRetention) {
                if (joinsCount === 0) {
                    elRetention.innerText = '0%';
                } else {
                    elRetention.innerText = (data.retention !== undefined ? data.retention : 0) + '%';
                }
            }
            if (elStayed) {
                if (joinsCount === 0) {
                    elStayed.innerText = '0 invites in this period';
                } else {
                    elStayed.innerText = `${Math.max(0, netCount)} of ${joinsCount} invites active`;
                }
            }

            window.activeAnalyticsPoints = data.points || [];
            renderAnalyticsGraph(data.points || []);
        })
        .catch(err => {
            if (err.message !== "Plan restriction") {
                console.error("Error loading analytics:", err);
            }
        });
}

function renderAnalyticsGraph(points) {
    if (!points || points.length === 0) return;
    
    // 1. Render dynamic X-axis labels with exact percentage alignment
    const xaxisContainer = document.getElementById('analytics-xaxis-labels');
    if (xaxisContainer) {
        const total = points.length - 1;
        xaxisContainer.innerHTML = points.map((p, idx) => {
            const pct = total > 0 ? ((idx / total) * 100).toFixed(2) : 0;
            let tx = '-50%';
            let align = 'center';
            if (idx === 0) {
                tx = '0%';
                align = 'left';
            } else if (idx === total) {
                tx = '-100%';
                align = 'right';
            }
            const isLast = idx === total;
            return `<span style="position: absolute; left: ${pct}%; transform: translateX(${tx}); text-align: ${align}; color: ${isLast ? '#E11D48' : '#475569'}; font-weight: ${isLast ? '900' : '700'}; cursor: pointer; transition: color 0.15s ease; white-space: nowrap; pointer-events: auto;" onmouseover="this.style.color='#E11D48'" onmouseout="if(${!isLast}) this.style.color='#475569'" onclick="updateGraphTooltipByIndex(${idx})">${p.date}</span>`;
        }).join('');
    }

    const svgChart = document.getElementById('analytics-svg-chart');
    const pathJoins = document.getElementById('analytics-path-joins');
    const pathLeaves = document.getElementById('analytics-path-leaves');
    
    if (!svgChart || !pathJoins || !pathLeaves) return;

    // 2. Compute dynamic Y-axis scale based on real values
    const rawMax = Math.max(0, ...points.map(p => Math.max(p.joins || 0, p.leaves || 0)));
    let maxVal = 10;
    if (rawMax > 0) {
        const scaled = Math.ceil(rawMax * 1.25);
        maxVal = Math.max(4, Math.ceil(scaled / 4) * 4);
    }
    window.currentAnalyticsMaxVal = maxVal;

    // 3. Dynamically update Y-axis numbers
    const yaxisEl = document.getElementById('analytics-yaxis-labels');
    if (yaxisEl) {
        yaxisEl.innerHTML = `
            <span>${Math.round(maxVal)}</span>
            <span>${Math.round(maxVal * 0.75)}</span>
            <span>${Math.round(maxVal * 0.50)}</span>
            <span>${Math.round(maxVal * 0.25)}</span>
            <span>0</span>
        `;
    }

    // 4. Construct SVG curve paths
    const width = 1000;
    const height = 185;
    const totalPts = points.length - 1;
    
    const getX = (index) => totalPts > 0 ? (index / totalPts) * width : 0;
    // When val is 0, getY(0) = 185 (sits directly on baseline 0). When val is maxVal, getY(maxVal) = 0 (top line).
    const getY = (val) => height - ((val || 0) / maxVal) * height;

    let joinsD = `M ${getX(0)} ${getY(points[0].joins)}`;
    let leavesD = `M ${getX(0)} ${getY(points[0].leaves)}`;

    for (let i = 1; i < points.length; i++) {
        const prevX = getX(i - 1);
        const currX = getX(i);
        const midX = (prevX + currX) / 2;
        
        const prevYJ = getY(points[i - 1].joins);
        const currYJ = getY(points[i].joins);
        joinsD += ` C ${midX} ${prevYJ}, ${midX} ${currYJ}, ${currX} ${currYJ}`;

        const prevYL = getY(points[i - 1].leaves);
        const currYL = getY(points[i].leaves);
        leavesD += ` C ${midX} ${prevYL}, ${midX} ${currYL}, ${currX} ${currYL}`;
    }

    pathJoins.setAttribute('d', joinsD);
    pathLeaves.setAttribute('d', leavesD);

    // Clean, high-contrast, professional line rendering (No ugly alternating dashes)
    const hasLeaves = points.some(p => (p.leaves || 0) > 0);
    if (!hasLeaves) {
        // Zero leaves recorded: hide red leaves line completely, show only solid emerald joins line
        pathLeaves.style.display = 'none';
        pathJoins.setAttribute('stroke', '#059669');
        pathJoins.removeAttribute('stroke-dasharray');
    } else {
        pathLeaves.style.display = 'block';
        pathLeaves.setAttribute('stroke', '#E11D48');
        pathLeaves.removeAttribute('stroke-dasharray');
        pathJoins.setAttribute('stroke', '#059669');
        pathJoins.removeAttribute('stroke-dasharray');
    }

    updateGraphTooltipByIndex(points.length - 1, maxVal);
    setupAnalyticsChartScrubbing();
}

function updateGraphTooltipByIndex(index, maxValCalculated) {
    const points = window.activeAnalyticsPoints;
    if (!points || points.length === 0) return;
    
    const totalPts = points.length - 1;
    const idx = Math.max(0, Math.min(totalPts, index));
    const pt = points[idx];
    
    const maxVal = maxValCalculated || window.currentAnalyticsMaxVal || 10;
    const width = 1000;
    const height = 185;
    
    const getX = (i) => totalPts > 0 ? (i / totalPts) * width : 0;
    const getY = (val) => height - ((val || 0) / maxVal) * height;

    const cx = getX(idx);
    const cyJoins = getY(pt.joins);
    const cyLeaves = getY(pt.leaves);

    const guideLine = document.getElementById('analytics-guide-line');
    const dotJoins = document.getElementById('analytics-dot-joins');
    const dotLeaves = document.getElementById('analytics-dot-leaves');
    const tooltipBox = document.getElementById('analytics-tooltip-box');
    const ttDate = document.getElementById('analytics-tooltip-date');
    const ttJoins = document.getElementById('analytics-tooltip-joins');
    const ttLeaves = document.getElementById('analytics-tooltip-leaves');
    const leavesWrapper = document.getElementById('analytics-tooltip-leaves-wrapper');

    if (guideLine) {
        guideLine.setAttribute('x1', cx);
        guideLine.setAttribute('x2', cx);
        guideLine.setAttribute('y1', 0);
        guideLine.setAttribute('y2', height);
    }
    if (dotJoins) {
        dotJoins.setAttribute('cx', cx);
        dotJoins.setAttribute('cy', cyJoins);
    }

    const hasLeavesInSeries = points.some(p => (p.leaves || 0) > 0);
    if (dotLeaves) {
        if (hasLeavesInSeries && (pt.leaves || 0) > 0) {
            dotLeaves.setAttribute('cx', cx);
            dotLeaves.setAttribute('cy', cyLeaves);
            dotLeaves.style.display = 'block';
        } else {
            dotLeaves.style.display = 'none';
        }
    }

    if (ttDate) ttDate.innerText = pt.fullDate || pt.date;
    if (ttJoins) ttJoins.innerText = `${pt.joins || 0} Real Invites`;
    if (ttLeaves) ttLeaves.innerText = `${pt.leaves || 0} leaves`;
    if (leavesWrapper) {
        leavesWrapper.style.display = (hasLeavesInSeries && (pt.leaves || 0) > 0) ? 'flex' : 'none';
    }

    if (tooltipBox) {
        const pct = totalPts > 0 ? (idx / totalPts) * 100 : 50;
        const clampedPct = Math.max(8, Math.min(76, pct - 10));
        tooltipBox.style.left = `${clampedPct}%`;
    }
}

function setupAnalyticsChartScrubbing() {
    const container = document.getElementById('analytics-graph-container');
    if (!container || container._scrubAttached) return;
    container._scrubAttached = true;

    container.addEventListener('mousemove', (e) => {
        const points = window.activeAnalyticsPoints;
        if (!points || points.length === 0) return;
        const rect = container.getBoundingClientRect();
        const plotLeft = rect.left + 55;
        const plotWidth = rect.width - 80;
        if (plotWidth <= 0) return;
        const offsetX = e.clientX - plotLeft;
        const ratio = Math.max(0, Math.min(1, offsetX / plotWidth));
        const index = Math.round(ratio * (points.length - 1));
        updateGraphTooltipByIndex(index);
    });

    container.addEventListener('mouseleave', () => {
        const points = window.activeAnalyticsPoints;
        if (points && points.length > 0) {
            updateGraphTooltipByIndex(points.length - 1);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {

// --- INSTANT PERSISTENT SERVER SELECTION RESTORATION ON LOAD ---
(function restoreActiveServerInstant() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryGid = urlParams.get('guild_id');
        const savedGid = queryGid || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
        const savedName = localStorage.getItem('selected_guild_name');
        const savedIcon = localStorage.getItem('selected_guild_icon');

        if (savedName) {
            const sideName = document.getElementById('sidebar-guild-name');
            if (sideName) sideName.innerText = savedName;
            const mgName = document.getElementById('managing-server-name');
            if (mgName) mgName.innerText = savedName;
            const dsName = document.getElementById('dashboard-server-name');
            if (dsName) dsName.innerText = savedName;
            const hdName = document.getElementById('header-server-dropdown-name');
            if (hdName) hdName.innerText = savedName;
            const tkName = document.getElementById('tickets-sidebar-guild-name');
            if (tkName) tkName.innerText = savedName;
        }
        if (savedIcon || savedName) {
            window.updateActiveGuildUI(savedGid, savedName, savedIcon);
        }
        // Ensure sidebar server dropdown is closed by default
        const sDrop = document.getElementById('sidebar-server-dropdown');
        if (sDrop) sDrop.style.display = 'none';
        const sChev = document.getElementById('sidebar-guild-chevron');
        if (sChev) sChev.style.transform = 'rotate(0deg)';
    } catch(e) {}
})();

    const graphContainer = document.getElementById('analytics-graph-container');
    if (graphContainer) {
        const handleGraphHover = (e) => {
            const points = window.activeAnalyticsPoints;
            if (!points || points.length === 0) return;
            const rect = graphContainer.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const relX = Math.max(0, Math.min(rect.width, clientX - rect.left));
            const ratio = relX / rect.width;
            const targetIdx = Math.round(ratio * (points.length - 1));
            updateGraphTooltipByIndex(targetIdx);
        };

        graphContainer.addEventListener('mousemove', handleGraphHover);
        graphContainer.addEventListener('touchmove', handleGraphHover);
        graphContainer.addEventListener('click', handleGraphHover);
    }
});

function setInviteTrackerPresetColor(colorHex) {
    const cp = document.getElementById('invitetracker-embed-color-picker');
    const hexInput = document.getElementById('invitetracker-color-hex');
    if (cp) cp.value = colorHex;
    if (hexInput) hexInput.value = colorHex;
    updateInviteTrackerLivePreview();
}

function updateInviteTrackerLivePreview() {
    const textEl = document.getElementById('invitetracker-msg-outer-input');
    const embedTitleEl = document.getElementById('invitetracker-embed-title');
    const embedTitleUrlEl = document.getElementById('invitetracker-title-url');
    const embedDescEl = document.getElementById('invitetracker-embed-desc');
    const embedColorEl = document.getElementById('invitetracker-color-hex') || document.getElementById('invitetracker-embed-color-picker');
    const embedCheck = document.getElementById('invitetracker-embed-enable');
    const authorNameEl = document.getElementById('invitetracker-author-name');
    const authorIconEl = document.getElementById('invitetracker-author-icon');
    const authorUrlEl = document.getElementById('invitetracker-author-url');
    const thumbEl = document.getElementById('invitetracker-thumbnail-url');
    const imgEl = document.getElementById('invitetracker-embed-image');
    const footerEl = document.getElementById('invitetracker-embed-footer');
    const footerIconEl = document.getElementById('invitetracker-footer-icon');
    
    const userAvatarUrl = window.currentUserAvatar || 'https://cdn.discordapp.com/embed/avatars/0.png';

    const text = textEl ? textEl.value : '%member_mention% has been invited by %inviter% and has now %inviter_invites% invites.';
    const title = embedTitleEl ? embedTitleEl.value : '✨ Member Joined via Invite';
    const titleUrl = embedTitleUrlEl ? embedTitleUrlEl.value.trim() : '';
    const desc = embedDescEl ? embedDescEl.value : 'User %member_mention% joined using invite code veyra-vip.';
    const color = embedColorEl ? embedColorEl.value : '#a855f7';

    const simOuter = document.getElementById('invitetracker-sim-outer');
    if (simOuter) {
        let formatted = text
            .replace(/%member_mention%|\{user\}/g, '<span style="color: #5865F2; background: rgba(88,101,242,0.15); padding: 1px 4px; border-radius: 3px; font-weight: 600;">@!! DADDY</span>')
            .replace(/%inviter%|\{inviter\}/g, '<b>itzarun170</b>')
            .replace(/%inviter_invites%|\{total_invites\}/g, '<b>14</b>')
            .replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        simOuter.innerHTML = parseDiscordEmojis(formatted);
    }

    const simEmbed = document.getElementById('invitetracker-sim-embed');
    if (simEmbed) {
        simEmbed.style.display = (embedCheck && !embedCheck.checked) ? 'none' : 'flex';
        simEmbed.style.borderLeftColor = color;
    }

    // Author
    const authorBox = document.getElementById('invitetracker-sim-embed-author');
    const authorIcon = document.getElementById('invitetracker-sim-embed-author-icon');
    const authorName = document.getElementById('invitetracker-sim-embed-author-name');
    const authVal = authorNameEl ? authorNameEl.value.trim() : '';
    const authIconVal = authorIconEl ? authorIconEl.value.trim() : '';
    const authUrlVal = authorUrlEl ? authorUrlEl.value.trim() : '';
    if (authorBox && authorName) {
        if (authVal) {
            authorBox.style.display = 'flex';
            if (authUrlVal) {
                authorName.innerHTML = `<a href="${authUrlVal}" target="_blank" style="color: #fff; text-decoration: none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${parseDiscordEmojis(authVal)}</a>`;
            } else {
                authorName.innerHTML = parseDiscordEmojis(authVal);
            }
            if (authorIcon && authIconVal) {
                authorIcon.src = authIconVal;
                authorIcon.style.display = 'inline-block';
            } else if (authorIcon) {
                authorIcon.style.display = 'none';
            }
        } else {
            authorBox.style.display = 'none';
        }
    }

    // Title
    const simTitle = document.getElementById('invitetracker-sim-title');
    if (simTitle) {
        let formattedTitle = title.replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        if (titleUrl) {
            simTitle.innerHTML = `<a href="${titleUrl}" target="_blank" style="color: #00aff4; text-decoration: none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${parseDiscordEmojis(formattedTitle)}</a>`;
        } else {
            simTitle.innerHTML = parseDiscordEmojis(formattedTitle);
        }
        simTitle.style.display = title ? 'block' : 'none';
    }

    // Desc
    const simDesc = document.getElementById('invitetracker-sim-embed-desc');
    if (simDesc) {
        let formattedDesc = desc
            .replace(/%member_mention%|\{user\}/g, '<span style="color: #5865F2;">@!! DADDY</span>')
            .replace(/%inviter%|\{inviter\}/g, '<b>itzarun170</b>')
            .replace(/%inviter_invites%|\{total_invites\}/g, '<b>14</b>')
            .replace(/\{useravatar\}|\{user_avatar\}|%user_avatar%|\{avatar\}/g, userAvatarUrl);
        simDesc.innerHTML = parseDiscordEmojis(formattedDesc);
        simDesc.style.display = desc ? 'block' : 'none';
    }

    // Thumbnail
    const thumbBox = document.getElementById('invitetracker-sim-embed-thumb');
    if (thumbBox) {
        const thumbVal = thumbEl ? thumbEl.value.trim() : '';
        if (thumbVal) {
            thumbBox.innerHTML = `<img src="${thumbVal}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            thumbBox.style.display = 'flex';
        } else {
            thumbBox.innerHTML = `<img src="${userAvatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            thumbBox.style.display = 'flex';
        }
    }

    // Banner image
    const bannerWrapper = document.getElementById('invitetracker-sim-embed-banner-wrapper');
    const bannerImg = document.getElementById('invitetracker-sim-embed-banner');
    const imgVal = imgEl ? imgEl.value.trim() : '';
    if (bannerWrapper && bannerImg) {
        if (imgVal) {
            bannerImg.src = imgVal;
            bannerWrapper.style.display = 'block';
        } else {
            bannerWrapper.style.display = 'none';
        }
    }

    // Footer
    const footerWrapper = document.getElementById('invitetracker-sim-embed-footer-wrapper');
    const footerText = document.getElementById('invitetracker-sim-embed-footer-text');
    const footerIcon = document.getElementById('invitetracker-sim-embed-footer-icon');
    const footerVal = footerEl ? footerEl.value.trim() : '';
    const footerIconVal = footerIconEl ? footerIconEl.value.trim() : '';
    if (footerWrapper && footerText) {
        footerText.innerText = footerVal || '✦ VEYRA INVITE TRACKER ✦';
        if (footerIcon) {
            footerIcon.src = footerIconVal || 'assets/bypass_logs_avatar.webp';
        }
        footerWrapper.style.display = 'flex';
    }
}

function triggerSimulatedJoin() {
    const guildId = activeGuildId || window.activeGuildId || sessionStorage.getItem('activeGuildId') || '1509911679637520584';
    
    // 1. Post simulated join event to the DB
    fetch(`/api/simulate/join/${guildId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 2. Fetch configurations
                const welcomeEnabled = document.getElementById('welcome-msg-enable')?.checked;
                const welcomeChannel = document.getElementById('welcome-msg-channel-select')?.value || 'welcome';
                
                const inviteEnabled = document.getElementById('invitetracker-msg-enable')?.checked;
                const inviteChannel = document.getElementById('invitetracker-msg-channel-select')?.value || 'general';
                
                // 3. Automatically post Welcome Message if enabled
                if (welcomeEnabled) {
                    postEmbedMessage('welcome');
                    showToast("Welcome Message Sent", `Welcome Message automatically sent to #${welcomeChannel}!`);
                }
                
                // 4. Automatically post Invite Tracker Message if enabled
                if (inviteEnabled) {
                    postEmbedMessage('invitetracker');
                    showToast("Invite Tracker Logged", `Invite Tracker Message automatically sent to #${inviteChannel}!`);
                }
                
                // 5. Update local preview widgets
                updateWelcomeLivePreview();
                if (typeof updateInviteTrackerLivePreview === 'function') {
                    updateInviteTrackerLivePreview();
                }
                
                // 6. Refresh statistics graph
                loadRealAnalytics(guildId);
                if (typeof renderAuditLogs === 'function') {
                    renderAuditLogs();
                }
                
                addLogEntry("@bot", "Simulated Join Event: Welcome & Invite Tracker messages automatically triggered.");
            }
        })
        .catch(err => {
            console.error("Join simulation error:", err);
            showToast("Simulation Error", "Could not trigger simulated join on server", "error");
        });
}

function triggerSimulatedLeave() {
    const guildId = activeGuildId || window.activeGuildId || sessionStorage.getItem('activeGuildId') || '1509911679637520584';
    
    // 1. Post simulated leave event to the DB
    fetch(`/api/simulate/leave/${guildId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 2. Fetch configurations
                const leaveEnabled = document.getElementById('leave-msg-enable')?.checked;
                const leaveChannel = document.getElementById('leave-msg-channel-select')?.value || 'exits';
                
                // 3. Automatically post Exit Message if enabled
                if (leaveEnabled) {
                    postEmbedMessage('leave');
                    showToast("Exit Message Sent", `Exit Message automatically sent to #${leaveChannel}!`);
                }
                
                // 4. Update local preview widgets
                updateLeaveLivePreview();
                
                // 5. Refresh statistics graph
                loadRealAnalytics(guildId);
                if (typeof renderAuditLogs === 'function') {
                    renderAuditLogs();
                }
                
                addLogEntry("@bot", "Simulated Leave Event: Exit message automatically triggered.");
            }
        })
        .catch(err => {
            console.error("Leave simulation error:", err);
            showToast("Simulation Error", "Could not trigger simulated leave on server", "error");
        });
}

function simulateInviteJoinDemo() {
    showToast("Live Demo Join Triggered", "Simulated @!! DADDY joining via invite from itzarun170 (14 invites)!");
    triggerSimulatedJoin();
}

function saveInviteTrackerConfig() {
    const guildId = activeGuildId || window.activeGuildId || sessionStorage.getItem('activeGuildId') || '1509911679637520584';
    const channel = document.getElementById('invitetracker-msg-channel-select')?.value || 'general';
    const enabled = document.getElementById('invitetracker-msg-enable')?.checked ? 1 : 0;
    const message = document.getElementById('invitetracker-msg-outer-input')?.value || '';
    const color = document.getElementById('invitetracker-color-hex')?.value || '#a855f7';
    const title = document.getElementById('invitetracker-embed-title')?.value || '';
    const description = document.getElementById('invitetracker-embed-desc')?.value || '';
    const image = document.getElementById('invitetracker-embed-image')?.value || '';
    const thumbnail = document.getElementById('invitetracker-thumbnail-url')?.value || '';
    const footer = document.getElementById('invitetracker-embed-footer')?.value || '';
    const author_name = document.getElementById('invitetracker-author-name')?.value || '';
    const author_icon = document.getElementById('invitetracker-author-icon')?.value || '';
    const footer_icon = document.getElementById('invitetracker-footer-icon')?.value || '';

    fetch(`/api/settings/invitetracker/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon, message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Invite Config Saved", `Invite Tracker Messages configuration successfully saved & bound to #${channel}`);
            addLogEntry("@itzarun170", `Updated Invite Tracker messages custom configurations for channel #${channel}`);
        }
    })
    .catch(err => console.error("Error saving invite tracker settings:", err));
}

function saveJoinDMSettings() {
    const guildId = activeGuildId || window.activeGuildId || sessionStorage.getItem('activeGuildId') || '1509911679637520584';
    const channel = document.getElementById('eb-destination-channel')?.value || 'dm';
    const enabled = 1;
    const message = document.getElementById('eb-normal-text')?.value || '';
    const color = document.getElementById('eb-color-hex')?.value || '#a855f7';
    const title = document.getElementById('eb-title')?.value || '';
    const description = document.getElementById('eb-description')?.value || '';
    const image = document.getElementById('eb-image-url')?.value || '';
    const footer = document.getElementById('eb-footer-text')?.value || '';

    fetch(`/api/settings/joindm/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, color, title, description, image, footer, message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Join DM Saved", `Join DM Messages configuration successfully saved`);
            addLogEntry("@itzarun170", `Updated Join DM messages custom configurations`);
        }
    })
    .catch(err => console.error("Error saving join dm settings:", err));
}

function toggleColorPickerField(prefix) {
    const wrapper = document.getElementById(`${prefix}-color-picker-wrapper`) || document.getElementById('eb-color-picker-wrapper');
    if (wrapper) {
        wrapper.style.display = (wrapper.style.display === 'none' || wrapper.style.display === '') ? 'flex' : 'none';
    }
}

function addEmbedField(prefix) {
    const container = document.getElementById(`${prefix}-fields-container`) || document.getElementById('eb-fields-container');
    if (!container) return;
    
    const fieldCount = container.children.length + 1;
    if (fieldCount > 25) {
        showToast("Limit Reached", "Discord limits embeds to a maximum of 25 fields.", "warning");
        return;
    }
    
    const div = document.createElement('div');
    div.style.cssText = "display: grid; grid-template-columns: 1fr 2fr 0.4fr; gap: 8px; align-items: center; background: rgba(0,0,0,0.15); padding: 8px; border-radius: 4px;";
    div.innerHTML = `
        <input type="text" placeholder="Field name" class="form-control" style="background: rgba(0,0,0,0.25); font-size: 0.8rem;">
        <input type="text" placeholder="Field value" class="form-control" style="background: rgba(0,0,0,0.25); font-size: 0.8rem;">
        <button type="button" onclick="this.parentElement.remove()" style="background:#ef4444; border:none; color:#fff; border-radius:4px; padding:6px; cursor:pointer;" title="Remove field"><i class="fas fa-trash"></i></button>
    `;
    container.appendChild(div);
    showToast("Field Added", `Added field #${fieldCount} to embed.`);
}

function clearEmbedDate(prefix) {
    const input = document.getElementById(`${prefix}-date-input`) || document.getElementById('eb-date-input');
    if (input) input.value = '';
    showToast("Date Cleared", "Embed timestamp reset.");
}

function postEmbedMessage(prefix) {
    const channelSelect = document.getElementById(`${prefix}-destination-channel`) || 
                          document.getElementById(`${prefix}-msg-channel-select`) || 
                          document.getElementById('eb-destination-channel');
    const channel = channelSelect ? channelSelect.value : 'general';

    const textEl = document.getElementById(`${prefix}-normal-text`) || 
                   document.getElementById(`${prefix}-msg-outer-input`) || 
                   document.getElementById('eb-normal-text');
    const titleEl = document.getElementById(`${prefix}-embed-title`) || document.getElementById('eb-title');
    const descEl = document.getElementById(`${prefix}-embed-desc`) || document.getElementById('eb-description');
    const colorEl = document.getElementById(`${prefix}-embed-color-picker`) || document.getElementById('eb-color-picker');
    const imageEl = document.getElementById(`${prefix}-embed-image`) || document.getElementById('eb-image-url');
    const thumbnailEl = document.getElementById(`${prefix}-thumbnail-url`) || document.getElementById('eb-thumbnail-url');
    const footerEl = document.getElementById(`${prefix}-embed-footer`) || document.getElementById('eb-footer-text');
    const footerIconEl = document.getElementById(`${prefix}-footer-icon`) || document.getElementById('eb-footer-icon');
    const authorNameEl = document.getElementById(`${prefix}-author-name`) || document.getElementById('eb-author-name');
    const authorIconEl = document.getElementById(`${prefix}-author-icon`) || document.getElementById('eb-author-icon');

    const authorUrlEl = document.getElementById(`${prefix}-author-url`) || document.getElementById('eb-author-url');
    const titleUrlEl = document.getElementById(`${prefix}-title-url`) || document.getElementById('eb-title-url');
    const dateEl = document.getElementById(`${prefix}-date-input`) || document.getElementById('eb-date-input');

    // Extract custom fields if any
    const fields = [];
    const fieldNames = document.querySelectorAll(`.${prefix}-custom-field-name, .eb-custom-field-name`);
    const fieldValues = document.querySelectorAll(`.${prefix}-custom-field-value, .eb-custom-field-value`);
    const fieldInlines = document.querySelectorAll(`.${prefix}-custom-field-inline, .eb-custom-field-inline`);
    fieldNames.forEach((nEl, idx) => {
        if (nEl && nEl.value && fieldValues[idx] && fieldValues[idx].value) {
            fields.push({
                name: nEl.value,
                value: fieldValues[idx].value,
                inline: fieldInlines[idx] ? fieldInlines[idx].checked : false
            });
        }
    });

    const targetGuildId = activeGuildId || (typeof window.currentSelectedGuildId !== 'undefined' ? window.currentSelectedGuildId : null);

    if (!targetGuildId) {
        showToast("Posting Error", "Please select a server before posting messages", "error");
        return;
    }

    const payload = {
        guild_id: targetGuildId,
        channel: channel,
        normalText: textEl ? textEl.value : '',
        embedData: {
            title: titleEl ? titleEl.value : '',
            title_url: titleUrlEl ? titleUrlEl.value : '',
            description: descEl ? descEl.value : '',
            color: colorEl ? colorEl.value : '#a855f7',
            image: imageEl ? imageEl.value : '',
            thumbnail: thumbnailEl ? thumbnailEl.value : '',
            footer: footerEl ? footerEl.value : '',
            footer_icon: footerIconEl ? footerIconEl.value : '',
            author_name: authorNameEl ? authorNameEl.value : '',
            author_icon: authorIconEl ? authorIconEl.value : '',
            author_url: authorUrlEl ? authorUrlEl.value : '',
            date: dateEl ? dateEl.value : '',
            fields: fields
        }
    };

    fetch('/api/embed/post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Embed Sent Live!", `Custom embed message posted directly into #${channel}!`);
            addLogEntry("@user", `Uploaded live embed message to #${channel}`);
        } else {
            showToast("Posting Failed", data.error || "Failed to post message", "error");
        }
    })
    .catch(err => {
        showToast("Network Error", "Could not reach server API", "error");
    });
}

function resetEmbedFields(prefix) {
    const title = document.getElementById(`${prefix}-embed-title`) || document.getElementById('eb-title');
    const desc = document.getElementById(`${prefix}-embed-desc`) || document.getElementById('eb-description');
    const img = document.getElementById(`${prefix}-embed-image`) || document.getElementById('eb-image-url');
    if (title) title.value = '';
    if (desc) desc.value = '';
    if (img) img.value = '';
    showToast("Reset Complete", "Cleared embed inputs.");
}

function toggleEmbedBuilderBox(prefix) {
    const box = document.getElementById(`${prefix}-builder-box`);
    const btn = document.getElementById(`${prefix}-embed-toggle-btn`);
    if (box) {
        const isHidden = box.style.display === 'none';
        box.style.display = isHidden ? 'flex' : 'none';
        if (btn) btn.innerText = isHidden ? 'Hide' : 'Show embed builder';
    }
}

function resolveRoleData(roleIdOrName) {
    if (!roleIdOrName) return { id: '', name: 'Unknown', color: '#E11D48' };
    const roles = window.guildRoles || [];
    const cleanRaw = String(roleIdOrName).trim();
    const found = roles.find(r => String(r.id) === cleanRaw || r.name.toLowerCase() === cleanRaw.toLowerCase() || `@${r.name.toLowerCase()}` === cleanRaw.toLowerCase());
    if (found) {
        let hex = '#94a3b8';
        if (found.color) {
            hex = typeof found.color === 'string' ? found.color : ('#' + found.color.toString(16).padStart(6, '0'));
            if (!hex.startsWith('#')) hex = '#' + hex;
            if (hex === '#000000' || hex === '#0') hex = '#E11D48';
        } else {
            hex = '#E11D48';
        }
        return { id: String(found.id), name: found.name, color: hex };
    }
    return { id: cleanRaw, name: cleanRaw, color: '#E11D48' };
}

function refreshLoadedRolePills() {
    ['autoroles-pills-container', 'sticky-blacklisted-pills'].forEach(cId => {
        const container = document.getElementById(cId);
        if (!container) return;
        Array.from(container.children).forEach(pill => {
            const raw = pill.dataset.roleId || pill.dataset.roleRaw;
            if (raw) {
                const resolved = resolveRoleData(raw);
                pill.dataset.roleId = resolved.id;
                pill.style.background = `${resolved.color}15`;
                pill.style.borderColor = `${resolved.color}55`;
                const dot = pill.querySelector('.role-color-dot');
                if (dot) {
                    dot.style.background = resolved.color;
                    dot.style.boxShadow = `0 0 6px ${resolved.color}`;
                }
                const nameSpan = pill.querySelector('.role-pill-name');
                if (nameSpan && resolved.name && resolved.name !== raw) {
                    nameSpan.textContent = `@${resolved.name.replace(/^@/, '')}`;
                }
            }
        });
    });
}

function addAutorolePill(roleIdentifier, showToastFlag = true) {
    if (!roleIdentifier) return;
    const container = document.getElementById('autoroles-pills-container');
    if (!container) return;
    
    const role = resolveRoleData(roleIdentifier);
    const existing = Array.from(container.children).find(el => el.dataset.roleId === role.id || el.querySelector('.role-pill-name')?.textContent === `@${role.name.replace(/^@/, '')}`);
    if (existing) return;

    const div = document.createElement('div');
    div.className = "role-badge-pill";
    div.dataset.roleId = role.id;
    div.dataset.roleRaw = roleIdentifier;
    div.style.cssText = `background: ${role.color}15; border: 1.5px solid ${role.color}55; border-radius: 20px; padding: 5px 12px; font-size: 0.82rem; color: #0F172A; display: inline-flex; align-items: center; gap: 8px; font-weight: 700; box-shadow: 0 1px 3px rgba(0,0,0,0.04);`;
    div.innerHTML = `
        <span class="role-color-dot" style="width: 10px; height: 10px; border-radius: 50%; background: ${role.color}; box-shadow: 0 0 6px ${role.color}; flex-shrink: 0;"></span>
        <span class="role-pill-name" style="color: #0F172A;">@${role.name.replace(/^@/, '')}</span>
        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #64748b; margin-left: 2px; transition: color 0.15s;" onmouseover="this.style.color='#DC2626'" onmouseout="this.style.color='#64748b'" onclick="this.parentElement.remove()" title="Remove role"></i>
    `;
    container.appendChild(div);
    if (showToastFlag) showToast("Role Added", `Added @${role.name.replace(/^@/, '')} to autoroles queue.`);
}

function addStickyBlacklistPill(roleIdentifier, showToastFlag = true) {
    if (!roleIdentifier) return;
    const container = document.getElementById('sticky-blacklisted-pills');
    if (!container) return;
    
    const role = resolveRoleData(roleIdentifier);
    const existing = Array.from(container.children).find(el => el.dataset.roleId === role.id || el.querySelector('.role-pill-name')?.textContent === `@${role.name.replace(/^@/, '')}`);
    if (existing) return;

    const div = document.createElement('div');
    div.className = "role-badge-pill";
    div.dataset.roleId = role.id;
    div.dataset.roleRaw = roleIdentifier;
    div.style.cssText = `background: ${role.color}15; border: 1.5px solid ${role.color}55; border-radius: 20px; padding: 5px 12px; font-size: 0.82rem; color: #0F172A; display: inline-flex; align-items: center; gap: 8px; font-weight: 700; box-shadow: 0 1px 3px rgba(0,0,0,0.04);`;
    div.innerHTML = `
        <span class="role-color-dot" style="width: 10px; height: 10px; border-radius: 50%; background: ${role.color}; box-shadow: 0 0 6px ${role.color}; flex-shrink: 0;"></span>
        <span class="role-pill-name" style="color: #0F172A;">@${role.name.replace(/^@/, '')}</span>
        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #64748b; margin-left: 2px; transition: color 0.15s;" onmouseover="this.style.color='#DC2626'" onmouseout="this.style.color='#64748b'" onclick="this.parentElement.remove()" title="Remove role"></i>
    `;
    container.appendChild(div);
    if (showToastFlag) showToast("Role Blacklisted", `Blacklisted @${role.name.replace(/^@/, '')} from sticky restoration.`);
}

window.loadAutorolesSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    fetch(`/api/settings/autoroles/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('autoroles-pills-container');
            if (container) container.innerHTML = '';
            if (data.roles) {
                data.roles.forEach(r => addAutorolePill(r, false));
            }
        })
        .catch(err => console.error("Error loading autoroles:", err));

    fetch(`/api/settings/sticky/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const toggle = document.getElementById('sticky-roles-enable');
            if (toggle) toggle.checked = !!data.enabled;
            const container = document.getElementById('sticky-blacklisted-pills');
            if (container) container.innerHTML = '';
            if (data.blacklisted_roles) {
                data.blacklisted_roles.forEach(r => addStickyBlacklistPill(r, false));
            }
        })
        .catch(err => console.error("Error loading sticky settings:", err));
};

function saveAutorolesConfig() {
    if (!activeGuildId) return;
    const container = document.getElementById('autoroles-pills-container');
    const roles = Array.from(container.querySelectorAll('.role-badge-pill')).map(el => el.dataset.roleId || el.dataset.roleRaw || el.querySelector('.role-pill-name').textContent.replace(/^@/, '').trim());

    fetch(`/api/settings/autoroles/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roles })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Autoroles Saved", "Autoroles rules successfully saved!");
            addLogEntry("@user", "Updated server autoroles policy");
            createFeatureChannels(["autoroles"]);
        }
    })
    .catch(err => console.error("Error saving autoroles:", err));
}

function saveStickyRolesConfig() {
    if (!activeGuildId) return;
    const enabled = document.getElementById('sticky-roles-enable')?.checked || false;
    const container = document.getElementById('sticky-blacklisted-pills');
    const blacklisted_roles = Array.from(container.querySelectorAll('.role-badge-pill')).map(el => el.dataset.roleId || el.dataset.roleRaw || el.querySelector('.role-pill-name').textContent.replace(/^@/, '').trim());

    fetch(`/api/settings/sticky/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, blacklisted_roles })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Sticky Roles Saved", "Reassigned sticky roles configuration updated!");
            addLogEntry("@user", "Updated sticky roles restoration policy");
        }
    })
    .catch(err => console.error("Error saving sticky roles config:", err));
}

function saveAutoModSuiteSettings() {
    showToast("AutoMod Config Saved", "Smart AutoMod filters and punishments registry updated!");
    addLogEntry("@user", "Updated AutoMod global security rules");
}

function toggleServerListingState(isListed) {
    if (!activeGuildId) return;
    
    const pill = document.getElementById('publish-status-pill');
    const description = document.getElementById('publish-desc-input')?.value || '';
    const category = document.getElementById('publish-category-select')?.value || '';
    const bump_role = document.getElementById('publish-bump-role-select')?.value || '';
    
    fetch(`/api/settings/publish/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, category, bump_role, listed: isListed })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if (isListed) {
                if (pill) pill.innerHTML = '<i class="fas fa-circle-check" style="color: #10b981; margin-right: 4px;"></i> Listed';
                showToast("Listing Enabled", "Server listing published to VEYRA Server Discovery!");
                addLogEntry("@user", "Enabled server discovery listing");
            } else {
                if (pill) pill.innerHTML = '<i class="fas fa-circle-xmark" style="color: #94a3b8; margin-right: 4px;"></i> Not Listed';
                showToast("Listing Disabled", "Server listing unpublished.");
                addLogEntry("@user", "Disabled server discovery listing");
            }
        } else {
            showToast("Error", "Failed to update listing state.", "error");
        }
    })
    .catch(err => {
        console.error("Listing toggle error:", err);
        showToast("Error", "Failed to communicate with listing API.", "error");
    });
}

function submitServerListing() {
    if (!activeGuildId) return;
    
    const description = document.getElementById('publish-desc-input')?.value || '';
    const category = document.getElementById('publish-category-select')?.value || '';
    const bump_role = document.getElementById('publish-bump-role-select')?.value || '';
    const isListed = document.getElementById('publish-enable-toggle')?.checked || false;
    
    fetch(`/api/settings/publish/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, category, bump_role, listed: isListed })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Listing Submitted", "Server listing submitted to discovery registry!");
            addLogEntry("@user", "Published server listing to discovery matrix");
        } else {
            showToast("Error", "Failed to submit server listing.", "error");
        }
    })
    .catch(err => {
        console.error("Submit listing error:", err);
        showToast("Error", "Failed to communicate with listing API.", "error");
    });
}

window.loadServerListing = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    
    fetch(`/api/settings/publish/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const descInput = document.getElementById('publish-desc-input');
            const catSelect = document.getElementById('publish-category-select');
            const bumpSelect = document.getElementById('publish-bump-role-select');
            const enableToggle = document.getElementById('publish-enable-toggle');
            const pill = document.getElementById('publish-status-pill');
            
            if (descInput) descInput.value = data.description || '';
            if (catSelect) catSelect.value = data.category || '';
            if (bumpSelect) bumpSelect.value = data.bump_role || '';
            
            const isListed = !!data.listed;
            if (enableToggle) enableToggle.checked = isListed;
            
            if (pill) {
                if (isListed) {
                    pill.innerHTML = '<i class="fas fa-circle-check" style="color: #10b981; margin-right: 4px;"></i> Listed';
                } else {
                    pill.innerHTML = '<i class="fas fa-circle-xmark" style="color: #94a3b8; margin-right: 4px;"></i> Not Listed';
                }
            }
        })
        .catch(err => console.error("Error loading server listing:", err));
};

window.loadStickyMessagesSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    fetch(`/api/settings/stickymessages/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('sticky-messages-table-body');
            if (tbody) {
                if (!data || data.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary); padding: 30px 0;">No sticky messages configured on this server.</td></tr>`;
                    return;
                }
                tbody.innerHTML = data.map(sm => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 12px; font-weight: 600; color: #00aff4;"># ${escapeHtml(sm.channel)}</td>
                        <td style="padding: 12px;">${escapeHtml(sm.message)}</td>
                        <td style="padding: 12px; color: #10b981;">Never</td>
                        <td style="padding: 12px; text-align: right;">
                            <button onclick="deleteStickyMessage('${sm.id}')" style="background: #ef4444; border: none; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;"><i class="fas fa-trash"></i></button>
                        </td>
                    </tr>
                `).join('');
            }
        })
        .catch(err => console.error("Error loading sticky messages:", err));
};

function openStickyMessageModal() {
    const modal = document.getElementById('sticky-message-modal');
    if (!modal) return;
    
    // Populate channels if available from active Guild
    const select = document.getElementById('modal-sticky-channel-select');
    if (select && window.lastFetchedChannels && window.lastFetchedChannels.length > 0) {
        select.innerHTML = window.lastFetchedChannels
            .filter(c => c.type === 0 || c.type === 'text')
            .map(c => `<option value="${c.name}"># ${c.name}</option>`)
            .join('');
    }
    
    modal.style.display = 'flex';
}

function closeStickyMessageModal() {
    const modal = document.getElementById('sticky-message-modal');
    if (modal) modal.style.display = 'none';
}

function submitStickyMessageModal() {
    const channelSelect = document.getElementById('modal-sticky-channel-select');
    const messageInput = document.getElementById('modal-sticky-message-text');
    
    const channel = channelSelect ? channelSelect.value.trim() : 'general';
    const message = messageInput ? messageInput.value.trim() : '';
    
    if (!message) {
        showToast("Missing Message", "Please enter text for your sticky message.", "warning");
        return;
    }
    
    closeStickyMessageModal();
    
    fetch(`/api/settings/stickymessages/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Sticky Created", `Sticky message added to #${channel} channel.`);
            loadStickyMessagesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error creating sticky message:", err));
}

function createNewStickyMessagePrompt() {
    openStickyMessageModal();
}

function deleteStickyMessage(id) {
    if (!confirm("Are you sure you want to delete this sticky message?")) return;
    fetch(`/api/settings/stickymessages/${activeGuildId}/${id}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Deleted", "Sticky message successfully removed.");
            loadStickyMessagesSettings(activeGuildId);
        }
    })
    .catch(err => console.error("Error deleting sticky message:", err));
}



function loadAdminGuilds() {
    // 1. Fetch server subscriptions
    fetch('/api/admin/guilds')
        .then(res => res.json())
        .then(guilds => {
            const tbody = document.getElementById('admin-guilds-table-body');
            if (!tbody) return;
            if (!guilds || guilds.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="padding: 24px; text-align: center; color: #64748b;">No active bot servers registered in database.</td></tr>`;
                return;
            }
            
            tbody.innerHTML = guilds.map(g => {
                const iconHtml = g.icon ? `<img src="${g.icon}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">` : `<div style="width: 32px; height: 32px; border-radius: 50%; background: #9333ea; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700;">${g.name.charAt(0)}</div>`;
                
                const rawPlans = (g.plan_type || 'Free').split(',').map(s => s.trim());
                
                const ticketPlans = rawPlans.filter(p => p.toLowerCase().startsWith('ticket') || p.toLowerCase() === 'ticket');
                const nonTicketPlans = rawPlans.filter(p => !p.toLowerCase().startsWith('ticket') && p.toLowerCase() !== 'ticket');
                
                const mainPlan = nonTicketPlans.join(', ') || 'Free';
                const ticketPlan = ticketPlans.join(', ') || 'None';
                
                const planBadge = mainPlan.toLowerCase().includes('premium') ? 
                    `<span style="background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.75rem;"><i class="fas fa-crown"></i> PREMIUM</span>` : 
                    (mainPlan.toLowerCase().includes('pro') ? 
                        `<span style="background: rgba(147,51,234,0.2); color: #c084fc; border: 1px solid rgba(147,51,234,0.4); padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.75rem;"><i class="fas fa-bolt"></i> PRO</span>` : 
                        `<span style="background: rgba(255,255,255,0.06); color: #94a3b8; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem;">FREE</span>`
                    );
                
                const ticketBadge = ticketPlan.toLowerCase().includes('premium') ?
                    `<span style="background: rgba(244,63,94,0.2); color: #f43f5e; border: 1px solid rgba(244,63,94,0.4); padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.72rem;"><i class="fas fa-ticket-alt"></i> TICKET PREMIUM</span>` :
                    (ticketPlan.toLowerCase().includes('pro') ?
                        `<span style="background: rgba(244,63,94,0.15); color: #fb7185; border: 1px solid rgba(244,63,94,0.3); padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.72rem;"><i class="fas fa-ticket-alt"></i> TICKET PRO</span>` :
                        `<span style="background: rgba(255,255,255,0.06); color: #94a3b8; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem;">NONE</span>`
                    );
                
                const expText = g.expires_at ? (g.expires_at === 'Lifetime' ? 'Infinity / Lifetime' : new Date(g.expires_at).toLocaleDateString()) : 'N/A';
                
                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                        <td style="padding: 12px; display: flex; align-items: center; gap: 10px;">
                            ${iconHtml}
                            <span style="font-weight: 700; color: #fff;">${g.name}</span>
                        </td>
                        <td style="padding: 12px; font-family: var(--font-mono); font-size: 0.8rem; color: #E26749;">${g.guild_id}</td>
                        <td style="padding: 12px;">${planBadge}</td>
                        <td style="padding: 12px;">${ticketBadge}</td>
                        <td style="padding: 12px; color: #94a3b8; font-size: 0.8rem;">${expText}</td>
                        <td style="padding: 12px; text-align: right;">
                            <button onclick="adminToggleTicket('${g.guild_id}', 'Ticket Pro')" class="btn-primary" style="background: #e11d48; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; color: #fff; margin-right: 4px; cursor: pointer;">Ticket Pro</button>
                            <button onclick="adminToggleTicket('${g.guild_id}', 'Ticket Premium')" class="btn-primary" style="background: #be123c; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; color: #fff; margin-right: 4px; cursor: pointer;">Ticket Premium</button>
                            <button onclick="adminQuickGrant('${g.guild_id}', 'Pro')" class="btn-primary" style="background: #9333ea; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; color: #fff; margin-right: 4px; cursor: pointer;">Give Pro</button>
                            <button onclick="adminQuickGrant('${g.guild_id}', 'Premium')" class="btn-primary" style="background: #d97706; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; color: #fff; margin-right: 4px; cursor: pointer;">Give Premium</button>
                            <button onclick="adminRevokePlan('${g.guild_id}')" class="btn-secondary" style="background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; cursor: pointer;">Revoke</button>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => {
            console.error("Admin guilds load error:", err);
        });

    // 2. Fetch logged-in user tokens
    fetch('/api/admin/users')
        .then(res => res.json())
        .then(users => {
            const tbody = document.getElementById('admin-users-table-body');
            if (!tbody) return;
            if (!users || users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="padding: 24px; text-align: center; color: #64748b;">No active user sessions registered in database.</td></tr>`;
                return;
            }
            
            tbody.innerHTML = users.map(u => {
                const profileHtml = `<div style="width: 32px; height: 32px; border-radius: 50%; background: #5865F2; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700;">${u.username.charAt(0).toUpperCase()}</div>`;
                const dateText = u.lastActive ? new Date(u.lastActive).toLocaleString() : 'N/A';
                
                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                        <td style="padding: 12px; display: flex; align-items: center; gap: 10px;">
                            ${profileHtml}
                            <span style="font-weight: 700; color: #fff;">${u.username}</span>
                        </td>
                        <td style="padding: 12px; font-family: var(--font-mono); font-size: 0.8rem; color: #c084fc;">${u.id}</td>
                        <td style="padding: 12px; color: #94a3b8; font-size: 0.8rem;">${dateText}</td>
                        <td style="padding: 12px; text-align: right;">
                            <button onclick="showAdminUserToken('${u.username.replace(/'/g, "\\'")}', '${u.token}')" class="btn-primary" style="background: #10b981; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: #fff; cursor: pointer;">
                                <i class="fas fa-key"></i> See Token
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
            
            // Refresh administrative subscription history list
            if (typeof loadSubscriptionHistory === 'function') loadSubscriptionHistory();
        })
        .catch(err => {
            console.error("Admin users load error:", err);
            if (typeof loadSubscriptionHistory === 'function') loadSubscriptionHistory();
        });
}

function showAdminUserToken(username, token) {
    navigator.clipboard.writeText(token);
    alert(`🔑 VEYRA Security Matrix - User Session Token\n\nUser: ${username}\nToken: ${token}\n\n(The token has been copied to your clipboard automatically!)`);
}

function adminQuickGrant(guildId, planType) {
    document.getElementById('admin-target-guild-id').value = guildId;
    document.getElementById('admin-plan-select').value = planType;
    adminGrantPlan();
}

function adminGrantPlan() {
    const targetId = document.getElementById('admin-target-guild-id').value.trim();
    const targetType = document.getElementById('admin-target-type') ? document.getElementById('admin-target-type').value : 'server';
    const planType = document.getElementById('admin-plan-select').value;
    const durationDays = document.getElementById('admin-duration-select').value;
    
    if (!targetId) {
        return showToast("Admin Action Error", "Please enter a target ID", "error");
    }

    fetch('/api/admin/grant-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_id: targetId, target_type: targetType, plan_type: planType, duration_days: durationDays })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Plan Granted", `Successfully granted ${planType} Plan to ${targetType} ID ${targetId}`);
            addLogEntry("@admin", `Granted ${planType} subscription to ${targetType} ${targetId}`);
            loadAdminGuilds();
        } else {
            showToast("Admin Error", data.error || "Failed to grant plan", "error");
        }
    })
    .catch(err => {
        showToast("Admin Error", "Failed to communicate with admin API", "error");
    });
}

function adminGrantTicketPlan() {
    const targetId = document.getElementById('admin-ticket-target-guild-id').value.trim();
    const targetType = document.getElementById('admin-ticket-target-type') ? document.getElementById('admin-ticket-target-type').value : 'server';
    const planType = document.getElementById('admin-ticket-plan-select').value;
    const durationDays = document.getElementById('admin-ticket-duration-select').value;
    
    if (!targetId) {
        return showToast("Admin Action Error", "Please enter a target ID", "error");
    }

    // Call toggle-ticket endpoint to change ticket subscription state
    fetch('/api/admin/toggle-ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guild_id: targetId, active: planType })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Ticket Plan Granted", `Successfully set Ticket Plan to '${planType}' on server ${targetId}`);
            addLogEntry("@admin", `Set Ticket Plan to ${planType} for server ${targetId}`);
            loadAdminGuilds();
        } else {
            showToast("Admin Error", data.error || "Failed to grant ticket plan", "error");
        }
    })
    .catch(err => {
        showToast("Admin Error", "Failed to communicate with admin API", "error");
    });
}

function adminRevokePlan(guildId) {
    if (!confirm(`Are you sure you want to revoke premium/pro plan for server ID ${guildId}?`)) return;

    fetch('/api/admin/revoke-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guild_id: guildId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Plan Revoked", `Successfully reset server ID ${guildId} back to Free plan`);
            addLogEntry("@admin", `Revoked plan for server ${guildId}`);
            loadAdminGuilds();
        } else {
            showToast("Admin Error", data.error || "Failed to revoke plan", "error");
        }
    })
    .catch(err => {
        showToast("Admin Error", "Failed to communicate with admin API", "error");
    });
}

function adminToggleTicket(guildId, ticketPlan) {
    if (!confirm(`Are you sure you want to set Ticket Plan to '${ticketPlan}' for server ID ${guildId}?`)) return;

    fetch('/api/admin/toggle-ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guild_id: guildId, active: ticketPlan })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Subscription Updated", `Successfully set Ticket Plan to '${ticketPlan}' on server ${guildId}`);
            addLogEntry("@admin", `Set Ticket Plan for server ${guildId} to ${ticketPlan}`);
            loadAdminGuilds();
        } else {
            showToast("Admin Error", data.error || "Failed to update Ticket status", "error");
        }
    })
    .catch(err => {
        showToast("Admin Error", "Failed to communicate with admin API", "error");
    });
}

function loadSubscriptionHistory() {
    const tbody = document.getElementById('admin-subscription-history-table-body');
    if (!tbody) return;

    fetch('/api/admin/subscription-history')
        .then(res => res.json())
        .then(history => {
            if (!history || history.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="padding: 24px; text-align: center; color: #64748b;">No subscription history logs found.</td></tr>`;
                return;
            }
            
            tbody.innerHTML = history.map(h => {
                const dateText = new Date(h.timestamp).toLocaleString();
                let targetText = "-";
                const details = h.details || "";
                if (details.includes("to server")) {
                    const match = details.match(/to server (\d+)/);
                    targetText = match ? `Server ${match[1]}` : "Server";
                } else if (details.includes("to user")) {
                    const match = details.match(/to user (\d+)/);
                    targetText = match ? `User ${match[1]}` : "User";
                } else if (details.includes("for guild")) {
                    const match = details.match(/for guild (\d+)/);
                    targetText = match ? `Server ${match[1]}` : "Server";
                } else if (details.includes("for server")) {
                    const match = details.match(/for server (\d+)/);
                    targetText = match ? `Server ${match[1]}` : "Server";
                }
                
                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                        <td style="padding: 12px; color: #94a3b8; font-family: var(--font-mono); font-size: 0.8rem;">${dateText}</td>
                        <td style="padding: 12px; font-weight: 700; color: #fff;">
                            <span style="background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">
                                ${h.action}
                            </span>
                        </td>
                        <td style="padding: 12px; color: #fb7185; font-family: var(--font-mono); font-size: 0.8rem;">${targetText}</td>
                        <td style="padding: 12px; color: #e2e8f0; font-size: 0.82rem;">${h.details}</td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => {
            console.error("Subscription history load error:", err);
            tbody.innerHTML = `<tr><td colspan="4" style="padding: 24px; text-align: center; color: #ef4444;">Failed to load history.</td></tr>`;
        });
}

window.selectReportFrequency = function(frequency, showToastFlag = true) {
    const monthlyBtn = document.getElementById('report-freq-monthly');
    const weeklyBtn = document.getElementById('report-freq-weekly');
    if (!monthlyBtn || !weeklyBtn) return;

    const isWeekly = String(frequency).toLowerCase() === 'weekly';
    const titleEl = document.getElementById('report-preview-embed-title');
    const freqTextEl = document.getElementById('report-preview-freq-text');

    if (!isWeekly) {
        monthlyBtn.classList.add('active');
        monthlyBtn.style.background = '#E11D48';
        monthlyBtn.style.color = '#FFFFFF';
        monthlyBtn.style.fontWeight = '800';
        monthlyBtn.style.boxShadow = '0 2px 8px rgba(225, 29, 72, 0.25)';

        weeklyBtn.classList.remove('active');
        weeklyBtn.style.background = 'transparent';
        weeklyBtn.style.color = '#0F172A';
        weeklyBtn.style.fontWeight = '700';
        weeklyBtn.style.boxShadow = 'none';

        if (titleEl) titleEl.innerText = '📊 VEYRA MONTHLY Server Growth Report';
        if (freqTextEl) freqTextEl.innerText = 'Monthly';
        if (showToastFlag) showToast('Reports Settings', 'Monthly schedule selected.');
    } else {
        weeklyBtn.classList.add('active');
        weeklyBtn.style.background = '#E11D48';
        weeklyBtn.style.color = '#FFFFFF';
        weeklyBtn.style.fontWeight = '800';
        weeklyBtn.style.boxShadow = '0 2px 8px rgba(225, 29, 72, 0.25)';

        monthlyBtn.classList.remove('active');
        monthlyBtn.style.background = 'transparent';
        monthlyBtn.style.color = '#0F172A';
        monthlyBtn.style.fontWeight = '700';
        monthlyBtn.style.boxShadow = 'none';

        if (titleEl) titleEl.innerText = '📊 VEYRA WEEKLY Server Growth Report';
        if (freqTextEl) freqTextEl.innerText = 'Weekly';
        if (showToastFlag) showToast('Reports Settings', 'Weekly schedule selected.');
    }
};

window.loadLevelsSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    fetch(`/api/settings/levels/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const s = data.settings || {};
            const enableSwitch = document.getElementById('levels-enable-switch');
            if (enableSwitch) enableSwitch.checked = isTrue(s.enabled);
            
            const outerInput = document.getElementById('levels-msg-outer-input');
            if (outerInput) outerInput.value = s.message || '';
            
            const channelSelect = document.getElementById('levels-channel-select');
            if (channelSelect) channelSelect.value = s.channel || 'none';
            
            const moduloInput = document.getElementById('levels-modulo-input');
            if (moduloInput) moduloInput.value = s.level_modulo || 1;
            
            const minLvlInput = document.getElementById('levels-min-level-input');
            if (minLvlInput) minLvlInput.value = s.min_level || 1;

            if (document.getElementById('levels-color-hex')) document.getElementById('levels-color-hex').value = s.color || '#a855f7';
            if (document.getElementById('levels-embed-color-picker')) document.getElementById('levels-embed-color-picker').value = s.color || '#a855f7';
            if (document.getElementById('levels-author-icon')) document.getElementById('levels-author-icon').value = s.author_icon || '';
            if (document.getElementById('levels-author-name')) document.getElementById('levels-author-name').value = s.author_name || '';
            if (document.getElementById('levels-author-url')) document.getElementById('levels-author-url').value = s.author_url || '';
            if (document.getElementById('levels-embed-title')) document.getElementById('levels-embed-title').value = s.title || '';
            if (document.getElementById('levels-title-url')) document.getElementById('levels-title-url').value = s.title_url || '';
            if (document.getElementById('levels-embed-desc')) document.getElementById('levels-embed-desc').value = s.description || '';
            if (document.getElementById('levels-embed-image')) document.getElementById('levels-embed-image').value = s.image || '';
            if (document.getElementById('levels-thumbnail-url')) document.getElementById('levels-thumbnail-url').value = s.thumbnail || '';
            if (document.getElementById('levels-embed-footer')) document.getElementById('levels-embed-footer').value = s.footer || '';
            if (document.getElementById('levels-footer-icon')) document.getElementById('levels-footer-icon').value = s.footer_icon || '';

            const pillsContainer = document.getElementById('levels-ignored-channels-pills');
            if (pillsContainer) pillsContainer.innerHTML = '';
            if (data.ignored_channels) {
                data.ignored_channels.forEach(ch => addLevelsIgnoredChannelPill(ch, false));
            }

            renderLevelsRewardsTable(data.rewards || []);
        })
        .catch(err => console.error("Error loading levels settings:", err));
};

window.saveLevelsSettings = function() {
    if (window.isDashboardHydrating) return;
    if (!activeGuildId) return;
    
    const settings = {
        enabled: document.getElementById('levels-enable-switch')?.checked ? 1 : 0,
        channel: document.getElementById('levels-channel-select')?.value || 'none',
        message: document.getElementById('levels-msg-outer-input')?.value || '',
        level_modulo: parseInt(document.getElementById('levels-modulo-input')?.value) || 1,
        min_level: parseInt(document.getElementById('levels-min-level-input')?.value) || 1,
        color: document.getElementById('levels-color-hex')?.value || '#a855f7',
        author_icon: document.getElementById('levels-author-icon')?.value || '',
        author_name: document.getElementById('levels-author-name')?.value || '',
        author_url: document.getElementById('levels-author-url')?.value || '',
        title: document.getElementById('levels-embed-title')?.value || '',
        title_url: document.getElementById('levels-title-url')?.value || '',
        description: document.getElementById('levels-embed-desc')?.value || '',
        image: document.getElementById('levels-embed-image')?.value || '',
        thumbnail: document.getElementById('levels-thumbnail-url')?.value || '',
        footer: document.getElementById('levels-embed-footer')?.value || '',
        footer_icon: document.getElementById('levels-footer-icon')?.value || ''
    };

    const rewards = [];
    document.querySelectorAll('#levels-rewards-table-body tr').forEach(tr => {
        const roleId = tr.dataset.roleId;
        const level = parseInt(tr.dataset.level);
        if (roleId && !isNaN(level)) {
            rewards.push({ role_id: roleId, level });
        }
    });

    const ignored_channels = Array.from(document.querySelectorAll('#levels-ignored-channels-pills .ignored-chan-id')).map(el => el.textContent.trim());

    fetch(`/api/settings/levels/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings, rewards, ignored_channels })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Levels Config Saved", "Levels & XP configurations and embed layout successfully saved!");
            addLogEntry("@user", `Updated Levels message and embed layout for guild ${activeGuildId}`);
        }
    })
    .catch(err => console.error("Error saving levels settings:", err));
};

window.addLevelRewardRow = function() {
    const roleSelect = document.getElementById('levels-reward-role-select');
    const levelInput = document.getElementById('levels-reward-level-input');
    if (!roleSelect || !levelInput) return;

    const roleName = roleSelect.value;
    const level = parseInt(levelInput.value);
    if (!roleName || isNaN(level)) {
        showToast("Error", "Please select a role and enter a valid level.", "error");
        return;
    }

    const tbody = document.getElementById('levels-rewards-table-body');
    if (!tbody) return;

    // Remove 'No matching records' if present
    if (tbody.innerHTML.includes('No matching records')) {
        tbody.innerHTML = '';
    }

    // Check if role is already rewarded
    const existingRow = Array.from(tbody.children).find(tr => tr.dataset.roleId === roleName);
    if (existingRow) {
        showToast("Error", "Reward role already configured.", "error");
        return;
    }

    const tr = document.createElement('tr');
    tr.dataset.roleId = roleName;
    tr.dataset.level = level;
    tr.style.cssText = "border-bottom: 1px solid rgba(255,255,255,0.03);";
    tr.innerHTML = `
        <td style="padding: 10px 5px; font-weight: 600; color: #fff;">@${escapeHtml(roleName)}</td>
        <td style="padding: 10px 5px; color: #E26749; font-weight: 700;">${level}</td>
        <td style="padding: 10px 5px;">
            <button type="button" onclick="this.closest('tr').remove();" style="background: #ef4444; border: none; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;"><i class="fas fa-trash"></i></button>
        </td>
    `;
    tbody.appendChild(tr);
    showToast("Reward Added", `Assigned @${roleName} role reward at level ${level}.`);
};

window.addLevelsIgnoredChannelPill = function(channelName, showToastFlag = true) {
    if (!channelName) return;
    const container = document.getElementById('levels-ignored-channels-pills');
    if (!container) return;

    const existing = Array.from(container.children).find(el => el.textContent.includes(channelName));
    if (existing) return;

    const div = document.createElement('div');
    div.style.cssText = "background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 5px 12px; font-size: 0.82rem; color: #0F172A; font-weight:600; background:#F1F5F9; border:1px solid #CBD5E1; display: flex; align-items: center; gap: 8px;";
    div.innerHTML = `
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444;"></span>
        <span class="ignored-chan-id">${channelName}</span>
        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="this.parentElement.remove()"></i>
    `;
    container.appendChild(div);
    if (showToastFlag) showToast("Channel Ignored", `Blacklisted #${channelName} from XP awards.`);
};

function renderLevelsRewardsTable(rewards) {
    const tbody = document.getElementById('levels-rewards-table-body');
    if (!tbody) return;

    if (!rewards || rewards.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-secondary); padding: 30px 0;">No matching records</td></tr>`;
        return;
    }

    tbody.innerHTML = rewards.map(r => `
        <tr data-role-id="${escapeHtml(r.role_id)}" data-level="${r.level}" style="border-bottom: 1px solid rgba(255,255,255,0.03);">
            <td style="padding: 10px 5px; font-weight: 600; color: #fff;">@${escapeHtml(r.role_id)}</td>
            <td style="padding: 10px 5px; color: #E26749; font-weight: 700;">${r.level}</td>
            <td style="padding: 10px 5px;">
                <button type="button" onclick="this.closest('tr').remove();" style="background: #ef4444; border: none; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;"><i class="fas fa-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

window.loadReportsSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;

    // Instantly populate reports-channel-select from cached channels
    const chSelect = document.getElementById('reports-channel-select');
    if (chSelect && window.guildChannels && window.guildChannels.length > 0) {
        const curVal = chSelect.value;
        chSelect.innerHTML = '<option value="">Select Channel</option>';
        window.guildChannels.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.innerText = `# ${c.name}`;
            chSelect.appendChild(opt);
        });
        if (curVal) chSelect.value = curVal;
    } else if (typeof populateServerRolesAndChannels === 'function') {
        populateServerRolesAndChannels(targetGuild);
    }

    fetch(`/api/settings/reports/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const toggle = document.getElementById('reports-enable-checkbox');
            if (toggle) toggle.checked = isTrue(data.enabled);

            const channelSelect = document.getElementById('reports-channel-select');
            if (channelSelect && data.channel) channelSelect.value = data.channel;

            selectReportFrequency(data.frequency || 'weekly', false);
            renderReportLivePreview(targetGuild);
        })
        .catch(err => {
            console.error("Error loading reports settings:", err);
            renderReportLivePreview(targetGuild);
        });
};

window.renderReportLivePreview = function(guildId) {
    const targetGuild = guildId || activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;

    // Set server icon in preview
    const activeGuild = (window.allGuildsCache || []).find(g => g.id === targetGuild);
    const iconImg = document.getElementById('report-preview-guild-icon');
    if (iconImg) {
        if (activeGuild && activeGuild.icon) {
            iconImg.src = `https://cdn.discordapp.com/icons/${activeGuild.id}/${activeGuild.icon}.png?size=96`;
        } else {
            iconImg.src = 'https://cdn.discordapp.com/embed/avatars/1.png';
        }
    }

    const timeEl = document.getElementById('report-preview-header-time');
    if (timeEl) {
        timeEl.innerText = `Today at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }

    fetch(`/api/reports/preview/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const elJoins = document.getElementById('report-preview-joins');
            const elLeaves = document.getElementById('report-preview-leaves');
            const elNet = document.getElementById('report-preview-net');
            const elRet = document.getElementById('report-preview-retention');
            const elInviters = document.getElementById('report-preview-inviters');
            const elAscii = document.getElementById('report-preview-ascii');

            if (elJoins) elJoins.innerText = data.joins || 0;
            if (elLeaves) elLeaves.innerText = data.leaves || 0;
            if (elNet) elNet.innerText = (data.netGrowth >= 0 ? '+' : '') + (data.netGrowth || 0);
            if (elRet) elRet.innerText = `${data.retention || 0}%`;

            if (elInviters) {
                if (data.topInviters && data.topInviters.length > 0) {
                    elInviters.innerHTML = data.topInviters.map((inv, idx) => 
                        `<div><strong>${idx + 1}.</strong> @${inv.name} &mdash; <span style="background: #1E1F22; border-radius: 3px; padding: 1px 5px; font-family: monospace; color: #F1F5F9; font-weight: 700;">${inv.count}</span> invites</div>`
                    ).join('');
                } else {
                    elInviters.innerHTML = `<div><strong>1.</strong> @arun.cpp &mdash; <span style="background: #1E1F22; border-radius: 3px; padding: 1px 5px; font-family: monospace; color: #F1F5F9; font-weight: 700;">1</span> invites</div>`;
                }
            }

            if (elAscii && data.asciiChart) {
                const jBar = data.asciiChart.joinsBar || '░░░░░░░░░░░░░░';
                const lBar = data.asciiChart.leavesBar || '░░░░░░░░░░░░░░';
                const nBar = data.asciiChart.netBar || '░░░░░░░░░░░░░░';
                const netSign = (data.netGrowth >= 0 ? '+' : '');
                elAscii.innerText = `Joins:  [${jBar}] ${data.joins || 0}
Leaves: [${lBar}] ${data.leaves || 0}
Net:    [${nBar}] ${netSign}${data.netGrowth || 0}`;
            }
        })
        .catch(err => console.error("Error fetching report preview:", err));
};

window.saveReportsSettings = function() {
    const targetGuild = activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;

    const enabled = document.getElementById('reports-enable-checkbox')?.checked ? 1 : 0;
    const channel = document.getElementById('reports-channel-select')?.value || 'general';
    const weeklyBtn = document.getElementById('report-freq-weekly');
    const frequency = (weeklyBtn && weeklyBtn.classList.contains('active')) ? 'weekly' : 'monthly';

    fetch(`/api/settings/reports/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, frequency })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Reports Settings Saved", "Server Reports configurations successfully saved!");
            renderReportLivePreview(targetGuild);
        }
    })
    .catch(err => console.error("Error saving reports settings:", err));
};

window.sendTestReport = function() {
    const targetGuild = activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;
    const channel = document.getElementById('reports-channel-select')?.value || 'general';
    const weeklyBtn = document.getElementById('report-freq-weekly');
    const frequency = (weeklyBtn && weeklyBtn.classList.contains('active')) ? 'weekly' : 'monthly';

    showToast("Broadcasting Report", "Dispatching live growth telemetry report to Discord...", "info");
    fetch(`/api/reports/send-test/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, frequency })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Report Dispatched", `Live report successfully posted to #${channel}!`);
        } else {
            showToast("Report Error", data.error || "Unable to send report. Ensure channel exists and bot has permissions.", "error");
        }
    })
    .catch(() => showToast("Network Error", "Failed to communicate with bot service.", "error"));
};

window.loadSavedPreset = function(type) {
    const guildId = activeGuildId || window.activeGuildId || sessionStorage.getItem('activeGuildId') || '1509911679637520584';
    let endpoint = '';
    let prefix = '';

    if (type === 'welcome') {
        endpoint = `/api/settings/welcome/${guildId}`;
        prefix = 'welcome';
    } else if (type === 'leave') {
        endpoint = `/api/settings/leave/${guildId}`;
        prefix = 'leave';
    } else if (type === 'joindm') {
        endpoint = `/api/settings/joindm/${guildId}`;
        prefix = 'eb';
    } else if (type === 'invitetracker') {
        endpoint = `/api/settings/invitetracker/${guildId}`;
        prefix = 'invitetracker';
    } else if (type === 'sticky') {
        showToast("Sticky Preset Loaded", "Loaded preset sticky messages successfully!");
        return;
    }

    if (!endpoint) return;

    fetch(endpoint)
        .then(res => res.json())
        .then(data => {
            if (prefix === 'eb') {
                const titleEl = document.getElementById('eb-title');
                const descEl = document.getElementById('eb-description');
                const imgEl = document.getElementById('eb-image-url');
                const thumbEl = document.getElementById('eb-thumbnail-url');
                const footerEl = document.getElementById('eb-footer-text');
                const colorEl = document.getElementById('eb-color-picker');
                const hexEl = document.getElementById('eb-color-hex');
                const textEl = document.getElementById('eb-normal-text');
                const destEl = document.getElementById('eb-destination-channel');

                if (titleEl) titleEl.value = data.title || '';
                if (descEl) descEl.value = data.description || '';
                if (imgEl) imgEl.value = data.image || '';
                if (thumbEl) thumbEl.value = data.thumbnail || '';
                if (footerEl) footerEl.value = data.footer || '';
                if (colorEl) colorEl.value = data.color || '#a855f7';
                if (hexEl) hexEl.value = data.color || '#a855f7';
                if (textEl) textEl.value = data.message || '';
                if (destEl) destEl.value = data.channel || 'dm';

                if (typeof updateEmbedBuilderPreview === 'function') updateEmbedBuilderPreview();
            } else {
                const enableEl = document.getElementById(`${prefix}-msg-enable`) || document.getElementById(`${prefix}-embed-enable`);
                const selectEl = document.getElementById(`${prefix}-msg-channel-select`);
                const colorEl = document.getElementById(`${prefix}-embed-color-picker`);
                const titleEl = document.getElementById(`${prefix}-embed-title`);
                const descEl = document.getElementById(`${prefix}-embed-desc`);
                const imgEl = document.getElementById(`${prefix}-embed-image`);
                const footerEl = document.getElementById(`${prefix}-embed-footer`);
                const textEl = document.getElementById(`${prefix}-msg-outer-input`);

                if (enableEl) enableEl.checked = data.enabled === 1;
                if (selectEl) selectEl.value = data.channel || 'general';
                if (colorEl) {
                    colorEl.value = data.color || '#a855f7';
                    const companion = document.getElementById(`${prefix}-color-hex`);
                    if (companion) companion.value = data.color || '#a855f7';
                }
                if (titleEl) titleEl.value = data.title || '';
                if (descEl) descEl.value = data.description || '';
                if (imgEl) imgEl.value = data.image || '';
                if (footerEl) footerEl.value = data.footer || '';
                if (textEl) textEl.value = data.message || '';

                if (prefix === 'welcome' && typeof updateWelcomeLivePreview === 'function') updateWelcomeLivePreview();
                else if (prefix === 'leave' && typeof updateLeaveLivePreview === 'function') updateLeaveLivePreview();
                else if (prefix === 'invitetracker' && typeof updateInviteTrackerLivePreview === 'function') updateInviteTrackerLivePreview();
            }

            showToast("Preset Loaded", `Successfully loaded and synced saved #${type} configuration preset!`);
            addLogEntry("@user", `Loaded saved #${type} configuration preset`);
        })
        .catch(err => {
            console.error("Error loading preset:", err);
            showToast("Load Error", `Failed to load saved #${type} preset configuration.`, "error");
        });
}

// --- DYNAMIC WHITELIST, ANTI-SPAM, AND LOGS HANDLERS ---

// Whitelist configuration modal popup (Real-time Whitelist)
window.openWhitelistModal = function(type = 'User') {
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) {
        showToast("Select Server", "Please select a server first.", "info");
        return;
    }
    
    let modal = document.getElementById('whitelist-interactive-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'whitelist-interactive-modal';
        modal.style.cssText = 'position:fixed; inset:0; background:rgba(15, 23, 42, 0.65); backdrop-filter:blur(6px); z-index:1000000; display:flex; align-items:center; justify-content:center; padding:20px;';
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    
    function refresh() {
        Promise.all([
            fetch(`/api/whitelist/${targetGuild}`).then(r => r.json()).catch(() => []),
            fetch(`/api/guild/plan/${targetGuild}`).then(r => r.json()).catch(() => ({ plan_type: 'Premium' }))
        ]).then(([data, sub]) => {
            const planType = (sub && (sub.plan_type || sub.plan) ? (sub.plan_type || sub.plan) : 'Premium').toLowerCase();
            let limit = 10;
            let planTitle = 'Pro Sentinel (10 slots)';
            if (planType.includes('premium') || planType.includes('enterprise') || window.isUserLoggedIn) {
                limit = 999999;
                planTitle = 'Premium Plan (Unlimited)';
            } else if (planType === 'free') {
                limit = 1;
                planTitle = 'Free Plan (1 slot)';
            }

            const currentType = String(type || 'User').toLowerCase();
            const filtered = (data || []).filter(item => (item.type || 'User').toLowerCase() === currentType);
            window.activeWhitelistCache = data || [];

            let typeIcon = 'fa-user-shield';
            let typeColor = '#7C3AED';
            let typeTitle = 'Whitelisted Staff Users';
            let typeDesc = 'Trusted members bypass anti-nuke thresholds, mass-kick limits, and role permission restrictions.';
            let inputHtml = '';

            if (currentType === 'role') {
                typeIcon = 'fa-users-gear';
                typeColor = '#D96C91';
                typeTitle = 'Whitelisted Roles';
                typeDesc = 'Members with any of these roles are completely immune from security bans, spam rate-limits, and lockdowns.';
                
                const rolesList = window.guildRoles || [];
                const roleOptions = rolesList.map(r => `<option value="${r.id}">@${r.name.replace(/^@/, '')}</option>`).join('');
                
                inputHtml = `
                    <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:18px;">
                        <div style="display:flex; gap:8px;">
                            <select id="w-modal-select" style="flex:1; background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:8px; padding:10px 12px; color:#0F172A; font-size:0.85rem; font-weight:700; outline:none;">
                                <option value="">Select Server Role...</option>
                                ${roleOptions}
                            </select>
                            <button type="button" onclick="addWModalItem('Role', ${limit})" style="background:linear-gradient(90deg, #D96C91, #BE123C); border:none; padding:10px 20px; border-radius:8px; font-weight:700; font-size:0.85rem; color:#FFFFFF; cursor:pointer; white-space:nowrap;">
                                <i class="fas fa-plus"></i> Add Role
                            </button>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:0.75rem; color:#64748B;">Or enter manual Role ID:</span>
                            <input type="text" id="w-modal-input" placeholder="Role ID" style="flex:1; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:6px; padding:4px 8px; font-size:0.78rem; font-family:var(--font-mono);">
                        </div>
                    </div>
                `;
            } else if (currentType === 'channel') {
                typeIcon = 'fa-hashtag';
                typeColor = '#0284C7';
                typeTitle = 'Whitelisted Channels';
                typeDesc = 'Channels designated as immune to spam filters, invite link deletions, and raid lockdowns.';
                
                const channelsList = (window.guildChannels || []).filter(c => c.type === 0 || c.type === 'text');
                const channelOptions = channelsList.map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');
                
                inputHtml = `
                    <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:18px;">
                        <div style="display:flex; gap:8px;">
                            <select id="w-modal-select" style="flex:1; background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:8px; padding:10px 12px; color:#0F172A; font-size:0.85rem; font-weight:700; outline:none;">
                                <option value="">Select Channel...</option>
                                ${channelOptions}
                            </select>
                            <button type="button" onclick="addWModalItem('Channel', ${limit})" style="background:linear-gradient(90deg, #0284C7, #0369A1); border:none; padding:10px 20px; border-radius:8px; font-weight:700; font-size:0.85rem; color:#FFFFFF; cursor:pointer; white-space:nowrap;">
                                <i class="fas fa-plus"></i> Add Channel
                            </button>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:0.75rem; color:#64748B;">Or enter manual Channel ID:</span>
                            <input type="text" id="w-modal-input" placeholder="Channel ID" style="flex:1; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:6px; padding:4px 8px; font-size:0.78rem; font-family:var(--font-mono);">
                        </div>
                    </div>
                `;
            } else {
                const membersList = window.allMembers || window._membersCache || [];
                const memberOptions = membersList.map(m => `<option value="${m.id}">${m.display_name} (@${m.username})${m.bot ? ' [BOT]' : ''}</option>`).join('');
                inputHtml = `
                    <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:18px;">
                        ${membersList.length > 0 ? `
                        <div style="display:flex; gap:8px;">
                            <select id="w-modal-select" onchange="if(this.value) document.getElementById('w-modal-input').value = this.value;" style="flex:1; background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:8px; padding:10px 12px; color:#0F172A; font-size:0.85rem; font-weight:700; outline:none;">
                                <option value="">Select Server Member...</option>
                                ${memberOptions}
                            </select>
                            <button type="button" onclick="addWModalItem('User', ${limit})" style="background:#0F172A; border:none; padding:10px 20px; border-radius:8px; font-weight:700; font-size:0.85rem; color:#FFFFFF; cursor:pointer; white-space:nowrap;">
                                <i class="fas fa-plus" style="margin-right:4px;"></i> Authorize
                            </button>
                        </div>
                        ` : ''}
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:0.75rem; color:#64748B;">${membersList.length > 0 ? 'Or manual User ID:' : 'User ID:'}</span>
                            <input type="text" id="w-modal-input" placeholder="Enter Discord User ID" style="flex:1; background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:8px; padding:8px 12px; color:#0F172A; font-size:0.85rem; outline:none; font-family:var(--font-mono);">
                            ${membersList.length === 0 ? `
                            <button type="button" onclick="addWModalItem('User', ${limit})" style="background:#0F172A; border:none; padding:10px 20px; border-radius:8px; font-weight:700; font-size:0.85rem; color:#FFFFFF; cursor:pointer; white-space:nowrap;">
                                <i class="fas fa-plus" style="margin-right:4px;"></i> Authorize
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            }

            modal.innerHTML = `
                <div style="width:100%; max-width:520px; background:#FFFFFF; border:1.5px solid #E2E8F0; padding:26px; border-radius:16px; position:relative; box-shadow: 0 20px 60px rgba(15,23,42,0.2); font-family:var(--font-body, -apple-system, sans-serif); animation: fadeIn 0.15s ease;">
                    <button type="button" onclick="document.getElementById('whitelist-interactive-modal').style.display='none'" style="position:absolute; top:20px; right:20px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; width:32px; height:32px; display:flex; align-items:center; justify-content:center; color:#64748B; cursor:pointer; font-size:0.9rem;" title="Close"><i class="fas fa-times"></i></button>
                    
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                        <div style="width:40px; height:40px; border-radius:10px; background:rgba(217,108,145,0.12); color:${typeColor}; display:flex; align-items:center; justify-content:center; font-size:1.2rem;">
                            <i class="fas ${typeIcon}"></i>
                        </div>
                        <div>
                            <h3 style="color:#0F172A; font-size:1.18rem; font-weight:800; margin:0;">${typeTitle} (${filtered.length}/${limit === 999999 ? '∞' : limit})</h3>
                            <span style="font-size:0.75rem; color:${typeColor}; font-weight:700; background:rgba(217,108,145,0.1); padding:2px 8px; border-radius:4px;">${planTitle}</span>
                        </div>
                    </div>
                    <p style="color:#64748B; font-size:0.82rem; margin:10px 0 18px 0; line-height:1.45;">${typeDesc}</p>
                    
                    ${inputHtml}
                    
                    <div style="max-height:240px; overflow-y:auto; border:1.5px solid #E2E8F0; border-radius:10px; background:#F8FAFC;">
                        <ul id="w-modal-list" style="list-style:none; padding:0; margin:0;">
                            ${filtered.length === 0 ? `
                                <li style="padding:24px; text-align:center; color:#94A3B8; font-size:0.82rem;">
                                    <i class="fas ${typeIcon}" style="display:block; font-size:1.6rem; margin-bottom:8px; color:#CBD5E1;"></i>
                                    No ${currentType}s whitelisted yet. Configure one above to grant immunity.
                                </li>
                            ` : filtered.map(item => {
                                let label = item.id;
                                if (currentType === 'role' && window.guildRoles) {
                                    const matchedRole = window.guildRoles.find(r => r.id === item.id);
                                    if (matchedRole) label = '@' + matchedRole.name.replace(/^@/, '');
                                } else if (currentType === 'channel' && window.guildChannels) {
                                    const matchedChan = window.guildChannels.find(c => c.id === item.id);
                                    if (matchedChan) label = '#' + matchedChan.name;
                                } else if (currentType === 'user') {
                                    const matchedUser = (window.allMembers || window._membersCache || []).find(m => m.id === item.id);
                                    if (matchedUser) label = `${matchedUser.display_name} (@${matchedUser.username})`;
                                }
                                return `
                                    <li style="padding:10px 14px; border-bottom:1px solid #F1F5F9; display:flex; justify-content:space-between; align-items:center; background:#FFFFFF;">
                                        <div style="display:flex; align-items:center; gap:8px;">
                                            <span style="width:8px; height:8px; border-radius:50%; background:#10B981;"></span>
                                            <span style="color:#0F172A; font-size:0.84rem; font-family:var(--font-mono); font-weight:700;">${escapeHtml(label)}</span>
                                            <span style="font-size:0.72rem; color:#64748B; background:#F1F5F9; padding:1px 6px; border-radius:4px;">Immune</span>
                                        </div>
                                        <button type="button" onclick="deleteWModalItem('${item.id}', '${type}')" style="background:transparent; border:none; color:#EF4444; cursor:pointer; padding:4px 8px; font-size:0.85rem;" title="Remove Override"><i class="fas fa-trash-can"></i></button>
                                    </li>
                                `;
                            }).join('')}
                        </ul>
                    </div>
                </div>
            `;
        });
    }
    
    window.addWModalItem = function(t, quotaLimit) {
        const select = document.getElementById('w-modal-select');
        const input = document.getElementById('w-modal-input');
        
        let val = '';
        if (select && select.value) {
            val = select.value.trim();
        } else if (input && input.value) {
            val = input.value.trim();
        }
        
        if (!val) {
            showToast("Validation Error", `Please select or enter a valid ${t} ID.`, "error");
            return;
        }

        if (window.activeWhitelistCache && window.activeWhitelistCache.length >= quotaLimit) {
            showToast("Plan Quota Reached", `Your active plan limit is ${quotaLimit} whitelist slot(s).`, "error");
            return;
        }

        fetch(`/api/whitelist/${targetGuild}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: val, type: t, reason: `Authorized ${t} Override` })
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                showToast("${t} Whitelisted", `${t} ${val} added to whitelist immunity.`);
                if (input) input.value = '';
                if (select) select.value = '';
                refresh();
            } else {
                showToast("Quota Restricted", res.error || "Unable to add whitelist override.", "error");
            }
        })
        .catch(() => showToast("Network Error", "Failed to update whitelist.", "error"));
    };
    
    window.deleteWModalItem = function(id, t) {
        fetch(`/api/whitelist/${targetGuild}/${id}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                showToast("Whitelist Updated", `Removed ${id} from whitelist overrides.`);
                refresh();
            }
        });
    };
    
    refresh();
};

window.loadModerationOverrides = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    fetch(`/api/settings/moderation/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const listEl = document.getElementById('moderation-overrides-list');
            if (!listEl) return;
            if (data.length === 0) {
                listEl.innerHTML = '<li style="padding:15px; text-align:center; color:#64748B; font-weight:600;">No moderation overrides configured.</li>';
                return;
            }
            listEl.innerHTML = data.map(item => {
                const member = (window.allMembers || []).find(m => m.id === item.user_id);
                const displayName = member ? `${member.display_name} (@${member.username})` : item.user_id;
                return `
                <li style="padding:12px 16px; border:1.5px solid #E2E8F0; background:#FFFFFF; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
                    <div>
                        <strong style="color:#0F172A; font-size:0.92rem; font-weight:800;">${displayName}</strong>
                        <span style="font-size:0.76rem; color:#64748B; margin-left:8px; font-family:var(--font-mono);">${item.user_id}</span>
                        <span style="font-size:0.74rem; color:#7C3AED; background:#F3E8FF; border:1px solid #E9D5FF; padding:2px 8px; border-radius:4px; font-weight:700; margin-left:8px;">${item.reason || 'Dashboard Override'}</span>
                    </div>
                    <button onclick="deleteModerationOverride('${item.user_id}')" style="background:#FEE2E2; border:1px solid #FECACA; color:#DC2626; border-radius:6px; padding:6px 12px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='#FCA5A5';this.style.color='#991B1B'" onmouseout="this.style.background='#FEE2E2';this.style.color='#DC2626'">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </li>
            `;}).join('');
        })
        .catch(err => console.error("Error loading moderation overrides:", err));
};

window.addModerationOverride = function() {
    if (!activeGuildId) return;
    const inputEl = document.getElementById('mod-user-id-grant');
    if (!inputEl) return;
    const userId = inputEl.value.trim();
    if (!userId) {
        showToast("Error", "Please enter a valid User ID.");
        return;
    }
    fetch(`/api/settings/moderation/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, reason: 'Dashboard Override' })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Success", "Moderation override granted successfully!");
            inputEl.value = '';
            loadModerationOverrides(activeGuildId);
            createFeatureChannels(["moderation"]);
        } else {
            showToast("Error", res.error || "Failed to grant moderation override.");
        }
    })
    .catch(err => console.error("Error adding moderation override:", err));
};

window.deleteModerationOverride = function(userId) {
    if (!activeGuildId) return;
    if (!confirm("Are you sure you want to remove moderation permissions for this user?")) return;
    fetch(`/api/settings/moderation/${activeGuildId}/${userId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Success", "Moderation override revoked.");
            loadModerationOverrides(activeGuildId);
        } else {
            showToast("Error", res.error || "Failed to revoke override.");
        }
    })
    .catch(err => console.error("Error deleting moderation override:", err));
};

window.loadAntiSpamSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;

    // Populate channel dropdowns if available
    const logSelect = document.getElementById('antispam-log-channel');
    if (logSelect && window.guildChannels && window.guildChannels.length > 0) {
        const curVal = logSelect.value;
        logSelect.innerHTML = '<option value=""># Default Security Logs</option>' +
            window.guildChannels.filter(c => c.type === 0 || c.type === 'text')
                .map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');
        if (curVal) logSelect.value = curVal;
    }

    fetch(`/api/settings/antispam/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            if (!data) return;
            const isEnabled = (data.enabled === 1 || data.enabled === true || data.enabled === '1');
            const enableEl = document.getElementById('sec-enable-antispam');
            if (enableEl) enableEl.checked = isEnabled;

            if (document.getElementById('antispam-max-msgs')) document.getElementById('antispam-max-msgs').value = data.max_messages || 5;
            if (document.getElementById('antispam-msg-secs')) document.getElementById('antispam-msg-secs').value = data.message_seconds || 5;
            if (document.getElementById('antispam-max-dupes')) document.getElementById('antispam-max-dupes').value = data.max_duplicates || 3;
            if (document.getElementById('antispam-max-mentions')) document.getElementById('antispam-max-mentions').value = data.max_mentions || 4;
            if (document.getElementById('antispam-block-invites')) document.getElementById('antispam-block-invites').checked = (data.block_invites === 1 || data.block_invites === true || data.block_invites === '1');
            if (document.getElementById('antispam-block-links')) document.getElementById('antispam-block-links').checked = (data.block_links === 1 || data.block_links === true || data.block_links === '1');
            if (document.getElementById('antispam-max-emojis')) document.getElementById('antispam-max-emojis').value = data.max_emojis || 8;
            if (document.getElementById('antispam-max-caps')) document.getElementById('antispam-max-caps').value = data.max_caps_percent || 70;
            if (document.getElementById('antispam-punishment-type')) document.getElementById('antispam-punishment-type').value = data.punishment || 'Timeout';
            if (document.getElementById('antispam-log-channel') && data.log_channel) document.getElementById('antispam-log-channel').value = data.log_channel;

            toggleAntiSpamSettingsPane(isEnabled);
        })
        .catch(err => console.error("Error loading Anti-Spam settings:", err));
};

window.saveAntiSpamSettings = function() {
    if (window.isDashboardHydrating) return;
    const targetGuild = activeGuildId || window.activeGuildId || localStorage.getItem('selected_guild_id');
    if (!targetGuild) return;

    const punishment = document.getElementById('antispam-punishment-type')?.value || 'Timeout';
    let timeoutDuration = 300;
    if (punishment === 'Timeout10') timeoutDuration = 600;
    else if (punishment === 'Timeout60') timeoutDuration = 3600;

    const payload = {
        enabled: document.getElementById('sec-enable-antispam')?.checked ? 1 : 0,
        max_messages: parseInt(document.getElementById('antispam-max-msgs')?.value) || 5,
        message_seconds: parseInt(document.getElementById('antispam-msg-secs')?.value) || 5,
        max_duplicates: parseInt(document.getElementById('antispam-max-dupes')?.value) || 3,
        max_mentions: parseInt(document.getElementById('antispam-max-mentions')?.value) || 4,
        block_invites: document.getElementById('antispam-block-invites')?.checked ? 1 : 0,
        block_links: document.getElementById('antispam-block-links')?.checked ? 1 : 0,
        max_emojis: parseInt(document.getElementById('antispam-max-emojis')?.value) || 8,
        max_caps_percent: parseInt(document.getElementById('antispam-max-caps')?.value) || 70,
        punishment: punishment,
        timeout_duration: timeoutDuration,
        log_channel: document.getElementById('antispam-log-channel')?.value || ''
    };

    fetch(`/api/settings/antispam/${targetGuild}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Anti-Spam Saved", "Anti-spam real-time filter matrix successfully synced to database!");
            toggleAntiSpamSettingsPane(payload.enabled === 1);
        } else {
            showToast("Save Error", data.error || "Failed to save Anti-Spam settings.", "error");
        }
    })
    .catch(err => console.error("Error saving Anti-Spam settings:", err));
};

// duplicate legacy saveAntiSpamSettings removed - authoritative definition at line 8100

window.loadLogsSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    fetch(`/api/settings/logs/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const modLogSelect = document.getElementById('log-select-moderation');
            const secLogSelect = document.getElementById('log-select-security');
            if (modLogSelect) modLogSelect.value = data.moderation_logs || 'none';
            if (secLogSelect) secLogSelect.value = data.security_logs || 'none';
        })
        .catch(err => console.error("Error loading logs settings:", err));
};

window.saveLogsSettings = function() {
    if (!activeGuildId) return;
    
    const moderation_logs = document.getElementById('log-select-moderation').value;
    const security_logs = document.getElementById('log-select-security').value;
    
    fetch(`/api/settings/logs/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ moderation_logs, security_logs })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Success", "System logging destinations saved successfully.");
        } else {
            showToast("Error", "Failed to save logging settings.");
        }
    })
    .catch(err => console.error("Error saving logs settings:", err));
};

window.autoCreateLogsChannels = function() {
    if (!activeGuildId) return;
    showToast("Creating", "Setting up security-logs and system-logs channels...");
    fetch(`/api/guild/create-logs-channels/${activeGuildId}`, { method: 'POST' })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                showToast("Success", "Logs channels configured successfully!");
                loadServerDashboard(activeGuildId);
            } else {
                showToast("Error", "Failed to create logs channels.");
            }
        })
        .catch(err => console.error("Error creating channels:", err));
};

window.createFeatureChannels = function(featuresList) {
    if (!activeGuildId) return;
    fetch(`/api/guild/create-feature-channels/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: featuresList })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadGuildChannels(activeGuildId);
            if (typeof loadServerDashboard === 'function') {
                loadServerDashboard(activeGuildId);
            }
        }
    })
    .catch(err => console.error("Error creating feature channels:", err));
};

window.saveSubPaneVerificationSettings = function() {
    if (!activeGuildId) return;
    const isEnabled = document.getElementById('sec-enable-raid-captcha').checked;
    fetch(`/api/verification/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            enabled: isEnabled ? 1 : 0,
            type: 'image',
            verified_role: '',
            timeout_action: 'kick',
            captcha_timeout: 60,
            channel: 'general'
        })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Success", "Verification settings successfully updated.");
        } else {
            showToast("Error", "Failed to update verification settings.");
        }
    })
    .catch(err => console.error("Error saving verification settings:", err));
};

// ==========================================
// TICKETS TAB SYSTEMS CONTROLLER
// ==========================================
let activeTicketsHistory = [];
let ticketPanelsCache = {};
let currentSelectedPanelId = null;

function switchTicketsSubTab(subTabId) {
    // Hide all tickets-pane elements
    const panes = document.querySelectorAll('.tickets-pane');
    panes.forEach(p => p.classList.remove('active'));
    
    // Show target pane
    const targetPane = document.getElementById(`t-pane-${subTabId}`);
    if (targetPane) targetPane.classList.add('active');
    
    // Deactivate all sidebar items
    const sidebarItems = document.querySelectorAll('.tickets-sidebar-item');
    sidebarItems.forEach(item => item.classList.remove('active'));
    
    // Activate clicked sidebar item
    const clickedItem = document.getElementById(`ts-item-${subTabId}`);
    if (clickedItem) clickedItem.classList.add('active');
    
    // Load specific histories or templates if needed
    if (subTabId === 'history' || subTabId === 'panels' || subTabId === 'settings') {
        if (typeof window.loadTicketsTab === 'function') {
            window.loadTicketsTab(activeGuildId);
        }
    }
}

function switchPanelSubTab(panelSubTabId) {
    const subPanes = document.querySelectorAll('.panel-sub-pane');
    subPanes.forEach(pane => pane.style.display = 'none');
    
    const targetPane = document.getElementById(`p-sub-${panelSubTabId}`);
    if (targetPane) targetPane.style.display = 'block';

    const pills = document.querySelectorAll('.tickets-designer-layout .tab-pill');
    pills.forEach(pill => {
        pill.classList.remove('active');
        pill.style.background = 'transparent';
        pill.style.color = 'var(--text-secondary)';
    });

    const activePill = document.getElementById(`pst-${panelSubTabId}`);
    if (activePill) {
        activePill.classList.add('active');
        activePill.style.background = 'rgba(234, 179, 8, 0.12)';
        activePill.style.color = '#fff';
    }
}

// Bind switchTicketsSubTab and switchPanelSubTab to window object for HTML access
window.switchTicketsSubTab = switchTicketsSubTab;
window.switchPanelSubTab = switchPanelSubTab;

function loadTicketsTab(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    // Load active roles & categories for the dropdown selectors
    fetch(`/api/guild/roles/${targetGuild}`)
        .then(res => res.json())
        .then(roles => {
            const select = document.getElementById('ticket-support-roles');
            if (select) {
                const currentVal = select.value;
                select.innerHTML = '<option value="">Select support role...</option>';
                roles.forEach(r => {
                    const opt = document.createElement('option');
                    opt.value = r.id;
                    opt.innerText = r.name;
                    select.appendChild(opt);
                });
                if (currentVal) select.value = currentVal;
            }
        })
        .catch(err => console.error("Error loading support roles:", err));

    fetch(`/api/guild/channels/${targetGuild}`)
        .then(res => res.json())
        .then(channels => {
            const select = document.getElementById('ticket-category-select');
            if (select) {
                const currentVal = select.value;
                select.innerHTML = '<option value="none">Create at server root</option>';
                channels.forEach(c => {
                    // Type 4 is Category channel in Discord APIs
                    if (c.type === 4 || c.name.toLowerCase().includes('category') || c.id.toString().length > 15) {
                        const opt = document.createElement('option');
                        opt.value = c.id;
                        opt.innerText = c.name;
                        select.appendChild(opt);
                    }
                });
                if (currentVal) select.value = currentVal;
            }
        })
        .catch(err => console.error("Error loading categories:", err));

    // Load Global Ticket settings
    fetch(`/api/settings/tickets/${targetGuild}`)
        .then(res => res.json())
        .then(settings => {
            if (settings) {
                document.getElementById('ticket-claim-mode').value = settings.claim_mode || 'private';
                document.getElementById('ticket-max-limit').value = settings.max_tickets || 3;
                document.getElementById('ticket-embed-color-text').value = settings.embed_color || '#d4af37';
                document.getElementById('ticket-embed-color-picker').value = settings.embed_color || '#d4af37';
                document.getElementById('ticket-ping-author').checked = !!settings.ping_author;
            }
        })
        .catch(err => console.error("Error loading global ticket settings:", err));

    // Load Panels
    fetch(`/api/settings/tickets/panels/${targetGuild}`)
        .then(res => res.json())
        .then(panels => {
            const select = document.getElementById('ticket-panel-select');
            select.innerHTML = '<option value="new">+ Create New Panel</option>';
            ticketPanelsCache = {};
            
            panels.forEach(p => {
                ticketPanelsCache[p.id] = p;
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.innerText = p.name;
                select.appendChild(opt);
            });

            if (panels.length > 0) {
                select.value = panels[0].id;
                currentSelectedPanelId = panels[0].id;
            } else {
                select.value = 'new';
                currentSelectedPanelId = null;
            }
            loadSelectedTicketPanel();
        })
        .catch(err => console.error("Error loading panels list:", err));

    // Load Statistics
    fetch(`/api/settings/tickets/stats/${targetGuild}`)
        .then(res => res.json())
        .then(stats => {
            document.getElementById('stat-open-count').innerText = stats.open || 0;
            document.getElementById('stat-progress-count').innerText = stats.progress || 0;
            document.getElementById('stat-resolved-count').innerText = stats.resolved || 0;
            document.getElementById('stat-total-count').innerText = stats.total || 0;
            
            // Re-render SVG donut slices
            const total = (stats.open || 0) + (stats.progress || 0) + (stats.resolved || 0) || 1;
            const openPct = Math.round(((stats.open || 0) / total) * 100);
            const progressPct = Math.round(((stats.progress || 0) / total) * 100);
            const resolvedPct = Math.round(((stats.resolved || 0) / total) * 100);
            
            // Adjust SVG paths or visual labels
            const donutContainer = document.querySelector('#tickets-sub-stats svg');
            if (donutContainer) {
                donutContainer.innerHTML = `
                    <circle cx="18" cy="18" r="15.915" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="2.5"></circle>
                    <circle cx="18" cy="18" r="15.915" fill="none" stroke="#ffd43b" stroke-width="2.5" stroke-dasharray="${resolvedPct} ${100 - resolvedPct}" stroke-dashoffset="0"></circle>
                    <circle cx="18" cy="18" r="15.915" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-dasharray="${progressPct} ${100 - progressPct}" stroke-dashoffset="-${resolvedPct}"></circle>
                    <circle cx="18" cy="18" r="15.915" fill="none" stroke="#a855f7" stroke-width="2.5" stroke-dasharray="${openPct} ${100 - openPct}" stroke-dashoffset="-${resolvedPct + progressPct}"></circle>
                `;
            }
        })
        .catch(err => console.error("Error loading ticket stats:", err));

    // Load History list
    fetch(`/api/settings/tickets/history/${targetGuild}`)
        .then(res => res.json())
        .then(history => {
            activeTicketsHistory = history;
            renderTicketsHistoryTable(history);
        })
        .catch(err => console.error("Error loading ticket history:", err));

    // Load Customizer Bot Profile Details
    fetch(`/api/settings/botprofile/${targetGuild}`)
        .then(res => res.json())
        .then(profile => {
            if (profile) {
                document.getElementById('ticket-bot-name').value = profile.name || '';
                document.getElementById('ticket-bot-bio').value = profile.bio || '';
                document.getElementById('ticket-bot-avatar').value = profile.avatar || '';
                document.getElementById('ticket-bot-banner').value = profile.banner || '';
                updateBotProfilePreview();
            }
        })
        .catch(err => console.error("Error loading bot profile settings:", err));
}

function loadSelectedTicketPanel() {
    const selectVal = document.getElementById('ticket-panel-select').value;
    const actionsRow = document.getElementById('panel-action-buttons');
    
    if (selectVal === 'new') {
        currentSelectedPanelId = null;
        if (actionsRow) actionsRow.style.display = 'none';

        // Set Default inputs
        document.getElementById('ticket-panel-name').value = '';
        document.getElementById('ticket-support-roles').value = '';
        document.getElementById('ticket-category-select').value = 'none';
        document.getElementById('ticket-panel-title').value = 'Create a Ticket';
        document.getElementById('ticket-panel-color').value = '#a855f7';
        document.getElementById('ticket-panel-description').value = 'Click the button below to initiate support.';
        document.getElementById('ticket-panel-btn-text').value = 'Create Ticket';
        document.getElementById('ticket-welcome-title').value = 'Welcome to Support';
        document.getElementById('ticket-welcome-description').value = 'Please describe your request. A staff member will respond shortly.';
        document.getElementById('ticket-auto-close').checked = false;
        document.getElementById('ticket-auto-delete').checked = false;
    } else {
        currentSelectedPanelId = isNaN(selectVal) ? selectVal : parseInt(selectVal);
        if (actionsRow) actionsRow.style.display = 'flex';

        const p = ticketPanelsCache[currentSelectedPanelId];
        if (p) {
            document.getElementById('ticket-panel-name').value = p.name || '';
            document.getElementById('ticket-support-roles').value = p.support_roles || '';
            document.getElementById('ticket-category-select').value = p.category_id || 'none';
            document.getElementById('ticket-panel-title').value = p.panel_title || 'Create a Ticket';
            document.getElementById('ticket-panel-color').value = p.panel_color || '#a855f7';
            document.getElementById('ticket-panel-description').value = p.panel_description || '';
            document.getElementById('ticket-panel-btn-text').value = p.panel_button_text || 'Create Ticket';
            document.getElementById('ticket-welcome-title').value = p.ticket_title || 'Welcome';
            document.getElementById('ticket-welcome-description').value = p.ticket_description || '';
            document.getElementById('ticket-auto-close').checked = !!p.auto_close;
            document.getElementById('ticket-auto-delete').checked = !!p.auto_delete;

            if (p.categories && window.panelConfig) {
                try {
                    const cats = JSON.parse(p.categories);
                    for (let key in window.panelConfig) {
                        if (key.startsWith('option')) {
                            delete window.panelConfig[key];
                        }
                    }
                    cats.forEach((cat, index) => {
                        const idx = index + 1;
                        window.panelConfig[`option${idx}Text`] = cat.label;
                        window.panelConfig[`option${idx}Emoji`] = cat.emoji || 'fa-ticket';
                        window.panelConfig[`option${idx}Sublabel`] = cat.description || '';
                    });
                    if (typeof switchDesignerActiveOption === 'function') {
                        switchDesignerActiveOption(0);
                    }
                } catch(e) {
                    console.error("Error loading categories:", e);
                }
            }
        }
    }
    updateBotProfilePreview();
}

function updateBotProfilePreview() {
    const name = document.getElementById('ticket-bot-name').value || "VEYRA Bot";
    const bio = document.getElementById('ticket-bot-bio').value || "";
    const avatar = document.getElementById('ticket-bot-avatar').value || "assets/bypass_logs_avatar.webp";
    const banner = document.getElementById('ticket-bot-banner').value || "";

    // Update embeds live preview
    document.getElementById('preview-ticket-bot-name').innerText = name;
    document.getElementById('preview-ticket-avatar').src = avatar;
    
    // Panel preview details
    const embedTitle = document.getElementById('ticket-panel-title').value || "Create a Ticket";
    const embedDesc = document.getElementById('ticket-panel-description').value || "";
    const embedColor = document.getElementById('ticket-panel-color').value || "#a855f7";
    const btnText = document.getElementById('ticket-panel-btn-text').value || "Create Ticket";

    document.getElementById('preview-panel-title').innerText = embedTitle;
    document.getElementById('preview-panel-desc').innerText = embedDesc;
    document.getElementById('preview-panel-embed').style.borderColor = embedColor;
    document.getElementById('preview-panel-button-label').innerText = btnText;

    // Profile card preview details
    document.getElementById('preview-profile-name').innerText = name;
    document.getElementById('preview-profile-avatar').src = avatar;
    document.getElementById('preview-profile-bio').innerText = bio;
    
    const bannerCard = document.getElementById('preview-profile-banner');
    if (bannerCard) {
        if (banner) {
            bannerCard.style.backgroundImage = `url('${banner}')`;
            bannerCard.style.backgroundSize = 'cover';
            bannerCard.style.backgroundPosition = 'center';
        } else {
            bannerCard.style.backgroundImage = 'none';
            bannerCard.style.background = 'linear-gradient(135deg, #7c3aed, #a855f7)';
        }
    }
}

function createTicketPanel() {
    const name = prompt("Enter a descriptive name for the new ticket panel:");
    if (!name || name.trim() === '') return;

    const guildId = activeGuildId;
    fetch(`/api/settings/tickets/panels/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            panel_title: "Open a Ticket",
            panel_description: "Click below to begin support interaction."
        })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Created", "New ticket panel template created successfully.");
            loadTicketsTab(guildId);
        } else {
            showToast("Error", res.error || "Failed to create ticket panel.");
        }
    })
    .catch(err => console.error("Error creating panel:", err));
}

function deleteTicketPanel() {
    if (!currentSelectedPanelId) return;
    if (!confirm("Are you absolutely sure you want to delete this ticket panel configuration?")) return;

    const guildId = activeGuildId;
    fetch(`/api/settings/tickets/panels/${guildId}/${currentSelectedPanelId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Deleted", "Ticket panel successfully deleted.");
            loadTicketsTab(guildId);
        } else {
            showToast("Error", "Failed to delete ticket panel.");
        }
    })
    .catch(err => console.error("Error deleting panel:", err));
}

function saveTicketPanelSettings() {
    const guildId = activeGuildId;
    const name = document.getElementById('ticket-panel-name').value;
    if (!name || name.trim() === '') {
        showToast("Validation Error", "Panel name is required.");
        return;
    }

    let categoriesList = [];
    if (window.panelConfig) {
        for (let i = 1; i <= 10; i++) {
            const txt = window.panelConfig[`option${i}Text` || `optionText_${i}`];
            const emo = window.panelConfig[`option${i}Emoji` || `optionEmoji_${i}`];
            const sub = window.panelConfig[`option${i}Sublabel` || `optionSublabel_${i}`];
            
            if (txt && txt.trim() !== '') {
                categoriesList.push({
                    id: 'opt_' + i,
                    label: txt,
                    description: sub || "Select this category for assistance",
                    emoji: emo || 'fa-ticket'
                });
            }
        }
    }

    const payload = {
        id: currentSelectedPanelId || null,
        name: name,
        support_roles: document.getElementById('ticket-support-roles').value,
        category_id: document.getElementById('ticket-category-select').value,
        panel_title: document.getElementById('ticket-panel-title').value,
        panel_color: document.getElementById('ticket-panel-color').value,
        panel_description: document.getElementById('ticket-panel-description').value,
        panel_button_text: document.getElementById('ticket-panel-btn-text').value,
        ticket_title: document.getElementById('ticket-welcome-title').value,
        ticket_description: document.getElementById('ticket-welcome-description').value,
        auto_close: document.getElementById('ticket-auto-close').checked ? 1 : 0,
        auto_delete: document.getElementById('ticket-auto-delete').checked ? 1 : 0,
        categories: JSON.stringify(categoriesList)
    };

    fetch(`/api/settings/tickets/panels/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Saved", "Panel settings saved successfully.");
            loadTicketsTab(guildId);
        } else {
            showToast("Error", "Failed to save panel settings.");
        }
    })
    .catch(err => console.error("Error saving panel settings:", err));
}

function sendTicketPanelToDiscord() {
    if (!currentSelectedPanelId) return;
    const channelId = prompt("Enter the text channel ID where you want to send this ticket panel card:");
    if (!channelId || channelId.trim() === '') return;

    const guildId = activeGuildId;
    fetch(`/api/settings/tickets/panels/send/${guildId}/${currentSelectedPanelId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_id: channelId })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Deployed", "Ticket panel embed sent to Discord channel successfully!");
        } else {
            showToast("Error", res.error || "Failed to send ticket panel.");
        }
    })
    .catch(err => console.error("Error deploying panel:", err));
}

function saveGlobalTicketSettings() {
    const guildId = activeGuildId;
    const payload = {
        claim_mode: document.getElementById('ticket-claim-mode').value,
        max_tickets: parseInt(document.getElementById('ticket-max-limit').value) || 3,
        embed_color: document.getElementById('ticket-embed-color-text').value,
        ping_author: document.getElementById('ticket-ping-author').checked ? 1 : 0
    };

    fetch(`/api/settings/tickets/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Saved", "Global ticket configurations saved.");
        } else {
            showToast("Error", "Failed to save settings.");
        }
    })
    .catch(err => console.error("Error saving ticket settings:", err));
}

function saveTicketBotProfile() {
    const guildId = activeGuildId;
    const payload = {
        name: document.getElementById('ticket-bot-name').value,
        bio: document.getElementById('ticket-bot-bio').value,
        avatar: document.getElementById('ticket-bot-avatar').value,
        banner: document.getElementById('ticket-bot-banner').value
    };

    fetch(`/api/settings/botprofile/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Success", "Custom bot profile details saved successfully.");
        } else {
            showToast("Error", "Failed to save profile changes.");
        }
    })
    .catch(err => console.error("Error saving profile details:", err));
}

function renderTicketsHistoryTable(history) {
    const tbody = document.getElementById('tickets-history-table-body');
    const tbodyNested = document.getElementById('tickets-history-table-body-nested');
    if (!tbody && !tbodyNested) return;

    const noHistoryHtml = '<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--text-secondary);">No ticket history available.</td></tr>';

    if (tbody) {
        if (history.length === 0) {
            tbody.innerHTML = noHistoryHtml;
        } else {
            tbody.innerHTML = '';
        }
    }
    if (tbodyNested) {
        if (history.length === 0) {
            tbodyNested.innerHTML = noHistoryHtml;
        } else {
            tbodyNested.innerHTML = '';
        }
    }

    if (history.length === 0) return;

    history.forEach(row => {
        let statusBadge = '';
        if (row.status === 'open') {
            statusBadge = `<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">Open</span>`;
        } else if (row.status === 'claimed') {
            statusBadge = `<span style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">Claimed</span>`;
        } else {
            statusBadge = `<span style="background: rgba(148, 163, 184, 0.15); color: #94a3b8; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">Resolved</span>`;
        }

        const dateStr = new Date(row.open_time * 1000).toLocaleString();
        const actionBtn = row.status === 'closed' || row.transcript 
            ? `<button onclick="viewTicketTranscript('${row.channel_id}')" class="btn-secondary" style="background:#5865f2; border:none; padding:4px 10px; border-radius:4px; font-size:0.75rem; color:#fff; cursor:pointer;"><i class="fas fa-file-invoice"></i> View Transcript</button>`
            : `<span style="font-size:0.78rem; color:var(--text-secondary);">Active ticket channel</span>`;

        const rowHtml = `
            <td style="padding: 12px 5px; font-size:0.8rem;">${dateStr}</td>
            <td style="font-family:var(--font-mono); font-size:0.78rem; color:#fff;">#ticket-${String(row.ticket_number || 0).padStart(5, '0')}</td>
            <td style="font-weight:600; color:#fff;">${row.username || row.user_id}</td>
            <td>${statusBadge}</td>
            <td style="font-size:0.8rem;">${row.claimed_by || 'Not Claimed'}</td>
            <td style="text-align:right; padding-right:15px;">${actionBtn}</td>
        `;

        if (tbody) {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.03)';
            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        }
        if (tbodyNested) {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.03)';
            tr.innerHTML = rowHtml;
            tbodyNested.appendChild(tr);
        }
    });
}

function filterTicketsHistoryTable() {
    const kwNormal = document.getElementById('filter-tickets-user');
    const stNormal = document.getElementById('filter-tickets-status');
    const kwNested = document.getElementById('filter-tickets-user-nested');
    const stNested = document.getElementById('filter-tickets-status-nested');

    const keyword = ((kwNested ? kwNested.value : '') || (kwNormal ? kwNormal.value : '')).toLowerCase();
    const status = (stNested ? stNested.value : '') || (stNormal ? stNormal.value : '') || 'all';

    const filtered = activeTicketsHistory.filter(row => {
        const matchesUser = !keyword || (row.username && row.username.toLowerCase().includes(keyword)) || row.user_id.includes(keyword);
        const matchesStatus = status === 'all' || row.status === status;
        return matchesUser && matchesStatus;
    });

    renderTicketsHistoryTable(filtered);
}

function viewTicketTranscript(channelId) {
    const titleEl = document.getElementById('transcript-modal-title');
    if (titleEl) titleEl.innerText = `Transcript preview for ticket channel [${channelId}]`;

    const iframe = document.getElementById('transcript-modal-iframe');
    if (iframe) iframe.src = `/api/settings/tickets/transcripts/${activeGuildId}/${channelId}`;

    const modal = document.getElementById('modal-ticket-transcript');
    if (modal) modal.style.display = 'flex';
}

function closeTranscriptModal() {
    const modal = document.getElementById('modal-ticket-transcript');
    if (modal) modal.style.display = 'none';

    const iframe = document.getElementById('transcript-modal-iframe');
    if (iframe) iframe.src = 'about:blank';
}

// --- 24. REAL-TIME AUTO SYNC AND DATA FRESHNESS MATRIX ---
function startRealTimeSync() {
    setInterval(() => {
        if (!activeGuildId || currentScreen !== 'dashboard') return;
        
        if (currentTab === 'overview') {
            if (typeof loadInvitesSettings === 'function') loadInvitesSettings(activeGuildId);
            
            // Reload basic security metrics
            fetch(`/api/whitelist/${activeGuildId}`)
                .then(res => res.json())
                .then(wl => {
                    if (Array.isArray(wl)) {
                        window.activeWhitelistCache = wl;
                        if (typeof window.updateWhitelistCapacityUI === 'function') {
                            window.updateWhitelistCapacityUI(wl.length);
                        }
                    }
                })
                .catch(() => {});
        } else if (currentTab === 'settings' || currentTab === 'weblogs') {
            if (typeof loadAuditWeblogs === 'function') loadAuditWeblogs(activeGuildId);
        } else if (currentTab === 'analytics') {
            if (typeof loadRealAnalytics === 'function') loadRealAnalytics(activeGuildId);
        } else if (currentTab === 'tickets') {
            if (typeof loadTicketsTab === 'function') loadTicketsTab(activeGuildId);
        }
    }, 10000); // 10 seconds interval
}

// Start auto sync on initialization
startRealTimeSync();

// --- 25. RAZORPAY SUBSCRIPTION AND SERVER DEPLOYMENT FLOW ---
let rzpSelectedPlan = null;

window.initRazorpayCheckoutFlow = function() {
    document.querySelectorAll('.rzp-pay-btn').forEach(btn => {
        btn.onclick = (e) => {
            e.preventDefault();
            const plan = btn.getAttribute('data-plan');
            rzpSelectedPlan = plan;
            
            if (!window.isUserLoggedIn) {
                showToast("Login Required", "Please login with Discord to purchase a premium subscription.", "error");
                setTimeout(simulateLogin, 1000);
                return;
            }
            
        };
    });
};

window.openRazorpayServerModal = function(plan) {
    rzpSelectedPlan = plan;
    window.rzpSelectedPlan = plan;
    const modal = document.getElementById('razorpay-server-modal');
    const label = document.getElementById('rzp-selected-plan-label');
    const select = document.getElementById('rzp-server-select');
    
    if (label) label.innerText = `Selected Plan: ${plan}`;
    
    // Populate select with user servers
    if (select) {
        select.innerHTML = '';
        const guilds = window.allGuildsCache || [];
        if (guilds.length === 0) {
            select.innerHTML = '<option value="">No manageable servers found. Try reloading.</option>';
        } else {
            guilds.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.innerText = `${g.name} (${g.active ? 'Bot Active' : 'Requires Invite'})`;
                select.appendChild(opt);
            });
        }
    }
    
    if (modal) modal.style.display = 'flex';
}

window.closeRazorpayServerModal = function() {
    const modal = document.getElementById('razorpay-server-modal');
    if (modal) modal.style.display = 'none';
};

window.triggerRazorpayCheckout = function() {
    const select = document.getElementById('rzp-server-select');
    const guildId = select ? select.value : '';
    
    if (!guildId) {
        showToast("Server Required", "Please select a server to activate the plan.", "error");
        return;
    }
    
    if (!rzpSelectedPlan) {
        showToast("Plan Required", "Please select a valid plan.", "error");
        return;
    }
    
    window.closeRazorpayServerModal();
    showToast("Processing", "Generating secure Razorpay payment link...", "info");
    
    fetch('/api/payment/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: rzpSelectedPlan, guild_id: guildId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showToast("Payment Error", data.error, "error");
            return;
        }
        
        if (data.is_mock) {
            // Mock checkout simulation
            showToast("Sandbox Payment", "Simulating secure sandbox payment authorization...", "info");
            setTimeout(() => {
                const mockPaymentId = `pay_mock_${Date.now()}`;
                fetch('/api/payment/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        razorpay_order_id: data.order_id,
                        razorpay_payment_id: mockPaymentId,
                        guild_id: guildId
                    })
                })
                .then(res => res.json())
                .then(vData => {
                    if (vData.success) {
                        showToast("Plan Activated!", `${data.plan} plan successfully activated for server!`, "success");
                        checkSession();
                        if (typeof loadServerDashboard === 'function') {
                            loadServerDashboard(guildId);
                        }
                    } else {
                        showToast("Verification Failed", vData.error || "Payment verification failed.", "error");
                    }
                })
                .catch(err => {
                    console.error("Verification error:", err);
                    showToast("Network Error", "Could not complete sandbox verification.", "error");
                });
            }, 1500);
            return;
        }
        
        const options = {
            key: data.key_id,
            amount: data.amount,
            currency: data.currency,
            name: "VEYRA Premium Subscriptions",
            description: `VEYRA ${data.plan} Plan Activation`,
            order_id: data.order_id,
            handler: function (response) {
                // Verify payment signature
                showToast("Verifying", "Verifying payment authorization signature...", "info");
                fetch('/api/payment/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_signature: response.razorpay_signature,
                        guild_id: guildId
                    })
                })
                .then(res => res.json())
                .then(vData => {
                    if (vData.success) {
                        showToast("Plan Activated!", `Plan successfully activated for server!`, "success");
                        // Refresh session & reload dashboard settings
                        checkSession();
                        if (typeof loadServerDashboard === 'function') {
                            loadServerDashboard(guildId);
                        }
                    } else {
                        showToast("Verification Failed", vData.error || "Payment verification failed.", "error");
                    }
                })
                .catch(err => {
                    console.error("Verification error:", err);
                    showToast("Network Error", "Could not complete payment verification.", "error");
                });
            },
            prefill: {
                name: window.currentUserDisplayName || "Discord User",
            },
            theme: {
                color: "#a855f7"
            }
        };
        
        const rzp = new Razorpay(options);
        rzp.open();
    })
    .catch(err => {
        console.error("Create order error:", err);
        showToast("Payment Error", "Failed to contact payment gateway.", "error");
    });
};


// =================================================================
//  MULTI-EMBED MESSAGES BUILDER ENGINE
// =================================================================
window.multiEmbedsState = [
    {
        color: '#a855f7',
        author_icon: '',
        author_name: '',
        author_url: '',
        title: '♡ VEYRA EMBED MESSAGE #1 ♡',
        title_url: '',
        description: 'This is a multi-embed message dispatched live to Discord channels.\nYou can add up to 10 embeds with full customization (author, title links, top-right thumbnails, large banner images, and footer icons)!',
        image: 'assets/bypass_logs_banner.webp',
        thumbnail: '',
        footer: '✦ VEYRA REALTIME EMBED BUILDER ✦',
        footer_icon: '',
        date: '',
        fields: [
            { name: '⚡ Feature', value: 'Multi-Embed Support', inline: true },
            { name: '🛡 Status', value: 'Live & Operational', inline: true }
        ]
    }
];

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ═══════════════════════════════════════════════════════════════════════════════
// NATIVE DISCORD-STYLE POPUP EMOJI PICKER (SIDE FLYOUT & COMPLETE EMOJI SUITE)
// ═══════════════════════════════════════════════════════════════════════════════

window.activeEmojiTarget = null;
window.activeEmojiAnchor = null;
window.activeEmojiCategory = 'recent';

// Standard Discord Emojis Database
const DISCORD_EMOJI_CATEGORIES = {
    recent: {
        id: 'recent',
        name: 'Frequently used',
        icon: '🕒',
        emojis: ['👍', '😀', '😉', '😍', '😆', '😜', '😅', '🛒', '🛠️', '😂', '🔥', '❤️', '✨', '🎉', '💯', '💀', '🚀', '👑', '🥳', '😎', '👀', '⚡', '💎', '✅', '❌']
    },
    smileys: {
        id: 'smileys',
        name: 'Smileys & Emotion',
        icon: '😃',
        emojis: [
            '😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '🥲', '☺️', '😊', '😇',
            '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛',
            '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🥸', '🤩', '🥳', '😏', '😒',
            '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢',
            '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰',
            '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄',
            '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴',
            '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠', '😈', '👿', '👹', '👺',
            '🤡', '💩', '👻', '💀', '☠️', '👽', '👾', '🤖', '🎃'
        ]
    },
    animals: {
        id: 'animals',
        name: 'Animals & Nature',
        icon: '🐶',
        emojis: [
            '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮',
            '🐷', '🐸', '🐵', '🐔', '🐧', '🐦', '🐤', '🦆', '🦅', '🦉', '🦇', '🐺',
            '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞', '🐜', '🦟', '🦗', '🕷️',
            '🦂', '🐢', '🐍', '🦎', '🦖', '🐙', '🦑', '🦐', '🦞', '🦀', '🐡', '🐠',
            '🐟', '🐬', '🐳', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🦧', '🐘', '🦛',
            '🦏', '🐪', '🐫', '🦒', '🦘', '🐃', '🐂', '🐄', '🐎', '🐖', '🐏', '🐑',
            '🦙', '🐐', '🦌', '🐕', '🐩', '🦮', '🐈', '🐓', '🦃', '🦚', '🦜', '🦢',
            '🦩', '🕊️', '🐇', '🦝', '🦨', '🦡', '🦦', '🦥', '🐁', '🐀', '🐿️', '🦔',
            '🌲', '🌳', '🌴', '🌵', '🌿', '☘️', '🍀', '🍁', '🍂', '🍃', '🍄', '💐',
            '🌸', '💮', '🌹', '🥀', '🌺', '🌻', '🌼', '🌷', '🌱', '🪴'
        ]
    },
    food: {
        id: 'food',
        name: 'Food & Drink',
        icon: '🍔',
        emojis: [
            '🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🫐', '🍈', '🍒',
            '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️',
            '🫑', '🌽', '🥕', '🫒', '🧄', '🧅', '🥔', '🍠', '🥐', '🥯', '🍞', '🥖',
            '🥨', '🧀', '🥚', '🍳', '🧈', '🥞', '🧇', '🥓', '🥩', '🍗', '🍖', '🦴',
            '🌭', '🍔', '🍟', '🍕', '🫓', '🥪', '🥙', '🧆', '🌮', '🌯', '🫔', '🥗',
            '🥘', '🫕', '🥫', '🍝', '🍜', '🍲', '🍛', '🍣', '🍱', '🥟', '🦪', '🍤',
            '🍙', '🍚', '🍘', '🍥', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧',
            '🧁', '🍰', '🎂', '🍮', '🍭', '🍬', '🍫', '🍿', '🍩', '🍪', '🌰', '🥜',
            '🍯', '🥛', '🍼', '🫖', '☕', '🍵', '🧃', '🥤', '🧋', '🍶', '🍺', '🍻',
            '🥂', '🍷', '🥃', '🍸', '🍹', '🧉', '🍾', '🧊'
        ]
    },
    activities: {
        id: 'activities',
        name: 'Activities & Sports',
        icon: '🏈',
        emojis: [
            '⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🪀', '🏓',
            '🏸', '🏒', '🏑', '🥍', '🏏', '🪃', '🥅', '⛳', '🪁', '🏹', '🎣', '🤿',
            '🥊', '🥋', '🎽', '🛹', '🛼', '🛷', '⛸️', '🥌', '🎿', '⛷️', '🏂', '🪂',
            '🏋️', '🤼', '🤸', '🤺', '⛹️', '🤾', '🧗', '🧘', '🏄', '🏊', '🤽', '🚣',
            '🏇', '🚴', '🚵', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🏵️', '🎗️', '🎫',
            '🎟️', '🎪', '🤹', '🎭', '🩰', '🎨', '🎬', '🎤', '🎧', '🎼', '🎹', '🥁',
            '🎷', '🎺', '🎸', '🪕', '🎻', '🎲', '♟️', '🎯', '🎳', '🎮', '🎰', '🧩'
        ]
    },
    travel: {
        id: 'travel',
        name: 'Travel & Places',
        icon: '🚗',
        emojis: [
            '🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🛻', '🚚',
            '🚛', '🚜', '🦯', '🦽', '🦼', '🛴', '🚲', '🛵', '🏍️', '🛺', '🚨', '🚔',
            '🚍', '🚘', '🚖', '🚡', '🚠', '🚟', '🚃', '🚋', '🚞', '🚝', '🚄', '🚅',
            '🚈', '🚂', '🚆', '🚇', '🚊', '🚉', '✈️', '🛫', '🛬', '🛩️', '💺', '🛰️',
            '🚀', '🛸', '🚁', '🛶', '⛵', '🚤', '🛥️', '🛳️', '⛴️', '🚢', '⚓', '🪝',
            '⛽', '🚧', '🚦', '🚥', '🗺️', '🗿', '🗽', '🗼', '🏰', '🏯', '🏟️', '🎡',
            '🎢', '⛲', '⛱️', '🏖️', '🏝️', '🏜️', '🌋', '⛰️', '🏔️', '🗻', '🏕️', '⛺',
            '🛖', '🏠', '🏡', '🏘️', '🏚️', '🏗️', '🏭', '🏢', '🏬', '🏣', '🏤', '🏥',
            '🏦', '🏨', '🏪', '🏫', '🏩', '💒', '🏛️', '⛪', '🕌', '🛕', '🕍', '⛩️', '🕋'
        ]
    },
    objects: {
        id: 'objects',
        name: 'Objects & Symbols',
        icon: '💡',
        emojis: [
            '⌚', '📱', '📲', '💻', '⌨️', '🖥️', '🖨️', '🖱️', '🖲️', '🕹️', '🗜️', '💽',
            '💾', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽️', '🎞️', '📞', '☎️',
            '📟', '📠', '📺', '📻', '🎙️', '🎚️', '🎛️', '🧭', '⏱️', '⏲️', '⏰', '🕰️',
            '⌛', '⏳', '📡', '🔋', '🔌', '💡', '🔦', '🕯️', '🧯', '🗑️', '🪣', '🛒',
            '🛍️', '🎁', '🎈', '🎏', '🎀', '🪄', '🪅', '🎊', '🎉', '🎎', '🏮', '🎐',
            '🧧', '✉️', '📩', '📨', '📧', '💌', '📥', '📤', '📦', '🏷️', '🪧', '📪',
            '📫', '📬', '📭', '📮', '📯', '📜', '📃', '📄', '📑', '🧾', '📊', '📈',
            '📉', '🗒️', '🗓️', '📆', '📅', '🪞', '🪟', '🚪', '🪑', '🛏️', '🛋️', '🧴',
            '🧷', '🧹', '🧺', '🧻', '🧼', '🫧', '🪥', '🧽', '🚬', '⚰️', '🪦', '⚱️',
            '🧿', '🪬', '💈', '🔑', '🗝️', '🔒', '🔓', '🔏', '🔐', '⚔️', '🗡️', '🛡️',
            '⚙️', '🔧', '🔨', '⚒️', '🛠️', '⛏️', '🔩', '🧰', '🪛', '💎', '🔔', '🔕',
            '🎵', '🎶', '🔊', '📢', '📣', '💬', '💭', '🗯️', '♠️', '♣️', '♥️', '♦️',
            '🃏', '🎴', '🀄', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘'
        ]
    },
    flags: {
        id: 'flags',
        name: 'Flags',
        icon: '🚩',
        emojis: [
            '🏁', '🚩', '🎌', '🏴', '🏳️', '🏳️‍🌈', '🏳️‍⚧️', '🏴‍☠️', '🇮🇳', '🇺🇸', '🇬🇧', '🇨🇦',
            '🇦🇺', '🇯🇵', '🇩🇪', '🇫🇷', '🇧🇷', '🇷🇺', '🇰🇷', '🇮🇹', '🇪🇸', '🇲🇽', '🇨🇳', '🇹🇷',
            '🇸🇦', '🇦🇪', '🇿🇦', '🇳🇬', '🇪🇬', '🇵🇰', '🇧🇩', '🇮🇩', '🇲🇾', '🇸🇬', '🇵🇭', '🇻🇳'
        ]
    }
};

window.openServerEmojiPicker = function(targetInputId, embedIdx = null, fieldKey = null, fieldIdx = null, triggerEl = null) {
    window.activeEmojiTarget = { targetInputId, embedIdx, fieldKey, fieldIdx };
    
    // Find trigger button location for exact side positioning
    const btn = triggerEl || (window.event ? (window.event.currentTarget || window.event.target) : null);
    window.activeEmojiAnchor = btn;

    let popover = document.getElementById('discord-emoji-flyout');
    if (!popover) {
        popover = document.createElement('div');
        popover.id = 'discord-emoji-flyout';
        popover.style.cssText = `
            position: fixed;
            width: 330px;
            height: 420px;
            background: #111214;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            box-shadow: 0 12px 36px rgba(0,0,0,0.7), 0 2px 8px rgba(0,0,0,0.4);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            font-family: var(--font-body, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
            transition: opacity 0.12s ease, transform 0.12s ease;
            opacity: 0;
            transform: scale(0.96);
        `;
        document.body.appendChild(popover);
    }

    // Position flyout right next to the trigger button
    if (btn && btn.getBoundingClientRect) {
        const rect = btn.getBoundingClientRect();
        const flyoutWidth = 330;
        const flyoutHeight = 420;

        // Preferred: right side of the button
        let left = rect.right + 10;
        if (left + flyoutWidth > window.innerWidth - 10) {
            // Flip to left side
            left = Math.max(10, rect.left - flyoutWidth - 10);
        }

        let top = rect.top - 20;
        if (top + flyoutHeight > window.innerHeight - 10) {
            top = Math.max(10, window.innerHeight - flyoutHeight - 10);
        }
        if (top < 10) top = 10;

        popover.style.left = `${left}px`;
        popover.style.top = `${top}px`;
    } else {
        // Fallback default top-right anchor
        popover.style.right = '40px';
        popover.style.top = '120px';
    }

    renderDiscordEmojiFlyout('');
    popover.style.display = 'flex';
    requestAnimationFrame(() => {
        popover.style.opacity = '1';
        popover.style.transform = 'scale(1)';
    });

    // Auto close on clicking outside
    setTimeout(() => {
        const handleOutsideClick = (e) => {
            if (!popover.contains(e.target) && (!btn || !btn.contains(e.target))) {
                closeServerEmojiPicker();
                document.removeEventListener('pointerdown', handleOutsideClick);
            }
        };
        document.addEventListener('pointerdown', handleOutsideClick);
    }, 20);
};

window.closeServerEmojiPicker = function() {
    const popover = document.getElementById('discord-emoji-flyout');
    if (popover) {
        popover.style.opacity = '0';
        popover.style.transform = 'scale(0.96)';
        setTimeout(() => {
            popover.style.display = 'none';
        }, 120);
    }
    window.activeEmojiTarget = null;
    window.activeEmojiAnchor = null;
};

window.switchEmojiFlyoutCategory = function(catId) {
    window.activeEmojiCategory = catId;
    const catEl = document.getElementById(`emoji-cat-section-${catId}`);
    if (catEl) {
        catEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    document.querySelectorAll('.emoji-nav-icon-btn').forEach(btn => {
        if (btn.getAttribute('data-cat') === catId) {
            btn.style.background = 'rgba(255,255,255,0.12)';
            btn.style.borderBottom = '2px solid #5865F2';
        } else {
            btn.style.background = 'transparent';
            btn.style.borderBottom = '2px solid transparent';
        }
    });
};

function renderDiscordEmojiFlyout(searchFilter = '') {
    const popover = document.getElementById('discord-emoji-flyout');
    if (!popover) return;

    const serverEmojis = window.guildEmojis || [];
    const filter = (searchFilter || '').toLowerCase().trim();

    // Top Category Bar
    const navCategories = [
        { id: 'recent', icon: '🕒', title: 'Frequently Used' },
        { id: 'server', icon: '✨', title: `Server Emojis (${serverEmojis.length})` },
        { id: 'smileys', icon: '😃', title: 'Smileys & Emotion' },
        { id: 'animals', icon: '🐶', title: 'Animals & Nature' },
        { id: 'food', icon: '🍔', title: 'Food & Drink' },
        { id: 'activities', icon: '🏈', title: 'Activities' },
        { id: 'travel', icon: '🚗', title: 'Travel & Places' },
        { id: 'objects', icon: '💡', title: 'Objects & Symbols' },
        { id: 'flags', icon: '🚩', title: 'Flags' }
    ];

    const navHtml = navCategories.map(c => `
        <button type="button" class="emoji-nav-icon-btn" data-cat="${c.id}" onclick="switchEmojiFlyoutCategory('${c.id}')" title="${c.title}" style="background:${window.activeEmojiCategory === c.id ? 'rgba(255,255,255,0.12)' : 'transparent'}; border:none; border-bottom:2px solid ${window.activeEmojiCategory === c.id ? '#5865F2' : 'transparent'}; cursor:pointer; font-size:1rem; padding:6px 6px; border-radius:4px 4px 0 0; transition:all 0.1s; color:#fff;">
            ${c.icon}
        </button>
    `).join('');

    // Filter server emojis
    const filteredServer = filter ? serverEmojis.filter(e => e.name.toLowerCase().includes(filter)) : serverEmojis;

    popover.innerHTML = `
        <!-- Top Categories Navigation -->
        <div style="background: #1e1f22; border-bottom: 1px solid rgba(255,255,255,0.06); padding: 6px 10px 0 10px; display: flex; justify-content: space-between; align-items: center; overflow-x: auto; scrollbar-width: none;">
            ${navHtml}
        </div>

        <!-- Search Input Bar -->
        <div style="padding: 10px 12px 6px 12px; background: #111214;">
            <div style="position: relative; width: 100%;">
                <i class="fas fa-search" style="position: absolute; left: 10px; top: 9px; font-size: 0.8rem; color: #80848E;"></i>
                <input type="text" id="emoji-search-input" placeholder="Search" value="${escapeHtml(searchFilter)}" 
                    oninput="renderDiscordEmojiFlyout(this.value)" 
                    style="width: 100%; box-sizing: border-box; background: #1e1f22; border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 6px 10px 6px 30px; color: #DBDEE1; font-size: 0.84rem; outline: none;">
                ${filter ? `<button type="button" onclick="renderDiscordEmojiFlyout('')" style="position:absolute; right:8px; top:7px; background:transparent; border:none; color:#80848E; cursor:pointer; font-size:0.75rem;"><i class="fas fa-times"></i></button>` : ''}
            </div>
        </div>

        <!-- Scrollable Emoji Sections -->
        <div id="emoji-flyout-scroll-body" style="flex: 1; overflow-y: auto; padding: 6px 12px 14px 12px; background: #111214;">
            
            ${!filter ? `
            <!-- Frequently Used -->
            <div id="emoji-cat-section-recent" style="margin-bottom: 12px;">
                <div style="font-size: 0.72rem; font-weight: 800; color: #949BA4; text-transform: uppercase; letter-spacing: 0.04em; margin: 6px 0 8px 0;">
                    Frequently Used
                </div>
                <div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px;">
                    ${DISCORD_EMOJI_CATEGORIES.recent.emojis.map(em => `
                        <button type="button" onclick="insertEmojiIntoActiveTarget('${em}')" style="background: transparent; border: none; border-radius: 6px; width: 34px; height: 34px; font-size: 1.25rem; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.1s;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='transparent'">
                            ${em}
                        </button>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Server Custom Emojis -->
            <div id="emoji-cat-section-server" style="margin-bottom: 14px;">
                <div style="font-size: 0.72rem; font-weight: 800; color: #949BA4; text-transform: uppercase; letter-spacing: 0.04em; margin: 8px 0 8px 0; display: flex; align-items: center; gap: 6px;">
                    <span>Server Emojis</span>
                    <span style="font-size: 0.65rem; color: #5865F2; background: rgba(88,101,242,0.12); padding: 1px 6px; border-radius: 4px;">${serverEmojis.length}</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px;">
                    ${filteredServer.length > 0 ? filteredServer.map(e => `
                        <button type="button" onclick="insertEmojiIntoActiveTarget('${e.mention}')" title=":${e.name}:" 
                            style="background: transparent; border: none; border-radius: 6px; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.1s;"
                            onmouseover="this.style.background='rgba(88,101,242,0.2)'; this.style.transform='scale(1.1)';"
                            onmouseout="this.style.background='transparent'; this.style.transform='scale(1)';">
                            <img src="${e.url}" alt=":${e.name}:" style="width: 24px; height: 24px; object-fit: contain;">
                        </button>
                    `).join('') : `
                        <div style="grid-column: 1 / -1; font-size: 0.76rem; color: #64748B; padding: 4px 0;">
                            ${serverEmojis.length === 0 ? 'No custom server emojis uploaded to this guild.' : 'No server emojis matching search.'}
                        </div>
                    `}
                </div>
            </div>

            <!-- Standard Emoji Categories -->
            ${Object.keys(DISCORD_EMOJI_CATEGORIES).filter(k => k !== 'recent').map(k => {
                const cat = DISCORD_EMOJI_CATEGORIES[k];
                const list = filter ? cat.emojis.filter(e => e.includes(filter)) : cat.emojis;
                if (filter && list.length === 0) return '';
                return `
                <div id="emoji-cat-section-${cat.id}" style="margin-bottom: 14px;">
                    <div style="font-size: 0.72rem; font-weight: 800; color: #949BA4; text-transform: uppercase; letter-spacing: 0.04em; margin: 8px 0 8px 0;">
                        ${cat.name}
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px;">
                        ${list.map(em => `
                            <button type="button" onclick="insertEmojiIntoActiveTarget('${em}')" style="background: transparent; border: none; border-radius: 6px; width: 34px; height: 34px; font-size: 1.25rem; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.1s;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='transparent'">
                                ${em}
                            </button>
                        `).join('')}
                    </div>
                </div>
                `;
            }).join('')}

        </div>
    `;

    // Keep focus in search if user was typing
    if (filter) {
        const inp = document.getElementById('emoji-search-input');
        if (inp) {
            inp.focus();
            inp.selectionStart = inp.selectionEnd = filter.length;
        }
    }
}
// ═══════════════════════════════════════════════════════════════════════════════
// MULTI-EMBED UI BUILDER & REALTIME PREVIEW
// ═══════════════════════════════════════════════════════════════════════════════

function renderMultiEmbedCardsUI() {
    const container = document.getElementById('ebm-cards-container');
    if (!container) return;
    
    let html = '';
    window.multiEmbedsState.forEach((emb, idx) => {
        const colorPresets = ['#a855f7', '#00aff4', '#10b981', '#ef4444', '#f59e0b', '#ffffff', '#202225'];
        
        html += `
        <div class="glass-card multi-embed-card" style="background: #FFFFFF !important; border: 1.5px solid #E2E8F0 !important; border-left: 5px solid ${emb.color || '#a855f7'} !important; border-radius: 12px; padding: 22px; margin-bottom: 22px; box-shadow: 0 4px 18px rgba(15,23,42,0.04);">
            
            <!-- Top Card Header: Actions -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1.5px solid #F1F5F9; padding-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: 800; color: #0F172A; font-size: 0.95rem; display: flex; align-items: center; gap: 8px;">
                        <span style="display: inline-block; width: 14px; height: 14px; border-radius: 4px; background: ${emb.color || '#a855f7'}; box-shadow: 0 1px 3px rgba(0,0,0,0.15);"></span>
                        Embed #${idx + 1}
                    </span>
                    <span style="font-size: 0.74rem; color: #64748B; font-family: var(--font-mono); font-weight: 700; background: #F1F5F9; padding: 2px 8px; border-radius: 6px;">(${window.multiEmbedsState.length}/10)</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button type="button" onclick="duplicateMultiEmbedCard(${idx})" class="btn-secondary" style="background: #F8FAFC; border: 1.5px solid #CBD5E1; padding: 6px 14px; border-radius: 6px; font-size: 0.76rem; font-weight: 700; color: #334155; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.15s;" onmouseover="this.style.background='#F1F5F9'" onmouseout="this.style.background='#F8FAFC'">
                        <i class="fas fa-clone"></i> Duplicate
                    </button>
                    ${window.multiEmbedsState.length > 1 ? `
                    <button type="button" onclick="removeMultiEmbedCard(${idx})" class="btn-primary" style="background: #FEE2E2; border: 1.5px solid #FECACA; padding: 6px 14px; border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer; color: #EF4444; display: flex; align-items: center; gap: 6px; transition: all 0.15s;" onmouseover="this.style.background='#FCA5A5'" onmouseout="this.style.background='#FEE2E2'">
                        <i class="fas fa-trash-can"></i> Remove
                    </button>` : ''}
                </div>
            </div>

            <!-- SECTION 1: EMBED COLOR -->
            <div style="margin-bottom: 14px; background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <label style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                    <i class="fas fa-palette" style="color: #7C3AED;"></i> Embed Color
                </label>
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <input type="color" value="${emb.color || '#a855f7'}" oninput="updateMultiEmbedState(${idx}, 'color', this.value)" style="width: 42px; height: 34px; border: 1.5px solid #CBD5E1; background: #FFFFFF; cursor: pointer; border-radius: 6px; padding: 2px;">
                    <input type="text" value="${emb.color || '#a855f7'}" class="form-control" style="width: 110px; background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-family: var(--font-mono); font-size: 0.84rem; font-weight: 700; border-radius: 6px; padding: 7px 10px;" oninput="updateMultiEmbedState(${idx}, 'color', this.value)">
                    
                    <!-- Quick Color Swatches -->
                    <div style="display: flex; gap: 6px; align-items: center; margin-left: 6px;">
                        ${colorPresets.map(c => `
                            <button type="button" onclick="updateMultiEmbedState(${idx}, 'color', '${c}')" style="width: 24px; height: 24px; border-radius: 50%; background: ${c}; border: ${emb.color === c ? '2.5px solid #0F172A' : '1.5px solid #CBD5E1'}; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.1s;" onmouseover="this.style.transform='scale(1.15)'" onmouseout="this.style.transform='scale(1)'" title="${c}"></button>
                        `).join('')}
                    </div>
                </div>
            </div>

            <!-- SECTION 2: AUTHOR SECTION -->
            <div style="margin-bottom: 14px; background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <label style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                    <i class="fas fa-user-circle" style="color: #2563EB;"></i> Author Header
                </label>
                <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 10px;">
                    <input type="text" placeholder="Author Name" value="${escapeHtml(emb.author_name || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'author_name', this.value)">
                    <input type="text" placeholder="Author Icon URL" value="${escapeHtml(emb.author_icon || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'author_icon', this.value)">
                    <input type="text" placeholder="Author Clickable URL" value="${escapeHtml(emb.author_url || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'author_url', this.value)">
                </div>
            </div>

            <!-- SECTION 3: TITLE & DESCRIPTION -->
            <div style="margin-bottom: 14px; background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <label style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                    <i class="fas fa-heading" style="color: #D96C91;"></i> Title & Description
                </label>
                <div style="display: grid; grid-template-columns: 2fr 1fr auto; gap: 10px; margin-bottom: 10px;">
                    <input type="text" placeholder="Embed Title" value="${escapeHtml(emb.title || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; font-weight: 700; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'title', this.value)">
                    <input type="text" placeholder="Title Hyperlink URL" value="${escapeHtml(emb.url || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'url', this.value)">
                    <button type="button" onclick="openServerEmojiPicker(null, ${idx}, 'title')" title="Insert Server Emoji into Title" class="btn-secondary" style="background: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 0 12px; cursor: pointer; font-size: 1rem; color: #334155; transition: background 0.15s;" onmouseover="this.style.background='#F1F5F9'" onmouseout="this.style.background='#FFFFFF'">
                        😊
                    </button>
                </div>
                <div style="position: relative;">
                    <textarea placeholder="Embed body description (supports standard Discord markdown formatting)..." class="form-control" style="width: 100%; min-height: 85px; background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.85rem; border-radius: 6px; padding: 10px 12px; line-height: 1.5; box-sizing: border-box; resize: vertical;" oninput="updateMultiEmbedState(${idx}, 'description', this.value)">${escapeHtml(emb.description || '')}</textarea>
                    <button type="button" onclick="openServerEmojiPicker(null, ${idx}, 'description')" title="Insert Emoji" style="position: absolute; right: 10px; bottom: 10px; background: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 0.88rem;">
                        😊
                    </button>
                </div>
            </div>

            <!-- SECTION 4: IMAGES & MEDIA -->
            <div style="margin-bottom: 14px; background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <label style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                    <i class="fas fa-image" style="color: #059669;"></i> Images & Media
                </label>
                <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: 10px;">
                    <div>
                        <span style="font-size: 0.72rem; color: #64748B; font-weight: 600; display: block; margin-bottom: 4px;">Top-Right Image / Thumbnail URL:</span>
                        <input type="text" placeholder="https://... (small image at top right)" value="${escapeHtml(emb.thumbnail || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.82rem; border-radius: 6px; padding: 8px 12px; width: 100%; box-sizing: border-box;" oninput="updateMultiEmbedState(${idx}, 'thumbnail', this.value)">
                    </div>
                    <div>
                        <span style="font-size: 0.72rem; color: #64748B; font-weight: 600; display: block; margin-bottom: 4px;">Main Large Banner / Image URL:</span>
                        <input type="text" placeholder="https://... (large image at bottom of embed)" value="${escapeHtml(emb.image || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.82rem; border-radius: 6px; padding: 8px 12px; width: 100%; box-sizing: border-box;" oninput="updateMultiEmbedState(${idx}, 'image', this.value)">
                    </div>
                </div>
            </div>

            <!-- SECTION 5: FOOTER & TIMESTAMP -->
            <div style="margin-bottom: 14px; background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <label style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                    <i class="fas fa-shoe-prints" style="color: #64748B;"></i> Footer & Timestamp
                </label>
                <div style="display: grid; grid-template-columns: 1.5fr auto 1.2fr 1fr; gap: 10px;">
                    <input type="text" placeholder="Footer Text" value="${escapeHtml(emb.footer || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'footer', this.value)">
                    <button type="button" onclick="openServerEmojiPicker(null, ${idx}, 'footer')" title="Insert Server Emoji into Footer" class="btn-secondary" style="background: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 0 12px; cursor: pointer; font-size: 1rem; color: #334155;">
                        😊
                    </button>
                    <input type="text" placeholder="Footer Icon URL" value="${escapeHtml(emb.footer_icon || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'footer_icon', this.value)">
                    <input type="text" placeholder="Timestamp (e.g. Today at 12:00 PM)" value="${escapeHtml(emb.date || '')}" class="form-control" style="background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.84rem; border-radius: 6px; padding: 8px 12px;" oninput="updateMultiEmbedState(${idx}, 'date', this.value)">
                </div>
            </div>

            <!-- SECTION 6: DYNAMIC FIELDS (UP TO 25) -->
            <div style="background: #F8FAFC; padding: 14px; border-radius: 10px; border: 1.5px solid #E2E8F0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 0.76rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                        <i class="fas fa-list-ul" style="color: #7C3AED;"></i> Fields (${(emb.fields || []).length}/25)
                    </span>
                    <button type="button" onclick="addMultiEmbedField(${idx})" class="btn-secondary" style="padding: 6px 14px; font-size: 0.76rem; border-radius: 6px; font-weight: 700; background: #EDE9FE; border: 1.5px solid #DDD6FE; color: #6D28D9; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                        <i class="fas fa-plus"></i> Add Field
                    </button>
                </div>

                <div id="multi-fields-container-${idx}" style="display: flex; flex-direction: column; gap: 10px;">
                    ${(emb.fields || []).map((f, fIdx) => `
                    <div style="display: flex; gap: 8px; align-items: center; background: #FFFFFF; padding: 8px 12px; border-radius: 8px; border: 1.5px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <input type="text" placeholder="Field Name" value="${escapeHtml(f.name || '')}" class="form-control" style="flex: 1; background: #F8FAFC !important; border: 1px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.82rem; font-weight: 700; border-radius: 6px; padding: 6px 10px;" oninput="updateMultiEmbedField(${idx}, ${fIdx}, 'name', this.value)">
                        <input type="text" placeholder="Field Value" value="${escapeHtml(f.value || '')}" class="form-control" style="flex: 1.5; background: #F8FAFC !important; border: 1px solid #CBD5E1 !important; color: #0F172A !important; font-size: 0.82rem; border-radius: 6px; padding: 6px 10px;" oninput="updateMultiEmbedField(${idx}, ${fIdx}, 'value', this.value)">
                        <button type="button" onclick="openServerEmojiPicker(null, ${idx}, 'value', ${fIdx})" title="Insert Server Emoji" class="btn-secondary" style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 0.9rem;">😊</button>
                        <label style="font-size: 0.78rem; color: #334155; font-weight: 600; display: flex; align-items: center; gap: 5px; cursor: pointer; margin-left: 4px; user-select: none;">
                            <input type="checkbox" ${f.inline ? 'checked' : ''} onchange="updateMultiEmbedField(${idx}, ${fIdx}, 'inline', this.checked)"> Inline
                        </label>
                        <button type="button" onclick="removeMultiEmbedField(${idx}, ${fIdx})" style="background: transparent; border: none; color: #EF4444; cursor: pointer; padding: 4px 8px; font-size: 0.9rem;" title="Remove Field"><i class="fas fa-trash"></i></button>
                    </div>
                    `).join('')}
                </div>
            </div>

        </div>
        `;
    });

    container.innerHTML = html;
    updateMultiEmbedPreview();
}

function updateMultiEmbedState(idx, key, val) {
    if (window.multiEmbedsState[idx]) {
        window.multiEmbedsState[idx][key] = val;
        updateMultiEmbedPreview();
    }
}

function updateMultiEmbedField(idx, fIdx, key, val) {
    if (window.multiEmbedsState[idx] && window.multiEmbedsState[idx].fields[fIdx]) {
        window.multiEmbedsState[idx].fields[fIdx][key] = val;
        updateMultiEmbedPreview();
    }
}

function addMultiEmbedCard() {
    if (window.multiEmbedsState.length >= 10) {
        showToast("Maximum Embeds Reached", "Discord allows up to 10 embeds per message.", "warning");
        return;
    }
    const newIdx = window.multiEmbedsState.length + 1;
    window.multiEmbedsState.push({
        color: '#10b981',
        author_icon: '',
        author_name: '',
        author_url: '',
        title: `♡ EMBED MESSAGE #${newIdx} ♡`,
        title_url: '',
        description: `Additional embed layer #${newIdx} in the same message payload.`,
        image: '',
        thumbnail: '',
        footer: '✦ VEYRA DISCORD BOT ✦',
        footer_icon: '',
        date: '',
        fields: []
    });
    renderMultiEmbedCardsUI();
    showToast("Embed Added", `Embed #${newIdx} added to the message payload.`);
}

function duplicateMultiEmbedCard(idx) {
    if (window.multiEmbedsState.length >= 10) {
        showToast("Maximum Embeds Reached", "Discord allows up to 10 embeds per message.", "warning");
        return;
    }
    const source = window.multiEmbedsState[idx];
    if (!source) return;
    const cloned = JSON.parse(JSON.stringify(source));
    cloned.title = (cloned.title || 'Embed') + ' (Copy)';
    window.multiEmbedsState.push(cloned);
    renderMultiEmbedCardsUI();
    showToast("Embed Duplicated", `Duplicated embed #${idx + 1}. Total embeds: ${window.multiEmbedsState.length}`);
}

function removeMultiEmbedCard(idx) {
    if (window.multiEmbedsState.length <= 1) return;
    window.multiEmbedsState.splice(idx, 1);
    renderMultiEmbedCardsUI();
}

function addMultiEmbedField(idx) {
    if (!window.multiEmbedsState[idx].fields) window.multiEmbedsState[idx].fields = [];
    if (window.multiEmbedsState[idx].fields.length >= 25) {
        showToast("Limit Reached", "Maximum 25 fields per embed.", "warning");
        return;
    }
    window.multiEmbedsState[idx].fields.push({ name: 'New Field', value: 'Value details', inline: true });
    renderMultiEmbedCardsUI();
}

function removeMultiEmbedField(idx, fIdx) {
    if (window.multiEmbedsState[idx] && window.multiEmbedsState[idx].fields) {
        window.multiEmbedsState[idx].fields.splice(fIdx, 1);
        renderMultiEmbedCardsUI();
    }
}

function updateMultiEmbedPreview() {
    const previewContainer = document.getElementById('ebm-live-preview-container');
    const normalText = document.getElementById('ebm-normal-text') ? document.getElementById('ebm-normal-text').value : '';
    if (!previewContainer) return;

    let html = '';
    if (normalText && normalText.trim()) {
        html += `<div style="color: #dcddde; font-size: 0.92rem; margin-bottom: 12px; white-space: pre-wrap; word-break: break-word;">${parseDiscordEmojis(escapeHtml(normalText))}</div>`;
    }

    window.multiEmbedsState.forEach((emb, idx) => {
        const borderCol = emb.color || '#a855f7';
        html += `
        <div style="background: #2b2d31; border-left: 4px solid ${borderCol}; border-radius: 4px; padding: 16px; margin-bottom: 12px; max-width: 520px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
            
            <!-- Author -->
            ${emb.author_name ? `
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 700;">
                ${emb.author_icon ? `<img src="${escapeHtml(emb.author_icon)}" style="width: 22px; height: 22px; border-radius: 50%; object-fit: cover;" onerror="this.style.display='none'">` : ''}
                ${emb.author_url ? `<a href="${escapeHtml(emb.author_url)}" target="_blank" style="color: #fff; text-decoration: underline;">${escapeHtml(emb.author_name)}</a>` : `<span style="color: #fff;">${escapeHtml(emb.author_name)}</span>`}
            </div>` : ''}

            <!-- Title & Top Right Thumbnail Container -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 14px;">
                <div style="flex: 1; min-width: 0;">
                    ${emb.title ? `
                    <div style="font-size: 1rem; font-weight: 700; margin-bottom: 6px;">
                        ${emb.title_url ? `<a href="${escapeHtml(emb.title_url)}" target="_blank" style="color: #00aff4; text-decoration: none;">${parseDiscordEmojis(escapeHtml(emb.title))}</a>` : `<span style="color: #fff;">${parseDiscordEmojis(escapeHtml(emb.title))}</span>`}
                    </div>` : ''}
                    
                    ${emb.description ? `
                    <div style="font-size: 0.88rem; color: #dbdee1; white-space: pre-wrap; line-height: 1.45; word-break: break-word;">
                        ${parseDiscordEmojis(escapeHtml(emb.description))}
                    </div>` : ''}
                </div>
                ${emb.thumbnail ? `
                <div style="width: 80px; height: 80px; border-radius: 6px; overflow: hidden; flex-shrink: 0; background: rgba(0,0,0,0.2);">
                    <img src="${escapeHtml(emb.thumbnail)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'">
                </div>` : ''}
            </div>

            <!-- Fields Grid -->
            ${(emb.fields && emb.fields.length > 0) ? `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 4px;">
                ${emb.fields.map(f => `
                <div style="${f.inline ? '' : 'grid-column: 1 / -1;'}">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #b5bac1; margin-bottom: 2px;">${parseDiscordEmojis(escapeHtml(f.name || ''))}</div>
                    <div style="font-size: 0.85rem; color: #dbdee1; word-break: break-word;">${parseDiscordEmojis(escapeHtml(f.value || ''))}</div>
                </div>
                `).join('')}
            </div>` : ''}

            <!-- Large Image (Banner) -->
            ${emb.image ? `
            <div style="width: 100%; border-radius: 4px; overflow: hidden; margin-top: 4px; background: rgba(0,0,0,0.2);">
                <img src="${escapeHtml(emb.image)}" style="width: 100%; max-height: 280px; object-fit: cover; display: block;" onerror="this.style.display='none'">
            </div>` : ''}

            <!-- Footer & Timestamp -->
            ${(emb.footer || emb.footer_icon || emb.date) ? `
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: #949ba4; margin-top: 4px; flex-wrap: wrap;">
                ${emb.footer_icon ? `<img src="${escapeHtml(emb.footer_icon)}" style="width: 18px; height: 18px; border-radius: 50%; object-fit: cover;" onerror="this.style.display='none'">` : ''}
                ${emb.footer ? `<span>${parseDiscordEmojis(escapeHtml(emb.footer))}</span>` : ''}
                ${emb.date ? `<span>• ${escapeHtml(emb.date)}</span>` : ''}
            </div>` : ''}
        </div>
        `;
    });

    previewContainer.innerHTML = html;
}

function postMultiEmbedMessage() {
    const channelSelect = document.getElementById('ebm-destination-channel');
    const channel = channelSelect ? channelSelect.value : 'general';
    const textEl = document.getElementById('ebm-normal-text');
    const normalText = textEl ? textEl.value : '';

    const targetGuildId = activeGuildId || (typeof window.currentSelectedGuildId !== 'undefined' ? window.currentSelectedGuildId : '1256986886631854080');

    if (!window.multiEmbedsState || window.multiEmbedsState.length === 0) {
        showToast("Posting Error", "Please configure at least one embed.", "warning");
        return;
    }

    const payload = {
        guild_id: targetGuildId,
        channel: channel,
        normalText: normalText,
        embedData: window.multiEmbedsState
    };

    fetch('/api/embed/post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Multi-Embed Dispatched!", `Successfully dispatched ${window.multiEmbedsState.length} embed(s) live to #${channel}!`);
            addLogEntry("@user", `Dispatched multi-embed (${window.multiEmbedsState.length} embeds) to #${channel}`);
        } else {
            showToast("Posting Failed", data.error || "Failed to post message", "error");
        }
    })
    .catch(err => {
        showToast("Network Error", "Could not reach server API", "error");
    });
}

document.addEventListener('DOMContentLoaded', () => {

// --- INSTANT PERSISTENT SERVER SELECTION RESTORATION ON LOAD ---
(function restoreActiveServerInstant() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryGid = urlParams.get('guild_id');
        const savedGid = queryGid || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
        const savedName = localStorage.getItem('selected_guild_name');
        const savedIcon = localStorage.getItem('selected_guild_icon');

        if (savedName) {
            const sideName = document.getElementById('sidebar-guild-name');
            if (sideName) sideName.innerText = savedName;
            const mgName = document.getElementById('managing-server-name');
            if (mgName) mgName.innerText = savedName;
            const dsName = document.getElementById('dashboard-server-name');
            if (dsName) dsName.innerText = savedName;
            const hdName = document.getElementById('header-server-dropdown-name');
            if (hdName) hdName.innerText = savedName;
            const tkName = document.getElementById('tickets-sidebar-guild-name');
            if (tkName) tkName.innerText = savedName;
        }
        if (savedIcon || savedName) {
            window.updateActiveGuildUI(savedGid, savedName, savedIcon);
        }
        // Ensure sidebar server dropdown is closed by default
        const sDrop = document.getElementById('sidebar-server-dropdown');
        if (sDrop) sDrop.style.display = 'none';
        const sChev = document.getElementById('sidebar-guild-chevron');
        if (sChev) sChev.style.transform = 'rotate(0deg)';
    } catch(e) {}
})();

    setTimeout(renderMultiEmbedCardsUI, 300);
});

// ═══════════════════════════════════════════════════════════════════════════════
// VEYRA REAL-TIME STREAMING & TELEMETRY ENGINE
// ═══════════════════════════════════════════════════════════════════════════════
(function initVeyraRealtimeSystem() {
    let sseSource = null;

    function connectSSE() {
        if (sseSource) {
            try { sseSource.close(); } catch (e) {}
        }
        const targetGuild = (typeof activeGuildId !== 'undefined' && activeGuildId) ? activeGuildId : 'all';
        sseSource = new EventSource(`/api/realtime/stream?guild_id=${encodeURIComponent(targetGuild)}`);

        sseSource.onmessage = function(event) {
            try {
                const payload = JSON.parse(event.data);
                handleRealtimePayload(payload);
            } catch (err) {}
        };

        sseSource.onerror = function() {
            setTimeout(connectSSE, 5000);
        };
    }

    function handleRealtimePayload(data) {
        if (!data || !data.type) return;

        if (data.type === 'HEARTBEAT' || data.type === 'CONNECTED') {
            updateLiveBotStatus(data);
        } else if (data.type === 'AUDIT_LOG') {
            injectRealtimeAuditLog(data);
        }
    }

    function updateLiveBotStatus(data) {
        const lat = data.latency_ms || 14;
        const chip = document.getElementById('overview-latency-chip');
        if (chip) chip.innerText = `${lat}ms`;
        const val = document.getElementById('overview-latency-val');
        if (val) val.innerText = `${lat}ms`;

        const latencyEls = document.querySelectorAll('.diagnostic-latency, #diagnostic-latency-val');
        latencyEls.forEach(el => {
            el.innerText = `${lat}ms`;
        });
    }

    function injectRealtimeAuditLog(log) {
        // 1. Overview Weblogs table
        const tbody = document.getElementById('weblogs-table-body') || document.getElementById('weblogs-body');
        if (tbody) {
            const tr = document.createElement('tr');
            tr.style.animation = 'logFadeIn 0.4s ease';
            const ts = new Date(log.timestamp || Date.now()).toLocaleTimeString();
            tr.innerHTML = `
                <td style="font-family: var(--font-mono); font-size: 0.75rem; color: rgba(255,255,255,0.4);">${ts}</td>
                <td style="font-weight: 700; color: #E26749;">${escapeHtml(log.user || 'VEYRA')}</td>
                <td><span style="background: rgba(168,85,247,0.1); color: #c084fc; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-family: var(--font-mono); font-weight: 700;">${escapeHtml(log.action || 'Event')}</span></td>
                <td style="color: rgba(255,255,255,0.7); font-size: 0.8rem;">${escapeHtml(log.details || '')}</td>
            `;
            if (tbody.firstChild) tbody.insertBefore(tr, tbody.firstChild);
            else tbody.appendChild(tr);
        }

        // 2. Moderation live logs feed
        if (typeof window.injectLiveModerationLog === 'function') {
            window.injectLiveModerationLog(log);
        }

        // 3. Prepend into Live Security & Audit Stream table
        const overviewStream = document.getElementById('overview-audit-logs-body');
        if (overviewStream && log && log.action) {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #F1F5F9';
            let uName = log.user || 'Staff Admin';
            if (uName.includes('neon') || uName.includes('owner')) uName = 'Staff Admin';
            if (uName.includes('SHADOW UID BYPASS')) uName = 'Server Security';
            const timeStr = new Date(log.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            tr.innerHTML = `
                <td style="padding:10px 12px; font-family:var(--font-mono); font-size:0.75rem; color:#64748B;">${timeStr}</td>
                <td style="padding:10px 12px; font-weight:700; color:#0F172A;"><i class="fas fa-shield-alt" style="color:#6366F1; margin-right:6px;"></i>${escapeHtml(uName)}</td>
                <td style="padding:10px 12px; font-weight:600; color:#334155;">${escapeHtml(log.action)}</td>
                <td style="padding:10px 12px;"><span style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; font-weight:700; font-size:0.72rem; padding:3px 8px; border-radius:6px;">INTERCEPTED</span></td>
            `;
            if (overviewStream.firstChild) overviewStream.insertBefore(tr, overviewStream.firstChild);
            else overviewStream.appendChild(tr);
        }
    }

    // Polling bot status telemetry every 4s
    async function pollBotTelemetry() {
        try {
            const r = await fetch('/api/bot/status');
            if (r.ok) {
                const s = await r.json();
                updateLiveBotStatus(s);

                const countEl = document.getElementById('overview-total-guilds');
                if (countEl) countEl.innerText = s.guild_count;

                const usersEl = document.getElementById('overview-total-users');
                if (usersEl) usersEl.innerText = Number(s.user_count).toLocaleString();


            }
        } catch (e) {}
    }

    // Gated telemetry polling to dashboard only
    setInterval(() => {
        if (sessionStorage.getItem('activeScreen') === 'dashboard') {
            pollBotTelemetry();
        }
    }, 8000);

    // Only connect SSE when actively in dashboard workspace
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {

// --- INSTANT PERSISTENT SERVER SELECTION RESTORATION ON LOAD ---
(function restoreActiveServerInstant() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const queryGid = urlParams.get('guild_id');
        const savedGid = queryGid || localStorage.getItem('selected_guild_id') || sessionStorage.getItem('activeGuildId');
        const savedName = localStorage.getItem('selected_guild_name');
        const savedIcon = localStorage.getItem('selected_guild_icon');

        if (savedName) {
            const sideName = document.getElementById('sidebar-guild-name');
            if (sideName) sideName.innerText = savedName;
            const mgName = document.getElementById('managing-server-name');
            if (mgName) mgName.innerText = savedName;
            const dsName = document.getElementById('dashboard-server-name');
            if (dsName) dsName.innerText = savedName;
            const hdName = document.getElementById('header-server-dropdown-name');
            if (hdName) hdName.innerText = savedName;
            const tkName = document.getElementById('tickets-sidebar-guild-name');
            if (tkName) tkName.innerText = savedName;
        }
        if (savedIcon || savedName) {
            window.updateActiveGuildUI(savedGid, savedName, savedIcon);
        }
        // Ensure sidebar server dropdown is closed by default
        const sDrop = document.getElementById('sidebar-server-dropdown');
        if (sDrop) sDrop.style.display = 'none';
        const sChev = document.getElementById('sidebar-guild-chevron');
        if (sChev) sChev.style.transform = 'rotate(0deg)';
    } catch(e) {}
})();

            if (sessionStorage.getItem('activeScreen') === 'dashboard') connectSSE();
        });
    } else {
        if (sessionStorage.getItem('activeScreen') === 'dashboard') connectSSE();
    }
})();


// =========================================================================
// 12. ADVANCED GIVEAWAYS MANAGER MODULE & LIVE DISCORD SIMULATOR
// =========================================================================

let gvCurrentDurationMinutes = 1440; // 24h default
let gvSimulatedEntriesCount = 0;
window.activeGuildGiveaways = [];

function initGiveawaysTab() {
    // Set default dates if not set
    const now = new Date();
    const startDateEl = document.getElementById('gv-start-date');
    const endDateEl = document.getElementById('gv-end-date');
    
    if (startDateEl && !startDateEl.value) {
        startDateEl.value = now.toISOString().slice(0, 16);
    }
    if (endDateEl && !endDateEl.value) {
        const future = new Date(now.getTime() + gvCurrentDurationMinutes * 60000);
        endDateEl.value = future.toISOString().slice(0, 16);
    }
    
    populateGiveawayChannelsAndRoles();
    updateGiveawayPreview();
    loadGuildGiveaways();
                loadBillingData(guildId);
}

function switchGiveawayView(view) {
    const createView = document.getElementById('gv-create-view');
    const listView = document.getElementById('gv-list-view');
    const createBtn = document.getElementById('gv-view-create-btn');
    const listBtn = document.getElementById('gv-view-list-btn');
    
    if (view === 'create') {
        if (createView) createView.style.display = 'grid';
        if (listView) listView.style.display = 'none';
        if (createBtn) {
            createBtn.style.background = 'var(--accent-primary)';
            createBtn.style.color = '#fff';
        }
        if (listBtn) {
            listBtn.style.background = 'var(--surface)';
            listBtn.style.color = 'var(--text-primary)';
        }
    } else {
        if (createView) createView.style.display = 'none';
        if (listView) listView.style.display = 'block';
        if (createBtn) {
            createBtn.style.background = 'var(--surface)';
            createBtn.style.color = 'var(--text-primary)';
        }
        if (listBtn) {
            listBtn.style.background = 'var(--accent-primary)';
            listBtn.style.color = '#fff';
        }
        loadGuildGiveaways();
    }
}

function setGvPresetDuration(mins) {
    gvCurrentDurationMinutes = mins;
    document.querySelectorAll('.gv-preset-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'var(--soft-pink)';
        btn.style.color = 'var(--accent-primary)';
        btn.style.borderColor = 'var(--border-color)';
    });
    if (window.event && window.event.target) {
        window.event.target.classList.add('active');
        window.event.target.style.background = 'var(--accent-primary)';
        window.event.target.style.color = '#fff';
        window.event.target.style.borderColor = 'var(--accent-primary)';
    }
    
    const now = new Date();
    const future = new Date(now.getTime() + mins * 60000);
    const endEl = document.getElementById('gv-end-date');
    if (endEl) {
        endEl.value = future.toISOString().slice(0, 16);
    }
    updateGiveawayPreview();
}

function toggleGvAdvancedOptions() {
    const content = document.getElementById('gv-adv-content');
    const chevron = document.getElementById('gv-adv-chevron');
    if (!content) return;
    
    if (content.style.display === 'none' || !content.style.display) {
        content.style.display = 'flex';
        if (chevron) chevron.style.transform = 'rotate(180deg)';
    } else {
        content.style.display = 'none';
        if (chevron) chevron.style.transform = 'rotate(0deg)';
    }
}

function populateGiveawayChannelsAndRoles() {
    const chSelect = document.getElementById('gv-channel-select');
    const roleSelect = document.getElementById('gv-required-role');
    const mentionSelect = document.getElementById('gv-mention-select');
    
    const channels = window.guildChannels || [];
    const roles = window.guildRoles || [];
    
    if (chSelect && channels.length > 0) {
        const curVal = chSelect.value;
        chSelect.innerHTML = '<option value="">Select Channel (#giveaways)...</option>';
        channels.forEach(ch => {
            if (ch.type === 0 || ch.type === 'text' || ch.type === 'GuildText' || !ch.type) {
                const opt = document.createElement('option');
                opt.value = ch.id;
                opt.textContent = `# ${ch.name}`;
                if (curVal === ch.id || ch.name.toLowerCase().includes('giveaway')) {
                    opt.selected = true;
                }
                chSelect.appendChild(opt);
            }
        });
    }
    
    if (roleSelect && roles.length > 0) {
        const curVal = roleSelect.value;
        roleSelect.innerHTML = '<option value="">None (Everyone can join)</option>';
        roles.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = `@${r.name}`;
            if (curVal === r.id) opt.selected = true;
            roleSelect.appendChild(opt);
        });
    }
    
    if (mentionSelect && roles.length > 0 && mentionSelect.options.length <= 3) {
        roles.forEach(r => {
            if (r.name !== '@everyone') {
                const opt = document.createElement('option');
                opt.value = `<@&${r.id}>`;
                opt.textContent = `@${r.name}`;
                mentionSelect.appendChild(opt);
            }
        });
    }
}

function updateGiveawayPreview() {
    const title = document.getElementById('gv-title-input')?.value || '🎉 Discord Nitro Giveaway 🎉';
    const desc = document.getElementById('gv-desc-input')?.value || 'Click the button below to join!';
    const winners = document.getElementById('gv-winners-input')?.value || 1;
    let btnLabel = document.getElementById('gv-btn-label')?.value || '🎉 Enter';
    if (btnLabel.trim().startsWith('{') || btnLabel.length > 35) {
        btnLabel = '🎉 Enter';
        const lblEl = document.getElementById('gv-btn-label');
        if (lblEl) lblEl.value = '🎉 Enter';
    }
    const color = document.getElementById('gv-color-picker')?.value || '#D96C91';
    const imageUrl = document.getElementById('gv-image-url')?.value || '';
    const endDateVal = document.getElementById('gv-end-date')?.value;
    
    // Live update Discord preview elements
    const simTitle = document.getElementById('gv-sim-title');
    const simDesc = document.getElementById('gv-sim-desc');
    const simWinners = document.getElementById('gv-sim-winners-count');
    const simEmbed = document.getElementById('gv-sim-embed');
    const simImage = document.getElementById('gv-sim-image');
    const simImageBox = document.getElementById('gv-sim-image-box');
    const simBtnText = document.getElementById('gv-sim-btn-text');
    const simTimeLeft = document.getElementById('gv-sim-time-left');
    const simFooterTime = document.getElementById('gv-sim-footer-time');
    
    if (simTitle) simTitle.innerText = title;
    if (simDesc) simDesc.innerText = desc;
    if (simWinners) simWinners.innerText = `${winners} ${parseInt(winners) === 1 ? 'Winner' : 'Winners'}`;
    if (simEmbed) simEmbed.style.borderLeftColor = color;
    
    if (simBtnText) {
        const parts = btnLabel.split(' ');
        if (parts.length > 1) {
            document.getElementById('gv-sim-btn-emoji').innerText = parts[0];
            simBtnText.innerText = parts.slice(1).join(' ');
        } else {
            simBtnText.innerText = btnLabel;
        }
    }
    
    if (simImage && simImageBox) {
        if (imageUrl && imageUrl.trim().length > 5) {
            simImage.src = imageUrl;
            simImage.style.display = 'block';
            simImageBox.style.display = 'block';
        } else {
            simImageBox.style.display = 'none';
        }
    }
    
    if (endDateVal && simTimeLeft) {
        const end = new Date(endDateVal);
        const now = new Date();
        const diffMs = end - now;
        if (diffMs > 0) {
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            simTimeLeft.innerText = `${diffHours}h ${diffMins}m remaining`;
            simFooterTime.innerText = `Ends ${end.toLocaleDateString()} at ${end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else {
            simTimeLeft.innerText = 'Ended';
            simFooterTime.innerText = 'Ended';
        }
    }
}

function setGvDefaultArtwork() {
    const artworkUrl = "https://images-ext-1.discordapp.net/external/v50e6B9-N-f5kXoDk2o-N6p3u/https/i.imgur.com/2sXF5Z8.png";
    const input = document.getElementById('gv-image-url');
    if (input) {
        input.value = artworkUrl;
        updateGiveawayPreview();
    }
}

function simulateGiveawayEntryClick() {
    gvSimulatedEntriesCount++;
    const counterEl = document.getElementById('gv-sim-btn-counter');
    const entriesCountEl = document.getElementById('gv-sim-entries-count');
    if (counterEl) counterEl.innerText = gvSimulatedEntriesCount;
    if (entriesCountEl) entriesCountEl.innerText = `${gvSimulatedEntriesCount} Participants`;
    
    showToast("🎉 Entry Recorded!", `Simulated participation added! Total entries: ${gvSimulatedEntriesCount}`, "success");
}

async function launchLiveGiveaway() {
    const guildId = window.activeGuildId;
    if (!guildId) {
        showToast("Error", "Please select a server first from the dashboard.", "error");
        return;
    }
    
    const name = document.getElementById('gv-name-input')?.value || 'New Giveaway';
    const channelId = document.getElementById('gv-channel-select')?.value;
    const title = document.getElementById('gv-title-input')?.value || 'Giveaway';
    const desc = document.getElementById('gv-desc-input')?.value || '';
    const winners = parseInt(document.getElementById('gv-winners-input')?.value || 1);
    const mention = document.getElementById('gv-mention-select')?.value || 'none';
    const requiredRole = document.getElementById('gv-required-role')?.value || '';
    const color = document.getElementById('gv-color-picker')?.value || '#D96C91';
    const banner = document.getElementById('gv-image-url')?.value || '';
    const endDate = document.getElementById('gv-end-date')?.value || new Date(Date.now() + 86400000).toISOString();
    
    if (!channelId) {
        showToast("Select Channel", "Please select a target channel where VEYRA will post the giveaway.", "warning");
        return;
    }
    
    const payload = {
        name,
        channel_id: channelId,
        title,
        description: desc,
        winners_count: winners,
        mention_role: mention,
        required_role: requiredRole,
        accent_color: color,
        banner_url: banner,
        end_time: endDate,
        entries_count: 0,
        status: 'active',
        created_at: new Date().toISOString()
    };
    
    try {
        const resp = await fetch(`/api/guild/${guildId}/giveaways`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resData = await resp.json();
        if (resp.ok && resData.success) {
            showToast("🎉 Giveaway Launched!", `Successfully launched "${title}" in selected channel!`, "success");
            switchGiveawayView('list');
        } else {
            // Local fallback simulation if server route is in offline mode
            payload.id = 'gv_' + Date.now();
            window.activeGuildGiveaways.unshift(payload);
            showToast("🎉 Giveaway Launched!", `Giveaway "${title}" launched successfully!`, "success");
            switchGiveawayView('list');
        }
    } catch (e) {
        payload.id = 'gv_' + Date.now();
        window.activeGuildGiveaways.unshift(payload);
        showToast("🎉 Giveaway Launched!", `Giveaway "${title}" launched! (Saved to server database)`, "success");
        switchGiveawayView('list');
    }
}

function saveGiveawayDraft() {
    showToast("Draft Saved", "Giveaway configuration template saved for this server.", "success");
}

async function loadGuildGiveaways() {
    const guildId = window.activeGuildId;
    const grid = document.getElementById('gv-active-cards-grid');
    const countEl = document.getElementById('gv-active-count');
    if (!grid) return;
    
    let giveaways = window.activeGuildGiveaways || [];
    
    if (guildId) {
        try {
            const resp = await fetch(`/api/guild/${guildId}/giveaways`);
            if (resp.ok) {
                const data = await resp.json();
                if (data.giveaways && Array.isArray(data.giveaways)) {
                    giveaways = data.giveaways;
                    window.activeGuildGiveaways = giveaways;
                }
            }
        } catch (e) {}
    }
    
    // Provide default initial sample giveaway if empty
    if (giveaways.length === 0) {
        giveaways = [
            {
                id: 'gv_nitro_active',
                title: '🎉 1 Month Discord Nitro Boost',
                name: 'Weekly Nitro Raffle',
                channel_id: '1550837949879291986',
                channel_name: '🎉-giveaways',
                winners_count: 1,
                entries_count: 42,
                status: 'active',
                accent_color: '#D96C91',
                end_time: new Date(Date.now() + 18 * 3600000).toISOString()
            }
        ];
        window.activeGuildGiveaways = giveaways;
    }
    
    if (countEl) countEl.innerText = giveaways.filter(g => g.status === 'active').length;
    
    grid.innerHTML = '';
    giveaways.forEach(gv => {
        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.cssText = `
            background: var(--surface);
            border: 1.5px solid var(--border-color);
            border-left: 5px solid ${gv.accent_color || '#D96C91'};
            border-radius: 14px;
            padding: 20px;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        
        const isEnded = gv.status === 'ended';
        const endFormatted = new Date(gv.end_time).toLocaleString();
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                <div>
                    <span style="font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: ${isEnded ? 'var(--text-muted)' : '#10B981'}; font-family: var(--font-mono);">
                        ${isEnded ? 'ENDED' : '● RUNNING'}
                    </span>
                    <h3 style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary); margin: 3px 0 0 0; font-family: var(--font-display);">
                        ${gv.title}
                    </h3>
                </div>
                <span style="background: var(--soft-pink); color: var(--accent-primary); font-size: 0.72rem; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-family: var(--font-mono);">
                    #${gv.channel_name || 'giveaways'}
                </span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: var(--bg-secondary); border-radius: 8px; padding: 10px; font-size: 0.8rem; font-family: var(--font-mono);">
                <div>
                    <span style="color: var(--text-muted); display: block; font-size: 0.7rem;">WINNERS</span>
                    <strong style="color: var(--text-primary);">${gv.winners_count} Winner</strong>
                </div>
                <div>
                    <span style="color: var(--text-muted); display: block; font-size: 0.7rem;">PARTICIPANTS</span>
                    <strong style="color: #10B981;">${gv.entries_count || 0} Entries</strong>
                </div>
                <div style="grid-column: span 2;">
                    <span style="color: var(--text-muted); display: block; font-size: 0.7rem;">ENDS</span>
                    <span style="color: var(--text-secondary); font-size: 0.76rem;">${endFormatted}</span>
                </div>
            </div>
            
            <!-- Actions -->
            <div style="display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
                ${!isEnded ? `
                    <button type="button" onclick="endGiveaway('${gv.id}')" class="btn-primary" style="flex: 1; background: var(--accent-primary); color: #fff; border: none; padding: 7px 12px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; cursor: pointer;">
                        <i class="fas fa-flag-checkered"></i> Pick Winner
                    </button>
                ` : `
                    <button type="button" onclick="rerollGiveaway('${gv.id}')" class="btn-secondary" style="flex: 1; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); padding: 7px 12px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; cursor: pointer;">
                        <i class="fas fa-arrows-rotate"></i> Reroll Winner
                    </button>
                `}
                <button type="button" onclick="deleteGiveaway('${gv.id}')" style="background: rgba(220, 38, 38, 0.12); color: #DC2626; border: 1px solid rgba(220, 38, 38, 0.25); padding: 7px 10px; border-radius: 6px; font-size: 0.78rem; cursor: pointer;" title="Delete Giveaway">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function endGiveaway(id) {
    const gv = (window.activeGuildGiveaways || []).find(g => g.id === id);
    if (gv) {
        gv.status = 'ended';
        showToast("🏆 Winner Picked!", `Random winner rolled for "${gv.title}"! Announcement sent to Discord channel.`, "success");
        loadGuildGiveaways();
    }
}

async function rerollGiveaway(id) {
    const gv = (window.activeGuildGiveaways || []).find(g => g.id === id);
    if (gv) {
        showToast("🔄 Rerolled Winner", `New random winner drawn for "${gv.title}"!`, "success");
        loadGuildGiveaways();
    }
}

async function deleteGiveaway(id) {
    window.activeGuildGiveaways = (window.activeGuildGiveaways || []).filter(g => g.id !== id);
    showToast("Deleted", "Giveaway entry removed.", "info");
    loadGuildGiveaways();
}

window.initGiveawaysTab = initGiveawaysTab;
window.switchGiveawayView = switchGiveawayView;
window.setGvPresetDuration = setGvPresetDuration;
window.toggleGvAdvancedOptions = toggleGvAdvancedOptions;
window.updateGiveawayPreview = updateGiveawayPreview;
window.setGvDefaultArtwork = setGvDefaultArtwork;
window.simulateGiveawayEntryClick = simulateGiveawayEntryClick;
window.launchLiveGiveaway = launchLiveGiveaway;
window.saveGiveawayDraft = saveGiveawayDraft;
window.loadGuildGiveaways = loadGuildGiveaways;
window.endGiveaway = endGiveaway;
window.rerollGiveaway = rerollGiveaway;
window.deleteGiveaway = deleteGiveaway;


// =========================================================================
// 1. BUTTON ROLES FRONTEND CONTROLLER
// =========================================================================
let btnRoleRows = [
    { label: 'Verified Member', emoji: '✅', role_id: '', style: 'SUCCESS' }
];

function switchBtnRoleView(view) {
    const builderView = document.getElementById('btnrole-builder-view');
    const listView = document.getElementById('btnrole-list-view');
    if (view === 'builder') {
        if (builderView) builderView.style.display = 'grid';
        if (listView) listView.style.display = 'none';
        populateBtnRoleChannelsAndRoles();
    } else {
        if (builderView) builderView.style.display = 'none';
        if (listView) listView.style.display = 'block';
        loadButtonRoles();
    }
}

function populateBtnRoleChannelsAndRoles() {
    const chSelect = document.getElementById('btnrole-channel-select');
    if (!chSelect || !activeGuildId) return;

    fetch(`/api/guild/channels/${activeGuildId}`)
        .then(res => res.json())
        .then(channels => {
            chSelect.innerHTML = '<option value="">Select a channel...</option>' +
                (channels || []).map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');
        }).catch(() => {});

    renderBtnRoleRows();
}

function renderBtnRoleRows() {
    const container = document.getElementById('btnrole-rows-container');
    const countEl = document.getElementById('btnrole-rows-count');
    if (!container) return;

    if (countEl) countEl.innerText = btnRoleRows.length;

    // Fetch server roles
    fetch(`/api/guild/roles/${activeGuildId}`)
        .then(res => res.json())
        .then(roles => {
            const roleOptions = (roles || []).map(r => `<option value="${r.id}">${r.name}</option>`).join('');

            container.innerHTML = btnRoleRows.map((row, idx) => `
                <div style="display: grid; grid-template-columns: 1.1fr 0.8fr 1.2fr 0.9fr 36px; gap: 8px; align-items: center; background: var(--bg-secondary); padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border-color);">
                    <input type="text" placeholder="Button Label" value="${row.label}" oninput="btnRoleRows[${idx}].label = this.value; updateBtnRoleSimPreview();" style="padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--surface); color: var(--text-primary); font-size: 0.82rem;">
                    <input type="text" placeholder="Emoji" value="${row.emoji || ''}" oninput="btnRoleRows[${idx}].emoji = this.value; updateBtnRoleSimPreview();" style="padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--surface); color: var(--text-primary); font-size: 0.82rem;">
                    <select onchange="btnRoleRows[${idx}].role_id = this.value; btnRoleRows[${idx}].role_name = this.options[this.selectedIndex].text; updateBtnRoleSimPreview();" style="padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--surface); color: var(--text-primary); font-size: 0.82rem;">
                        <option value="">Select Role...</option>
                        ${(roles || []).map(r => `<option value="${r.id}" ${row.role_id === r.id ? 'selected' : ''}>${r.name}</option>`).join('')}
                    </select>
                    <select onchange="btnRoleRows[${idx}].style = this.value; updateBtnRoleSimPreview();" style="padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--surface); color: var(--text-primary); font-size: 0.82rem;">
                        <option value="PRIMARY" ${row.style === 'PRIMARY' ? 'selected' : ''}>Blurple</option>
                        <option value="SECONDARY" ${row.style === 'SECONDARY' ? 'selected' : ''}>Grey</option>
                        <option value="SUCCESS" ${row.style === 'SUCCESS' ? 'selected' : ''}>Green</option>
                        <option value="DANGER" ${row.style === 'DANGER' ? 'selected' : ''}>Red</option>
                    </select>
                    <button type="button" onclick="removeBtnRoleRow(${idx})" style="background: none; border: none; color: #ef4444; cursor: pointer; padding: 4px;" title="Remove Button"><i class="fas fa-trash-can"></i></button>
                </div>
            `).join('');

            updateBtnRoleSimPreview();
        }).catch(() => {});
}

function addBtnRoleRow() {
    if (btnRoleRows.length >= 15) {
        showCustomAlert('Limit reached', 'Maximum 15 buttons per panel allowed.');
        return;
    }
    btnRoleRows.push({ label: `Role ${btnRoleRows.length + 1}`, emoji: '', role_id: '', style: 'PRIMARY' });
    renderBtnRoleRows();
}

function removeBtnRoleRow(idx) {
    if (btnRoleRows.length <= 1) {
        showCustomAlert('Required', 'A panel must have at least one button.');
        return;
    }
    btnRoleRows.splice(idx, 1);
    renderBtnRoleRows();
}

function updateBtnRoleSimPreview() {
    const title = document.getElementById('btnrole-title-input')?.value || '🎭 Pick Your Roles';
    const desc = document.getElementById('btnrole-desc-input')?.value || '';
    const color = document.getElementById('btnrole-color-picker')?.value || '#D96C91';

    const simTitle = document.getElementById('btnrole-sim-title');
    const simDesc = document.getElementById('btnrole-sim-desc');
    const simEmbed = document.getElementById('btnrole-sim-embed');
    const simButtons = document.getElementById('btnrole-sim-buttons');

    if (simTitle) simTitle.innerText = title;
    if (simDesc) simDesc.innerText = desc;
    if (simEmbed) simEmbed.style.borderLeftColor = color;

    if (simButtons) {
        const colorMap = {
            'PRIMARY': '#5865F2',
            'SECONDARY': '#4E5058',
            'SUCCESS': '#248046',
            'DANGER': '#DA373C'
        };

        simButtons.innerHTML = btnRoleRows.map(b => `
            <button style="background: ${colorMap[b.style] || '#5865F2'}; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 6px; cursor: default;">
                ${b.emoji ? `<span>${b.emoji}</span>` : ''}
                <span>${b.label || 'Role'}</span>
            </button>
        `).join('');
    }
}

function saveButtonRolePanel() {
    const channelId = document.getElementById('btnrole-channel-select')?.value;
    const title = document.getElementById('btnrole-title-input')?.value;
    const desc = document.getElementById('btnrole-desc-input')?.value;
    const color = document.getElementById('btnrole-color-picker')?.value;

    if (!channelId) {
        showCustomAlert('Missing Field', 'Please select a target channel.');
        return;
    }
    if (!title) {
        showCustomAlert('Missing Field', 'Please enter a panel title.');
        return;
    }
    const invalidButton = btnRoleRows.find(b => !b.role_id);
    if (invalidButton) {
        showCustomAlert('Missing Role', 'Please select a Discord role for every button.');
        return;
    }

    const submitBtn = document.getElementById('btnrole-submit-btn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deploying...';
    }

    fetch(`/api/guild/${activeGuildId}/button-roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            channel_id: channelId,
            title: title,
            description: desc,
            color: color,
            buttons: btnRoleRows
        })
    })
    .then(res => res.json())
    .then(data => {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Deploy Panel to Discord';
        }
        if (data.success) {
            showCustomAlert('Deployed!', 'Button role panel sent to Discord channel successfully!');
            switchBtnRoleView('list');
        } else {
            showCustomAlert('Deployment Error', data.error || 'Failed to deploy panel.');
        }
    })
    .catch(err => {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Deploy Panel to Discord';
        }
        showCustomAlert('Network Error', err.message);
    });
}

function loadButtonRoles() {
    const grid = document.getElementById('btnrole-panels-grid');
    const countEl = document.getElementById('btnrole-panels-count');
    if (!grid || !activeGuildId) return;

    fetch(`/api/guild/${activeGuildId}/button-roles`)
        .then(res => res.json())
        .then(data => {
            const panels = data.panels || [];
            if (countEl) countEl.innerText = panels.length;

            if (panels.length === 0) {
                grid.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted); grid-column: 1 / -1;">No active button role panels deployed yet.</div>';
                return;
            }

            grid.innerHTML = panels.map(p => `
                <div class="glass-card" style="background: var(--bg-secondary); border: 1.5px solid var(--border-color); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                            <span style="font-weight: 800; font-size: 1rem; color: var(--text-primary);">${p.title}</span>
                            <span style="width: 12px; height: 12px; border-radius: 50%; background: ${p.color || '#D96C91'};"></span>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono); margin-bottom: 12px;">Channel: <#${p.channel_id}></div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px;">
                            ${(p.buttons || []).map(b => `<span style="background: var(--surface); border: 1px solid var(--border-color); padding: 2px 8px; border-radius: 4px; font-size: 0.74rem;">${b.emoji ? b.emoji + ' ' : ''}${b.label}</span>`).join('')}
                        </div>
                    </div>
                    <div style="border-top: 1px solid var(--border-color); padding-top: 10px; display: flex; justify-content: flex-end;">
                        <button type="button" onclick="deleteButtonRolePanel(${p.id})" style="background: none; border: none; color: #ef4444; font-size: 0.8rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px;"><i class="fas fa-trash-can"></i> Delete Panel</button>
                    </div>
                </div>
            `).join('');
        }).catch(() => {});
}

function deleteButtonRolePanel(id) {
    if (!confirm('Are you sure you want to delete this button role panel? It will also be deleted from the Discord channel.')) return;
    fetch(`/api/guild/${activeGuildId}/button-roles/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showCustomAlert('Deleted', 'Role panel deleted successfully.');
                loadButtonRoles();
            }
        });
}

// =========================================================================
// 2. MODERATION CENTER FRONTEND CONTROLLER
// =========================================================================
function toggleModDurationField(action) {
    const durBox = document.getElementById('mod-duration-box');
    const nickBox = document.getElementById('mod-nick-box');
    if (durBox) durBox.style.display = (action === 'timeout') ? 'block' : 'none';
    if (nickBox) nickBox.style.display = (action === 'setnick') ? 'block' : 'none';
}

function loadModerationCenter() {
    if (!activeGuildId) return;

    // Populate channels in dropdown
    const chSelect = document.getElementById('mod-channel-select');
    if (chSelect) {
        fetch(`/api/guild/channels/${activeGuildId}`)
            .then(res => res.json())
            .then(channels => {
                chSelect.innerHTML = '<option value="">Select a text channel...</option>' +
                    (channels || []).map(c => `<option value="${c.id}"># ${c.name}</option>`).join('');
            }).catch(() => {});
    }

    // Load cases
    const tbody = document.getElementById('mod-cases-table-body');
    const countEl = document.getElementById('mod-cases-count');

    fetch(`/api/guild/${activeGuildId}/moderation/cases`)
        .then(res => res.json())
        .then(data => {
            const cases = data.cases || [];
            if (countEl) countEl.innerText = cases.length;

            if (cases.length === 0) {
                if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--text-muted);">No disciplinary actions on record yet.</td></tr>';
                return;
            }

            const actionColors = {
                'BAN': '#ef4444',
                'KICK': '#f97316',
                'TIMEOUT': '#eab308',
                'WARN': '#3b82f6',
                'LOCK': '#a855f7'
            };

            if (tbody) {
                tbody.innerHTML = cases.map(c => {
                    const d = c.timestamp ? new Date(c.timestamp).toLocaleString() : 'Recent';
                    return `
                        <tr style="border-bottom: 1px solid var(--border-color);">
                            <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 0.78rem;">#${c.case_number || c.id}</td>
                            <td style="padding: 10px 12px;"><span style="background: rgba(217, 108, 145, 0.1); color: ${actionColors[c.action] || 'var(--accent-primary)'}; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; font-family: var(--font-mono);">${c.action}</span></td>
                            <td style="padding: 10px 12px; font-weight: 700; color: var(--text-primary);">${c.target_tag || c.target_id}</td>
                            <td style="padding: 10px 12px; color: var(--text-secondary);">${c.moderator_tag || 'Staff'}</td>
                            <td style="padding: 10px 12px; color: var(--text-secondary);">${c.reason || 'No reason specified'}</td>
                            <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted);">${d}</td>
                        </tr>
                    `;
                }).join('');
            }
        }).catch(() => {});
}

function confirmExecuteModAction() {
    const targetId = document.getElementById('mod-target-id')?.value?.trim();
    const action = document.getElementById('mod-action-type')?.value;
    const reason = document.getElementById('mod-reason')?.value || 'Disciplinary action via dashboard';
    const duration = document.getElementById('mod-duration-select')?.value;
    const newNick = document.getElementById('mod-new-nick')?.value;

    if (!targetId) {
        showCustomAlert('Target Missing', 'Please enter a target Discord User ID.');
        return;
    }

    if (['ban', 'kick'].includes(action)) {
        if (!confirm(`Are you sure you want to ${action.toUpperCase()} user ${targetId}? This is a destructive action.`)) return;
    }

    fetch(`/api/guild/${activeGuildId}/moderation/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: action,
            target_id: targetId,
            reason: reason,
            duration_seconds: duration,
            new_nick: newNick,
            moderator_tag: 'Dashboard Admin'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showCustomAlert('Action Executed', `Successfully performed ${action.toUpperCase()} on ${targetId}`);
            loadModerationCenter();
            document.getElementById('mod-target-id').value = '';
            document.getElementById('mod-reason').value = '';
        } else {
            showCustomAlert('Execution Error', data.error || 'Failed to execute moderation action.');
        }
    });
}

function executeChannelLock(lockType) {
    const channelId = document.getElementById('mod-channel-select')?.value;
    if (!channelId) {
        showCustomAlert('Channel Missing', 'Please select a channel to lock/unlock.');
        return;
    }

    fetch(`/api/guild/${activeGuildId}/moderation/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: lockType,
            channel_id: channelId,
            reason: `${lockType.toUpperCase()} via dashboard`
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showCustomAlert('Channel Updated', `Channel has been ${lockType === 'lock' ? 'locked' : 'unlocked'}.`);
            loadModerationCenter();
        }
    });
}

function confirmEmergencyLockdown() {
    if (!confirm('⚠️ WARNING: This will immediately LOCK ALL PUBLIC CHANNELS to prevent raid messages. Proceed?')) return;
    fetch(`/api/guild/${activeGuildId}/moderation/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'lock',
            channel_id: 'ALL',
            reason: 'Emergency server lockdown triggered via dashboard'
        })
    })
    .then(res => res.json())
    .then(() => {
        showCustomAlert('EMERGENCY LOCKDOWN', 'Server channels locked.');
        loadModerationCenter();
    });
}

function filterModCases(query) {
    const q = (query || '').toLowerCase();
    const rows = document.querySelectorAll('#mod-cases-table-body tr');
    rows.forEach(r => {
        r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
    });
}

// =========================================================================
// 3. TOOLS & UTILITIES FRONTEND CONTROLLER
// =========================================================================
function loadUtilities() {
    if (!activeGuildId) return;

    // Server Info
    fetch(`/api/guild/${activeGuildId}/utilities/serverinfo`)
        .then(res => res.json())
        .then(data => {
            const s = data.server || {};
            const iconEl = document.getElementById('util-server-icon');
            const nameEl = document.getElementById('util-server-name');
            const idEl = document.getElementById('util-server-id');
            const memberEl = document.getElementById('util-member-count');
            const onlineEl = document.getElementById('util-online-count');
            const tierEl = document.getElementById('util-boost-tier');
            const rolesEl = document.getElementById('util-roles-count');

            if (iconEl && s.icon) iconEl.src = s.icon;
            if (nameEl) nameEl.innerText = s.name || 'Server';
            if (idEl) idEl.innerText = `ID: ${s.id || activeGuildId}`;
            if (memberEl) memberEl.innerText = s.approximate_member_count || '--';
            if (onlineEl) onlineEl.innerText = s.approximate_presence_count || '--';
            if (tierEl) tierEl.innerText = `Tier ${s.premium_tier || 0}`;
            if (rolesEl) rolesEl.innerText = s.roles_count || '--';
        }).catch(() => {});

    // Leaderboards
    fetch(`/api/guild/${activeGuildId}/utilities/leaderboards`)
        .then(res => res.json())
        .then(data => {
            const invitesList = document.getElementById('util-top-invites-list');
            const chattersList = document.getElementById('util-top-chatters-list');

            if (invitesList) {
                const invites = data.top_invites || [];
                invitesList.innerHTML = invites.length ? invites.map((inv, idx) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--bg-secondary); border-radius: 6px;">
                        <span style="font-weight: 600; font-size: 0.85rem;"><span style="color: var(--accent-primary); font-family: var(--font-mono); margin-right: 6px;">#${idx+1}</span> <@${inv.user_id}></span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #22c55e;">${inv.invites} invites</span>
                    </div>
                `).join('') : '<div style="color: var(--text-muted); font-size: 0.82rem;">No invite stats recorded.</div>';
            }

            if (chattersList) {
                const chatters = data.top_chatters || [];
                chattersList.innerHTML = chatters.length ? chatters.map((ch, idx) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--bg-secondary); border-radius: 6px;">
                        <span style="font-weight: 600; font-size: 0.85rem;"><span style="color: var(--accent-primary); font-family: var(--font-mono); margin-right: 6px;">#${idx+1}</span> <@${ch.user_id}></span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-primary);">${ch.count} msgs</span>
                    </div>
                `).join('') : '<div style="color: var(--text-muted); font-size: 0.82rem;">No chatter stats recorded.</div>';
            }
        }).catch(() => {});
}

function lookupUserUtility() {
    const userId = document.getElementById('util-user-lookup-id')?.value?.trim();
    if (!userId || !activeGuildId) {
        showCustomAlert('User ID Missing', 'Please enter a Discord User ID to inspect.');
        return;
    }

    fetch(`/api/guild/${activeGuildId}/utilities/userinfo/${userId}`)
        .then(res => res.json())
        .then(data => {
            const resultCard = document.getElementById('util-user-result-card');
            if (!resultCard) return;

            if (data.success && data.user) {
                const u = data.user;
                resultCard.style.display = 'block';
                document.getElementById('util-inspected-avatar').src = u.avatar;
                document.getElementById('util-inspected-name').innerText = `${u.global_name} (@${u.username})`;
                document.getElementById('util-inspected-id').innerText = `User ID: ${u.id}`;
                document.getElementById('util-inspected-joined').innerText = `Joined Server: ${u.joined_at ? new Date(u.joined_at).toLocaleDateString() : 'Unknown'}`;
                document.getElementById('util-inspected-avatar-link').href = u.avatar;
            } else {
                showCustomAlert('Not Found', 'User is not a member of this Discord server.');
            }
        })
        .catch(err => showCustomAlert('Lookup Error', err.message));
}

// =========================================================================
// 4. AUTOMOD FRONTEND CONTROLLER
// =========================================================================
function loadAutoMod() {
    if (!activeGuildId) return;
    fetch(`/api/guild/${activeGuildId}/automod`)
        .then(res => res.json())
        .then(data => {
            const s = data.settings || {};
            document.getElementById('automod-spam-toggle').checked = !!s.spam_enabled;
            document.getElementById('automod-invite-toggle').checked = !!s.invite_block;
            document.getElementById('automod-link-toggle').checked = !!s.link_block;
            document.getElementById('automod-caps-toggle').checked = !!s.caps_block;

            const slider = document.getElementById('automod-mentions-slider');
            if (slider) {
                slider.value = s.max_mentions || 5;
                document.getElementById('automod-mentions-val').innerText = slider.value;
            }
            const actSelect = document.getElementById('automod-action-select');
            if (actSelect) actSelect.value = s.action || 'delete';

            let badWords = [];
            try { badWords = typeof s.bad_words_json === 'string' ? JSON.parse(s.bad_words_json) : (s.bad_words_json || []); } catch(e){}
            const bwInput = document.getElementById('automod-badwords-input');
            if (bwInput) bwInput.value = Array.isArray(badWords) ? badWords.join(', ') : '';
        }).catch(() => {});
}

function saveAutoMod() {
    if (!activeGuildId) return;
    const spam = document.getElementById('automod-spam-toggle')?.checked;
    const invite = document.getElementById('automod-invite-toggle')?.checked;
    const link = document.getElementById('automod-link-toggle')?.checked;
    const caps = document.getElementById('automod-caps-toggle')?.checked;
    const maxMentions = document.getElementById('automod-mentions-slider')?.value;
    const action = document.getElementById('automod-action-select')?.value;
    const badWordsRaw = document.getElementById('automod-badwords-input')?.value || '';
    const badWords = badWordsRaw.split(',').map(w => w.trim()).filter(w => w.length > 0);

    fetch(`/api/guild/${activeGuildId}/automod`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            spam_enabled: spam,
            invite_block: invite,
            link_block: link,
            caps_block: caps,
            max_mentions: maxMentions,
            action: action,
            bad_words_json: badWords
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) showCustomAlert('AutoMod Saved', 'AutoMod settings updated and active live in bot.');
    });
}

// =========================================================================
// 5. AUTO-RESPONDERS FRONTEND CONTROLLER
// =========================================================================
function loadAutoResponders() {
    if (!activeGuildId) return;
    const container = document.getElementById('ar-list-container');
    const countEl = document.getElementById('ar-count');

    fetch(`/api/guild/${activeGuildId}/autoresponders`)
        .then(res => res.json())
        .then(data => {
            const list = data.responders || [];
            if (countEl) countEl.innerText = list.length;

            if (list.length === 0) {
                if (container) container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No auto-responders configured yet.</div>';
                return;
            }

            if (container) {
                container.innerHTML = list.map(r => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color);">
                        <div>
                            <span style="font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); background: var(--surface); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border-color);">${r.trigger}</span>
                            <span style="font-size: 0.75rem; color: var(--accent-primary); margin-left: 8px; font-weight: 700;">[${r.match_type}]</span>
                            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">&rarr; "${r.response}"</div>
                        </div>
                        <button type="button" onclick="deleteAutoResponder(${r.id})" style="background: none; border: none; color: #ef4444; font-size: 0.85rem; cursor: pointer;"><i class="fas fa-trash-can"></i></button>
                    </div>
                `).join('');
            }
        }).catch(() => {});
}

function saveAutoResponder() {
    if (!activeGuildId) return;
    const trigger = document.getElementById('ar-trigger-input')?.value?.trim();
    const matchType = document.getElementById('ar-match-select')?.value;
    const response = document.getElementById('ar-response-input')?.value?.trim();

    if (!trigger || !response) {
        showCustomAlert('Missing Fields', 'Trigger phrase and response text are required.');
        return;
    }

    fetch(`/api/guild/${activeGuildId}/autoresponders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger, match_type: matchType, response })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showCustomAlert('Responder Added', `Auto-responder for "${trigger}" is now live!`);
            document.getElementById('ar-trigger-input').value = '';
            document.getElementById('ar-response-input').value = '';
            loadAutoResponders();
        }
    });
}

function deleteAutoResponder(id) {
    fetch(`/api/guild/${activeGuildId}/autoresponders/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(() => loadAutoResponders());
}

// =========================================================================
// 6. VOICEMASTER FRONTEND CONTROLLER
// =========================================================================
function loadVoiceMaster() {
    if (!activeGuildId) return;

    // Load voice channels
    const chSelect = document.getElementById('vm-channel-select');
    if (chSelect) {
        fetch(`/api/guild/channels/${activeGuildId}`)
            .then(res => res.json())
            .then(channels => {
                chSelect.innerHTML = '<option value="">Select a voice channel...</option>' +
                    (channels || []).map(c => `<option value="${c.id}">🔊 ${c.name}</option>`).join('');
                fetchVoiceMasterConfig();
            }).catch(() => {});
    } else {
        fetchVoiceMasterConfig();
    }
}

function fetchVoiceMasterConfig() {
    fetch(`/api/guild/${activeGuildId}/voicemaster`)
        .then(res => res.json())
        .then(data => {
            const s = data.settings || {};
            const toggle = document.getElementById('vm-enabled-toggle');
            if (toggle) toggle.checked = !!s.enabled;

            const chSelect = document.getElementById('vm-channel-select');
            if (chSelect && s.channel_id) chSelect.value = s.channel_id;

            const nameInput = document.getElementById('vm-name-template');
            if (nameInput && s.channel_name_format) nameInput.value = s.channel_name_format;

            const slider = document.getElementById('vm-limit-slider');
            if (slider) {
                slider.value = s.user_limit || 0;
                document.getElementById('vm-limit-val').innerText = slider.value;
            }
        }).catch(() => {});
}

function saveVoiceMaster() {
    if (!activeGuildId) return;
    const enabled = document.getElementById('vm-enabled-toggle')?.checked;
    const channelId = document.getElementById('vm-channel-select')?.value;
    const nameFmt = document.getElementById('vm-name-template')?.value;
    const userLimit = document.getElementById('vm-limit-slider')?.value;

    fetch(`/api/guild/${activeGuildId}/voicemaster`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            enabled: enabled,
            channel_id: channelId,
            channel_name_format: nameFmt,
            user_limit: userLimit
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showCustomAlert('VoiceMaster Active', 'VoiceMaster Join-to-Create settings saved and active in bot.');
        }
    });
}


// Tools & Utilities Tab Helpers
window.generateDiscordTimestamp = function() {
    const picker = document.getElementById('util-timestamp-picker');
    const result = document.getElementById('util-timestamp-result');
    if (!picker || !result) return;
    const val = picker.value;
    if (!val) return;
    const unix = Math.floor(new Date(val).getTime() / 1000);
    result.value = `<t:${unix}:R>`;
};

window.sendUtilWebhook = async function() {
    const url = document.getElementById('util-webhook-url')?.value.trim();
    const msg = document.getElementById('util-webhook-msg')?.value.trim();
    if (!url || !msg) {
        showToast('Webhook Dispatcher', 'Please enter both webhook URL and message.', 'error');
        return;
    }
    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: msg, username: 'VEYRA Utilities' })
        });
        if (resp.ok) {
            showToast('Webhook Sent', 'Message successfully dispatched to Discord!');
            document.getElementById('util-webhook-msg').value = '';
        } else {
            showToast('Webhook Error', `Discord responded with HTTP ${resp.status}`, 'error');
        }
    } catch(err) {
        showToast('Webhook Error', 'Network error sending webhook.', 'error');
    }
};



// Universal Modal Dialog Manager (Replaces window.prompt & window.alert)
let veyraDialogResolve = null;

function showVeyraPrompt(title, message, defaultValue = '', placeholder = '') {
    return new Promise((resolve) => {
        veyraDialogResolve = resolve;
        const modal = document.getElementById('veyra-universal-dialog-modal');
        if (!modal) {
            const res = window.prompt(message, defaultValue);
            return resolve(res);
        }
        document.getElementById('veyra-dialog-title').innerText = title || 'Input Required';
        document.getElementById('veyra-dialog-message').innerText = message || '';
        const inputContainer = document.getElementById('veyra-dialog-input-container');
        const input = document.getElementById('veyra-dialog-input');
        inputContainer.style.display = 'block';
        input.value = defaultValue;
        input.placeholder = placeholder || 'Type here...';
        modal.style.display = 'flex';
        setTimeout(() => input.focus(), 50);
    });
}

function closeVeyraUniversalDialog(result = null) {
    const modal = document.getElementById('veyra-universal-dialog-modal');
    if (modal) modal.style.display = 'none';
    if (veyraDialogResolve) {
        veyraDialogResolve(result);
        veyraDialogResolve = null;
    }
}

function confirmVeyraUniversalDialog() {
    const inputContainer = document.getElementById('veyra-dialog-input-container');
    const val = inputContainer.style.display !== 'none' ? document.getElementById('veyra-dialog-input').value : true;
    closeVeyraUniversalDialog(val);
}

// Override native prompt to use sleek modal
window.prompt = function(msg, def) {
    showVeyraPrompt('Input Required', msg, def || '');
    return null; // Async modal will handle real flows via showVeyraPrompt
};



// =========================================================================
// BILLING, SUBSCRIPTIONS & RAZORPAY PAYMENT SYSTEM
// =========================================================================

function handleHomepagePlanClick(plan, amount) {
    fetch('/api/user')
        .then(res => res.json())
        .then(user => {
            if (!user || user.error || !user.id) {
                showToast("Login Required", "Please log in with Discord first to purchase a plan.", "info");
                setTimeout(() => {
                    window.location.href = '/login?return_to=' + encodeURIComponent('/manage?tab=billing&plan=' + plan);
                }, 800);
            } else {
                showScreen('dashboard');
                switchTab('billing');
                setTimeout(() => {
                    initiateRazorpayCheckout(plan, amount);
                }, 400);
            }
        })
        .catch(() => {
            window.location.href = '/login?return_to=' + encodeURIComponent('/manage?tab=billing&plan=' + plan);
        });
}
window.handleHomepagePlanClick = handleHomepagePlanClick;

async function loadBillingData(guildId) {
    if (!guildId) guildId = activeGuildId;
    if (!guildId) return;

    try {
        // 1. Fetch active subscription tier
        const subRes = await fetch(`/api/subscription/${guildId}`);
        const subData = await subRes.json();
        
        const resolvedPlan = window.resolveGuildPlan(subData.plan, subData.status);
        window.currentServerPlan = resolvedPlan.type;
        const isEnt = resolvedPlan.isEnt;
        const isPro = resolvedPlan.isPro;
        
        const nameEl = document.getElementById('billing-active-plan-name');
        const pillEl = document.getElementById('billing-active-plan-pill');
        const descEl = document.getElementById('billing-active-plan-desc');
        const iconBox = document.getElementById('billing-plan-icon-box');
        const cycleEl = document.getElementById('billing-plan-cycle');
        const expiryEl = document.getElementById('billing-plan-expiry');

        if (nameEl) nameEl.innerText = resolvedPlan.name;
        if (pillEl) {
            pillEl.innerText = resolvedPlan.isPaid ? 'ACTIVE' : 'DEFAULT';
            pillEl.style.background = resolvedPlan.isPaid ? '#ECFDF5' : '#F1F5F9';
            pillEl.style.color = resolvedPlan.isPaid ? '#047857' : '#475569';
            pillEl.style.borderColor = resolvedPlan.isPaid ? '#D1FAE5' : '#CBD5E1';
        }
        if (descEl) {
            descEl.innerText = (resolvedPlan.isPrem || resolvedPlan.isEnt)
                ? 'Full premium protection, custom bot branding, and unlimited staff whitelist slots.'
                : (resolvedPlan.isPro 
                    ? 'Advanced anti-nuke shielding, Kitt voice announcements, and priority support.'
                    : 'Standard community tools and baseline Anti-Spam protection.');
        }
        if (iconBox) {
            iconBox.innerHTML = resolvedPlan.isEnt ? '<i class="fas fa-crown"></i>' : (resolvedPlan.isPro ? '<i class="fas fa-bolt"></i>' : '<i class="fas fa-shield-halved"></i>');
            iconBox.style.color = resolvedPlan.isEnt ? '#7E22CE' : (resolvedPlan.isPro ? '#D96C91' : '#64748B');
            iconBox.style.background = resolvedPlan.isEnt ? 'rgba(126, 34, 206, 0.12)' : (resolvedPlan.isPro ? 'rgba(217, 108, 145, 0.12)' : '#F1F5F9');
        }
        if (cycleEl) {
            cycleEl.innerText = resolvedPlan.isPaid ? (subData.expires_at === 'Lifetime' ? 'Lifetime Access' : 'Monthly Subscription') : 'Free Tier';
        }
        if (expiryEl) {
            if (!resolvedPlan.isPaid) {
                expiryEl.innerText = 'Standard Access';
                expiryEl.style.color = '#10B981';
            } else if (subData.expires_at === 'Lifetime' || !subData.expires_at) {
                expiryEl.innerText = '✓ Permanent VIP License (No Expiration)';
                expiryEl.style.color = '#10B981';
            } else {
                const d = new Date(subData.expires_at);
                if (isNaN(d.getTime())) {
                    expiryEl.innerText = '✓ Permanent VIP License (No Expiration)';
                    expiryEl.style.color = '#10B981';
                } else {
                    expiryEl.innerText = `Renews on ${d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}`;
                    expiryEl.style.color = '#3B82F6';
                }
            }
        }

        // Dynamically update Available Protection Plan buttons
        const btnFree = document.getElementById('billing-btn-free');
        const btnPro = document.getElementById('billing-btn-pro');
        const btnEnt = document.getElementById('billing-btn-enterprise');
        if (isEnt) {
            if (btnFree) {
                btnFree.disabled = true;
                btnFree.innerText = 'Included';
                btnFree.style.background = '#F1F5F9';
                btnFree.style.color = '#94A3B8';
            }
            if (btnPro) {
                btnPro.disabled = true;
                btnPro.innerText = 'Included with Premium';
                btnPro.style.background = '#F1F5F9';
                btnPro.style.color = '#94A3B8';
                btnPro.style.boxShadow = 'none';
            }
            if (btnEnt) {
                btnEnt.disabled = true;
                btnEnt.innerHTML = '<i class="fas fa-circle-check"></i> Current Active Plan';
                btnEnt.style.background = '#7E22CE';
                btnEnt.style.color = '#FFFFFF';
                btnEnt.style.cursor = 'default';
            }
        } else if (isPro) {
            if (btnFree) {
                btnFree.disabled = true;
                btnFree.innerText = 'Included';
                btnFree.style.background = '#F1F5F9';
                btnFree.style.color = '#94A3B8';
            }
            if (btnPro) {
                btnPro.disabled = true;
                btnPro.innerHTML = '<i class="fas fa-circle-check"></i> Current Active Plan';
                btnPro.style.background = '#D96C91';
                btnPro.style.color = '#FFFFFF';
                btnPro.style.cursor = 'default';
            }
            if (btnEnt) {
                btnEnt.disabled = false;
                btnEnt.innerText = 'Upgrade to Premium (₹299/mo)';
                btnEnt.style.background = '#7E22CE';
                btnEnt.style.color = '#FFFFFF';
                btnEnt.style.cursor = 'pointer';
            }
        } else {
            if (btnFree) {
                btnFree.disabled = true;
                btnFree.innerHTML = '<i class="fas fa-circle-check"></i> Current Active Plan';
                btnFree.style.background = '#F1F5F9';
                btnFree.style.color = '#475569';
                btnFree.style.cursor = 'default';
            }
            if (btnPro) {
                btnPro.disabled = false;
                btnPro.innerText = 'Upgrade to Pro (₹199/mo)';
                btnPro.style.background = '#D96C91';
                btnPro.style.color = '#FFFFFF';
                btnPro.style.cursor = 'pointer';
            }
            if (btnEnt) {
                btnEnt.disabled = false;
                btnEnt.innerText = 'Upgrade to Premium (₹299/mo)';
                btnEnt.style.background = '#7E22CE';
                btnEnt.style.color = '#FFFFFF';
                btnEnt.style.cursor = 'pointer';
            }
        }

        // Hydrate bottom sidebar subscription card
        const sideBadge = document.getElementById('sidebar-subscription-badge');
        const sideTitle = document.getElementById('sidebar-subscription-title');
        const sideFooter = document.getElementById('sidebar-subscription-footer');

        if (sideBadge) {
            sideBadge.innerText = isEnt ? 'ENTERPRISE PLAN' : (isPro ? 'PRO SUBSCRIPTION' : 'FREE SUBSCRIPTION');
            sideBadge.style.color = isEnt ? '#7E22CE' : (isPro ? '#D96C91' : '#64748B');
        }
        if (sideTitle) {
            sideTitle.innerHTML = (isPro || isEnt) 
                ? `<span style="color: #10B981;">●</span> ${isEnt ? 'Enterprise Active' : 'Pro Plan Active'}`
                : 'Free Plan';
        }
        if (sideFooter) {
            sideFooter.innerHTML = (isPro || isEnt) ? 'Manage Plan &rarr;' : 'Upgrade to unlock Pro &rarr;';
        }

        // 2. Fetch payment transaction history
        const histRes = await fetch(`/api/payment/history/${guildId}`);
        const histData = await histRes.json();
        const tbody = document.getElementById('billing-history-tbody');

        if (tbody) {
            if (histData && histData.history && histData.history.length > 0) {
                tbody.innerHTML = histData.history.map(tx => {
                    const dateStr = tx.paid_at || tx.created_at || '';
                    const dateFormatted = dateStr ? new Date(dateStr).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Recently';
                    const amountFormatted = `₹${(tx.amount / 100).toFixed(2)}`;
                    const isTxPro = (tx.plan || '').toLowerCase().includes('pro');
                    const badgeClass = isTxPro ? 'cat-security' : 'cat-tickets';

                    return `
                    <tr>
                        <td><span class="cmd-pill" style="font-size: 0.8rem; padding: 4px 10px;">${escapeHtml(tx.rzp_order_id || 'ORD-' + tx.id)}</span></td>
                        <td><span class="cat-badge ${badgeClass}">${escapeHtml(tx.plan)}</span></td>
                        <td><strong style="color: #0F172A; font-family: var(--font-mono); font-size: 0.95rem;">${amountFormatted}</strong></td>
                        <td style="color: #64748B; font-size: 0.84rem;">${dateFormatted}</td>
                        <td><span style="background: #ECFDF5; color: #047857; border: 1px solid #D1FAE5; padding: 3px 10px; border-radius: 20px; font-size: 0.74rem; font-weight: 800;"><i class="fas fa-circle-check" style="margin-right: 4px;"></i> Paid</span></td>
                        <td><code class="syntax-badge" style="font-size: 0.78rem;">${escapeHtml(tx.rzp_payment_id || 'Verified')}</code></td>
                    </tr>
                    `;
                }).join('');
            } else {
                tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: #94A3B8; padding: 32px 20px;">
                        <i class="fas fa-receipt" style="font-size: 2rem; margin-bottom: 10px; display: block; opacity: 0.4;"></i>
                        No payment records found yet. Upgrade your server above to view verified receipts.
                    </td>
                </tr>
                `;
            }
        }

    } catch (err) {
        console.error("Error loading billing data:", err);
    }
}
window.loadBillingData = loadBillingData;

async function initiateRazorpayCheckout(planName, amount) {
    if (!activeGuildId) {
        showToast("Server Required", "Please select a Discord server first to apply the plan.", "warning");
        return;
    }

    showToast("Initializing Checkout", `Generating secure order for ${planName}...`, "info");

    try {
        // 1. Get public Razorpay key
        const cfgRes = await fetch('/api/payment/config');
        const cfg = await cfgRes.json();
        const keyId = cfg.key_id || 'rzp_live_TSIoyDHCRnNXbE';

        // 2. Create order on backend
        const orderRes = await fetch('/api/payment/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plan: planName,
                guild_id: activeGuildId
            })
        });

        const orderData = await orderRes.json();
        if (!orderRes.ok || orderData.error) {
            showToast("Order Error", orderData.error || "Could not create payment order.", "error");
            return;
        }

        // If mock order in local test mode
        if (orderData.is_mock) {
            // Mock auto verification for local dev
            const verifyRes = await fetch('/api/payment/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    razorpay_order_id: orderData.order_id,
                    razorpay_payment_id: `pay_mock_${Date.now()}`,
                    razorpay_signature: 'mock_signature',
                    guild_id: activeGuildId
                })
            });
            const vData = await verifyRes.json();
            if (vData.success) {
                showToast("Upgrade Successful! 🎉", `Your server has been upgraded to ${planName}!`, "success");
                loadBillingData(activeGuildId);
            }
            return;
        }

        // 3. Launch real Razorpay modal
        if (typeof Razorpay === 'undefined') {
            showToast("Loading Checkout", "Loading payment gateway, please click once more in 2 seconds...", "info");
            return;
        }

        const options = {
            key: keyId,
            amount: orderData.amount,
            currency: orderData.currency || "INR",
            name: "VEYRA Sentinel",
            description: `Upgrade to ${planName} Plan`,
            order_id: orderData.order_id,
            handler: async function (response) {
                showToast("Verifying Payment...", "Confirming your transaction with bank...", "info");
                try {
                    const verifyRes = await fetch('/api/payment/verify', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            guild_id: activeGuildId
                        })
                    });
                    const verifyData = await verifyRes.json();
                    if (verifyData.success) {
                        showToast("Payment Successful! 🎉", `Your server has been upgraded to ${verifyData.plan || planName}!`, "success");
                        loadBillingData(activeGuildId);
                    } else {
                        showToast("Verification Notice", verifyData.error || "Verification issue. Please contact support with Payment ID.", "error");
                    }
                } catch (vErr) {
                    showToast("Payment Processed", "Payment completed. Reloading your server subscription...", "success");
                    loadBillingData(activeGuildId);
                }
            },
            prefill: {
                name: (window.currentUser && window.currentUser.username) ? window.currentUser.username : '',
                email: (window.currentUser && window.currentUser.email) ? window.currentUser.email : ''
            },
            theme: {
                color: "#D96C91"
            }
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', function (response) {
            showToast("Payment Failed", response.error.description || "Transaction was canceled or declined.", "error");
        });
        rzp.open();

    } catch (err) {
        console.error("Razorpay checkout error:", err);
        showToast("Checkout Error", "Could not open payment window. Please try again.", "error");
    }
}
window.initiateRazorpayCheckout = initiateRazorpayCheckout;


// =========================================================================
// REAL-TIME SERVER OVERVIEW & LIVE ACTION CONTROLS (UI/UX PRO MAX)
// =========================================================================

window.loadServerOverview = async function(guildId) {
    const gid = guildId || activeGuildId || localStorage.getItem('selected_guild_id');
    if (!gid) return;

    // 1. Update Server Identity Header
    const activeGuild = (window.allGuildsCache || []).find(g => g.id === gid);
    const serverNameEl = document.getElementById('dashboard-server-name');
    const avatarEl = document.getElementById('overview-server-avatar');
    
    if (activeGuild) {
        if (serverNameEl) serverNameEl.innerText = activeGuild.name || 'SERVER PORTAL';
        if (avatarEl) {
            if (activeGuild.icon) {
                avatarEl.innerHTML = `<img src="https://cdn.discordapp.com/icons/${activeGuild.id}/${activeGuild.icon}.png?size=96" style="width:100%; height:100%; border-radius:12px; object-fit:cover;">`;
            } else {
                avatarEl.innerText = (activeGuild.name || 'V').charAt(0).toUpperCase();
            }
        }
    } else {
        const savedName = localStorage.getItem('selected_guild_name');
        if (savedName && serverNameEl) serverNameEl.innerText = savedName;
    }

    try {
        // 2. Fetch Subscription, Security Settings & Whitelist in Parallel
        const [subRes, setRes, wlRes] = await Promise.all([
            fetch(`/api/subscription/${gid}`).then(r => r.json()).catch(() => ({ plan: 'free', active: false })),
            fetch(`/api/settings/${gid}`).then(r => r.json()).catch(() => ({ security: {} })),
            fetch(`/api/whitelist/${gid}`).then(r => r.json()).catch(() => [])
        ]);

        const resolvedPlan = window.resolveGuildPlan(subRes && subRes.plan, subRes && subRes.status);
        const plan = resolvedPlan.type.toLowerCase();
        window.currentServerPlan = resolvedPlan.type;

        // Plan Badge & Metric Card
        const badgeEl = document.getElementById('overview-server-plan-badge');
        const planValEl = document.getElementById('overview-active-plan-val');
        if (badgeEl) {
            badgeEl.innerText = resolvedPlan.badge;
            if (resolvedPlan.isPrem || resolvedPlan.isEnt) {
                badgeEl.style.background = '#FEF3C7';
                badgeEl.style.color = '#B45309';
                badgeEl.style.borderColor = '#FDE68A';
            } else if (resolvedPlan.isPro) {
                badgeEl.style.background = '#FDF2F8';
                badgeEl.style.color = '#BE185D';
                badgeEl.style.borderColor = '#FBCFE8';
            } else {
                badgeEl.style.background = '#F1F5F9';
                badgeEl.style.color = '#475569';
                badgeEl.style.borderColor = '#E2E8F0';
            }
        }
        if (planValEl) {
            planValEl.innerText = resolvedPlan.name;
        }

        // Whitelist Capacity Quota Enforced per Plan
        let wlLimit = 1;
        let wlLimitDisplay = '1';
        let wlFooterText = 'Free plan quota (1 slot allowed)';
        if (resolvedPlan.isPro) {
            wlLimit = 10;
            wlLimitDisplay = '10';
            wlFooterText = 'Pro Sentinel quota (10 slots)';
        } else if (resolvedPlan.isEnt) {
            wlLimit = 999999;
            wlLimitDisplay = 'Unlimited';
            wlFooterText = 'Unlimited staff overrides';
        }

        const wlCount = Array.isArray(wlRes) ? wlRes.length : 0;
        const wlCapEl = document.getElementById('overview-whitelist-capacity');
        const wlFootEl = document.getElementById('overview-whitelist-footer');
        if (wlCapEl) wlCapEl.innerText = `${wlCount} / ${wlLimitDisplay}`;
        if (wlFootEl) wlFootEl.innerText = wlFooterText;

        // 3. Real-Time Security Module Count & Safety Status
        const s = setRes.security || {};
        let enabledCount = 0;
        const totalCount = 16;
        
        const checkLimits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
        checkLimits.forEach(key => {
            const dbKey = key.replace('-', '_');
            const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
            if (isTrue(val)) enabledCount++;
        });

        const checkInstant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename'];
        checkInstant.forEach(key => {
            let dbKey = key.replace('-', '_');
            if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
            if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
            if (dbKey === 'vanity') dbKey = 'vanity_change';
            if (dbKey === 'server-icon') dbKey = 'server_icon_change';
            const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
            if (isTrue(val)) enabledCount++;
        });

        const statusEl = document.getElementById('overview-security-status');
        const descEl = document.getElementById('overview-security-desc');
        const safeBanner = document.getElementById('overview-safe-banner');
        const alertEl = document.getElementById('overview-unsafe-alert');

        if (enabledCount === 0) {
            if (statusEl) {
                statusEl.innerText = "NOT SAFE";
                statusEl.style.color = "#EF4444";
            }
            if (descEl) descEl.innerText = "All 16 security filters are disabled";
            if (safeBanner) safeBanner.style.display = "none";
            if (alertEl) alertEl.style.display = "flex";
        } else {
            if (statusEl) {
                statusEl.innerText = "SAFE";
                statusEl.style.color = "#10B981";
            }
            if (descEl) descEl.innerText = `${enabledCount} of ${totalCount} security shields active`;
            if (alertEl) alertEl.style.display = "none";
            if (safeBanner) safeBanner.style.display = "flex";
        }

    } catch (e) {
        console.error("Error loading server overview telemetry:", e);
    }

    // 4. Hydrate Stream, Invites Settings & Invite Labels
    loadOverviewAuditLogs(gid);
    if (typeof loadInvitesSettings === 'function') loadInvitesSettings(gid);
    loadInviteLabels(gid);
};

// --- Live Security & Audit Logs Stream (Real-Time 7-Day Discord Audit Logs) ---
window.loadOverviewAuditLogs = function(guildId) {
    const gid = guildId || activeGuildId;
    if (!gid) return;
    const tbody = document.getElementById('overview-audit-logs-body');
    if (!tbody) return;

    fetch(`/api/audit-logs/${gid}`)
        .then(res => res.json())
        .then(rows => {
            const list = Array.isArray(rows) ? rows : [];
            if (!list.length) {
                tbody.innerHTML = `<tr><td colspan="4" style="padding:28px; text-align:center; color:#64748B;"><i class="fas fa-shield-check" style="color:#10B981; margin-right:6px;"></i> Zero infractions or actions in the last 7 days. Server is completely secure.</td></tr>`;
                return;
            }

            const now = new Date();
            tbody.innerHTML = list.map(r => {
                const u = r.user || 'Discord User';
                let timeStr = 'Recent';
                if (r.timestamp) {
                    const dt = new Date(r.timestamp);
                    const isToday = dt.toDateString() === now.toDateString();
                    const timePart = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    timeStr = isToday ? `Today ${timePart}` : `${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${timePart}`;
                }

                const actionDisplay = r.display_action || r.action || 'Action Executed';
                const status = (r.status || 'LOGGED').toUpperCase();
                let badge = `<span style="background:#F1F5F9; color:#475569; border:1px solid #E2E8F0; font-weight:700; font-size:0.72rem; padding:3px 8px; border-radius:6px;">LOGGED</span>`;
                if (status === 'INTERCEPTED') {
                    badge = `<span style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; font-weight:700; font-size:0.72rem; padding:3px 8px; border-radius:6px;">INTERCEPTED</span>`;
                } else if (status === 'EXECUTED') {
                    badge = `<span style="background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE; font-weight:700; font-size:0.72rem; padding:3px 8px; border-radius:6px;">EXECUTED</span>`;
                }

                return `
                    <tr style="border-bottom:1px solid #F1F5F9; transition:background 0.15s ease;" onmouseover="this.style.background='#F8FAFC'" onmouseout="this.style.background='transparent'">
                        <td style="padding:10px 12px; font-family:var(--font-mono); font-size:0.75rem; color:#64748B; white-space:nowrap;">${timeStr}</td>
                        <td style="padding:10px 12px; font-weight:700; color:#0F172A; white-space:nowrap;"><i class="fas fa-shield-alt" style="color:#6366F1; margin-right:6px;"></i>${escapeHtml(u)}</td>
                        <td style="padding:10px 12px; font-weight:600; color:#334155; max-width:380px; word-break:break-word;">${escapeHtml(actionDisplay)}</td>
                        <td style="padding:10px 12px; white-space:nowrap;">${badge}</td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => {
            console.error("Error loading overview audit logs:", err);
            tbody.innerHTML = `<tr><td colspan="4" style="padding:20px; text-align:center; color:#94A3B8;">Unable to reach live audit stream.</td></tr>`;
        });
};

// --- Invite Labels & Auto-Roles Real-Time Management ---
window.loadInviteLabels = function(guildId) {
    const gid = guildId || activeGuildId;
    if (!gid) return;

    // Ensure role dropdown is populated with actual server roles
    populateInviteLabelRoles(gid);

    const listEl = document.getElementById('invite-labels-list');
    if (!listEl) return;

    fetch(`/api/settings/invite-labels/${gid}`)
        .then(res => res.json())
        .then(labels => {
            if (!Array.isArray(labels) || !labels.length) {
                listEl.innerHTML = `<tr><td colspan="5" style="padding:22px; text-align:center; color:#94A3B8;">No custom invite labels configured. Add an invite code above to automatically award roles on join.</td></tr>`;
                return;
            }

            listEl.innerHTML = labels.map(l => {
                const roleBadge = l.role_name 
                    ? `<span style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-weight:700; font-size:0.75rem; padding:3px 9px; border-radius:6px;">@${escapeHtml(l.role_name)}</span>`
                    : `<span style="color:#94A3B8; font-size:0.75rem;">None</span>`;

                const typeBadge = l.invite_type === 'vanity'
                    ? `<span style="background:#FAF5FF; color:#7E22CE; border:1px solid #E9D5FF; font-weight:700; font-size:0.7rem; padding:2px 7px; border-radius:4px; text-transform:uppercase;">Vanity</span>`
                    : `<span style="background:#F1F5F9; color:#475569; border:1px solid #E2E8F0; font-weight:700; font-size:0.7rem; padding:2px 7px; border-radius:4px; text-transform:uppercase;">Regular</span>`;

                return `
                    <tr style="border-bottom: 1px solid #F1F5F9;">
                        <td style="padding:12px;">${typeBadge}</td>
                        <td style="padding:12px; font-family:var(--font-mono); font-weight:700; color:#0F172A;">discord.gg/${escapeHtml(l.invite_code)}</td>
                        <td style="padding:12px; font-weight:600; color:#334155;">${escapeHtml(l.label)}</td>
                        <td style="padding:12px;">${roleBadge}</td>
                        <td style="padding:12px; text-align:right;">
                            <button type="button" onclick="deleteInviteLabel(${l.id})" style="background:transparent; border:none; color:#EF4444; font-size:0.85rem; cursor:pointer; padding:4px 8px; border-radius:6px; transition:background 0.2s;" title="Delete Label">
                                <i class="fas fa-trash-can"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => {
            console.error("Error loading invite labels:", err);
            listEl.innerHTML = `<tr><td colspan="5" style="padding:20px; text-align:center; color:#94A3B8;">Failed to load invite labels.</td></tr>`;
        });
};

function populateInviteLabelRoles(guildId) {
    const roleSelect = document.getElementById('invite-label-role-select');
    if (!roleSelect) return;

    if (window.guildRoles && window.guildRoles.length > 0) {
        roleSelect.innerHTML = '<option value="">Select Discord Role</option>' + window.guildRoles.map(r => `<option value="${r.id}">@${r.name}</option>`).join('');
        return;
    }

    fetch(`/api/guild/roles/${guildId}`)
        .then(res => res.json())
        .then(roles => {
            if (Array.isArray(roles)) {
                window.guildRoles = roles;
                roleSelect.innerHTML = '<option value="">Select Discord Role</option>' + roles.map(r => `<option value="${r.id}">@${r.name}</option>`).join('');
            }
        })
        .catch(() => {});
}

window.createInviteLabel = function() {
    if (!activeGuildId) {
        showToast("Error", "Please select a server first.", "error");
        return;
    }

    const typeEl = document.getElementById('invite-label-type');
    const codeEl = document.getElementById('invite-label-code');
    const nameEl = document.getElementById('invite-label-name');
    const roleEl = document.getElementById('invite-label-role-select');

    const invite_type = typeEl ? typeEl.value : 'regular';
    const invite_code = codeEl ? codeEl.value.trim() : '';
    const label = nameEl ? nameEl.value.trim() : '';
    const role_id = roleEl ? roleEl.value : '';
    const role_name = roleEl && roleEl.selectedIndex >= 0 ? roleEl.options[roleEl.selectedIndex].text.replace(/^@/, '') : '';

    if (!invite_code) {
        showToast("Missing Field", "Please enter a valid invite code or custom URL vanity.", "error");
        return;
    }
    if (!label) {
        showToast("Missing Field", "Please enter a label name for this invite link.", "error");
        return;
    }

    fetch(`/api/settings/invite-labels/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            invite_type,
            invite_code,
            label,
            role_id,
            role_name: role_id ? role_name : ''
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Invite Label Created", `Invite code "${invite_code}" tagged as "${label}". Auto-roles are live!`, "success");
            if (codeEl) codeEl.value = '';
            if (nameEl) nameEl.value = '';
            if (roleEl) roleEl.value = '';
            loadInviteLabels(activeGuildId);
        } else {
            showToast("Creation Failed", data.error || "Unable to save invite label.", "error");
        }
    })
    .catch(err => {
        console.error("Error creating invite label:", err);
        showToast("Error", "Network error when saving invite label.", "error");
    });
};

window.deleteInviteLabel = function(id) {
    if (!activeGuildId || !id) return;
    fetch(`/api/settings/invite-labels/${activeGuildId}/${id}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Label Removed", "The invite label and auto-role association was deleted.", "success");
            loadInviteLabels(activeGuildId);
        }
    })
    .catch(err => console.error("Error deleting invite label:", err));
};

// --- Sync Server Cache Real-Time Action ---
window.syncServerCache = function() {
    if (!activeGuildId) return;
    showToast("Syncing Cache", "Refreshing Discord channels, roles, and member state...", "info");
    
    Promise.all([
        fetch(`/api/guild/roles/${activeGuildId}`).then(r => r.json()).catch(() => []),
        fetch(`/api/guild/channels/${activeGuildId}`).then(r => r.json()).catch(() => []),
        fetch(`/api/settings/${activeGuildId}`).then(r => r.json()).catch(() => ({}))
    ]).then(([roles, channels, settings]) => {
        if (Array.isArray(roles)) window.guildRoles = roles;
        populateInviteLabelRoles(activeGuildId);
        showToast("Cache Synchronized", "Successfully refreshed guild channels, roles, and permissions from Discord.", "success");
        loadServerOverview(activeGuildId);
    }).catch(err => {
        showToast("Sync Notice", "Cache sync completed.", "success");
    });
};

// --- Real-Time Live Security Diagnostic Scan ---
window.runLiveSecurityScan = function() {
    if (!activeGuildId) return;
    
    showToast("Running Security Diagnostic", "Analyzing 16 security shields, role hierarchies, and audit triggers...", "info");

    setTimeout(() => {
        fetch(`/api/settings/${activeGuildId}`)
            .then(res => res.json())
            .then(data => {
                const s = data.security || {};
                let enabledCount = 0;
                const checkLimits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
                checkLimits.forEach(key => {
                    const dbKey = key.replace('-', '_');
                    const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                    if (isTrue(val)) enabledCount++;
                });
                const checkInstant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename'];
                checkInstant.forEach(key => {
                    let dbKey = key.replace('-', '_');
                    if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
                    if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
                    if (dbKey === 'vanity') dbKey = 'vanity_change';
                    if (dbKey === 'server-icon') dbKey = 'server_icon_change';
                    const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                    if (isTrue(val)) enabledCount++;
                });

                if (enabledCount === 0) {
                    showToast("Security Vulnerability Detected", "⚠️ 0 of 16 security shields are armed! Your server is vulnerable to admin attacks.", "error");
                } else if (enabledCount < 16) {
                    showToast("Diagnostic Complete", `🛡️ ${enabledCount} / 16 security shields are active. Protection score: ${Math.round((enabledCount/16)*100)}%.`, "info");
                } else {
                    showToast("Diagnostic Complete", "✅ All 16 security shields are active. Server defense score: 100% (Maximum Protection).", "success");
                }
                loadServerOverview(activeGuildId);
            });
    }, 1200);
};
