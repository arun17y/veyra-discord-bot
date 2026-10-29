const { Pool } = require('pg');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_QyNVAknl8BZ6@ep-floral-mouse-artqhsoc-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require',
  ssl: { rejectUnauthorized: false }
});

async function migrate() {
  try {
    await pool.query('ALTER TABLE sticky_messages ADD COLUMN IF NOT EXISTS channel_name TEXT;');
    console.log('Added channel_name to sticky_messages in Neon PG');
    await pool.query("ALTER TABLE verification_settings ADD COLUMN IF NOT EXISTS button_emoji TEXT DEFAULT '✅';");
    console.log('Added button_emoji to verification_settings in Neon PG');
  } catch (err) {
    console.error('Migration error:', err.message);
  } finally {
    await pool.end();
  }
}
migrate();
