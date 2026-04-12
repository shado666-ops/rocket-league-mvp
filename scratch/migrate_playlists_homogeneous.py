
import sqlite3
import os

DB_PATH = 'data/app.db'

def homogenize_playlists():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Selectionner tous les matchs
    cursor.execute("SELECT id, playlist FROM matches")
    matches = cursor.fetchall()
    
    updates = []
    for match_id, old_name in matches:
        new_name = old_name
        
        # Format X Ranked -> X (Ranked)
        if " Ranked" in old_name and "(" not in old_name:
            new_name = old_name.replace(" Ranked", " (Ranked)")
            
        # Format X Ranked+R -> X (Ranked+R)
        elif " Ranked+R" in old_name and "(" not in old_name:
            new_name = old_name.replace(" Ranked+R", " (Ranked+R)")
            
        # Format X Private -> X (Private)
        elif " Private" in old_name and "(" not in old_name:
            new_name = old_name.replace(" Private", " (Private)")
            
        # Specifique pour 3v3 Ranked+R si non capturé par les précédents
        if old_name == "3v3 Ranked+R":
            new_name = "3v3 (Ranked+R)"
            
        if old_name != new_name:
            updates.append((new_name, match_id))
            print(f"Renaming: '{old_name}' -> '{new_name}'")

    if updates:
        print(f"Applying {len(updates)} updates...")
        cursor.executemany("UPDATE matches SET playlist = ? WHERE id = ?", updates)
        conn.commit()
        print("Migration complete.")
    else:
        print("No matches need renaming.")
    
    conn.close()

if __name__ == "__main__":
    homogenize_playlists()
