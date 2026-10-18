// moderation.js — VEYRA Real-Time Moderation Panel
// Provides: member list, live log polling, ban/kick/timeout/warn/unban from the web

'use strict';

// ── LIVE LOG POLLING ──────────────────────────────────────────────────────────
let _liveLogPollInterval = null;
let _liveLogLastSeen = new Date(Date.now() - 30 * 60 * 1000).toISOString(); // last 30 min on first load
let _liveLogGuildId = null;

function startLiveLogPolling(guildId) {
    _liveLogGuildId = guildId;
    _liveLogLastSeen = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    if (_liveLogPollInterval) clearInterval(_liveLogPollInterval);
    _pollLiveLogs(); // immediate first poll
    _liveLogPollInterval = setInterval(_pollLiveLogs, 5000); // poll every 5s
}

function stopLiveLogPolling() {
    if (_liveLogPollInterval) { clearInterval(_liveLogPollInterval); _liveLogPollInterval = null; }
}

async function _pollLiveLogs() {
    if (!_liveLogGuildId) return;
    try {
        const r = await fetch(`/api/logs/live/${_liveLogGuildId}?since=${encodeURIComponent(_liveLogLastSeen)}&limit=30`);
        if (!r.ok) return;
        const data = await r.json();
        if (data.logs && data.logs.length > 0) {
            _liveLogLastSeen = data.server_time || new Date().toISOString();
            _injectLiveLogs(data.logs);
        }
    } catch (e) { /* silent */ }
}

const LOG_ICONS = {
    'Ban': { icon: '🔨', color: '#ef4444' },
    'Kick': { icon: '👢', color: '#f97316' },
    'Timeout': { icon: '⏱️', color: '#eab308' },
    'Warn': { icon: '⚠️', color: '#f59e0b' },
    'Unban': { icon: '✅', color: '#10b981' },
    'Remove Timeout': { icon: '🔓', color: '#06b6d4' },
    'Member Leave': { icon: '🚪', color: '#94a3b8' },
    'Member Join': { icon: '🟢', color: '#22c55e' },
    'Join': { icon: '🟢', color: '#22c55e' },
    'Leave': { icon: '🚪', color: '#94a3b8' },
    'Security': { icon: '🛡️', color: '#a855f7' },
    'Embed Post': { icon: '📝', color: '#60a5fa' },
    'default': { icon: '📋', color: '#64748b' }
};

function _injectLiveLogs(logs) {
    const container = document.getElementById('live-logs-feed') || document.getElementById('weblogs-body');
    if (!container) return;
    // logs come newest-first; prepend in DOM
    for (const log of logs) {
        const ts = new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false });
        const typeKey = Object.keys(LOG_ICONS).find(k => log.action && log.action.includes(k)) || 'default';
        const { icon, color } = LOG_ICONS[typeKey];
        const row = document.createElement('div');
        row.className = 'live-log-row';
        row.style.cssText = `display:flex;align-items:flex-start;gap:10px;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.04);animation:logFadeIn 0.4s ease;`;
        row.innerHTML = `
            <span style="font-size:1rem;margin-top:1px;flex-shrink:0">${icon}</span>
            <div style="flex:1;min-width:0">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                    <span style="color:${color};font-weight:700;font-size:0.78rem;font-family:var(--font-mono)">${escapeHtml(log.action || 'Event')}</span>
                    <span style="color:rgba(255,255,255,0.35);font-size:0.72rem;font-family:var(--font-mono)">${ts}</span>
                    ${log.user ? `<span style="color:#a855f7;font-size:0.72rem;font-family:var(--font-mono)">by ${escapeHtml(log.user)}</span>` : ''}
                </div>
                <div style="color:rgba(255,255,255,0.6);font-size:0.80rem;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(log.details || '')}">${escapeHtml(log.details || '')}</div>
            </div>
        `;
        if (container.firstChild) container.insertBefore(row, container.firstChild);
        else container.appendChild(row);
    }
    // Keep max 100 rows
    while (container.children.length > 100) container.removeChild(container.lastChild);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── MEMBER SEARCH & LOAD ─────────────────────────────────────────────────────
let _membersCache = [];

