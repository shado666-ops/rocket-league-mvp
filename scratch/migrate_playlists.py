
import sqlite3
import os
from datetime import datetime

# Path to the database
DB_PATH = 'data/app.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Get all club member pseudos and aliases
    cursor.execute("SELECT display_name FROM club_members WHERE is_active = 1")
    club_members = [row['display_name'] for row in cursor.fetchall()]
    
    cursor.execute("SELECT pseudo FROM player_aliases")
    aliases = [row['pseudo'] for row in cursor.fetchall()]
    
    all_club_pseudos = set(club_members + aliases)
    print(f"Found {len(all_club_pseudos)} club member pseudos/aliases.")

    # 2. Get all 3v3 Ranked variation matches
    # We look for "3v3 (Ranked)", "Standard (Ranked)", "3v3 Ranked", etc.
    cursor.execute("""
        SELECT id, playlist FROM matches 
        WHERE playlist LIKE '%3v3%Ranked%' 
           OR playlist LIKE '%Standard%Ranked%'
           OR playlist = '3v3 (Ranked)'
           OR playlist = 'Standard (Ranked)'
    """)
    matches = cursor.fetchall()
    print(f"Found {len(matches)} matches to check.")

    updates = []
    for m in matches:
        match_id = m['id']
        old_playlist = m['playlist']
        
        # Get players for this match
        cursor.execute("""
            SELECT ps.team, p.display_name 
            FROM match_player_stats ps
            JOIN players p ON ps.player_id = p.id
            WHERE ps.match_id = ?
        """, (match_id,))
        players = cursor.fetchall()
        
        # Count club members per team
        teams_club_count = {}
        for p in players:
            if p['display_name'] in all_club_pseudos:
                teams_club_count[p['team']] = teams_club_count.get(p['team'], 0) + 1
        
        # Find the team with the most club members (assuming that's our tea)
        max_club_on_team = max(teams_club_count.values()) if teams_club_count else 0
        
        new_playlist = "3v3 Ranked"
        if 0 < max_club_on_team < 3:
            new_playlist = "3v3 Ranked+R"
            
        if old_playlist != new_playlist:
            updates.append((new_playlist, match_id))

    # 3. Apply updates
    if updates:
        print(f"Updating {len(updates)} matches...")
        cursor.executemany("UPDATE matches SET playlist = ? WHERE id = ?", updates)
        conn.commit()
        print("Migration complete.")
    else:
        print("No matches need updating.")

    conn.close()

if __name__ == "__main__":
    migrate()
