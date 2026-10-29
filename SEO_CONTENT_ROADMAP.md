# Veyra Discord Bot — SEO Content Strategy & Editorial Roadmap

**Target Domain**: `https://veyra-bot.vercel.app/`  
**Focus**: Organic Search Acquisition, Knowledge Base Expansion & High-Intent Guide Deployment  

---

## 1. Editorial Vision & Quality Guidelines

To establish Veyra as an authoritative, high-ranking brand for Discord communities, content must be **accurate, human-crafted, technically rigorous, and directly tied to verified bot functionality**.

### Quality Rules:
1. **Zero Thin Content**: Every article must solve a complete user problem with concrete step-by-step instructions and real Discord command examples.
2. **Verified Product Truth**: Never claim features that do not exist in the Veyra codebase.
3. **No Keyword Stuffing**: Integrate keywords naturally into H2/H3 headings and instructive prose.
4. **Internal Cross-Linking**: Every guide must link directly to the relevant dashboard settings pane (`/manage`), command directory (`/commands`), or ticket showcase (`/ticket`).

---

## 2. Priority Editorial Roadmap (Top 10 High-Intent Guides)

### Guide 1: How to Set Up Veyra on a Discord Server (Complete 2026 Onboarding Guide)
- **Target Keywords**: `how to add a bot to discord`, `how to setup a discord bot`, `veyra setup guide`, `discord bot setup tutorial`
- **Search Intent**: Informational / Educational (Beginner)
- **Target URL**: `/docs/getting-started/` or `/about#pane-docs`
- **Required Product Facts**:
  - Official Discord OAuth2 authorization URL (`client_id=1527243189860175933`).
  - Required Discord permissions: Administrator (Permission integer 8).
  - Role hierarchy rule: The `Veyra` bot role must sit above the roles it manages in Server Settings > Roles.
  - Initial configuration commands: `/quicksetup`, `/settings`, `,prefix`.

---

### Guide 2: How to Configure Discord Anti-Nuke Protection & Sub-Second Reverts
- **Target Keywords**: `how to setup discord anti nuke`, `discord anti-nuke bot`, `best discord anti nuke bot`, `discord mass ban protection`, `discord server defense bot`
- **Search Intent**: Commercial / High Value
- **Target URL**: `/docs/security/` or `/about#pane-security`
- **Required Product Facts**:
  - Modules active: Anti-Ban, Anti-Kick, Anti-Channel Delete, Anti-Role Delete, Anti-Bot Add, Anti-Webhook Create.
  - Action limits & threshold triggers (e.g. max 3 bans per 10 seconds).
  - Punishment types: Quarantining staff roles, instant ban of rogue administrator, or kick.
  - Sub-second restore: Channel and role permission reconstruction from memory cache.
  - BeastMode: Pro-tier automated lockdown during sustained mass API attacks.

---

### Guide 3: How to Build an Interactive Discord Ticket System with Buttons
- **Target Keywords**: `how to setup discord tickets`, `discord ticket bot`, `discord ticket panel bot`, `discord ticket setup guide`, `discord ticket transcript system`
- **Search Intent**: Commercial / Educational
- **Target URL**: `/docs/tickets/` or `/ticket`
- **Required Product Facts**:
  - Slash command: `/ticket-setup` deploying custom embed panel.
  - Interactive UI: Button clicks generate private ticket channels under configured category.
  - Staff controls: Claim (`/ticket-add`), Transfer, Close (`/ticket-close`), and Reopen.
  - HTML Transcripts: Auto-archived to SQLite/Postgres with private web transcript viewer.

---

### Guide 4: How to Configure Discord Member Verification & Captcha Gates
- **Target Keywords**: `how to setup discord verification`, `discord verification bot`, `discord verify role bot`, `discord member verification setup`, `discord onboarding bot`
- **Search Intent**: Informational / Security
- **Target URL**: `/docs/verification/` or `/about#pane-security`
- **Required Product Facts**:
  - Gating mechanism: Unverified members assigned `@Unverified` role on join.
  - Verification types: 1-Click Button (`UnifiedVerificationButtonView`) or Captcha challenge.
  - Role transition: Automatically removes `@Unverified` and grants designated `@Verified` / `@Member` role.
  - Web dashboard preview: Real-time customization of verification embed text, banner, and color.

---

