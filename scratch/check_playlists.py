
import sqlite3
import os

DB_PATH = 'data/app.db'

def check_playlists():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT playlist FROM matches")
    playlists = cursor.fetchall()
    
    print("Distinct playlists in database:")
    for p in playlists:
        print(f"- {p[0]}")
    
    conn.close()

if __name__ == "__main__":
    check_playlists()
