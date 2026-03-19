import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("boost_collected", "INTEGER"),
        ("boost_stolen", "INTEGER"),
        ("time_zero_boost", "INTEGER"),
        ("time_full_boost", "INTEGER"),
        ("time_defensive_third", "INTEGER"),
        ("time_neutral_third", "INTEGER"),
        ("time_offensive_third", "INTEGER"),
        ("avg_speed", "INTEGER"),
        ("time_supersonic", "INTEGER")
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE match_player_stats ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to match_player_stats table.")
        except sqlite3.OperationalError:
            print(f"Column {col_name} already exists in match_player_stats table.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
