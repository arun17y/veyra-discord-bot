
// --- 11b. NEW SECURITY SUB-PANES HANDLERS ---
function loadVerificationSettings(guildId) {
    if (!guildId) return;
    fetch(`/api/settings/verification/${guildId}`)
        .then(res => res.json())
        .then(v => {
            const verEnableEl = document.getElementById('sec-enable-verification');
            if (verEnableEl) verEnableEl.checked = v.enabled === 1;
            
            const capEnableEl = document.getElementById('ver-enable-captcha');
            if (capEnableEl) capEnableEl.checked = v.captcha_enabled !== undefined ? v.captcha_enabled === 1 : true;
            
            const verTypeEl = document.getElementById('ver-type');
            if (verTypeEl) verTypeEl.value = v.type || 'Captcha Code';
            
            const verUnverifiedEl = document.getElementById('ver-unverified-role');
            if (verUnverifiedEl) verUnverifiedEl.value = v.unverified_role || 'Unverified';
            
            const verChannelEl = document.getElementById('ver-channel');
            if (verChannelEl) verChannelEl.value = v.channel || 'verify';
            
            const verVerifiedEl = document.getElementById('ver-verified-role');
            if (verVerifiedEl) verVerifiedEl.value = v.verified_role || 'Member';
            
            const verTimeoutEl = document.getElementById('ver-timeout');
            if (verTimeoutEl) verTimeoutEl.value = v.captcha_timeout !== undefined ? v.captcha_timeout : 60;
            
            const verLengthEl = document.getElementById('ver-length');
            if (verLengthEl) verLengthEl.value = v.captcha_lines !== undefined ? v.captcha_lines : 5;
            
            const verLinesEl = document.getElementById('ver-lines');
            if (verLinesEl) verLinesEl.value = v.captcha_lines !== undefined ? v.captcha_lines : 5;
            
            const verNumbersEl = document.getElementById('ver-numbers');
            if (verNumbersEl) verNumbersEl.checked = v.captcha_numbers === 1;
            
            const verCaseEl = document.getElementById('ver-case-sensitive');
            if (verCaseEl) verCaseEl.checked = v.captcha_sensitive === 1;
            
            toggleVerificationSettingsPane(v.enabled === 1);
            toggleCaptchaOptionsBypass();
        })
        .catch(err => console.error("Error loading verification settings:", err));
}

function toggleCaptchaOptionsBypass() {
    const verType = document.getElementById('ver-type')?.value;
    const captchaEnabled = document.getElementById('ver-enable-captcha')?.checked;
    const shouldDisable = (verType === 'One-Click Verification') || (!captchaEnabled);
    
    // Disable or enable fields
    const inputs = [
        document.getElementById('ver-timeout'),
        document.getElementById('ver-length'),
        document.getElementById('ver-lines'),
        document.getElementById('ver-numbers'),
        document.getElementById('ver-case-sensitive')
    ];
    inputs.forEach(input => {
        if (input) {
            input.disabled = shouldDisable;
            input.style.opacity = shouldDisable ? '0.45' : '1';
        }
    });
}

function saveVerificationSettings() {
    if (!activeGuildId) return;
    const payload = {
        enabled: document.getElementById('sec-enable-verification')?.checked ? 1 : 0,
        captcha_enabled: document.getElementById('ver-enable-captcha')?.checked ? 1 : 0,
        type: document.getElementById('ver-type')?.value || 'Captcha Code',
        unverified_role: document.getElementById('ver-unverified-role')?.value || 'Unverified',
        channel: document.getElementById('ver-channel')?.value || 'verify',
        verified_role: document.getElementById('ver-verified-role')?.value || 'Member',
        captcha_timeout: parseInt(document.getElementById('ver-timeout')?.value || 60),
        captcha_lines: parseInt(document.getElementById('ver-length')?.value || 5),
        captcha_numbers: document.getElementById('ver-numbers')?.checked ? 1 : 0,
        captcha_sensitive: document.getElementById('ver-case-sensitive')?.checked ? 1 : 0
    };
    
    fetch(`/api/settings/verification/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Verification Gate Saved", "Server verification gateway rules successfully written to database.");
            if (payload.enabled) {
                createFeatureChannels(["verification"]);
            }
        } else {
            showToast("Save Error", data.error || "Failed to save verification settings");
        }
    })
    .catch(err => console.error("Error saving verification settings:", err));
}

function toggleVerificationSettingsPane(enabled) {
    const form = document.getElementById('verification-form-container');
    const opts = document.getElementById('captcha-options-pane');
    if (form) form.style.opacity = enabled ? '1' : '0.6';
    if (opts) opts.style.opacity = enabled ? '1' : '0.6';
}

function loadBeastModeSettings(guildId) {
    if (!guildId) return;
    fetch(`/api/settings/beastmode/${guildId}`)
        .then(res => res.json())
        .then(b => {
            const beastEnableEl = document.getElementById('sec-enable-beast');
            if (beastEnableEl) beastEnableEl.checked = b.enabled === 1;
            
            const limitEl = document.getElementById('beast-score-limit');
            if (limitEl) limitEl.value = b.score_limit !== undefined ? b.score_limit : 40;
            
            const punishEl = document.getElementById('beast-punishment-type');
            if (punishEl) punishEl.value = b.punishment_type || 'Kick';
            
            const wlBypassEl = document.getElementById('beast-whitelist-bypass');
            if (wlBypassEl) wlBypassEl.checked = b.whitelist_bypass === 1;
            
            const scores = ['bot-add', 'ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'prune', 'mention', 'vanity', 'webhook'];
            scores.forEach(key => {
                const el = document.getElementById(`score-${key}`);
                if (el) {
                    const dbKey = key.replace('-', '_');
                    el.value = b[`score_${dbKey}`] !== undefined ? b[`score_${dbKey}`] : 0;
                }
            });
            
            toggleBeastModeState(b.enabled === 1);
        })
        .catch(err => console.error("Error loading Beast Mode settings:", err));
}

function saveBeastModeSettings() {
    if (!activeGuildId) return;
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
    
    fetch(`/api/settings/beastmode/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Beast Mode Saved", "Aggressive beast-mode protection thresholds successfully synced.");
        } else {
            showToast("Save Error", data.error || "Failed to save Beast Mode settings");
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
    if (!guildId) return;
    fetch(`/api/settings/antiraid/${guildId}`)
        .then(res => res.json())
        .then(r => {
            const protectEl = document.getElementById('sec-enable-raid-inv');
            if (protectEl) protectEl.checked = r.invite_link_protection === 1;
        })
        .catch(err => console.error("Error loading Anti Raid settings:", err));
}

function saveAntiRaidSettings() {
    if (!activeGuildId) return;
    const payload = {
        invite_link_protection: document.getElementById('sec-enable-raid-inv')?.checked ? 1 : 0
    };
    fetch(`/api/settings/antiraid/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Anti Raid Saved", "Anti-raid rate-limit controls successfully synced.");
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
    if (tabName === 'beastmode') {
        loadBeastModeSettings(activeGuildId);
    } else if (tabName === 'antiraid') {
        loadAntiRaidSettings(activeGuildId);
    } else if (tabName === 'verification') {
        loadVerificationSettings(activeGuildId);
    } else if (tabName === 'moderation') {
        if (typeof window.loadModerationOverrides === 'function') window.loadModerationOverrides(activeGuildId);
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
window.toggleCaptchaOptionsBypass = toggleCaptchaOptionsBypass;

function toggleAntiRaidSettingsPane(enabled) {
    const form = document.getElementById('antiraid-form-container');
    if (form) form.style.opacity = enabled ? '1' : '0.6';
}
window.toggleAntiRaidSettingsPane = toggleAntiRaidSettingsPane;
window.toggleBeastModeState = toggleBeastModeState;

const originalFetch = window.fetch;
window.fetch = function(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    
    const sessionData = localStorage.getItem('SENTRIX_session');
    if (sessionData && sessionData !== 'undefined') {
        options.headers['Authorization'] = 'Bearer ' + encodeURIComponent(sessionData);
    }
    
    return originalFetch(url, options).then(async (response) => {
        try {
            const clone = response.clone();
            const data = await clone.clone().json().catch(() => null);
            if (data && data.sessionData) {
                localStorage.setItem('SENTRIX_session', JSON.stringify(data.sessionData));
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
    
    function renderHeroLoop() {
        heroCtx.fillStyle = 'rgba(5, 5, 5, 0.2)';
        heroCtx.fillRect(0, 0, heroCanvas.width, heroCanvas.height);
        
        heroParticles.forEach(p => {
            p.update();
            p.draw();
        });
        
        requestAnimationFrame(renderHeroLoop);
    }
    renderHeroLoop();
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
    
    // If none of these screen elements exist, we are on a static page and should redirect to manage if showing servers/dashboard
    if (!screenLanding && !screenServers && !screenDashboard && !screenAdmin) {
        if (screenId === 'servers' || screenId === 'dashboard') {
            window.location.href = '/manage';
        }
        return;
    }
    
    if (screenLanding) screenLanding.style.display = 'none';
    if (screenServers) screenServers.style.display = 'none';
    if (screenDashboard) screenDashboard.style.display = 'none';
    if (screenAdmin) screenAdmin.style.display = 'none';
    
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
        if (screenLanding) screenLanding.style.display = 'block';
        if (!preserveScroll) setNavBtnActive(navHome, true);
    } else if (screenId === 'servers') {
        if (screenServers) screenServers.style.display = 'block';
        if (!preserveScroll) setNavBtnActive(navManageServers, true);
    } else if (screenId === 'dashboard') {
        if (screenDashboard) screenDashboard.style.display = 'flex';
        if (!preserveScroll) setNavBtnActive(navManageServers, true);
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
    if (window.location.pathname.includes('/manage')) {
        window.location.href = `/?guild_id=${guildId}`;
        return;
    }
    activeGuildId = guildId;
    sessionStorage.setItem('activeGuildId', guildId);
    
    // Find active server and update UI headers dynamically
    const activeGuild = (window.allGuildsCache || []).find(g => g.id === guildId);
    if (activeGuild) {
        const guildName = activeGuild.name;
        if (document.getElementById('sidebar-guild-name')) {
            document.getElementById('sidebar-guild-name').innerText = guildName;
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
        const iconUrl = activeGuild.icon 
            ? `https://cdn.discordapp.com/icons/${activeGuild.id}/${activeGuild.icon}.png?size=128`
            : 'assets/bypass_logs_avatar.webp';
            
        const headerImg = document.querySelector('#header-server-avatar-img img');
        if (headerImg) headerImg.src = iconUrl;
        
        const dropdownImg = document.querySelector('#header-server-dropdown-icon img');
        if (dropdownImg) dropdownImg.src = iconUrl;
        
        const ticketsSidebarImg = document.getElementById('tickets-sidebar-guild-icon');
        if (ticketsSidebarImg) ticketsSidebarImg.src = iconUrl;

        // Update member count
        const ticketsSidebarMembers = document.getElementById('tickets-sidebar-guild-members');
        if (ticketsSidebarMembers) {
            const members = activeGuild.member_count || (guildName === 'GHOST' ? 1452 : 2083);
            ticketsSidebarMembers.innerText = `${members.toLocaleString()} members`;
        }
    }
    
    showScreen('dashboard');
    
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
            const pendingTab = sessionStorage.getItem('pendingTab');
            if (pendingTab) {
                switchTab(pendingTab);
                sessionStorage.removeItem('pendingTab');
            } else {
                switchTab('overview');
            }
            if (typeof updateSidebarLocks === 'function') updateSidebarLocks();
        })
        .catch(() => {
            window.currentServerPlan = 'Premium';
            const pendingTab = sessionStorage.getItem('pendingTab');
            if (pendingTab) {
                switchTab(pendingTab);
                sessionStorage.removeItem('pendingTab');
            } else {
                switchTab('overview');
            }
            if (typeof updateSidebarLocks === 'function') updateSidebarLocks();
        });

    // Fetch configurations from SQLite DB
    fetch(`/api/settings/${guildId}`)
        .then(res => res.json())
        .then(data => {
            const g = data.guild || {};
            const s = data.security || {};
            
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
                if (enableEl) enableEl.checked = (val !== undefined ? val === 1 : true);
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
                if (enableEl) enableEl.checked = (val !== undefined ? val === 1 : true);
            });

            // Dynamic Safety Status Indicator & Alert Card
            let enabledCount = 0;
            let totalCount = 16;
            
            const checkLimits = ['ban', 'kick', 'role-create', 'role-delete', 'channel-create', 'channel-delete', 'mention'];
            checkLimits.forEach(key => {
                const dbKey = key.replace('-', '_');
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (val === 1) enabledCount++;
            });
            
            const checkInstant = ['bot-add', 'prune', 'role-perm-update', 'role-add', 'vanity', 'server-rename', 'server-icon', 'role-rename', 'channel-rename'];
            checkInstant.forEach(key => {
                let dbKey = key.replace('-', '_');
                if (dbKey === 'role-perm-update') dbKey = 'dangerous_role_update';
                if (dbKey === 'role-add') dbKey = 'dangerous_role_add';
                if (dbKey === 'vanity') dbKey = 'vanity_change';
                if (dbKey === 'server-icon') dbKey = 'server_icon_change';
                const val = s[`anti_${dbKey}_enabled`] !== undefined ? s[`anti_${dbKey}_enabled`] : s[`anti_${dbKey}`];
                if (val === 1) enabledCount++;
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
                    if (document.getElementById('welcome-msg-enable')) document.getElementById('welcome-msg-enable').checked = w.enabled === 1;
                    if (document.getElementById('welcome-msg-channel-select')) document.getElementById('welcome-msg-channel-select').value = w.channel || 'general';
                    if (document.getElementById('welcome-msg-outer-input')) document.getElementById('welcome-msg-outer-input').value = w.message || '';
                    if (document.getElementById('welcome-embed-enable')) document.getElementById('welcome-embed-enable').checked = w.enabled === 1;
                    if (document.getElementById('welcome-embed-color-picker')) {
                        document.getElementById('welcome-embed-color-picker').value = w.color || '#a855f7';
                        document.getElementById('welcome-color-hex').value = w.color || '#a855f7';
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
                    if (document.getElementById('leave-msg-enable')) document.getElementById('leave-msg-enable').checked = l.enabled === 1;
                    if (document.getElementById('leave-msg-channel-select')) document.getElementById('leave-msg-channel-select').value = l.channel || 'exits';
                    if (document.getElementById('leave-msg-outer-input')) document.getElementById('leave-msg-outer-input').value = l.message || '';
                    if (document.getElementById('leave-embed-enable')) document.getElementById('leave-embed-enable').checked = l.enabled === 1;
                    if (document.getElementById('leave-embed-color-picker')) {
                        document.getElementById('leave-embed-color-picker').value = l.color || '#a855f7';
                        document.getElementById('leave-color-hex').value = l.color || '#a855f7';
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
                    if (document.getElementById('verif-enable')) document.getElementById('verif-enable').checked = v.enabled === 1;
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
                        document.getElementById('eb-color-hex').value = dm.color || '#a855f7';
                    }
                    if (typeof updateEmbedBuilderPreview === 'function') updateEmbedBuilderPreview();
                });

            // Fetch Invite Tracker configuration
            fetch(`/api/settings/invitetracker/${guildId}`)
                .then(res => res.json())
                .then(it => {
                    if (document.getElementById('invitetracker-msg-enable')) document.getElementById('invitetracker-msg-enable').checked = it.enabled === 1;
                    if (document.getElementById('invitetracker-msg-channel-select')) document.getElementById('invitetracker-msg-channel-select').value = it.channel || 'general';
                    if (document.getElementById('invitetracker-msg-outer-input')) document.getElementById('invitetracker-msg-outer-input').value = it.message || '';
                    if (document.getElementById('invitetracker-embed-color-picker')) {
                        document.getElementById('invitetracker-embed-color-picker').value = it.color || '#a855f7';
                        document.getElementById('invitetracker-color-hex').value = it.color || '#a855f7';
                    }
                    if (document.getElementById('invitetracker-embed-title')) document.getElementById('invitetracker-embed-title').value = it.title || '';
                    if (document.getElementById('invitetracker-embed-desc')) document.getElementById('invitetracker-embed-desc').value = it.description || '';
                    if (document.getElementById('invitetracker-embed-image')) document.getElementById('invitetracker-embed-image').value = it.image || '';
                    if (document.getElementById('invitetracker-embed-footer')) document.getElementById('invitetracker-embed-footer').value = it.footer || '';
                    
                    updateInviteTrackerLivePreview();
                });
        })
        .catch(err => console.error("Error loading server settings:", err));
}

