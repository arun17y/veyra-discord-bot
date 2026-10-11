const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const DB_PATH = path.join(__dirname, 'VEYRA.db');
const db = new sqlite3.Database(DB_PATH);

const GUILD_ID = '1509911679637520584';

const leaveDesc = [
    "**{user}** has left **{server}**.",
    "",
    "We're sorry to see you go. \uD83D\uDE22",
    "Thanks for being part of the community, and we hope to see you again someday!",
    "",
    "\uD83D\uDC65 **Members now:** {member_count}"
].join('\n');

const joinDmDesc = [
    "Hey **{user}**, thanks for joining **{server}**! \uD83C\uDF89",
    "",
    "We're happy to have you here. Make sure to check out the server rules and explore the available channels.",
    "",
    "\uD83D\uDCDC Read the rules",
    "\uD83D\uDCAC Meet the community",
    "\uD83D\uDCE2 Stay updated with announcements",
    "\uD83C\uDFAB Need help? Contact the support team",
    "",
    "\u2728 **Enjoy your stay!**"
].join('\n');

const inviteDesc = [
    "\uD83D\uDC64 **Inviter:** {inviter}",
    "\uD83D\uDC4B **New Member:** {user}",
    "",
    "\uD83D\uDCC8 **Invite Count:** `{invites}`",
    "\uD83C\uDFAF **Total Invites:** `{total_invites}`",
    "",
    "Thanks for helping grow our community! \uD83D\uDE80"
].join('\n');

db.serialize(() => {
    // Seed leave_settings
    db.run(
        `INSERT OR REPLACE INTO leave_settings (guild_id, enabled, channel, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon, message)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [GUILD_ID, 1, 'general', '#ef4444', '\uD83D\uDC4B Goodbye!', leaveDesc, '', '', '\u2726 SEE YOU SOON \u2726', '', '', '', ''],
        (err) => { if (err) console.error('leave_settings error:', err.message); else console.log('\u2705 leave_settings seeded'); }
    );

    // Seed joindm_settings (cols: guild_id, enabled, channel, color, title, description, image, footer, message)
    db.run(
        `INSERT OR REPLACE INTO joindm_settings (guild_id, enabled, channel, color, title, description, image, footer, message)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [GUILD_ID, 1, 'dm', '#a855f7', '\uD83D\uDC4B Welcome!', joinDmDesc, '', '\u2726 THANKS FOR JOINING \u2726', ''],
        (err) => { if (err) console.error('joindm_settings error:', err.message); else console.log('\u2705 joindm_settings seeded'); }
    );

    // Seed invitetracker_settings (cols: guild_id, enabled, channel, message, embed_json, color, title, description, image, footer)
    db.run(
        `INSERT OR REPLACE INTO invitetracker_settings (guild_id, enabled, channel, message, embed_json, color, title, description, image, footer)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [GUILD_ID, 1, 'general', '', '', '#a855f7', '\uD83C\uDF89 Invite Tracked!', inviteDesc, '', '\u2726 VEYRA INVITE TRACKER \u2726'],
        (err) => { if (err) console.error('invitetracker_settings error:', err.message); else console.log('\u2705 invitetracker_settings seeded'); }
    );

    setTimeout(() => db.close(), 500);
});
