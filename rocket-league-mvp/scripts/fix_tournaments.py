import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from database import SessionLocal
from models import Match
from app.services.boxcars_service import BoxcarsService

# Sync with app/routes/matches.py
PLAYLIST_MAP = {
    1: "Duel (Casual)", 2: "Doubles (Casual)", 3: "Standard (Casual)", 4: "Chaos (Casual)",
    6: "Private Match", 7: "Season Match", 8: "Offline Match", 9: "Local Match",
    10: "Duel (Ranked)", 11: "Doubles (Ranked)", 12: "Solo Standard (Ranked)",
    13: "Standard (Ranked)", 15: "Snow Day", 16: "Rocket Labs",
    17: "Hoops (Casual)", 18: "Rumble (Casual)", 19: "Dropshot (Casual)",
    22: "Tournament", 23: "Dropshot (Ranked)", 24: "Local Match",
    26: "Tutorial", 27: "Hoops (Ranked)", 28: "Rumble (Ranked)",
    29: "Snow Day (Ranked)", 30: "Chaos (Ranked)", 31: "Gridiron",
    34: "Knockout", 38: "Heatseeker", 41: "3v3 Tournament",
    43: "2v2 Tournament", 45: "1v1 Tournament",
    47: "2v2 Tournament (Double Elim)", 48: "3v3 Tournament (Double Elim)",
}

def fix_tournaments():
    db = SessionLocal()
    try:
        # On cible les matchs récents qui pourraient être des tournois mal identifiés
        # Notamment ceux avec "Casual" dans la playlist
        target_matches = db.query(Match).filter(
            Match.played_at >= datetime(2026, 4, 1),
            (Match.playlist.like("%Casual%") | Match.playlist.like("%Inconnue%"))
        ).all()
        
        print(f"Checking {len(target_matches)} potential tournament matches...")
        
        updated_count = 0
        for m in target_matches:
            replay_path = os.path.join(ROOT, "uploaded_replays", f"{m.replay_id}.replay")
            if not os.path.exists(replay_path):
                continue
                
            try:
                print(f"Processing Match {m.id} at {m.played_at} (current: {m.playlist})...")
                replay_data = BoxcarsService.parse_replay(replay_path)
                props = replay_data.get("properties", {})
                if not props and "Properties" in replay_data:
                    props = replay_data["Properties"]
                
                # Logic from matches.py
                raw_playlist = props.get("Playlist")
                playlist_id = None
                if isinstance(raw_playlist, int):
                    playlist_id = raw_playlist
                elif isinstance(raw_playlist, dict):
                    playlist_id = raw_playlist.get("Value")
                
                new_playlist = None
                if playlist_id is not None and playlist_id in PLAYLIST_MAP:
                    new_playlist = PLAYLIST_MAP[playlist_id]
                    if playlist_id == 6:
                        # Private format detection
                        p_stats = props.get("PlayerStats", [])
                        blue_size = sum(1 for p in p_stats if p.get("Team") == 0)
                        orange_size = sum(1 for p in p_stats if p.get("Team") == 1)
                        new_playlist = f"{blue_size}v{orange_size} Private"
                else:
                    # Fallback detection
                    match_type_raw = props.get("MatchType", "")
                    match_type = ""
                    if isinstance(match_type_raw, dict):
                        match_type = match_type_raw.get("Value", "")
                    else:
                        match_type = str(match_type_raw)
                    
                    replay_name = props.get("ReplayName", "").lower()
                    team_size = props.get("TeamSize", 0)
                    
                    display_type = None
                    if match_type == "Online" or "online" in replay_name:
                        display_type = "Ranked"
                    elif match_type == "Tournament" or "tournoi" in replay_name or "tournament" in replay_name:
                        display_type = "Tournament"
                    elif match_type == "Private":
                        display_type = "Private Match"
                    else:
                        display_type = "Casual"
                        
                    if display_type == "Private Match":
                        p_stats = props.get("PlayerStats", [])
                        blue_size = sum(1 for p in p_stats if p.get("Team") == 0)
                        orange_size = sum(1 for p in p_stats if p.get("Team") == 1)
                        new_playlist = f"{blue_size}v{orange_size} Private"
                    else:
                        new_playlist = f"{team_size}v{team_size} ({display_type})" if team_size else "Inconnue"

                if new_playlist and m.playlist != new_playlist:
                    # On vérifie si c'est devenu un tournoi ou si ça a juste changé
                    if "Tournament" in new_playlist or "tournoi" in new_playlist.lower():
                        print(f"  [FIXED] Updated to: {new_playlist}")
                        m.playlist = new_playlist
                        updated_count += 1
                    else:
                        # On met à jour quand même si c'est plus précis (ex: Inconnue -> 3v3 Casual)
                        # Mais le but principal est "Tournament"
                        if "Inconnue" in m.playlist:
                            print(f"  [UPDATED] Updated to: {new_playlist}")
                            m.playlist = new_playlist
                            updated_count += 1
                
            except Exception as e:
                print(f"  [ERROR] Failed to process {m.id}: {e}")
                
        db.commit()
        print(f"\nDone! {updated_count} matches have been updated.")
        
    except Exception as e:
        print(f"Global error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_tournaments()
