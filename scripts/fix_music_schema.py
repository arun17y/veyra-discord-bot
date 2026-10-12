import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "bot"))
import db_adapter

db = db_adapter.get_db()
cursor = db.cursor()

cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'guild_settings'")
cols = [r[0] for r in cursor.fetchall()]
print("Current columns in guild_settings:", cols)

needed_cols = [
    ("volume", "INTEGER DEFAULT 100"),
    ("stay_247", "INTEGER DEFAULT 0"),
    ("stay_voice_id", "TEXT"),
    ("stay_text_id", "TEXT"),
]

for col_name, col_type in needed_cols:
    if col_name not in cols:
        print(f"Adding missing column {col_name} to guild_settings...")
        try:
            cursor.execute(f"ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            db.commit()
            print(f"Successfully added column {col_name}!")
        except Exception as e:
            print(f"Error adding {col_name}:", e)
    else:
        print(f"Column {col_name} already exists.")

db.close()
print("Database schema migration completed successfully!")
