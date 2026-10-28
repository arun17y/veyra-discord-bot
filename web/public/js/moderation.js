// moderation.js — VEYRA Real-Time Moderation Panel
// Provides: member list, live log polling, ban/kick/timeout/warn/unban from the web

'use strict';

// ── LIVE LOG POLLING ──────────────────────────────────────────────────────────
let _liveLogPollInterval = null;
let _liveLogLastSeen = null; // null on first load to get latest live events
let _liveLogGuildId = null;

function startLiveLogPolling(guildId) {
    _liveLogGuildId = guildId;
    _liveLogLastSeen = null;
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
        const url = _liveLogLastSeen 
            ? `/api/logs/live/${_liveLogGuildId}?since=${encodeURIComponent(_liveLogLastSeen)}&limit=30`
            : `/api/logs/live/${_liveLogGuildId}?limit=30`;
        const r = await fetch(url);
        if (!r.ok) return;
        const data = await r.json();
        if (data.logs && data.logs.length > 0) {
            const isInitial = !_liveLogLastSeen;
            _liveLogLastSeen = data.server_time || new Date().toISOString();
            _injectLiveLogs(data.logs, isInitial);
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

function _injectLiveLogs(logs, isInitial = false) {
    const container = document.getElementById('live-logs-feed') || document.getElementById('weblogs-body');
    if (!container) return;
    
    // Clear initial placeholder or loading state
    const placeholder = container.querySelector('div');
    if (placeholder && (placeholder.textContent.includes('Live audit events will appear') || placeholder.textContent.includes('Connecting to real-time'))) {
        container.innerHTML = '';
    }

    if (isInitial || container.children.length === 0) {
        container.innerHTML = '';
        for (const log of logs) {
            const row = _createLiveLogRow(log);
            container.appendChild(row);
        }
        return;
    }

    // New real-time delta items: insert newest at top
    const reversed = [...logs].reverse();
    for (const log of reversed) {
        const row = _createLiveLogRow(log);
        if (container.firstChild) container.insertBefore(row, container.firstChild);
        else container.appendChild(row);
    }
    while (container.children.length > 200) container.removeChild(container.lastChild);
}

function _createLiveLogRow(log) {
    const ts = new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false });
    const typeKey = Object.keys(LOG_ICONS).find(k => log.action && log.action.includes(k)) || 'default';
    const { icon, color } = LOG_ICONS[typeKey] || LOG_ICONS['default'];
    
    let actor = (log.user || '').trim();
    if (actor.toLowerCase().includes('neondb') || actor.toLowerCase().includes('postgres') || actor.toLowerCase().includes('automod') || actor.toLowerCase().includes('shield')) {
        actor = '';
    }

    const row = document.createElement('div');
    row.className = 'live-log-row';
    row.style.cssText = `display:flex;align-items:flex-start;gap:12px;padding:12px 16px;border-bottom:1px solid #F1F5F9;background:#FFFFFF;border-radius:8px;margin-bottom:6px;transition:background 0.15s;box-shadow:0 1px 2px rgba(0,0,0,0.02);`;
    row.onmouseenter = () => row.style.background = '#F8FAFC';
    row.onmouseleave = () => row.style.background = '#FFFFFF';

    row.innerHTML = `
        <span style="font-size:1.25rem;margin-top:2px;flex-shrink:0">${icon}</span>
        <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <span style="color:${color};font-weight:800;font-size:0.88rem;font-family:var(--font-mono);letter-spacing:0.02em">${escapeHtml(log.action || 'Event')}</span>
                <span style="color:#64748B;font-size:0.75rem;font-weight:600;font-family:var(--font-mono)">${ts}</span>
                ${actor ? `<span style="color:#64748B;font-size:0.75rem;font-weight:600;font-family:var(--font-mono)">• by ${escapeHtml(actor)}</span>` : ''}
            </div>
            <div style="color:#1E293B;font-size:0.84rem;margin-top:4px;line-height:1.55;font-weight:500;word-break:break-word">${escapeHtml(log.details || '')}</div>
        </div>
    `;
    return row;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── MEMBER SEARCH & LOAD ─────────────────────────────────────────────────────
let _membersCache = [];
let _memberTypeFilter = 'all';

async function loadMembersForModeration(guildId, query = '') {
    const container = document.getElementById('mod-members-list');
    if (!container) return;
    container.innerHTML = `<div style="text-align:center;padding:30px;color:#64748B;font-size:0.9rem;font-weight:600">Loading all server members...</div>`;
    try {
        const url = `/api/bot/members/${guildId}?limit=1000${query ? '&query=' + encodeURIComponent(query) : ''}`;
        const r = await fetch(url);
        if (!r.ok) throw new Error('Failed to load members');
        _membersCache = await r.json();
        window._membersCache = _membersCache;
        window.allMembers = _membersCache;
        _populateOverrideUserSelect(_membersCache);
        renderMembersForModeration(_membersCache);
    } catch (e) {
        container.innerHTML = `<div style="text-align:center;padding:30px;color:#EF4444;font-size:0.85rem">Failed to load members: ${e.message}</div>`;
    }
}

function _populateOverrideUserSelect(members) {
    const sel = document.getElementById('mod-override-user-select');
    if (!sel || !members) return;
    const curVal = sel.value;
    sel.innerHTML = `<option value="">-- Choose from server members (${members.length}) --</option>` +
        members.map(m => `<option value="${m.id}">${escapeHtml(m.display_name)} (@${escapeHtml(m.username)})${m.bot ? ' [BOT]' : ''} — ${m.id}</option>`).join('');
    if (curVal) sel.value = curVal;
}
window._populateOverrideUserSelect = _populateOverrideUserSelect;

function setMemberTypeFilter(filterType) {
    _memberTypeFilter = filterType;
    renderMembersForModeration(_membersCache);
}
window.setMemberTypeFilter = setMemberTypeFilter;

function renderMembersForModeration(members) {
    const container = document.getElementById('mod-members-list');
    if (!container) return;
    if (!members || members.length === 0) {
        container.innerHTML = `<div style="text-align:center;padding:30px;color:#64748B;font-size:0.9rem;font-weight:600">No members found matching query.</div>`;
        return;
    }

    const totalCount = members.length;
    const humanCount = members.filter(m => !m.bot).length;
    const botCount = members.filter(m => m.bot).length;

    let filtered = members;
    if (_memberTypeFilter === 'humans') filtered = members.filter(m => !m.bot);
    else if (_memberTypeFilter === 'bots') filtered = members.filter(m => m.bot);

    container.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; gap:6px;">
                <button onclick="setMemberTypeFilter('all')" style="background:${_memberTypeFilter === 'all' ? '#0F172A' : '#F1F5F9'}; color:${_memberTypeFilter === 'all' ? '#FFFFFF' : '#475569'}; border:1px solid ${_memberTypeFilter === 'all' ? '#0F172A' : '#E2E8F0'}; border-radius:6px; padding:5px 12px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.15s">All (${totalCount})</button>
                <button onclick="setMemberTypeFilter('humans')" style="background:${_memberTypeFilter === 'humans' ? '#0F172A' : '#F1F5F9'}; color:${_memberTypeFilter === 'humans' ? '#FFFFFF' : '#475569'}; border:1px solid ${_memberTypeFilter === 'humans' ? '#0F172A' : '#E2E8F0'}; border-radius:6px; padding:5px 12px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.15s">Members (${humanCount})</button>
                <button onclick="setMemberTypeFilter('bots')" style="background:${_memberTypeFilter === 'bots' ? '#0F172A' : '#F1F5F9'}; color:${_memberTypeFilter === 'bots' ? '#FFFFFF' : '#475569'}; border:1px solid ${_memberTypeFilter === 'bots' ? '#0F172A' : '#E2E8F0'}; border-radius:6px; padding:5px 12px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.15s">Bots (${botCount})</button>
            </div>
            <span style="color:#64748B; font-size:0.78rem; font-weight:600">Showing ${filtered.length} of ${totalCount}</span>
        </div>
        <div id="mod-members-cards-container"></div>
    `;

    const cardsContainer = document.getElementById('mod-members-cards-container');
    for (const m of filtered) {
        const card = document.createElement('div');
        card.className = 'mod-member-card';
        card.style.cssText = `display:flex;align-items:center;gap:14px;padding:12px 18px;border-radius:10px;border:1.5px solid #E2E8F0;background:#FFFFFF;margin-bottom:10px;cursor:pointer;transition:all 0.15s;box-shadow:0 1px 2px rgba(0,0,0,0.03);`;
        card.onmouseenter = () => { card.style.background = '#F8FAFC'; card.style.borderColor = '#CBD5E1'; };
        card.onmouseleave = () => { card.style.background = '#FFFFFF'; card.style.borderColor = '#E2E8F0'; };
        card.onclick = () => openModActionModal(m);

        const botBadge = m.bot 
            ? `<span style="background:#5865F2;color:#FFFFFF;font-size:0.62rem;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:0.04em;margin-left:6px;vertical-align:middle;">BOT</span>`
            : '';

        card.innerHTML = `
            <img src="${escapeHtml(m.avatar)}" style="width:42px;height:42px;border-radius:50%;flex-shrink:0;object-fit:cover;border:1.5px solid #E2E8F0" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div style="flex:1;min-width:0">
                <div style="display:flex;align-items:center;gap:6px">
                    <span style="font-weight:800;color:#0F172A;font-size:0.95rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(m.display_name)}</span>
                    ${botBadge}
                </div>
                <div style="color:#64748B;font-size:0.76rem;font-weight:600;font-family:var(--font-mono);margin-top:2px">${escapeHtml(m.username)} · ${m.id}</div>
            </div>
            <div style="display:flex;gap:8px">
                <button onclick="event.stopPropagation();quickAction('ban','${m.id}','${escapeHtml(m.username)}')" title="Ban" style="background:#FEE2E2;border:1px solid #FECACA;color:#DC2626;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.78rem;font-weight:700;transition:all 0.15s" onmouseover="this.style.background='#FCA5A5';this.style.color='#991B1B'" onmouseout="this.style.background='#FEE2E2';this.style.color='#DC2626'">Ban</button>
                <button onclick="event.stopPropagation();quickAction('kick','${m.id}','${escapeHtml(m.username)}')" title="Kick" style="background:#FFEDD5;border:1px solid #FED7AA;color:#EA580C;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.78rem;font-weight:700;transition:all 0.15s" onmouseover="this.style.background='#FDBA74';this.style.color='#9A3412'" onmouseout="this.style.background='#FFEDD5';this.style.color='#EA580C'">Kick</button>
                <button onclick="event.stopPropagation();quickAction('timeout','${m.id}','${escapeHtml(m.username)}')" title="Timeout" style="background:#FEF9C3;border:1px solid #FEF08A;color:#CA8A04;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.78rem;font-weight:700;transition:all 0.15s" onmouseover="this.style.background='#FDE047';this.style.color='#854D0E'" onmouseout="this.style.background='#FEF9C3';this.style.color='#CA8A04'">TO</button>
            </div>
        `;
        cardsContainer.appendChild(card);
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
            if (typeof _pollLiveLogs === 'function') _pollLiveLogs();
            if (typeof refreshMembers === 'function') refreshMembers();
            if (typeof refreshBanList === 'function') refreshBanList();
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
    container.innerHTML = `<div style="text-align:center;padding:30px;color:#64748B;font-weight:600">Loading live ban list from Discord...</div>`;
    try {
        const r = await fetch(`/api/bot/bans/${guildId}`);
        const bans = await r.json();
        if (!bans || !bans.length) {
            container.innerHTML = `<div style="text-align:center;padding:30px;color:#64748B;font-size:0.88rem;font-weight:600">No banned users found in this guild.</div>`;
            return;
        }
        container.innerHTML = bans.map(b => `
            <div style="display:flex;align-items:center;gap:14px;padding:12px 16px;border-bottom:1px solid #F1F5F9;background:#FFFFFF;border-radius:8px;margin-bottom:6px">
                <img src="https://cdn.discordapp.com/embed/avatars/${parseInt(b.user.id || 0) % 6}.png" style="width:36px;height:36px;border-radius:50%;border:1px solid #E2E8F0">
                <div style="flex:1">
                    <div style="font-weight:800;color:#0F172A;font-size:0.92rem">${escapeHtml(b.user.username)}</div>
                    <div style="color:#64748B;font-size:0.75rem;font-weight:600;font-family:var(--font-mono);margin-top:2px">${b.user.id} · <span style="color:#DC2626">${escapeHtml(b.reason || 'No reason specified')}</span></div>
                </div>
                <button onclick="unbanUser('${b.user.id}','${escapeHtml(b.user.username)}')"
                    style="background:#DCFCE7;border:1px solid #BBF7D0;color:#16A34A;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.78rem;font-weight:700;transition:all 0.15s"
                    onmouseover="this.style.background='#86EFAC';this.style.color='#14532D'" onmouseout="this.style.background='#DCFCE7';this.style.color='#16A34A'">Unban</button>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div style="text-align:center;padding:30px;color:#EF4444;font-size:0.85rem">Failed to load ban list: ${e.message}</div>`;
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