async function loadMembersForModeration(guildId, query = '') {
    const container = document.getElementById('mod-members-list');
    if (!container) return;
    container.innerHTML = `<div style="text-align:center;padding:20px;color:#64748b;font-size:0.85rem">Loading members...</div>`;
    try {
        const url = `/api/bot/members/${guildId}?limit=200${query ? '&query=' + encodeURIComponent(query) : ''}`;
        const r = await fetch(url);
        if (!r.ok) throw new Error('Failed to load members');
        _membersCache = await r.json();
        renderMembersForModeration(_membersCache);
    } catch (e) {
        container.innerHTML = `<div style="text-align:center;padding:20px;color:#ef4444;font-size:0.85rem">Failed to load members: ${e.message}</div>`;
    }
}

function renderMembersForModeration(members) {
    const container = document.getElementById('mod-members-list');
    if (!container) return;
    if (!members || members.length === 0) {
        container.innerHTML = `<div style="text-align:center;padding:20px;color:#64748b;font-size:0.85rem">No members found.</div>`;
        return;
    }
    container.innerHTML = '';
    for (const m of members) {
        if (m.bot) continue; // skip bots
        const card = document.createElement('div');
        card.className = 'mod-member-card';
        card.style.cssText = `display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:8px;border:1px solid rgba(255,255,255,0.04);background:rgba(255,255,255,0.02);margin-bottom:8px;cursor:pointer;transition:all 0.15s;`;
        card.onmouseenter = () => card.style.background = 'rgba(168,85,247,0.08)';
        card.onmouseleave = () => card.style.background = 'rgba(255,255,255,0.02)';
        card.onclick = () => openModActionModal(m);
        card.innerHTML = `
            <img src="${escapeHtml(m.avatar)}" style="width:36px;height:36px;border-radius:50%;flex-shrink:0;object-fit:cover" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;color:#fff;font-size:0.88rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(m.display_name)}</div>
                <div style="color:#64748b;font-size:0.74rem;font-family:var(--font-mono)">${escapeHtml(m.username)} · ${m.id}</div>
            </div>
            <div style="display:flex;gap:6px">
                <button onclick="event.stopPropagation();quickAction('ban','${m.id}','${escapeHtml(m.username)}')" title="Ban" style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:0.75rem;font-weight:700" onmouseover="this.style.background='rgba(239,68,68,0.25)'" onmouseout="this.style.background='rgba(239,68,68,0.15)'">Ban</button>
                <button onclick="event.stopPropagation();quickAction('kick','${m.id}','${escapeHtml(m.username)}')" title="Kick" style="background:rgba(249,115,22,0.15);border:1px solid rgba(249,115,22,0.3);color:#f97316;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:0.75rem;font-weight:700" onmouseover="this.style.background='rgba(249,115,22,0.25)'" onmouseout="this.style.background='rgba(249,115,22,0.15)'">Kick</button>
                <button onclick="event.stopPropagation();quickAction('timeout','${m.id}','${escapeHtml(m.username)}')" title="Timeout" style="background:rgba(234,179,8,0.15);border:1px solid rgba(234,179,8,0.3);color:#eab308;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:0.75rem;font-weight:700" onmouseover="this.style.background='rgba(234,179,8,0.25)'" onmouseout="this.style.background='rgba(234,179,8,0.15)'">TO</button>
            </div>
        `;
        container.appendChild(card);
    }
}

// ── MOD ACTION MODAL ──────────────────────────────────────────────────────────
let _modTargetUser = null;

function openModActionModal(member) {
    _modTargetUser = member;
    const modal = document.getElementById('mod-action-modal');
    if (!modal) { buildModActionModal(); return openModActionModal(member); }
    document.getElementById('mod-modal-avatar').src = member.avatar;
    document.getElementById('mod-modal-name').textContent = member.display_name;
    document.getElementById('mod-modal-tag').textContent = `@${member.username} · ${member.id}`;
    document.getElementById('mod-modal-reason').value = '';
    document.getElementById('mod-modal-duration').value = '60';
    document.getElementById('mod-modal-result').textContent = '';
    modal.style.display = 'flex';
}

function closeModActionModal() {
    const modal = document.getElementById('mod-action-modal');
    if (modal) modal.style.display = 'none';
}

function quickAction(action, userId, username) {
    const member = _membersCache.find(m => m.id === userId) || { id: userId, username, display_name: username, avatar: '' };
    openModActionModal(member);
    // Pre-select the action tab
    setTimeout(() => switchModTab(action), 50);
}

