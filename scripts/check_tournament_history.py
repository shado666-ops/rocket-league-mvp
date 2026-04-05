import sqlite3
from datetime import datetime

def check_tournament_history():
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # On cherche les matchs du tournoi du 04/04/2026
    # On filtre par playlist contenant "Tournament" (depuis ma correction)
    cursor.execute("""
        SELECT id, playlist, played_at, result 
        FROM matches 
        WHERE (playlist LIKE '%Tournament%' OR playlist LIKE '%Tournoi%')
        AND played_at LIKE '2026-04-04%'
        ORDER BY played_at ASC
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("Aucun match de tournoi trouvé pour le 04/04/2026.")
        return

    print(f"Matchs de tournoi trouvés pour le 04/04/2026 :")
    for r in rows:
        print(f"ID: {r[0]} | Playlist: {r[1]} | Date: {r[2]} | Result: {r[3]}")
    
    conn.close()

if __name__ == "__main__":
    check_tournament_history()
