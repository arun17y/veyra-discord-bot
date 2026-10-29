const { Pool } = require('pg');
const pool = new Pool({
  connectionString: 'postgresql://neondb_owner:npg_QyNVAknl8BZ6@ep-floral-mouse-artqhsoc-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require',
  ssl: { rejectUnauthorized: false }
});

async function fixAllIdSequences() {
  try {
    const res = await pool.query(`
      SELECT table_name, column_name, data_type, column_default
      FROM information_schema.columns
      WHERE column_name = 'id' AND table_schema = 'public';
    `);
    
    for (const row of res.rows) {
      if (!row.column_default) {
        console.log(`Table ${row.table_name} has column 'id' with no default. Adding sequence...`);
        const seqName = `${row.table_name}_id_seq`;
        await pool.query(`
          CREATE SEQUENCE IF NOT EXISTS "${seqName}";
          ALTER TABLE "${row.table_name}" ALTER COLUMN id SET DEFAULT nextval('"${seqName}"');
        `);
        console.log(`Fixed ${row.table_name}.id -> default nextval('${seqName}')`);
      }
    }
    console.log('All id sequences checked and fixed.');
  } catch (err) {
    console.error('Error fixing id sequences:', err);
  } finally {
    await pool.end();
  }
}

fixAllIdSequences();