function loadAuditWeblogs(guildId) {
    const weblogsBody = document.getElementById('weblogs-table-body');
    const recentBody = document.getElementById('recent-actions-table-body');
    if (weblogsBody) weblogsBody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">Loading logs...</td></tr>';
    if (recentBody) recentBody.innerHTML = '<tr><td colspan="3" style="padding: 20px; text-align: center; color: var(--text-secondary);">Loading...</td></tr>';

    fetch(`/api/logs/${guildId}`)
        .then(res => res.json())
        .then(rows => {
            window.activeAuditLogsCache = rows;
            renderAuditLogs();
        })
        .catch(err => {
            console.error("Error loading server audit logs:", err);
            if (weblogsBody) weblogsBody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary); color: #ef4444;">Failed to load logs.</td></tr>';
        });
}

// --- 4. Sidebar tab switches ---
const tabPermissions = {
    'overview': 'Free',
    'invitetracker': 'Pro',
    'weblogs': 'Free',
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
    'tickets': 'Ticket'
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

    // Dynamically adjust padding of workspace content area for tickets tab to start flush from the left edge
    const workspaceContent = document.getElementById('workspace-content');
    if (workspaceContent) {
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
    } else if (tabId === 'tickets') {
        if (typeof loadTicketsTab === 'function') loadTicketsTab(activeGuildId);
        setTimeout(() => {
            const dismissed = sessionStorage.getItem('tutorialDismissed30Days') || localStorage.getItem('tutorialDismissed30Days');
            if (!dismissed && typeof openTutorialModal === 'function') {
                openTutorialModal();
            }
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
        if (typeof loadInvitesSettings === 'function') loadInvitesSettings(activeGuildId);
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
        'tickets': 'Ticket'
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
    document.querySelectorAll('.analytics-tf-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-secondary)';
    });
    
    const activeBtn = document.getElementById(`tf-btn-${timeframe}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.background = 'rgba(255,255,255,0.08)';
        activeBtn.style.color = '#fff';
    }
    
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

function simulateLogin() {
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
    }
    
    // Redirect directly to authentication handler with demo fallback mode
    window.location.href = '/api/auth/login?mode=demo';
}

function simulateAddBot(serverName, serverId) {
    const clientId = '1527243189860175933';
    let url = `https://discord.com/oauth2/authorize?client_id=${clientId}&permissions=8&redirect_uri=https%3A%2F%2Fveyra.vercel.app%2Fauth%2Fcallback&integration_type=0&scope=bot+applications.commands`;
    if (serverId && !serverId.startsWith('mock-')) {
        url += '&guild_id=' + encodeURIComponent(serverId);
    }
    window.open(url, 'Invite VEYRA Bot', 'width=500,height=800,resizable=yes,scrollbars=yes');
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
                <i class="fab fa-discord" style="color: #a855f7;"></i>
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
    
    try {
        fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    } catch (e) {}
    
    showScreen('landing');
    showToast("Logged Out", "You have closed the server session.");
}

// --- 6. SWATCH THEMING ENGINE ---
let activeTheme = 'slate';

function changeSystemTheme(themeName, silent = false) {
    document.body.className = `theme-${themeName}`;
    activeTheme = themeName;
    
    document.querySelectorAll('.theme-swatch').forEach(swatch => {
        swatch.classList.remove('active');
    });
    const activeSwatch = document.getElementById(`swatch-${themeName}`);
    if (activeSwatch) activeSwatch.classList.add('active');
    
    if (!silent) {
        showToast("Theme Selected", `Visual layout theme set to: ${themeName.toUpperCase()}`);
    }
    
    fetch('/api/settings/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: themeName })
    }).catch(e => console.log("Offline mode default active."));
}

function loadActiveTheme() {
    fetch('/api/settings/theme')
        .then(res => res.json())
        .then(data => {
            if (data.theme) {
                changeSystemTheme(data.theme, true);
            }
        }).catch(e => {
            changeSystemTheme('slate', true);
        });
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

function filterCommands(category) {
    const container = document.getElementById('commands-toggle-container');
    if (!container) return;
    container.innerHTML = '';
    
    commandsData.forEach((cmd, idx) => {
        if (category !== 'all' && cmd.cat !== category) return;
        
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
            
            // Auto save verification and beastmode settings in parallel
            if (typeof saveVerificationSettings === 'function') saveVerificationSettings();
            if (typeof saveBeastModeSettings === 'function') saveBeastModeSettings();
            if (typeof saveAntiRaidSettings === 'function') saveAntiRaidSettings();
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
function showToast(title, msg) {
    const toast = document.createElement('div');
    toast.className = 'glass-card';
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '999999';
    toast.style.width = '320px';
    toast.style.padding = '16px';
    toast.style.borderLeft = '4px solid var(--accent-primary)';
    toast.style.animation = 'slideIn 0.5s ease forwards';
    
    toast.innerHTML = `
        <h4 style="color:var(--accent-primary); font-size:0.95rem; margin-bottom:4px;">${title}</h4>
        <p style="font-size:0.8rem; color:var(--text-secondary);">${msg}</p>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3800);
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

    function renderFooterLoop() {
        renderAscii(leftCtx, leftData, '#c084fc');
        renderAscii(rightCtx, rightData, '#c084fc');
        requestAnimationFrame(renderFooterLoop);
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
document.addEventListener('DOMContentLoaded', () => {
    loadActiveTheme();
    filterCommands('all');
    updateEmbedPreview();

    // Setup security sub-pane toggles
    // Handled globally by switchSecTab() without locks!

    // Setup sidebar collapse toggle listener
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('collapsed');
            toggleBtn.classList.toggle('crossed');
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
        shouldCleanUrl = true;
    }
    if (urlParams.has('tab')) {
        sessionStorage.setItem('pendingTab', urlParams.get('tab'));
        shouldCleanUrl = true;
    }
    if (urlParams.has('action')) {
        sessionStorage.setItem('pendingAction', urlParams.get('action'));
        shouldCleanUrl = true;
    }
    if (shouldCleanUrl) {
        window.history.replaceState({}, document.title, window.location.pathname);
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
    const isStaticSubpage = path.includes('/ticket') || path.includes('/manage') || path.includes('/admin');
    
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
        
        const activeScreen = sessionStorage.getItem('activeScreen') || 'landing';
        const savedGuildId = sessionStorage.getItem('activeGuildId');
        
        setTimeout(() => {
            if (activeScreen === 'dashboard' && savedGuildId) {
                window.activeGuildId = savedGuildId;
                loadServerDashboard(savedGuildId);
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
});

// --- 11.8 INTERACTIVE THREAT SIMULATOR CONTROL ---
let threatsBlockedCount = 14854;

window.simulateThreat = function(type, isAuto = false) {
    const counterNode = document.getElementById('threats-blocked-count');
    const shieldNode = document.getElementById('shield-core-node');
    const statusValNode = document.getElementById('shield-status-val');
    
    if (counterNode) {
        threatsBlockedCount += 1;
        counterNode.innerText = Number(threatsBlockedCount).toLocaleString();
    }

    // Visual card active state toggle
    const cardIds = {
        'spam': 'threat-card-spam',
        'phish': 'threat-card-phish',
        'abuse': 'threat-card-abuse'
    };
    Object.keys(cardIds).forEach(k => {
        const card = document.getElementById(cardIds[k]);
        if (card) {
            if (k === type) {
                card.style.background = 'rgba(255, 255, 255, 0.08)';
                card.style.borderColor = 'var(--accent-primary)';
                card.style.boxShadow = '0 0 20px rgba(0, 242, 254, 0.2)';
            } else {
                card.style.background = 'rgba(255, 255, 255, 0.01)';
                card.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                card.style.boxShadow = 'none';
            }
        }
    });
    
    // Animate shield flash response
    if (shieldNode) {
        let flashColor = '#00f2fe';
        if (type === 'spam') {
            flashColor = '#00f2fe';
        } else if (type === 'phish') {
            flashColor = '#ef4444';
        } else if (type === 'abuse') {
            flashColor = '#a855f7';
        } else {
            flashColor = '#00f2fe';
        }
        
        shieldNode.style.borderColor = flashColor;
        shieldNode.style.boxShadow = `0 0 40px ${flashColor}, inset 0 0 20px ${flashColor}`;
        shieldNode.style.transform = 'scale(1.1)';
        
        if (statusValNode) {
            statusValNode.innerText = 'MITIGATING...';
            statusValNode.style.color = flashColor;
        }
        
        setTimeout(() => {
            shieldNode.style.borderColor = '#00f2fe';
            shieldNode.style.boxShadow = '0 0 30px rgba(0, 242, 254, 0.35)';
            shieldNode.style.transform = 'scale(1.0)';
            if (statusValNode) {
                statusValNode.innerText = 'ARMED';
                statusValNode.style.color = '#10b981';
            }
        }, 500);
    }
    
    // Canvas collision particles animation
    animateThreatParticles(type);
    
    // Push notifications (only if NOT triggered automatically)
    if (!isAuto) {
        if (type === 'spam') {
            showToast("Spam Attack Blocked", "Neutralized 142 rogue bot accounts attempting to join.");
        } else if (type === 'phish') {
            showToast("Phishing Link Blocked", "Deleted suspicious domain redirect to wallet-stealer.ru.");
        } else if (type === 'abuse') {
            showToast("Access Attack Prevented", "Flagged unauthorized Administrator edit role sweep attempt.");
        }
    }
}

// 2.5s Auto-trigger threat simulator loop (runs silently in the background without toast notifications)
let currentThreatIdx = 0;
const threatTypes = ['spam', 'phish', 'abuse'];
setInterval(() => {
    const activeScreen = sessionStorage.getItem('activeScreen') || 'landing';
    const path = window.location.pathname.toLowerCase();
    if (activeScreen === 'landing' && !path.includes('/manage') && !path.includes('/ticket') && !path.includes('/admin')) {
        const type = threatTypes[currentThreatIdx];
        if (window.simulateThreat) {
            window.simulateThreat(type, true);
        }
        currentThreatIdx = (currentThreatIdx + 1) % threatTypes.length;
    }
}, 2500);


function animateThreatParticles(type) {
    const canvas = document.getElementById('canvas-threat-sim');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Reset canvas dimensions to fill bounds
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    // Shield center coordinates relative to canvas (ORIGIN: Circle of Security)
    const shield = document.getElementById('shield-core-node');
    if (!shield) return;
    const shieldRect = shield.getBoundingClientRect();
    const startX = (shieldRect.left + shieldRect.width / 2) - rect.left;
    const startY = (shieldRect.top + shieldRect.height / 2) - rect.top;
    
    // Target threat card coordinates relative to canvas (DESTINATION)
    let cardId = 'threat-card-spam';
    if (type === 'phish') cardId = 'threat-card-phish';
    if (type === 'abuse') cardId = 'threat-card-abuse';
    
    const cardEl = document.getElementById(cardId);
    let targetX = canvas.width - 140;
    let targetY = startY;
    if (cardEl) {
        const cardRect = cardEl.getBoundingClientRect();
        targetX = (cardRect.left + cardRect.width / 2) - rect.left;
        targetY = (cardRect.top + cardRect.height / 2) - rect.top;
    }
    
    let threatColor = '#00aff4';
    if (type === 'spam') threatColor = '#eab308';
    if (type === 'phish') threatColor = '#ef4444';
    if (type === 'abuse') threatColor = '#a855f7';
    
    // Spawn 50 tiny glowing particles originating in a circle
    let particles = [];
    const baseRadius = 55; // radius of circle around shield
    
    for (let i = 0; i < 50; i++) {
        let angle = Math.random() * Math.PI * 2;
        let radiusOffset = (Math.random() - 0.5) * 15; // slightly spread thickness
        particles.push({
            angle: angle,
            radius: baseRadius + radiusOffset,
            rotationSpeed: (0.015 + Math.random() * 0.02) * (Math.random() > 0.5 ? 1 : -1),
            progress: 0,
            speed: 0.006 + Math.random() * 0.007,
            size: Math.random() * 2.8 + 1.2,
            color: threatColor,
            alpha: 1,
            radialDrift: Math.random() * 15
        });
    }
    
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        let active = false;
        particles.forEach(p => {
            if (p.progress < 1) {
                p.progress += p.speed;
                
                // Update rotation angle
                const currentAngle = p.angle + p.progress * p.rotationSpeed * 50;
                
                // Update radius (rise slightly outward)
                const currentRadius = p.radius + p.progress * p.radialDrift;
                
                // Compute coordinates around shield center
                const currentX = startX + currentRadius * Math.cos(currentAngle);
                const currentY = startY + currentRadius * Math.sin(currentAngle);
                
                p.alpha = 1 - p.progress;
                active = true;
                
                // Outer glow shadow
                ctx.beginPath();
                ctx.arc(currentX, currentY, p.size * 2.2, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = p.alpha * 0.4;
                ctx.fill();

                // Core particle
                ctx.beginPath();
                ctx.arc(currentX, currentY, p.size, 0, Math.PI * 2);
                ctx.fillStyle = '#ffffff';
                ctx.globalAlpha = p.alpha;
                ctx.fill();
            }
        });
        
        if (active) {
            requestAnimationFrame(draw);
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }
    
    draw();
}

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
        return `<div class="dyno-server-icon" style="background: #18181b; color: #a855f7; border: 1.5px solid rgba(168, 85, 247, 0.4); display:flex; align-items:center; justify-content:center;"><i class="fas fa-crosshairs"></i></div>`;
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
function checkSession() {
    fetch('/api/auth/session?t=' + Date.now(), { cache: 'no-store' })
        .then(res => res.json())
        .then(data => {
            if (data.loggedIn && data.user) {
                window.isUserLoggedIn = true;
                const tag = (data.user.global_name || data.user.username) ? (data.user.global_name || data.user.username) : '!! DADDY';
                let avatarUrl = 'https://cdn.discordapp.com/avatars/1256986886631854080/e5f2679c33de4dfea4d337d6ea14d4c3.png?size=256';
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
                    loginBtn.innerHTML = `<img src="${avatarUrl}" style="width:32px; height:32px; border-radius:50%; margin-right:10px; border: 1.5px solid rgba(255,255,255,0.15); vertical-align:middle; display:inline-block; object-fit: cover;"> ${tag}`;
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
                
                const serversList = data.guilds || [];
                renderUserGuilds(serversList, true);
                if (typeof window.initRazorpayCheckoutFlow === 'function') {
                    window.initRazorpayCheckoutFlow();
                }
                
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.has('login')) {
                    sessionStorage.setItem('hasEntered', 'true');
                    sessionStorage.setItem('activeScreen', 'servers');
                    window.location.href = '/manage';
                    return;
                }
                
                const pendingAction = sessionStorage.getItem('pendingAction');
                if (pendingAction === 'invite') {
                    sessionStorage.removeItem('pendingAction');
                    setTimeout(() => {
                        showScreen('servers');
                    }, 200);
                }
            } else {
                window.isUserLoggedIn = false;
                const pendingAction = sessionStorage.getItem('pendingAction');
                if (pendingAction === 'invite') {
                    sessionStorage.removeItem('pendingAction');
                    setTimeout(() => {
                        simulateLogin();
                    }, 200);
                }
                updateHeaderWidgetsVisibility(false);
                renderUserGuilds([], false);
                const loginBtn = document.getElementById('login-btn');
                if (loginBtn) {
                    loginBtn.innerHTML = `
                        <div class="liquid-metal-btn-inner">
                            <i class="fab fa-discord" style="color: #a855f7;"></i>
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
            }
        })
        .catch(err => {
            window.isUserLoggedIn = false;
            updateHeaderWidgetsVisibility(false);
            console.error("Session fetch failed, using empty fallback:", err);
            renderUserGuilds([], false);
        });
}

function renderUserGuilds(guilds, loggedIn = false) {
    const container = document.getElementById('screen-servers');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!loggedIn) {
        container.style.maxWidth = '500px';
        container.innerHTML = `
            <div class="login-auth-card-container" style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 70vh; width: 100%; position: relative;">
                <div class="glass-card" style="width: 100%; max-width: 440px; background: rgba(15, 17, 26, 0.7); border: 1.5px solid rgba(255, 255, 255, 0.04); border-radius: 20px; padding: 40px 30px; text-align: center; box-shadow: 0 30px 60px rgba(0,0,0,0.8); backdrop-filter: blur(10px); position: relative; z-index: 10;">
                    <div style="width: 80px; height: 80px; border-radius: 20px; background: #1a1c23; border: 1.5px solid rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; margin: 0 auto 25px auto; overflow: hidden; position: relative;">
                        <img src="assets/bypass_logs_avatar.webp" style="width: 100%; height: 100%; object-fit: cover;">
                        <span style="position: absolute; bottom: 8px; right: 8px; width: 10px; height: 10px; border-radius: 50%; background: #a855f7; border: 2px solid #1a1c23;"></span>
                    </div>
                    <div style="background: rgba(168, 85, 247, 0.1); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 4px; padding: 4px 10px; font-family: var(--font-mono); font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; display: inline-block; margin-bottom: 12px;">
                        ADMIN AUTH REQUIRED
                    </div>
                    <h2 style="font-size: 1.6rem; font-weight: 800; color: #fff; margin: 0 0 16px 0; font-family: var(--font-display);">VEYRA Bot Core</h2>
                    <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; margin: 0 0 30px 0; font-family: var(--font-display); font-weight: 500; max-width: 320px; margin-left: auto; margin-right: auto;">
                        Welcome, Administrator. Please authenticate using Discord OAuth 2.0 to access the VEYRA Firewall controls.
                    </p>
                    <button class="liquid-metal-btn" onclick="simulateLogin()" style="width: 100%; font-size: 1.05rem; border-radius: 12px; cursor: pointer;">
                        <div class="liquid-metal-btn-inner" style="padding: 15px 0; border-radius: 12px; display: flex; align-items: center; justify-content: center; gap: 10px; font-weight: 700; background: linear-gradient(135deg, #5865F2, #4752c4);">
                            <i class="fab fa-discord" style="color: #fff; font-size: 1.25rem;"></i>
                            <span>LOGIN WITH DISCORD</span>
                        </div>
                    </button>
                    <div style="margin-top: 30px; display: flex; align-items: center; justify-content: center; gap: 6px; font-family: var(--font-mono); font-size: 0.65rem; color: var(--text-secondary); letter-spacing: 0.08em;">
                        <i class="fas fa-shield-halved" style="color: #a855f7; font-size: 0.75rem;"></i>
                        <span>ECC ENCRYPTED GATEWAY</span>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    // Render the Server Management view (if logged in)
    container.style.maxWidth = '550px';
    
    // Header section
    const headerDiv = document.createElement('div');
    headerDiv.style.marginBottom = '25px';
    headerDiv.innerHTML = `
        <h1 style="font-size: 2.2rem; color: #fff; font-family: var(--font-display); font-weight: 800; margin: 0 0 6px 0;">Server Management</h1>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0 0 16px 0; font-family: var(--font-display); font-weight: 500;">
            Manage your Discord servers with VEYRA Security & VEYRA TICKET
        </p>
        <button onclick="simulateAddBot('New Guild')" class="invite-bot-btn" style="background: transparent; color: #f59e0b; border: 1.5px solid rgba(245, 158, 11, 0.45); padding: 8px 18px; border-radius: 6px; font-family: var(--font-mono); font-weight: 700; font-size: 0.76rem; letter-spacing: 0.05em; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='rgba(245, 158, 11, 0.05)'" onmouseout="this.style.background='transparent'">
            + INVITE BOT
        </button>
    `;
    container.appendChild(headerDiv);

    // Search bar
    const searchDiv = document.createElement('div');
    searchDiv.style.position = 'relative';
    searchDiv.style.marginBottom = '20px';
    searchDiv.innerHTML = `
        <input type="text" id="guild-search-input" placeholder="Search for a server..." style="width: 100%; padding: 14px 45px 14px 16px; background: #0f111a; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; color: #fff; font-size: 0.92rem; font-family: var(--font-display); box-sizing: border-box;">
        <i class="fas fa-magnifying-glass" style="position: absolute; right: 16px; top: 16px; color: var(--text-secondary); font-size: 0.95rem; pointer-events: none;"></i>
    `;
    container.appendChild(searchDiv);

    // Stats row
    const statsDiv = document.createElement('div');
    statsDiv.id = 'servers-stats-row';
    statsDiv.style.display = 'flex';
    statsDiv.style.alignItems = 'center';
    statsDiv.style.gap = '8px';
    statsDiv.style.flexWrap = 'wrap';
    statsDiv.style.fontFamily = 'var(--font-mono)';
    statsDiv.style.fontSize = '0.72rem';
    statsDiv.style.color = 'var(--text-secondary)';
    statsDiv.style.fontWeight = '600';
    statsDiv.style.marginBottom = '25px';
    
    // Count stats
    const totalCount = guilds.length;
    const activeCount = guilds.filter(g => g.active === true && g.missing !== true).length;
    const notConfiguredCount = guilds.filter(g => g.active !== true && g.can_invite !== false).length;
    const noPermissionCount = guilds.filter(g => g.active !== true && g.can_invite === false).length;

    statsDiv.innerHTML = `
        <span>${totalCount} Servers</span>
        <span>&bull;</span>
        <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981; display: inline-block;"></span> ${activeCount} Active</span>
        <span>&bull;</span>
        <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 6px; height: 6px; border-radius: 50%; background: #a855f7; display: inline-block;"></span> ${notConfiguredCount} Not Configured</span>
        <span>&bull;</span>
        <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 6px; height: 6px; border-radius: 50%; background: #6b7280; display: inline-block;"></span> ${noPermissionCount} No Permission</span>
    `;
    container.appendChild(statsDiv);

    // Cards list container
    const listGrid = document.createElement('div');
    listGrid.id = 'servers-selection-grid';
    listGrid.style.display = 'flex';
    listGrid.style.flexDirection = 'column';
    listGrid.style.gap = '18px';
    container.appendChild(listGrid);

    window.allGuildsCache = guilds;

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
    // 1st: bot is active (g.active === true && g.missing !== true) -> priority 1
    // 2nd: bot not configured or missing (g.active !== true && g.can_invite !== false) -> priority 2
    // 3rd: dont have permission (g.can_invite === false) -> priority 3
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
        noServersCard.style.padding = '35px 20px';
        noServersCard.style.textAlign = 'center';
        noServersCard.style.color = 'var(--text-secondary)';
        noServersCard.style.fontFamily = 'var(--font-display)';
        noServersCard.style.fontSize = '0.9rem';
        noServersCard.style.background = '#111214';
        noServersCard.style.border = '1.5px dashed rgba(255,255,255,0.05)';
        noServersCard.style.borderRadius = '14px';
        noServersCard.innerHTML = `
            <i class="fas fa-server" style="font-size: 1.8rem; color: rgba(255,255,255,0.15); margin-bottom: 12px; display: block;"></i>
            No manageable servers found.<br>
            <span style="font-size: 0.74rem; opacity: 0.7; display: inline-block; margin-top: 4px; line-height: 1.4;">Make sure you are the Owner or have Manage Server/Admin permission in your servers.</span>
        `;
        listGrid.appendChild(noServersCard);
    } else {
        filtered.forEach(g => {
            const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.background = '#111214';
        card.style.border = '1.5px solid rgba(255,255,255,0.02)';
        card.style.borderRadius = '14px';
        card.style.padding = '20px';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.gap = '16px';
        card.style.boxShadow = '0 8px 24px rgba(0,0,0,0.3)';

        let iconHtml = '';
        if (g.icon) {
            iconHtml = `<img src="https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png?size=128" style="width:44px; height:44px; border-radius:8px; object-fit:cover; border: 1.5px solid rgba(255,255,255,0.08);">`;
        } else {
            iconHtml = `<div style="width: 44px; height: 44px; border-radius: 8px; background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-weight:700; color:#fff; font-size:0.9rem;">${g.name.charAt(0)}</div>`;
        }

        const isBotActive = g.active === true && g.missing !== true;
        const isMissing = g.missing === true;
        const canInvite = g.can_invite !== false;
        
        let statusText = 'Not Configured';
        let statusDotColor = '#a855f7'; // purple for not configured
        let actionBtnText = '+ ADD TO SERVER';
        let actionBtnStyle = 'background: #248046; border: none; color: #fff; padding: 10px 0; border-radius: 8px; width: 100%; font-weight: 600; cursor: pointer; text-align: center; font-family: var(--font-display);';
        let clickHandler = `simulateAddBot('${g.name.replace(/'/g, "\\'")}', '${g.id}')`;
        
        if (isBotActive) {
            statusText = 'Bot Active';
            statusDotColor = '#10b981'; // green
            actionBtnText = 'MANAGE SERVER';
            actionBtnStyle = 'background: linear-gradient(135deg, #7c3aed, #6d28d9); border: 1px solid rgba(255,255,255,0.3); color: #ffffff; padding: 12px 0; border-radius: 10px; width: 100%; font-weight: 800; font-size: 0.95rem; cursor: pointer; text-align: center; text-transform: uppercase; letter-spacing: 0.08em; font-family: var(--font-display); box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4);';
            clickHandler = `loadServerDashboard('${g.id}')`;
        } else if (isMissing) {
            statusText = 'Missing (Offline / Kicked)';
            statusDotColor = '#f59e0b'; // orange
            actionBtnText = 'RE-INVITE BOT';
            actionBtnStyle = 'background: #d97706; border: none; color: #fff; padding: 10px 0; border-radius: 8px; width: 100%; font-weight: 600; cursor: pointer; text-align: center; font-family: var(--font-display);';
            clickHandler = `simulateAddBot('${g.name.replace(/'/g, "\\'")}', '${g.id}')`;
        } else if (!canInvite) {
            statusText = 'No Permission (Missing Admin Rights)';
            statusDotColor = '#6b7280'; // grey
            actionBtnText = 'YOU DON\'T HAVE PERMISSION';
            actionBtnStyle = 'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); color: rgba(255,255,255,0.2); padding: 10px 0; border-radius: 8px; width: 100%; font-weight: 600; cursor: not-allowed; text-align: center; font-family: var(--font-display);';
            clickHandler = 'event.stopPropagation(); return false;';
        }

        card.innerHTML = `
            <div style="display: flex; align-items: center; gap: 14px;">
                ${iconHtml}
                <div>
                    <h4 style="font-size: 0.95rem; font-weight: 800; color: #fff; margin: 0 0 4px 0; font-family: var(--font-display);">${g.name}</h4>
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 0.72rem; font-family: var(--font-mono); color: ${statusDotColor}; font-weight: 600;">
                        <span style="width: 6px; height: 6px; border-radius: 50%; background: ${statusDotColor}; display: inline-block;"></span>
                        ${statusText}
                    </div>
                </div>
            </div>
            <button onclick="${clickHandler}" style="${actionBtnStyle}" onmouseover="this.style.opacity='0.95'" onmouseout="this.style.opacity='1'">
                ${actionBtnText}
            </button>
        `;
        listGrid.appendChild(card);
    });
}

    // Add New Server card at the bottom of the stack
    const addCard = document.createElement('div');
    addCard.className = 'glass-card';
    addCard.style.border = '2px dashed rgba(255,255,255,0.1)';
    addCard.style.borderRadius = '14px';
    addCard.style.padding = '24px 20px';
    addCard.style.display = 'flex';
    addCard.style.flexDirection = 'column';
    addCard.style.alignItems = 'center';
    addCard.style.justifyContent = 'center';
    addCard.style.gap = '8px';
    addCard.style.cursor = 'pointer';
    addCard.style.transition = 'all 0.2s';
    addCard.style.background = 'transparent';
    addCard.onclick = () => simulateAddBot('New Guild');

    addCard.onmouseover = () => {
        addCard.style.borderColor = 'rgba(255,255,255,0.25)';
        addCard.style.background = 'rgba(255,255,255,0.01)';
    };
    addCard.onmouseout = () => {
        addCard.style.borderColor = 'rgba(255,255,255,0.1)';
        addCard.style.background = 'transparent';
    };

    addCard.innerHTML = `
        <div style="width: 38px; height: 38px; border-radius: 50%; border: 1.5px solid rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; color: var(--text-secondary); font-size: 1rem;">
            <i class="fas fa-plus"></i>
        </div>
        <div style="font-weight: 700; color: #fff; font-size: 0.88rem; margin-top: 4px; font-family: var(--font-display);">Add New Server</div>
        <div style="font-size: 0.72rem; color: var(--text-secondary); font-weight: 500; font-family: var(--font-display);">Invite VEYRA Security to another server</div>
    `;
    listGrid.appendChild(addCard);
}

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
            const offCtx = offCanvas.getContext('2d');

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