### Guide 5: How to Configure Custom Welcome & Exit Embed Messages
- **Target Keywords**: `how to setup welcome messages on discord`, `discord welcome bot`, `discord welcome embed bot`, `discord custom welcome messages`
- **Search Intent**: Informational / Community
- **Target URL**: `/docs/welcome/`
- **Required Product Facts**:
  - Available placeholders: `{user}`, `{username}`, `{mention}`, `{server}`, `{membercount}`.
  - Embed customizer: Custom title, description, color hex, thumbnail avatar, and background image.
  - Multi-channel routing: Separate channels for public greetings and private DM notifications.

---

### Guide 6: How Discord Moderation Permissions & Role Hierarchy Work
- **Target Keywords**: `discord moderation tools`, `discord moderation commands`, `discord staff tools`, `discord role management system`
- **Search Intent**: Educational / Informational
- **Target URL**: `/docs/moderation/`
- **Required Product Facts**:
  - Discord permission hierarchy: Bot cannot moderate members whose highest role is higher or equal to Veyra.
  - Built-in commands: `/ban`, `/kick`, `/timeout`, `/warn`, `/slowmode-all`, `/lock-all`, `/emergency-lockdown`.
  - Infraction history: Persistent logging of strikes and warnings per user.

---

### Guide 7: How to Set Up Discord Autoroles & Persistent Sticky Roles
- **Target Keywords**: `how to configure discord autoroles`, `discord autorole bot`, `discord sticky roles bot`, `discord persistent roles bot`
- **Search Intent**: Informational / Utility
- **Target URL**: `/docs/roles/`
- **Required Product Facts**:
  - Autorole: Automatically assigned to new joining members or bots (`/autorole-add`).
  - Sticky Roles: Restores roles to members who leave and rejoin to bypass mutes or rank loss (`/stickyrole-enable`).

---

### Guide 8: How to Run Server Giveaways with Veyra
- **Target Keywords**: `discord giveaway bot`, `discord giveaway command`, `discord giveaway setup`, `discord giveaway reroll bot`
- **Search Intent**: Community / Engagement
- **Target URL**: `/docs/giveaways/`
- **Required Product Facts**:
  - Setup: `/giveaway-start [duration] [winners] [prize]`.
  - Interactive entry: One-click button entry tracked in database (`giveaway_entries`).
  - End & Reroll: `/giveaway-end` and `/giveaway-reroll`.

---

### Guide 9: How to Set Up Temporary Voice Channels (TempVoice / VoiceMaster)
- **Target Keywords**: `discord temporary voice channel bot`, `discord voice channel management`, `discord VoiceMaster bot`, `discord voice channel creator`
- **Search Intent**: Utility / Community
- **Target URL**: `/docs/voice/`
- **Required Product Facts**:
  - Join-to-Create: Joining the trigger channel creates a private dynamic voice lounge.
  - Interactive TempVoice Interface:
    - Row 1: Name, Limit, Privacy, Waiting Room, Chat.
    - Row 2: Trust, Untrust, Invite, Kick, Region.
    - Row 3: Block, Unblock, Claim, Transfer, Delete.
  - Auto-cleanup: Channels automatically delete as soon as the last member leaves.

---

### Guide 10: Veyra Free vs Pro vs Premium: Which Plan Does Your Server Need?
- **Target Keywords**: `discord bot premium`, `discord bot pricing`, `discord bot pro plan`, `affordable discord bot`, `veyra bot pricing`
- **Search Intent**: Commercial Investigation / Transactional
- **Target URL**: `/premium`
- **Required Product Facts**:
  - Free Plan: Unlimited core Anti-Nuke, verification button, support tickets, 160+ moderation commands.
  - Pro Plan (₹199 / month): BeastMode continuous defense, emergency lockdown commands, role automation, priority webhook streaming.
  - Premium Plan: Unlimited server snapshots, 24/7 lossless voice stay, white-label custom bot branding.

---

## 3. SEO Content Publishing Checklist

Before any article is published:
- [ ] Validated against live bot code in `bot/` and `web/server.js`.
- [ ] Unique title and meta description targeted to the primary intent.
- [ ] Heading hierarchy: Exactly one `<h1>`, structured `<h2>` and `<h3>` tags.
- [ ] Code blocks specify exact syntax (`/command [arg]`).
- [ ] Clear callout alerts for common permission pitfalls (e.g. role hierarchy).
- [ ] Added to `web/public/sitemap.xml` with appropriate canonical URL.
