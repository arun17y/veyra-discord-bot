import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

SQLITE_PATH = os.path.abspath("database/VEYRA.db")
PG_URL = "postgresql://neondb_owner:npg_u16miIQSLZGO@ep-morning-hat-b5421rgl-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"

sqlite_conn = sqlite3.connect(SQLITE_PATH)
s_cur = sqlite_conn.cursor()

pg_conn = psycopg2.connect(PG_URL)
pg_conn.autocommit = True
p_cur = pg_conn.cursor()

s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in s_cur.fetchall()]
print(f"Total tables to migrate: {len(tables)}", flush=True)

type_mapping = {
    'integer': 'BIGINT',
    'int': 'BIGINT',
    'text': 'TEXT',
    'varchar': 'TEXT',
    'real': 'DOUBLE PRECISION',
    'blob': 'BYTEA',
    'numeric': 'NUMERIC',
    'boolean': 'BOOLEAN'
}

for idx, table in enumerate(tables, 1):
    try:
        s_cur.execute(f"PRAGMA table_info({table})")
        cols = s_cur.fetchall()
        if not cols:
            continue
            
        p_cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
        
        col_defs = []
        pk_cols = [c[1] for c in cols if c[5] >= 1]
        
        for col in cols:
            cid, cname, ctype, notnull, dflt, pk = col
            ctype_clean = ctype.lower().split('(')[0].strip() if ctype else 'text'
            pg_type = type_mapping.get(ctype_clean, 'TEXT')
            definition = f'"{cname}" {pg_type}'
            col_defs.append(definition)
            
        if pk_cols:
            pk_str = ", ".join([f'"{pk}"' for pk in pk_cols])
            col_defs.append(f'PRIMARY KEY ({pk_str})')
            
        create_sql = f'CREATE TABLE "{table}" ({", ".join(col_defs)});'
        p_cur.execute(create_sql)
        
        # Copy rows using fast bulk execute_values
        s_cur.execute(f"SELECT * FROM {table}")
        rows = s_cur.fetchall()
        if rows:
            col_names_str = ", ".join([f'"{c[1]}"' for c in cols])
            insert_sql = f'INSERT INTO "{table}" ({col_names_str}) VALUES %s;'
            execute_values(p_cur, insert_sql, rows, page_size=1000)
            print(f"[{idx}/{len(tables)}] {table}: {len(rows)} rows copied.", flush=True)
        else:
            print(f"[{idx}/{len(tables)}] {table}: 0 rows (table ready).", flush=True)
    except Exception as ex:
        print(f"[{idx}/{len(tables)}] Error on {table}: {ex}", flush=True)

try:
    p_cur.execute('CREATE OR REPLACE VIEW audit_histories AS SELECT id, guild_id, action as action_type, timestamp FROM audit_logs;')
    print("audit_histories view created.", flush=True)
except Exception as e:
    print("audit_histories notice:", e, flush=True)

sqlite_conn.close()
pg_conn.close()
print("SUCCESS: Migration to Neon PostgreSQL finished completely!", flush=True)
