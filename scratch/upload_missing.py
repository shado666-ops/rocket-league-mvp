import os
import requests
from datetime import datetime
import json
import sys

# Ajouter le dossier parent au path pour importer les services locaux
sys.path.append(os.getcwd())
from app.services.boxcars_service import BoxcarsService

# API Config
API_MATCHES_URL = "https://notre-club-rl.fr/api/matches"
# Utilisation des identifiants confirmés par le backend
# NOTE: Le backend utilise le système de secours si Shado666 n'est pas encore en cache Auth
ADMIN_USER = os.getenv("ADMIN_USER", "Shado666")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cloudff7!")

# Paths
USER_HOME = os.path.expanduser("~")
DEMOS_PATH = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")

# Si OneDrive est actif
if not os.path.exists(DEMOS_PATH):
    DEMOS_PATH = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

# Mappage des Playlist IDs Rocket League (Identique au backend)
PLAYLIST_MAP = {
    1: "Duel (Casual)", 2: "Doubles (Casual)", 3: "Standard (Casual)", 4: "Chaos (Casual)",
    6: "6:Private Match", 7: "Season Match", 8: "Offline Match", 9: "Local Match",
    10: "Duel (Ranked)", 11: "Doubles (Ranked)", 12: "Solo Standard (Ranked)", 13: "3v3 (Ranked)",
    15: "Snow Day", 16: "Rocket Labs", 17: "Hoops (Casual)", 18: "Rumble (Casual)",
    19: "Dropshot (Casual)", 22: "Tournament", 23: "Dropshot (Ranked)", 24: "Local Match",
    26: "Tutorial", 27: "Hoops (Ranked)", 28: "Rumble (Ranked)", 29: "Snow Day (Ranked)",
    30: "Chaos (Ranked)", 31: "Gridiron", 34: "Knockout", 38: "Heatseeker",
    41: "3v3 Tournament", 43: "2v2 Tournament", 45: "1v1 Tournament",
    47: "2v2 Tournament (Double Elim)", 48: "3v3 Tournament (Double Elim)",
}

def upload_missing_locally():
    print(f"--- RÉCUPÉRATION LOCALE DES MATCHS ---", flush=True)
    print(f"Scanning {DEMOS_PATH} for matches since 13/04...", flush=True)
    
    # Date cible : 13/04/2026 00:00 (timestamp)
    target_ts = datetime(2026, 4, 13, 0, 0).timestamp()
    
    if not os.path.exists(DEMOS_PATH):
        print(f"ERROR: Dossier demos introuvable : {DEMOS_PATH}", flush=True)
        return

    files = [f for f in os.listdir(DEMOS_PATH) if f.endswith('.replay')]
    to_process = []
    
    for f in files:
        path = os.path.join(DEMOS_PATH, f)
        mtime = os.path.getmtime(path)
        if mtime > target_ts:
            to_process.append((f, path, mtime))
            
    print(f"Found {len(to_process)} potential matches to process locally.", flush=True)
    
    success_count = 0
    # Trier par date pour respecter l'ordre chronologique
    for name, path, mtime in sorted(to_process, key=lambda x: x[2]):
        print(f"Processing {name}...", end="", flush=True)
        try:
            # 1. Parsing Local
            replay_data = BoxcarsService.parse_replay(path, played_at_mtime=mtime)
            
            # Extraction des propriétés
            props = replay_data.get("properties", {})
            if not props and "Properties" in replay_data:
                props = replay_data["Properties"]
            
            if not props:
                print("  -> ERROR: Parsing vide", flush=True)
                continue

            # 2. Construction du Payload JSON (format MatchIngestPayload)
            team0_score = props.get("Team0Score", 0)
            team1_score = props.get("Team1Score", 0)
            winning_team = 0 if team0_score > team1_score else 1
            
            players = []
            for p in props.get("PlayerStats", []):
                players.append({
                    "display_name": p.get("Name", "Unknown"),
                    "team": p.get("Team", 0),
                    "goals": p.get("Goals", 0),
                    "assists": p.get("Assists", 0),
                    "saves": p.get("Saves", 0),
                    "shots": p.get("Shots", 0),
                    "score": p.get("Score", 0),
                    "won": (p.get("Team", 0) == winning_team)
                })

            # Identification playlist
            raw_playlist = props.get("Playlist")
            playlist_id = None
            if isinstance(raw_playlist, int): playlist_id = raw_playlist
            elif isinstance(raw_playlist, dict): playlist_id = raw_playlist.get("Value")
            
            playlist = PLAYLIST_MAP.get(playlist_id, "unknown")
            if playlist_id == 6:
                blue_size = sum(1 for p in players if p['team'] == 0)
                orange_size = sum(1 for p in players if p['team'] == 1)
                playlist = f"{blue_size}v{orange_size} Private"

            played_at = None
            played_at_str = props.get("Date", "")
            if played_at_str:
                try:
                    played_at = datetime.strptime(played_at_str, "%Y-%m-%d %H-%M-%S").isoformat()
                except:
                    played_at = datetime.fromtimestamp(mtime).isoformat()
            else:
                played_at = datetime.fromtimestamp(mtime).isoformat()

            payload = {
                "replay_id": props.get("Id", "") or name.split('.')[0],
                "playlist": playlist,
                "result": "Imported (Local Process)",
                "played_at": played_at,
                "players": players
            }

            # 3. Envoi au serveur
            r = requests.post(
                API_MATCHES_URL,
                json=payload,
                auth=(ADMIN_USER, ADMIN_PASSWORD),
                timeout=30
            )

            if r.status_code in [200, 201]:
                print(f"  -> SUCCESS", flush=True)
                success_count += 1
            elif r.status_code == 409:
                print(f"  -> ALREADY EXISTS", flush=True)
            else:
                print(f"  -> ERROR {r.status_code}: {r.json().get('detail', r.text) if r.headers.get('content-type') == 'application/json' else r.text}", flush=True)

        except Exception as e:
            print(f"  -> EXCEPTION: {e}", flush=True)
            
    print(f"\nDone! {success_count} matches recovered and synced with the server.", flush=True)

if __name__ == "__main__":
    upload_missing_locally()