function saveVerificationSettings() {
    if (!activeGuildId) {
        showToast("Error", "No active guild selected.", "error");
        return;
    }
    const isEnabled = document.getElementById('verif-enable').checked;
    const level = document.getElementById('verif-level').value;
    const role = document.getElementById('verif-role').value;
    const action = document.getElementById('verif-action').value;
    const timeout = document.getElementById('verif-timeout').value;
    const channel = document.getElementById('verif-channel').value;
    
    const payload = {
        enabled: isEnabled ? 1 : 0,
        type: level,
        verified_role: role,
        timeout_action: action,
        captcha_timeout: parseInt(timeout) || 60,
        channel: channel
    };
    
    fetch(`/api/verification/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Verification Saved", `Configurations updated. Role: ${role}, Level: ${level}, Action: ${action}`);
            loadAuditWeblogs(activeGuildId);
        } else {
            showToast("Save Failed", data.error || "Failed to save verification settings.", "error");
        }
    })
    .catch(err => {
        console.error("Verification save error:", err);
        showToast("Save Failed", "Network error when saving settings.", "error");
    });
}

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
                    <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.82rem; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444;"></span>
                        <span>${escapeHtml(uId)}</span>
                        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="deleteBlacklistUser('${uId}')"></i>
                    </div>
                `).join('') || '<span style="font-size:0.78rem; color:var(--text-secondary);">No blacklisted users</span>';
            }

            const hiddenContainer = document.getElementById('leaderboard-hidden-list');
            if (hiddenContainer) {
                hiddenContainer.innerHTML = (data.hidden || []).map(uId => `
                    <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.82rem; color: #fff; display: flex; align-items: center; gap: 8px;">
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

// --- DISCORD EMOJI PARSER & WELCOME / LEAVE LIVE PREVIEWS ---

function parseDiscordEmojis(text) {
    if (!text) return '';
    let parsed = text
        .replace(/&lt;a?:([a-zA-Z0-9_]+):([0-9]+)&gt;/g, (match, name, id) => {
            const ext = match.includes('&lt;a:') ? 'gif' : 'png';
            return `<img src="https://cdn.discordapp.com/emojis/${id}.${ext}" alt=":${name}:" title=":${name}:" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;">`;
        })
        .replace(/<a?:([a-zA-Z0-9_]+):([0-9]+)>/g, (match, name, id) => {
            const ext = match.startsWith('<a:') ? 'gif' : 'png';
            return `<img src="https://cdn.discordapp.com/emojis/${id}.${ext}" alt=":${name}:" title=":${name}:" style="width: 1.35em; height: 1.35em; vertical-align: -0.2em; display: inline-block; object-fit: contain;">`;
        });
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
        if (recentBody) {
            recentBody.innerHTML = mockAuditLogs.slice(0, 8).map(log => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
                    <td style="padding: 10px 5px; font-family: var(--font-mono); font-size:0.78rem;">${log.time}</td>
                    <td style="padding: 10px 5px; font-weight:600; color:#fff;">${log.user}</td>
                    <td style="padding: 10px 5px; line-height: 1.4;">System: ${log.action}</td>
                </tr>
            `).join('');
        }
        if (weblogsBody) {
            weblogsBody.innerHTML = mockAuditLogs.map(log => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
                    <td style="padding: 12px 5px; font-family: var(--font-mono); font-size:0.8rem;">${log.time}</td>
                    <td style="padding: 12px 5px; font-weight:600; color:#fff;">${log.user}</td>
                    <td style="padding: 12px 5px;"><span style="background:rgba(168,85,247,0.12); color:#c084fc; border:1px solid rgba(168,85,247,0.3); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:var(--font-mono); font-weight:700;">System</span></td>
                    <td style="padding: 12px 5px; line-height: 1.4;">${log.action}</td>
                </tr>
            `).join('');
        }
        return;
    }

    if (recentBody) {
        recentBody.innerHTML = logs.slice(0, 8).map(row => {
            let dateStr = 'Today';
            if (row.timestamp) {
                const d = new Date(row.timestamp);
                dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            return `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
                    <td style="padding: 10px 5px; font-family: var(--font-mono); font-size:0.78rem;">${dateStr}</td>
                    <td style="padding: 10px 5px; font-weight:600; color:#fff;">${row.user}</td>
                    <td style="padding: 10px 5px; line-height: 1.4;">${row.action}: ${row.details}</td>
                </tr>
            `;
        }).join('');
    }

    if (weblogsBody) {
        weblogsBody.innerHTML = logs.map(row => {
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
                    <td style="padding: 12px 5px; line-height: 1.4;">${row.details || ''}</td>
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
    showToast("Bot Nickname Applied", `Changed bot's global guild nickname to ${nick}`);
    addLogEntry("!! DADDY", `Set guild bot name to: ${nick}`);
    
    // Add new log to database preview
    mockAuditLogs.unshift({
        time: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: '!! DADDY',
        action: `Set nickname to ${nick}`
    });
    renderAuditLogs();
}

function addBotPrefix() {
    const prefixInput = document.getElementById('bot-prefix-input');
    const val = prefixInput?.value.trim();
    if (!val) {
        showToast("Error", "Please input a valid command prefix character.", "error");
        return;
    }
    showToast("Prefix Added", `Command trigger registry updated with prefix: ${val}`);
    prefixInput.value = '';
}

function removeBotPrefix() {
    showToast("Prefix Revoked", "Successfully removed command prefix triger '!'");
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
        previewOuter.innerText = normVal;
        previewOuter.style.display = normVal ? 'block' : 'none';
    }

    const embedBox = document.getElementById('eb-preview-embed');
    const colorPicker = document.getElementById('eb-color-picker');
    if (embedBox && colorPicker) {
        embedBox.style.borderLeftColor = colorPicker.value;
    }

    const authNameVal = document.getElementById('eb-author-name')?.value || '';
    const authIconVal = document.getElementById('eb-author-icon')?.value || '';
    const previewAuth = document.getElementById('eb-preview-author');
    const previewAuthName = document.getElementById('eb-preview-author-name');
    const previewAuthIcon = document.getElementById('eb-preview-author-icon');

    if (previewAuth && previewAuthName && previewAuthIcon) {
        if (authNameVal) {
            previewAuthName.innerText = authNameVal;
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

    const previewTitle = document.getElementById('eb-preview-title');
    if (previewTitle) {
        previewTitle.innerText = titleVal;
        previewTitle.style.display = titleVal ? 'block' : 'none';
    }

    const previewDesc = document.getElementById('eb-preview-description');
    if (previewDesc) {
        previewDesc.innerText = descVal;
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

function updateBotProfileLivePreview() {
    const nickEl = document.getElementById('bot-nickname-field');
    const bioEl = document.getElementById('bot-bio-field');
    const webEl = document.getElementById('bot-website-field');
    const suppEl = document.getElementById('bot-support-field');
    
    const nick = nickEl ? nickEl.value : 'VEYRA';
    const bioRaw = bioEl ? bioEl.value : '';
    const website = webEl ? webEl.value.trim() : '';
    const support = suppEl ? suppEl.value.trim() : '';

    // Update char counts
    const nickCount = document.getElementById('nickname-char-count');
    if (nickCount) nickCount.innerText = `${nick.length}/32 characters`;
    
    const bioCount = document.getElementById('bio-char-count');
    if (bioCount) bioCount.innerText = `${bioRaw.length}/180`;

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

function handleBotAvatarUpload(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            window.currentBotAvatarData = e.target.result;
            
            const previewBox = document.getElementById('bot-avatar-preview-box');
            if (previewBox) {
                previewBox.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
            }
            
            const cardAvatar = document.getElementById('preview-bot-avatar');
            if (cardAvatar) {
                cardAvatar.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover;">`;
            }
            
            showToast("Avatar Selected", "Bot avatar updated in live preview!");
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function handleBotBannerUpload(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            window.currentBotBannerData = e.target.result;
            
            const previewBox = document.getElementById('bot-banner-preview-box');
            if (previewBox) {
                previewBox.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">`;
            }
            
            const cardBanner = document.getElementById('preview-bot-banner');
            if (cardBanner) {
                cardBanner.style.backgroundImage = `url('${e.target.result}')`;
                cardBanner.style.backgroundSize = 'cover';
                cardBanner.style.backgroundPosition = 'center';
            }
            
            showToast("Banner Selected", "Bot profile banner updated in live preview!");
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function saveBotProfileSettings() {
    const guildId = activeGuildId || '1509911679637520584';
    const nickname = document.getElementById('bot-nickname-field') ? document.getElementById('bot-nickname-field').value : 'VEYRA';
    const bio = document.getElementById('bot-bio-field') ? document.getElementById('bot-bio-field').value : '';
    const website = document.getElementById('bot-website-field') ? document.getElementById('bot-website-field').value : '';
    const support = document.getElementById('bot-support-field') ? document.getElementById('bot-support-field').value : '';

    const payload = {
        nickname,
        bio,
        website,
        support,
        avatar: window.currentBotAvatarData || '',
        banner: window.currentBotBannerData || ''
    };

    fetch(`/api/settings/bot-profile/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            showToast("Profile Saved", "Bot profile settings, avatar & banner saved for server!");
            addLogEntry("@user", `Updated Bot Profile: Nickname='${nickname}'`);
        } else {
            showToast("Save Failed", res.error || "Failed to save profile settings", "error");
        }
    })
    .catch(err => {
        console.error("Save profile error:", err);
        showToast("Profile Saved", "Bot profile settings saved locally for server!");
    });
}

function loadBotProfileSettings(guildId) {
    fetch(`/api/settings/bot-profile/${guildId}`)
        .then(res => res.json())
        .then(data => {
            if (document.getElementById('bot-nickname-field')) document.getElementById('bot-nickname-field').value = data.nickname || 'VEYRA';
            if (document.getElementById('bot-bio-field')) document.getElementById('bot-bio-field').value = data.bio || "The most powerful invite tracking bot on Discord.\n\nWebsite: \nSupport: ";
            if (document.getElementById('bot-website-field')) document.getElementById('bot-website-field').value = data.website || '';
            if (document.getElementById('bot-support-field')) document.getElementById('bot-support-field').value = data.support || '';

            if (data.avatar) {
                window.currentBotAvatarData = data.avatar;
                const previewBox = document.getElementById('bot-avatar-preview-box');
                if (previewBox) previewBox.innerHTML = `<img src="${data.avatar}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                const cardAvatar = document.getElementById('preview-bot-avatar');
                if (cardAvatar) cardAvatar.innerHTML = `<img src="${data.avatar}" style="width: 100%; height: 100%; object-fit: cover;">`;
            }

            if (data.banner) {
                window.currentBotBannerData = data.banner;
                const previewBox = document.getElementById('bot-banner-preview-box');
                if (previewBox) previewBox.innerHTML = `<img src="${data.banner}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">`;
                const cardBanner = document.getElementById('preview-bot-banner');
                if (cardBanner) {
                    cardBanner.style.backgroundImage = `url('${data.banner}')`;
                    cardBanner.style.backgroundSize = 'cover';
                    cardBanner.style.backgroundPosition = 'center';
                }
            }

            updateBotProfileLivePreview();
        })
        .catch(err => console.error("Error loading bot profile settings:", err));
}

function populateServerRolesAndChannels(guildId) {
    // Fetch Roles
    fetch(`/api/guild/roles/${guildId}`)
        .then(res => res.json())
        .then(roles => {
            const roleSelects = Array.from(document.querySelectorAll('.guild-roles-dropdown, #verif-role, #verification-role-select, #autoroles-select, #sticky-blacklisted-select, #publish-bump-role-select, #am-mute-role, #am-allowed-roles'));
            roleSelects.forEach(select => {
                if (select) {
                    const currentVal = select.value;
                    select.innerHTML = '<option value="">Select option</option>';
                    roles.forEach(r => {
                        const opt = document.createElement('option');
                        opt.value = r.id;
                        opt.innerText = r.name;
                        select.appendChild(opt);
                    });
                    if (currentVal) select.value = currentVal;
                }
            });
        })
        .catch(err => console.error("Error fetching roles:", err));

    // Fetch Channels
    fetch(`/api/guild/channels/${guildId}`)
        .then(res => res.json())
        .then(channels => {
            const channelSelects = [
                document.getElementById('welcome-msg-channel-select'),
                document.getElementById('leave-msg-channel-select'),
                document.getElementById('invitetracker-msg-channel-select'),
                document.getElementById('eb-destination-channel'),
                document.getElementById('verif-channel'),
                document.getElementById('log-select-moderation'),
                document.getElementById('log-select-security'),
                document.getElementById('reports-channel-select')
            ];
            channelSelects.forEach(select => {
                if (select) {
                    const isLog = select.id.startsWith('log-select-');
                    select.innerHTML = isLog ? '<option value="none">None</option>' : '<option value="">Select option</option>';
                    channels.forEach(c => {
                        const opt = document.createElement('option');
                        opt.value = c.id;
                        opt.innerText = `#${c.name}`;
                        select.appendChild(opt);
                    });
                }
            });
        })
        .catch(err => console.error("Error fetching channels:", err));
}

function loadRealAnalytics(guildId, timeframe = '30D') {
    const targetGuild = guildId || activeGuildId || '1509911679637520584';
    fetch(`/api/analytics/${targetGuild}?timeframe=${timeframe}`)
        .then(res => res.json())
        .then(data => {
            const elNet = document.getElementById('analytics-net-growth');
            const elJoins = document.getElementById('analytics-joins');
            const elLeaves = document.getElementById('analytics-leaves');
            const elRetention = document.getElementById('analytics-retention');
            const elStayed = document.getElementById('analytics-stayed-subtext');

            if (elNet) elNet.innerText = (data.netGrowth >= 0 ? '+' : '') + data.netGrowth;
            if (elJoins) elJoins.innerText = data.joins;
            if (elLeaves) elLeaves.innerText = data.leaves;
            if (elRetention) elRetention.innerText = data.retention + '%';
            if (elStayed) elStayed.innerText = `${data.netGrowth >= 0 ? data.netGrowth : 0} of ${data.joins} invites active`;

            window.activeAnalyticsPoints = data.points || [];
            renderAnalyticsGraph(data.points || []);
        })
        .catch(err => console.error("Error loading analytics:", err));
}

function renderAnalyticsGraph(points) {
    if (!points || points.length === 0) return;
    
    const xaxisContainer = document.getElementById('analytics-xaxis-labels');
    if (xaxisContainer) {
        xaxisContainer.innerHTML = points.map((p, idx) => 
            `<span style="${idx === points.length - 1 ? 'color:#a855f7; font-weight:800;' : ''}">${p.date}</span>`
        ).join('');
    }

    const svgChart = document.getElementById('analytics-svg-chart');
    const pathJoins = document.getElementById('analytics-path-joins');
    const pathLeaves = document.getElementById('analytics-path-leaves');
    
    if (!svgChart || !pathJoins || !pathLeaves) return;

    const maxVal = Math.max(50, ...points.map(p => Math.max(p.joins, p.leaves))) * 1.15;
    const width = 1000;
    const height = 200;
    const padding = 20;
    
    const getX = (index) => padding + (index / (points.length - 1)) * (width - 2 * padding);
    const getY = (val) => height - (val / maxVal) * (height - 30);

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
    pathLeaves.style.display = 'block';

    updateGraphTooltipByIndex(points.length - 1, maxVal);
}

function updateGraphTooltipByIndex(index, maxValCalculated) {
    const points = window.activeAnalyticsPoints;
    if (!points || points.length === 0) return;
    
    const idx = Math.max(0, Math.min(points.length - 1, index));
    const pt = points[idx];
    
    const maxVal = maxValCalculated || (Math.max(50, ...points.map(p => Math.max(p.joins, p.leaves))) * 1.15);
    const width = 1000;
    const height = 200;
    const padding = 20;
    
    const getX = (i) => padding + (i / (points.length - 1)) * (width - 2 * padding);
    const getY = (val) => height - (val / maxVal) * (height - 30);

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
    }
    if (dotJoins) {
        dotJoins.setAttribute('cx', cx);
        dotJoins.setAttribute('cy', cyJoins);
    }
    if (dotLeaves) {
        dotLeaves.setAttribute('cx', cx);
        dotLeaves.setAttribute('cy', cyLeaves);
        dotLeaves.style.display = 'block';
    }

    if (ttDate) ttDate.innerText = pt.fullDate || pt.date;
    if (ttJoins) ttJoins.innerText = `${pt.joins} Real Invites`;
    if (ttLeaves) ttLeaves.innerText = `${pt.leaves} leaves`;
    if (leavesWrapper) leavesWrapper.style.display = 'flex';

    if (tooltipBox) {
        const pct = (idx / (points.length - 1)) * 75 + 10;
        tooltipBox.style.left = `${pct}%`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
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
    const embedDescEl = document.getElementById('invitetracker-embed-desc');
    const embedColorEl = document.getElementById('invitetracker-color-hex') || document.getElementById('invitetracker-embed-color-picker');
    const embedCheck = document.getElementById('invitetracker-embed-enable');
    
    const text = textEl ? textEl.value : '%member_mention% has been invited by %inviter% and has now %inviter_invites% invites.';
    const title = embedTitleEl ? embedTitleEl.value : '✨ Member Joined via Invite';
    const desc = embedDescEl ? embedDescEl.value : 'User %member_mention% joined using invite code veyra-vip.';
    const color = embedColorEl ? embedColorEl.value : '#a855f7';

    const simOuter = document.getElementById('invitetracker-sim-outer');
    if (simOuter) {
        simOuter.innerHTML = text
            .replace('%member_mention%', '<span style="color: #5865F2; background: rgba(88,101,242,0.15); padding: 1px 4px; border-radius: 3px; font-weight: 600;">@!! DADDY</span>')
            .replace('%inviter%', '<b>itzarun170</b>')
            .replace('%inviter_invites%', '<b>14</b>');
    }

    const simEmbed = document.getElementById('invitetracker-sim-embed');
    const simTitle = document.getElementById('invitetracker-sim-title');
    if (simEmbed) {
        simEmbed.style.display = (embedCheck && embedCheck.checked) ? 'block' : 'none';
        simEmbed.style.borderLeftColor = color;
    }
    if (simTitle) simTitle.innerText = title;
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
    const footer = document.getElementById('invitetracker-embed-footer')?.value || '';

    fetch(`/api/settings/invitetracker/${guildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, color, title, description, image, footer, message })
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
            description: descEl ? descEl.value : '',
            color: colorEl ? colorEl.value : '#a855f7',
            image: imageEl ? imageEl.value : '',
            thumbnail: thumbnailEl ? thumbnailEl.value : '',
            footer: footerEl ? footerEl.value : '',
            footer_icon: footerIconEl ? footerIconEl.value : '',
            author_name: authorNameEl ? authorNameEl.value : '',
            author_icon: authorIconEl ? authorIconEl.value : ''
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

function addAutorolePill(roleName, showToastFlag = true) {
    if (!roleName) return;
    const container = document.getElementById('autoroles-pills-container');
    if (!container) return;
    
    const existing = Array.from(container.children).find(el => el.textContent.includes(roleName));
    if (existing) return;

    const div = document.createElement('div');
    div.style.cssText = "background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.82rem; color: #fff; display: flex; align-items: center; gap: 8px;";
    div.innerHTML = `
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #94a3b8;"></span>
        <span class="role-pill-name">${roleName}</span>
        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="this.parentElement.remove()"></i>
    `;
    container.appendChild(div);
    if (showToastFlag) showToast("Role Added", `Added @${roleName} to autoroles queue.`);
}

function addStickyBlacklistPill(roleName, showToastFlag = true) {
    if (!roleName) return;
    const container = document.getElementById('sticky-blacklisted-pills');
    if (!container) return;
    
    const existing = Array.from(container.children).find(el => el.textContent.includes(roleName));
    if (existing) return;

    const div = document.createElement('div');
    div.style.cssText = "background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.82rem; color: #fff; display: flex; align-items: center; gap: 8px;";
    div.innerHTML = `
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #94a3b8;"></span>
        <span class="role-pill-name">${roleName}</span>
        <i class="fas fa-times" style="cursor: pointer; font-size: 0.75rem; color: #94a3b8;" onclick="this.parentElement.remove()"></i>
    `;
    container.appendChild(div);
    if (showToastFlag) showToast("Role Blacklisted", `Blacklisted @${roleName} from sticky role restoration.`);
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
    const roles = Array.from(container.querySelectorAll('.role-pill-name')).map(el => el.textContent.trim());

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
    const blacklisted_roles = Array.from(container.querySelectorAll('.role-pill-name')).map(el => el.textContent.trim());

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

function createNewStickyMessagePrompt() {
    const channel = prompt("Enter channel name (e.g. general):", "general");
    if (!channel) return;
    const msg = prompt("Enter sticky message text:", "⚡ Read rules before opening a ticket!");
    if (!msg) return;

    fetch(`/api/settings/stickymessages/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, message: msg })
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
                        <td style="padding: 12px; font-family: var(--font-mono); font-size: 0.8rem; color: #a855f7;">${g.guild_id}</td>
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

    if (frequency === 'monthly') {
        monthlyBtn.className = 'btn-primary';
        monthlyBtn.style.background = '#00aff4';
        monthlyBtn.style.border = 'none';
        monthlyBtn.style.color = '#fff';

        weeklyBtn.className = 'btn-secondary';
        weeklyBtn.style.background = 'transparent';
        weeklyBtn.style.border = '1.5px solid rgba(255,255,255,0.1)';
        weeklyBtn.style.color = '#fff';

        if (showToastFlag) showToast('Reports Settings', 'Monthly schedule selected.');
    } else if (frequency === 'weekly') {
        weeklyBtn.className = 'btn-primary';
        weeklyBtn.style.background = '#00aff4';
        weeklyBtn.style.border = 'none';
        weeklyBtn.style.color = '#fff';

        monthlyBtn.className = 'btn-secondary';
        monthlyBtn.style.background = 'transparent';
        monthlyBtn.style.border = '1.5px solid rgba(255,255,255,0.1)';
        monthlyBtn.style.color = '#fff';

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
    if (!activeGuildId) return;
    
    const settings = {
        enabled: 1,
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
        <td style="padding: 10px 5px; color: #a855f7; font-weight: 700;">${level}</td>
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
    div.style.cssText = "background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.82rem; color: #fff; display: flex; align-items: center; gap: 8px;";
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
            <td style="padding: 10px 5px; color: #a855f7; font-weight: 700;">${r.level}</td>
            <td style="padding: 10px 5px;">
                <button type="button" onclick="this.closest('tr').remove();" style="background: #ef4444; border: none; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;"><i class="fas fa-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

window.loadReportsSettings = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;

    fetch(`/api/settings/reports/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const toggle = document.getElementById('reports-enable-checkbox');
            if (toggle) toggle.checked = data.enabled === 1;

            const channelSelect = document.getElementById('reports-channel-select');
            if (channelSelect) channelSelect.value = data.channel || '';

            selectReportFrequency(data.frequency || 'monthly', false);
        })
        .catch(err => console.error("Error loading reports settings:", err));
};

window.saveReportsSettings = function() {
    if (!activeGuildId) return;

    const enabled = document.getElementById('reports-enable-checkbox')?.checked ? 1 : 0;
    const channel = document.getElementById('reports-channel-select')?.value || 'general';
    const weeklyBtn = document.getElementById('report-freq-weekly');
    const frequency = weeklyBtn && weeklyBtn.classList.contains('btn-primary') ? 'weekly' : 'monthly';

    fetch(`/api/settings/reports/${activeGuildId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, channel, frequency })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Reports Settings Saved", "Server Reports configurations successfully saved!");
            addLogEntry("@user", `Updated Server Reports: status ${enabled ? 'Enabled' : 'Disabled'}, channel #${channel}, frequency ${frequency}`);
        }
    })
    .catch(err => console.error("Error saving reports settings:", err));
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
window.openWhitelistModal = function(type) {
    const targetGuild = activeGuildId;
    if (!targetGuild) return;
    
    let modal = document.getElementById('whitelist-interactive-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'whitelist-interactive-modal';
        modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.85); z-index:1000000; display:flex; align-items:center; justify-content:center; padding:20px;';
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    
    function refresh() {
        fetch(`/api/whitelist/${targetGuild}`)
            .then(res => res.json())
            .then(data => {
                const filtered = data.filter(item => item.type.toLowerCase() === type.toLowerCase());
                modal.innerHTML = `
                    <div class="glass-card" style="width:100%; max-width:480px; background:#050508; border:1px solid rgba(57, 255, 20, 0.2); padding:30px; border-radius:16px; position:relative; box-shadow: 0 20px 50px rgba(0,0,0,0.9);">
                        <button onclick="document.getElementById('whitelist-interactive-modal').style.display='none'" style="position:absolute; top:20px; right:20px; background:transparent; border:none; color:var(--text-secondary); cursor:pointer; font-size:1.2rem;"><i class="fas fa-times"></i></button>
                        <h3 style="color:#39FF14; font-size:1.25rem; font-weight:800; text-transform:uppercase; margin-bottom:15px;">Whitelisted ${type}s</h3>
                        <p style="color:var(--text-secondary); font-size:0.8rem; margin-bottom:20px;">Manage whitelisted ${type.toLowerCase()} bypass privileges.</p>
                        
                        <div style="display:flex; gap:10px; margin-bottom:20px;">
                            <input type="text" id="w-modal-input" placeholder="Enter ${type} ID..." style="flex:1; background:rgba(0,0,0,0.4); border:1px solid rgba(57, 255, 20, 0.15); border-radius:6px; padding:10px; color:#fff; font-size:0.85rem; outline:none;">
                            <button onclick="addWModalItem('${type}')" class="btn-primary" style="background:#39FF14; border:none; padding:10px 16px; border-radius:6px; font-weight:700; color:#000; cursor:pointer;">Add</button>
                        </div>
                        
                        <div style="max-height:220px; overflow-y:auto; border:1px solid rgba(255,255,255,0.03); border-radius:6px; background:rgba(0,0,0,0.15);">
                            <ul id="w-modal-list" style="list-style:none; padding:0; margin:0;">
                                ${filtered.length === 0 ? `<li style="padding:15px; text-align:center; color:var(--text-secondary); font-size:0.82rem;">No whitelisted ${type.toLowerCase()}s found.</li>` : filtered.map(item => `
                                    <li style="padding:10px 14px; border-bottom:1px solid rgba(255,255,255,0.02); display:flex; justify-content:space-between; align-items:center;">
                                        <span style="color:#fff; font-size:0.82rem; font-family:var(--font-mono);">${item.id}</span>
                                        <button onclick="deleteWModalItem('${item.id}', '${type}')" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--text-secondary)'"><i class="fas fa-trash"></i></button>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            });
    }
    
    window.addWModalItem = function(t) {
        const val = document.getElementById('w-modal-input').value.trim();
        if (!val) return showToast("Error", "Please enter an ID.");
        fetch(`/api/whitelist/${targetGuild}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: val, type: t, reason: 'Added via Dashboard Whitelist Modal' })
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                showToast("Success", `${t} whitelisted successfully.`);
                refresh();
            } else {
                showToast("Error", res.error || "Failed to whitelist.");
            }
        });
    };
    
    window.deleteWModalItem = function(id, t) {
        fetch(`/api/whitelist/${targetGuild}/${id}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast("Success", "Removed from whitelist.");
                    refresh();
                } else {
                    showToast("Error", "Failed to remove.");
                }
            });
    };
    
    refresh();
};

window.loadWhitelist = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    fetch(`/api/whitelist/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const capacityEl = document.getElementById('overview-whitelist-capacity');
            if (capacityEl) {
                capacityEl.innerText = `${data.length} / 100`;
            }
        })
        .catch(err => console.error("Error loading whitelist capacity:", err));
};

// Moderation overrides logic
window.loadModerationOverrides = function(guildId) {
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    fetch(`/api/settings/moderation/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const listEl = document.getElementById('moderation-overrides-list');
            if (!listEl) return;
            if (data.length === 0) {
                listEl.innerHTML = '<li style="padding:15px; text-align:center; color:var(--text-secondary);">No moderation overrides configured.</li>';
                return;
            }
            listEl.innerHTML = data.map(item => `
                <li style="padding:12px; border-bottom:1px solid rgba(255,255,255,0.02); display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong style="color:#fff;">${item.user_id}</strong>
                        <span style="font-size:0.75rem; color:var(--text-secondary); margin-left:10px;">${item.reason}</span>
                    </div>
                    <button onclick="deleteModerationOverride('${item.user_id}')" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--text-secondary)'">
                        <i class="fas fa-trash"></i>
                    </button>
                </li>
            `).join('');
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
    const targetGuild = guildId || activeGuildId;
    if (!targetGuild) return;
    
    // Dynamically show/hide premium lock block
    const isPremium = (window.currentServerPlan === 'Pro' || window.currentServerPlan === 'Premium');
    const lockContainer = document.getElementById('antispam-lock-container');
    const settingsContainer = document.getElementById('antispam-settings-container');
    if (isPremium) {
        if (lockContainer) lockContainer.style.display = 'none';
        if (settingsContainer) settingsContainer.style.display = 'block';
    } else {
        if (lockContainer) lockContainer.style.display = 'block';
        if (settingsContainer) settingsContainer.style.display = 'none';
    }

    fetch(`/api/settings/${targetGuild}`)
        .then(res => res.json())
        .then(data => {
            const disabledCmds = data.disabled_commands || [];
            
            const linksChecked = !disabledCmds.includes('antispam-links');
            const mentionsChecked = !disabledCmds.includes('antispam-mentions');
            const invitesChecked = !disabledCmds.includes('antispam-invites');
            
            const chkLinks = document.getElementById('antispam-enable-links');
            const chkMentions = document.getElementById('antispam-enable-mentions');
            const chkInvites = document.getElementById('antispam-enable-invites');
            
            if (chkLinks) chkLinks.checked = linksChecked;
            if (chkMentions) chkMentions.checked = mentionsChecked;
            if (chkInvites) chkInvites.checked = invitesChecked;
        })
        .catch(err => console.error("Error loading anti-spam settings:", err));
};

window.saveAntiSpamSettings = function() {
    if (!activeGuildId) return;
    
    fetch(`/api/settings/${activeGuildId}`)
        .then(res => res.json())
        .then(data => {
            let disabledCmds = data.disabled_commands || [];
            
            const chkLinks = document.getElementById('antispam-enable-links');
            const chkMentions = document.getElementById('antispam-enable-mentions');
            const chkInvites = document.getElementById('antispam-enable-invites');
            
            const linksActive = chkLinks ? chkLinks.checked : true;
            const mentionsActive = chkMentions ? chkMentions.checked : true;
            const invitesActive = chkInvites ? chkInvites.checked : true;
            
            const setCommandStatus = (cmdName, isActive) => {
                if (isActive) {
                    disabledCmds = disabledCmds.filter(name => name !== cmdName);
                } else {
                    if (!disabledCmds.includes(cmdName)) {
                        disabledCmds.push(cmdName);
                    }
                }
            };
            
            setCommandStatus('antispam-links', linksActive);
            setCommandStatus('antispam-mentions', mentionsActive);
            setCommandStatus('antispam-invites', invitesActive);
            
            fetch(`/api/settings/commands/${activeGuildId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ disabled_commands: disabledCmds })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast("Success", "Anti-Spam matrix filters updated successfully.");
                } else {
                    showToast("Error", "Failed to update Anti-Spam settings.");
                }
            })
            .catch(err => console.error("Error saving anti-spam settings:", err));
        });
};

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
                    const capacityEl = document.getElementById('overview-whitelist-capacity');
                    if (capacityEl) capacityEl.innerText = `${wl.length} / 100`;
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
        description: 'This is a multi-embed message dispatched live to Discord channels.\nYou can add up to 10 embeds in a single message!',
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

function renderMultiEmbedCardsUI() {
    const container = document.getElementById('ebm-cards-container');
    if (!container) return;
    
    let html = '';
    window.multiEmbedsState.forEach((emb, idx) => {
        html += `
        <div class="glass-card multi-embed-card" style="background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid ${emb.color || '#a855f7'}; border-radius: 8px; padding: 18px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 8px;">
                <span style="font-weight: 700; color: #fff; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-layer-group" style="color: ${emb.color || '#a855f7'};"></i> Embed #${idx + 1}
                </span>
                ${window.multiEmbedsState.length > 1 ? `
                <button type="button" onclick="removeMultiEmbedCard(${idx})" class="btn-primary" style="background: #ef4444; border: none; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer;">
                    <i class="fas fa-trash-can"></i> Remove
                </button>` : ''}
            </div>

            <!-- Color picker -->
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 0.8rem; color: var(--text-secondary); font-weight: 600;">Embed Color:</span>
                <input type="color" value="${emb.color || '#a855f7'}" oninput="updateMultiEmbedState(${idx}, 'color', this.value)" style="width: 35px; height: 28px; border: none; background: transparent; cursor: pointer;">
                <input type="text" value="${emb.color || '#a855f7'}" class="form-control" style="width: 100px; background: rgba(0,0,0,0.3); font-family: var(--font-mono); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'color', this.value)">
            </div>

            <!-- Author info -->
            <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: 10px; margin-bottom: 10px;">
                <input type="text" placeholder="Author Icon URL" value="${escapeHtml(emb.author_icon || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'author_icon', this.value)">
                <input type="text" placeholder="Author Name" value="${escapeHtml(emb.author_name || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'author_name', this.value)">
            </div>

            <!-- Title & Description -->
            <div style="margin-bottom: 10px;">
                <input type="text" placeholder="Embed Title" value="${escapeHtml(emb.title || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.82rem; font-weight: 700; margin-bottom: 8px;" oninput="updateMultiEmbedState(${idx}, 'title', this.value)">
                <textarea placeholder="Embed Description" class="form-control" style="height: 80px; background: rgba(0,0,0,0.2); font-family: var(--font-mono); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'description', this.value)">${escapeHtml(emb.description || '')}</textarea>
            </div>

            <!-- Image & Thumbnail -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <input type="text" placeholder="Image URL (large)" value="${escapeHtml(emb.image || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'image', this.value)">
                <input type="text" placeholder="Thumbnail URL (small)" value="${escapeHtml(emb.thumbnail || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'thumbnail', this.value)">
            </div>

            <!-- Footer -->
            <div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 10px; margin-bottom: 10px;">
                <input type="text" placeholder="Footer Text" value="${escapeHtml(emb.footer || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'footer', this.value)">
                <input type="text" placeholder="Footer Icon URL" value="${escapeHtml(emb.footer_icon || '')}" class="form-control" style="background: rgba(0,0,0,0.2); font-size: 0.8rem;" oninput="updateMultiEmbedState(${idx}, 'footer_icon', this.value)">
            </div>

            <!-- Fields Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; margin-bottom: 8px;">
                <span style="font-size: 0.78rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Fields (${(emb.fields || []).length}/25)</span>
                <button type="button" onclick="addMultiEmbedField(${idx})" class="btn-secondary" style="padding: 3px 8px; font-size: 0.72rem; border-radius: 4px;">+ Add Field</button>
            </div>

            <div id="multi-fields-container-${idx}" style="display: flex; flex-direction: column; gap: 8px;">
                ${(emb.fields || []).map((f, fIdx) => `
                <div style="display: flex; gap: 6px; align-items: center;">
                    <input type="text" placeholder="Field Name" value="${escapeHtml(f.name || '')}" class="form-control" style="flex: 1; background: rgba(0,0,0,0.3); font-size: 0.78rem;" oninput="updateMultiEmbedField(${idx}, ${fIdx}, 'name', this.value)">
                    <input type="text" placeholder="Field Value" value="${escapeHtml(f.value || '')}" class="form-control" style="flex: 1.5; background: rgba(0,0,0,0.3); font-size: 0.78rem;" oninput="updateMultiEmbedField(${idx}, ${fIdx}, 'value', this.value)">
                    <label style="font-size: 0.72rem; color: var(--text-secondary); display: flex; align-items: center; gap: 3px; cursor: pointer;">
                        <input type="checkbox" ${f.inline ? 'checked' : ''} onchange="updateMultiEmbedField(${idx}, ${fIdx}, 'inline', this.checked)"> Inline
                    </label>
                    <button type="button" onclick="removeMultiEmbedField(${idx}, ${fIdx})" style="background: transparent; border: none; color: #ef4444; cursor: pointer; padding: 2px 4px;"><i class="fas fa-times"></i></button>
                </div>
                `).join('')}
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
        title: `♡ EMBED MESSAGE #${newIdx} ♡`,
        description: `Additional embed layer #${newIdx} in the same message payload.`,
        image: '',
        thumbnail: '',
        footer: '✦ VEYRA DISCORD BOT ✦',
        footer_icon: '',
        fields: []
    });
    renderMultiEmbedCardsUI();
    showToast("Embed Added", `Embed #${newIdx} added to the message payload.`);
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
    if (normalText) {
        html += `<div style="color: #dcddde; font-size: 0.9rem; margin-bottom: 10px; white-space: pre-wrap;">${escapeHtml(normalText)}</div>`;
    }

    window.multiEmbedsState.forEach((emb, idx) => {
        const borderCol = emb.color || '#a855f7';
        html += `
        <div style="background: #2f3136; border-left: 4px solid ${borderCol}; border-radius: 4px; padding: 14px; margin-bottom: 10px; max-width: 520px; display: flex; flex-direction: column; gap: 8px;">
            ${emb.author_name ? `
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.8rem; font-weight: 700; color: #fff;">
                ${emb.author_icon ? `<img src="${escapeHtml(emb.author_icon)}" style="width: 20px; height: 20px; border-radius: 50%; object-fit: cover;">` : ''}
                <span>${escapeHtml(emb.author_name)}</span>
            </div>` : ''}

            <div style="display: flex; justify-content: space-between; gap: 10px;">
                <div style="flex: 1;">
                    ${emb.title ? `<div style="font-size: 0.95rem; font-weight: 700; color: #fff; margin-bottom: 6px;">${escapeHtml(emb.title)}</div>` : ''}
                    ${emb.description ? `<div style="font-size: 0.85rem; color: #dbdee1; white-space: pre-wrap; line-height: 1.4;">${escapeHtml(emb.description)}</div>` : ''}
                </div>
                ${emb.thumbnail ? `
                <div style="width: 60px; height: 60px; border-radius: 6px; overflow: hidden; flex-shrink: 0;">
                    <img src="${escapeHtml(emb.thumbnail)}" style="width: 100%; height: 100%; object-fit: cover;">
                </div>` : ''}
            </div>

            ${(emb.fields && emb.fields.length > 0) ? `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-top: 6px;">
                ${emb.fields.map(f => `
                <div style="${f.inline ? '' : 'grid-column: 1 / -1;'}">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #b9bbbe;">${escapeHtml(f.name || '')}</div>
                    <div style="font-size: 0.8rem; color: #dcddde;">${escapeHtml(f.value || '')}</div>
                </div>
                `).join('')}
            </div>` : ''}

            ${emb.image ? `
            <div style="width: 100%; border-radius: 4px; overflow: hidden; margin-top: 6px;">
                <img src="${escapeHtml(emb.image)}" style="width: 100%; max-height: 220px; object-fit: cover; display: block;">
            </div>` : ''}

            ${emb.footer ? `
            <div style="display: flex; align-items: center; gap: 6px; font-size: 0.72rem; color: #a3a6aa; margin-top: 4px;">
                ${emb.footer_icon ? `<img src="${escapeHtml(emb.footer_icon)}" style="width: 16px; height: 16px; border-radius: 50%;">` : ''}
                <span>${escapeHtml(emb.footer)}</span>
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
        const indicator = document.getElementById('bot-status-indicator');
        if (indicator) {
            indicator.innerHTML = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981; margin-right:6px; animation: pulse 2s infinite;"></span> VEYRA Online (${data.latency_ms || 12}ms)`;
        }

        const latencyEls = document.querySelectorAll('.diagnostic-latency, #diagnostic-latency-val');
        latencyEls.forEach(el => {
            el.innerText = `${data.latency_ms || 12}ms`;
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
                <td style="font-weight: 700; color: #a855f7;">${escapeHtml(log.user || 'VEYRA')}</td>
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

        // 3. Update security status card if threat or action detected
        const secDesc = document.getElementById('overview-security-desc');
        if (secDesc && log.action) {
            secDesc.innerText = `Latest: ${log.action} (${log.user})`;
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

                const secStatus = document.getElementById('overview-security-status');
                if (secStatus) secStatus.innerText = 'SAFE';
            }
        } catch (e) {}
    }

    setInterval(pollBotTelemetry, 4000);
    pollBotTelemetry();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', connectSSE);
    } else {
        connectSSE();
    }
})();