function switchModTab(tab) {
    document.querySelectorAll('.mod-tab-btn').forEach(b => {
        b.style.background = b.dataset.tab === tab ? 'rgba(168,85,247,0.25)' : 'rgba(255,255,255,0.04)';
        b.style.color = b.dataset.tab === tab ? '#c084fc' : '#64748b';
        b.style.borderColor = b.dataset.tab === tab ? 'rgba(168,85,247,0.4)' : 'rgba(255,255,255,0.06)';
    });
    document.querySelectorAll('.mod-tab-pane').forEach(p => {
        p.style.display = p.dataset.tab === tab ? 'block' : 'none';
    });
}

async function executeModAction(action) {
    if (!_modTargetUser) return;
    const guildId = window.activeGuildId || sessionStorage.getItem('activeGuildId');
    if (!guildId) return showModResult('error', 'No guild selected');
    const reason = document.getElementById('mod-modal-reason')?.value || 'No reason provided';
    const duration = parseInt(document.getElementById('mod-modal-duration')?.value) || 60;
    const resultEl = document.getElementById('mod-modal-result');
    if (resultEl) { resultEl.textContent = 'Processing...'; resultEl.style.color = '#64748b'; }

    const actionMap = {
        ban: { url: '/api/bot/ban', body: { guild_id: guildId, user_id: _modTargetUser.id, reason, delete_message_days: 0 } },
        kick: { url: '/api/bot/kick', body: { guild_id: guildId, user_id: _modTargetUser.id, reason } },
        timeout: { url: '/api/bot/timeout', body: { guild_id: guildId, user_id: _modTargetUser.id, duration_minutes: duration, reason } },
        untimeout: { url: '/api/bot/untimeout', body: { guild_id: guildId, user_id: _modTargetUser.id } },
        warn: { url: '/api/bot/warn', body: { guild_id: guildId, user_id: _modTargetUser.id, reason } },
        unban: { url: '/api/bot/unban', body: { guild_id: guildId, user_id: _modTargetUser.id, reason } },
    };

    const cfg = actionMap[action];
    if (!cfg) return;

    try {
        const r = await fetch(cfg.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg.body) });
        const data = await r.json();
        if (data.success) {
            if (resultEl) { resultEl.textContent = `✅ ${data.message || 'Action completed!'}`; resultEl.style.color = '#22c55e'; }
            if (typeof showToast === 'function') showToast('Action Completed', data.message || `${action} executed successfully.`);
            setTimeout(closeModActionModal, 1500);
        } else {
            if (resultEl) { resultEl.textContent = `❌ ${data.error || 'Action failed'}`; resultEl.style.color = '#ef4444'; }
        }
    } catch (e) {
        if (resultEl) { resultEl.textContent = `❌ Network error: ${e.message}`; resultEl.style.color = '#ef4444'; }
    }
}

