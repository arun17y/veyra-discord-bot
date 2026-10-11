const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const db = new sqlite3.Database(path.join(__dirname, 'VEYRA.db'));

db.all("PRAGMA table_info(joindm_settings)", (e, rows) => {
    console.log('joindm cols:', rows ? rows.map(r => r.name) : 'error: ' + (e && e.message));
    db.all("PRAGMA table_info(invitetracker_settings)", (e2, r2) => {
        console.log('invitetracker cols:', r2 ? r2.map(r => r.name) : 'error: ' + (e2 && e2.message));
        db.close();
    });
});
