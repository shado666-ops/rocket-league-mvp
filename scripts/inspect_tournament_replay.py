import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from database import SessionLocal
from models import Match
from app.services.boxcars_service import BoxcarsService

def inspect_match(match_id):
    db = SessionLocal()
    try:
        m = db.query(Match).filter(Match.id == match_id).first()
        if not m:
            print(f"Match {match_id} not found.")
            return

        replay_path = os.path.join(ROOT, "uploaded_replays", f"{m.replay_id}.replay")
        if not os.path.exists(replay_path):
            print(f"Replay file not found: {replay_path}")
            return

        print(f"Inspecting Match {m.id} (Replay: {m.replay_id})...")
        replay_data = BoxcarsService.parse_replay(replay_path)
        
        props = replay_data.get("properties", {})
        if not props and "Properties" in replay_data:
            props = replay_data["Properties"]
            
        print("\n--- ALL PROPERTIES ---")
        for k, v in props.items():
            print(f"{k} = {v}")
        
        print("\n--- TOURNAMENT DATA ---")
        tournament_props = {k: v for k, v in props.items() if "Tournament" in k}
        print(json.dumps(tournament_props, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_match(297) # Match mentioned by user
