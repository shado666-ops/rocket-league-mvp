import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "app.db"

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(matches)")
        columns = [row[1] for row in cursor.fetchall()]

        if "ballchasing_id" not in columns:
            print("Adding ballchasing_id column to matches table...")
            cursor.execute("ALTER TABLE matches ADD COLUMN ballchasing_id TEXT")
        
        if "ballchasing_url" not in columns:
            print("Adding ballchasing_url column to matches table...")
            cursor.execute("ALTER TABLE matches ADD COLUMN ballchasing_url TEXT")

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