// ── BUILD THE MODAL HTML DYNAMICALLY ─────────────────────────────────────────
function buildModActionModal() {
    if (document.getElementById('mod-action-modal')) return;
    const modal = document.createElement('div');
    modal.id = 'mod-action-modal';
    modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:20000;align-items:center;justify-content:center;padding:20px;';
    modal.onclick = (e) => { if (e.target === modal) closeModActionModal(); };
    modal.innerHTML = `
        <div style="width:100%;max-width:480px;background:#111214;border:1px solid rgba(168,85,247,0.25);border-radius:16px;padding:28px;box-shadow:0 30px 60px rgba(0,0,0,0.8);position:relative">
            <button onclick="closeModActionModal()" style="position:absolute;top:16px;right:16px;background:transparent;border:none;color:#64748b;font-size:1.2rem;cursor:pointer" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#64748b'">&times;</button>
            <!-- User Info -->
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:24px">
                <img id="mod-modal-avatar" src="" style="width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid rgba(168,85,247,0.4)" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div>
                    <div id="mod-modal-name" style="font-size:1.1rem;font-weight:800;color:#fff"></div>
                    <div id="mod-modal-tag" style="font-size:0.75rem;color:#64748b;font-family:var(--font-mono)"></div>
                </div>
            </div>
            <!-- Action Tabs -->
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px">
                ${[['ban','Ban','#ef4444'],['kick','Kick','#f97316'],['timeout','Timeout','#eab308'],['untimeout','Un-TO','#06b6d4'],['warn','Warn','#f59e0b'],['unban','Unban','#22c55e']].map(([id,label,color]) => `
                    <button class="mod-tab-btn" data-tab="${id}" onclick="switchModTab('${id}')"
                        style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);color:#64748b;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.78rem;font-weight:700;transition:all 0.15s">${label}</button>
                `).join('')}
            </div>
            <!-- Reason Field -->
            <div style="margin-bottom:14px">
                <label style="font-size:0.78rem;font-weight:700;color:#94a3b8;display:block;margin-bottom:6px">REASON</label>
                <textarea id="mod-modal-reason" placeholder="Enter reason..." rows="2"
                    style="width:100%;background:#0c0a18;border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#fff;padding:10px 12px;font-size:0.85rem;resize:vertical;box-sizing:border-box;font-family:var(--font-display)"></textarea>
            </div>
            <!-- Duration (only for timeout) -->
            <div class="mod-tab-pane" data-tab="timeout" style="display:none;margin-bottom:14px">
                <label style="font-size:0.78rem;font-weight:700;color:#94a3b8;display:block;margin-bottom:6px">DURATION (minutes)</label>
                <select id="mod-modal-duration" style="width:100%;background:#0c0a18;border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#fff;padding:10px 12px;font-size:0.85rem;box-sizing:border-box">
                    <option value="5">5 minutes</option>
                    <option value="10">10 minutes</option>
                    <option value="30">30 minutes</option>
                    <option value="60" selected>1 hour</option>
                    <option value="120">2 hours</option>
                    <option value="360">6 hours</option>
                    <option value="720">12 hours</option>
                    <option value="1440">24 hours</option>
                    <option value="4320">3 days</option>
                    <option value="10080">7 days</option>
                    <option value="40320">28 days</option>
                </select>
            </div>
            <!-- Execute Buttons per tab -->
            ${[['ban','🔨 BAN MEMBER','#ef4444'],['kick','👢 KICK MEMBER','#f97316'],['timeout','⏱️ APPLY TIMEOUT','#eab308'],['untimeout','🔓 REMOVE TIMEOUT','#06b6d4'],['warn','⚠️ SEND WARNING','#f59e0b'],['unban','✅ UNBAN MEMBER','#22c55e']].map(([id,label,color]) => `
                <div class="mod-tab-pane" data-tab="${id}" style="display:none">
                    <button onclick="executeModAction('${id}')"
                        style="width:100%;background:rgba(${hexToRgb(color)},0.15);border:1.5px solid rgba(${hexToRgb(color)},0.4);color:${color};border-radius:8px;padding:12px;font-weight:800;font-size:0.9rem;cursor:pointer;letter-spacing:0.04em;transition:all 0.15s"
                        onmouseover="this.style.background='rgba(${hexToRgb(color)},0.25)'"
                        onmouseout="this.style.background='rgba(${hexToRgb(color)},0.15)'">${label}</button>
                </div>
            `).join('')}
            <!-- Result feedback -->
            <div id="mod-modal-result" style="text-align:center;margin-top:12px;font-size:0.85rem;font-weight:600;min-height:20px"></div>
        </div>
    `;
    document.body.appendChild(modal);
    // Default to ban tab
    switchModTab('ban');
}

function hexToRgb(hex) {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return `${r},${g},${b}`;
}

// ── REAL-TIME STATS TICKER ────────────────────────────────────────────────────
let _statsInterval = null;

async function startRealTimeStats(guildId) {
    if (_statsInterval) clearInterval(_statsInterval);
    await _fetchAndUpdateStats(guildId);
    _statsInterval = setInterval(() => _fetchAndUpdateStats(guildId), 30000); // every 30s
}

async function _fetchAndUpdateStats(guildId) {
    try {
        const r = await fetch(`/api/bot/stats/${guildId}`);
        if (!r.ok) return;
        const s = await r.json();
        // Update any stat elements that exist in the DOM
        _updateEl('stat-member-count', s.member_count ? s.member_count.toLocaleString() : null);
        _updateEl('stat-online-count', s.online_count ? s.online_count.toLocaleString() : null);
        _updateEl('stat-boost-count', s.boost_count != null ? s.boost_count : null);
        _updateEl('stat-total-bans', s.total_bans != null ? s.total_bans : null);
        _updateEl('stat-total-kicks', s.total_kicks != null ? s.total_kicks : null);
        _updateEl('stat-total-warns', s.total_warnings != null ? s.total_warnings : null);
        _updateEl('stat-total-actions', s.total_actions != null ? s.total_actions : null);
        // Also update overview cards if they exist
        _updateEl('overview-member-count', s.member_count ? s.member_count.toLocaleString() : null);
        _updateEl('overview-online-count', s.online_count ? s.online_count.toLocaleString() : null);
    } catch (e) { /* silent */ }
}

