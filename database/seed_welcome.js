const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'VEYRA.db');
const db = new sqlite3.Database(DB_PATH);

const welcomeDesc = [
    "Hey **{user}**, welcome to **{server}**! \uD83C\uDF89",
    "",
    "We're glad to have you here. Take a moment to check out the server rules and explore the available channels.",
    "",
    "\uD83D\uDCDC **Read the rules** before chatting",
    "\uD83D\uDCAC **Introduce yourself** and meet the community",
    "\uD83D\uDCE2 **Stay updated** with announcements",
    "\uD83C\uDFAB **Need help?** Contact the support team",
    "",
    "\u2728 Have fun, stay respectful, and enjoy your time here!"
].join('\n');

const guildIds = ['1509911679637520584', '1234567890', '9876543210'];

db.serialize(() => {
    const stmt = db.prepare(`INSERT OR REPLACE INTO welcome_settings 
        (guild_id, enabled, channel, color, title, description, image, thumbnail, footer, author_name, author_icon, footer_icon, message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);

    // Update all existing rows that have blank/old title values
    db.all("SELECT guild_id, title FROM welcome_settings", [], (err, rows) => {
        if (!err && rows) {
            rows.forEach(row => {
                const oldTitles = ['', 'WELCOME TO VEYRA ALL-IN-ONE SECURITY BOT', null, undefined];
                const needsUpdate = !row.title || oldTitles.some(t => row.title && row.title.includes('WELCOME TO VEYRA'));
                if (needsUpdate) {
                    stmt.run(
                        row.guild_id, 1, 'welcome', '#a855f7',
                        '\uD83D\uDC4B Welcome to the Server!', welcomeDesc,
                        '', '', '\u2726 THANKS FOR JOINING \u2726', '', '', '', '',
                        function(e) {
                            if (e) console.error('Error updating', row.guild_id, e.message);
                            else console.log('Updated welcome settings for guild:', row.guild_id);
                        }
                    );
                } else {
                    console.log('Skipped (already customised):', row.guild_id, '|', row.title);
                }
            });
        }

        // Ensure the primary guild always gets the default seeded
        stmt.run(
            '1509911679637520584', 1, 'welcome', '#a855f7',
            '\uD83D\uDC4B Welcome to the Server!', welcomeDesc,
            '', '', '\u2726 THANKS FOR JOINING \u2726', '', '', '', '',
            function(e) {
                if (e) console.error('Error seeding primary guild:', e.message);
                else console.log('Seeded welcome embed template for primary guild.');
                stmt.finalize();
                db.close();
            }
        );
    });
});
