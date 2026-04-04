import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add the project root to sys.path
ROOT = r"c:\Users\perno\Desktop\Rocket-League-MVP-Propre"
sys.path.append(ROOT)

from database import SessionLocal
from models import Match
from app.services.boxcars_service import BoxcarsService

def recover_matches():
    db = SessionLocal()
    try:
        # Matches from today/yesterday that are labeled Private
        target_matches = db.query(Match).filter(
            Match.created_at >= datetime(2026, 3, 27),
            Match.playlist.like("%Private%")
        ).all()
        
        print(f"Checking {len(target_matches)} matches for recovery.")
        
        PLAYLIST_MAP = {
            1: "Duel (Casual)", 2: "Doubles (Casual)", 3: "Standard (Casual)", 4: "Chaos (Casual)",
            6: "Private Match", 10: "Duel (Ranked)", 11: "Doubles (Ranked)", 
            12: "Solo Standard (Ranked)", 13: "Standard (Ranked)", 15: "Snow Day", 
            17: "Hoops (Casual)", 18: "Rumble (Casual)", 19: "Dropshot (Casual)",
            22: "Tournament", 23: "Dropshot (Ranked)", 27: "Hoops (Ranked)",
            28: "Rumble (Ranked)", 29: "Snow Day (Ranked)", 30: "Chaos (Ranked)"
        }
        
        updated_count = 0
        for m in target_matches:
            # Check if we have a replay file
            replay_path = os.path.join(ROOT, "uploaded_replays", f"{m.replay_id}.replay")
            if os.path.exists(replay_path):
                print(f"Re-parsing Replay for match {m.id} (ID: {m.replay_id})...")
                try:
                    replay_data = BoxcarsService.parse_replay(replay_path)
                    props = replay_data.get("properties", {})
                    if not props and "Properties" in replay_data:
                        props = replay_data["Properties"]
                    
                    playlist_id = props.get("Playlist")
                    if isinstance(playlist_id, dict): playlist_id = playlist_id.get("Value")
                    
                    match_type_raw = props.get("MatchType", "")
                    match_type = match_type_raw.get("Value") if isinstance(match_type_raw, dict) else str(match_type_raw)
                    
                    team_size = props.get("TeamSize", 0)
                    
                    # Logic from matches.py
                    new_playlist = None
                    if playlist_id in PLAYLIST_MAP:
                        if playlist_id == 6:
                            # Still private, but re-calculate format just in case
                            blue_size = sum(1 for p in props.get("PlayerStats", []) if p.get("Team") == 0)
                            orange_size = sum(1 for p in props.get("PlayerStats", []) if p.get("Team") == 1)
                            new_playlist = f"{blue_size}v{orange_size} Private"
                        else:
                            new_playlist = PLAYLIST_MAP[playlist_id]
                    else:
                        # Fallback
                        display_type = "Casual"
                        if match_type == "Online": display_type = "Ranked"
                        elif match_type == "Private": display_type = "Private Match"
                        
                        if display_type == "Private Match":
                            blue_size = sum(1 for p in props.get("PlayerStats", []) if p.get("Team") == 0)
                            orange_size = sum(1 for p in props.get("PlayerStats", []) if p.get("Team") == 1)
                            new_playlist = f"{blue_size}v{orange_size} Private"
                        else:
                            new_playlist = f"{team_size}v{team_size} ({display_type})" if team_size else "Inconnue"
                    
                    if new_playlist and m.playlist != new_playlist:
                        print(f"  -> Corrected: '{m.playlist}' -> '{new_playlist}'")
                        m.playlist = new_playlist
                        updated_count += 1
                except Exception as e:
                    print(f"  -> Failed to parse replay: {e}")
            elif m.replay_id.startswith("game_stats_"):
                # CSV only match
                if "Blue_vs_Orange" in m.replay_id:
                    print(f"Reverting CSV-only match {m.id} to 'BakkesMod CSV' (unreliable private label)")
                    m.playlist = "BakkesMod CSV"
                    updated_count += 1
        
        db.commit()
        print(f"Recovery complete: {updated_count} matches updated.")
        
    except Exception as e:
        print(f"Error during recovery: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    recover_matches()