function _updateEl(id, value) {
    if (value == null) return;
    const el = document.getElementById(id);
    if (el) {
        if (el.textContent !== String(value)) {
            el.style.transition = 'opacity 0.3s';
            el.style.opacity = '0';
            setTimeout(() => { el.textContent = value; el.style.opacity = '1'; }, 150);
        }
    }
}

// ── BAN LIST VIEWER ───────────────────────────────────────────────────────────
async function loadBanList(guildId) {
    const container = document.getElementById('ban-list-container');
    if (!container) return;
    container.innerHTML = `<div style="text-align:center;padding:20px;color:#64748b">Loading ban list...</div>`;
    try {
        const r = await fetch(`/api/bot/bans/${guildId}`);
        const bans = await r.json();
        if (!bans || !bans.length) {
            container.innerHTML = `<div style="text-align:center;padding:20px;color:#64748b;font-size:0.85rem">No banned users.</div>`;
            return;
        }
        container.innerHTML = bans.map(b => `
            <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.04)">
                <img src="https://cdn.discordapp.com/embed/avatars/${parseInt(b.user.id) % 6}.png" style="width:32px;height:32px;border-radius:50%">
                <div style="flex:1">
                    <div style="font-weight:700;color:#fff;font-size:0.85rem">${escapeHtml(b.user.username)}</div>
                    <div style="color:#64748b;font-size:0.74rem">${b.user.id} · ${escapeHtml(b.reason || 'No reason')}</div>
                </div>
                <button onclick="unbanUser('${b.user.id}','${escapeHtml(b.user.username)}')"
                    style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);color:#22c55e;border-radius:5px;padding:5px 10px;cursor:pointer;font-size:0.75rem;font-weight:700"
                    onmouseover="this.style.background='rgba(34,197,94,0.2)'" onmouseout="this.style.background='rgba(34,197,94,0.1)'">Unban</button>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div style="text-align:center;padding:20px;color:#ef4444;font-size:0.85rem">Failed: ${e.message}</div>`;
    }
}

async function unbanUser(userId, username) {
    const guildId = window.activeGuildId || sessionStorage.getItem('activeGuildId');
    if (!guildId) return;
    if (!confirm(`Unban @${username}?`)) return;
    try {
        const r = await fetch('/api/bot/unban', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ guild_id: guildId, user_id: userId }) });
        const data = await r.json();
        if (data.success) {
            if (typeof showToast === 'function') showToast('Unbanned', `@${username} has been unbanned.`);
            loadBanList(guildId);
        } else {
            alert(`Failed to unban: ${data.error}`);
        }
    } catch (e) { alert(e.message); }
}

// ── CSS ANIMATIONS ────────────────────────────────────────────────────────────
(function injectModerationStyles() {
    if (document.getElementById('mod-styles')) return;
    const style = document.createElement('style');
    style.id = 'mod-styles';
    style.textContent = `
        @keyframes logFadeIn {
            from { opacity: 0; transform: translateY(-6px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .mod-member-card:hover { border-color: rgba(168,85,247,0.25) !important; }
        #mod-action-modal textarea:focus,
        #mod-action-modal select:focus { outline: none; border-color: rgba(168,85,247,0.5) !important; }
        .live-log-row:hover { background: rgba(255,255,255,0.02); }
    `;
    document.head.appendChild(style);
})();

// ── AUTO-INITIALIZE when guildId changes ────────────────────────────────────
// Called by dashboard.js when a server is selected
window.initModeration = function(guildId) {
    buildModActionModal();
    startLiveLogPolling(guildId);
    startRealTimeStats(guildId);
};

window.openModActionModal = openModActionModal;
window.closeModActionModal = closeModActionModal;
window.switchModTab = switchModTab;
window.executeModAction = executeModAction;
window.loadMembersForModeration = loadMembersForModeration;
window.quickAction = quickAction;
window.loadBanList = loadBanList;
window.unbanUser = unbanUser;
window.startLiveLogPolling = startLiveLogPolling;
window.stopLiveLogPolling = stopLiveLogPolling;
window.injectLiveModerationLog = function(log) { _injectLiveLogs([log]); };
