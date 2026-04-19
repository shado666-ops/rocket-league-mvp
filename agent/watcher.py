import os
import time
import requests
import datetime
import sys
import json
import subprocess
import csv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Logging configuration
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "watcher.log")

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger(LOG_FILE)
sys.stderr = sys.stdout

# Save PID for the launcher
os.makedirs("data", exist_ok=True)
with open("data/watcher.pid", "w") as f:
    f.write(str(os.getpid()))

# --- CONFIGURATION ---
USER_HOME = os.path.expanduser("~")
STANDARD_DOCS = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")
ONEDRIVE_DOCS = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

if os.path.exists(STANDARD_DOCS):
    DEMOS_PATH = STANDARD_DOCS
elif os.path.exists(ONEDRIVE_DOCS):
    DEMOS_PATH = ONEDRIVE_DOCS
else:
    DEMOS_PATH = STANDARD_DOCS

# Chemin vers l'outil de parsing local
RRROCKET_PATH = os.path.join(os.getcwd(), "parsers", "boxcars", "rrrocket.exe")

print(f"\n--- [Watcher] Demarrage le {datetime.datetime.now()} ---", flush=True)
print(f"[Watcher] Dossier cible identifie : {DEMOS_PATH}", flush=True)
print(f"[Watcher] Parser local : {RRROCKET_PATH}", flush=True)

# API du tracker (Production VPS)
API_INGEST_URL = "https://notre-club-rl.fr/api/matches"

# Authentification
ADMIN_USER = os.getenv("ADMIN_USER", "Shado666")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cloudff7!")

# Mapping des Playlists (Identique au backend pour coherence)
PLAYLIST_MAP = {
    1: "Duel (Casual)", 2: "Doubles (Casual)", 3: "Standard (Casual)", 4: "Chaos (Casual)",
    6: "Private Match", 7: "Season Match", 8: "Offline Match", 9: "Local Match",
    10: "Duel (Ranked)", 11: "Doubles (Ranked)", 12: "Solo Standard (Ranked)", 13: "3v3 (Ranked)",
    15: "Snow Day", 16: "Rocket Labs", 17: "Hoops (Casual)", 18: "Rumble (Casual)",
    19: "Dropshot (Casual)", 22: "Tournament", 23: "Dropshot (Ranked)", 24: "Local Match",
    26: "Tutorial", 27: "Hoops (Ranked)", 28: "Rumble (Ranked)", 29: "Snow Day (Ranked)",
    30: "Chaos (Ranked)", 31: "Gridiron", 34: "Knockout", 38: "Heatseeker",
    41: "3v3 Tournament", 43: "2v2 Tournament", 45: "1v1 Tournament",
    47: "2v2 Tournament (Double Elim)", 48: "3v3 Tournament (Double Elim)",
}

class MatchHandler(FileSystemEventHandler):
    def parse_replay_local(self, filepath, mtime=None):
        """Parse le replay en local et retourne le dictionnaire formaté pour l'API."""
        if not os.path.exists(RRROCKET_PATH):
            print(f"[Watcher] ERROR: Parser introuvable a {RRROCKET_PATH}", flush=True)
            return None

        try:
            result = subprocess.run([RRROCKET_PATH, filepath], capture_output=True, text=True, encoding="utf-8")
            if result.returncode != 0:
                print(f"[Watcher] ERROR rrrocket: {result.stderr}", flush=True)
                return None

            data = json.loads(result.stdout)
            props = data.get("properties", {}) or data.get("Properties", {})
            
            # Extraction score et vainqueur
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

            # Playlist
            raw_pl = props.get("Playlist")
            pl_id = raw_pl.get("Value") if isinstance(raw_pl, dict) else raw_pl
            playlist = PLAYLIST_MAP.get(pl_id, "Inconnue")
            
            if pl_id == 6: # Private
                blue = sum(1 for p in players if p["team"] == 0)
                orange = sum(1 for p in players if p["team"] == 1)
                playlist = f"{blue}v{orange} Private"

            # Date
            played_at = None
            date_str = props.get("Date", "")
            if date_str:
                try: played_at = datetime.datetime.strptime(date_str, "%Y-%m-%d %H-%M-%S").isoformat()
                except: pass
            
            if not played_at and mtime:
                played_at = datetime.datetime.fromtimestamp(mtime).isoformat()

            return {
                "replay_id": props.get("Id", "") or os.path.splitext(os.path.basename(filepath))[0],
                "played_at": played_at,
                "playlist": playlist,
                "result": f"{team0_score}-{team1_score} (Local Parse)",
                "players": players
            }
        except Exception as e:
            print(f"[Watcher] ERROR parsing replay: {e}", flush=True)
            return None

    def parse_csv_local(self, filepath):
        """Lit le CSV BakkesMod et retourne le dictionnaire formaté pour l'API."""
        try:
            players = []
            played_at = None
            
            with open(filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not played_at and row.get('Date'):
                        try: played_at = datetime.datetime.strptime(row['Date'], "%Y-%m-%d %H:%M:%S").isoformat()
                        except: pass
                    
                    players.append({
                        "display_name": row.get('Name', 'Unknown'),
                        "team": int(row.get('Team', 0)),
                        "goals": int(row.get('Goals', 0)),
                        "assists": int(row.get('Assists', 0)),
                        "saves": int(row.get('Saves', 0)),
                        "shots": int(row.get('Shots', 0)),
                        "score": int(row.get('Score', 0)),
                        "won": row.get('Won', 'False').lower() == 'true'
                    })

            if not players: return None

            return {
                "replay_id": os.path.splitext(os.path.basename(filepath))[0],
                "played_at": played_at or datetime.datetime.now().isoformat(),
                "playlist": "BakkesMod CSV",
                "result": "CSV Import (Local)",
                "players": players
            }
        except Exception as e:
            print(f"[Watcher] ERROR parsing CSV: {e}", flush=True)
            return None

    def process_replay(self, filepath):
        if not filepath.endswith('.replay'): return
        print(f"\n[Watcher] >>> Parsing local Replay : {os.path.basename(filepath)}", flush=True)
        time.sleep(2) # Attendre fin écriture
        
        mtime = os.path.getmtime(filepath)
        payload = self.parse_replay_local(filepath, mtime)
        
        if payload:
            self.send_to_server(payload)

    def process_csv(self, filepath):
        if not filepath.endswith('.csv'): return
        print(f"\n[Watcher] >>> Parsing local CSV : {os.path.basename(filepath)}", flush=True)
        time.sleep(1)
        
        payload = self.parse_csv_local(filepath)
        if payload:
            self.send_to_server(payload)

    def send_to_server(self, payload):
        try:
            response = requests.post(
                API_INGEST_URL,
                json=payload,
                auth=(ADMIN_USER, ADMIN_PASSWORD),
                timeout=30
            )
            if response.status_code in [200, 201]:
                print(f"[Watcher] SUCCESS: Match {payload['replay_id']} envoye.", flush=True)
            else:
                print(f"[Watcher] API ERROR: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"[Watcher] NETWORK ERROR: {e}", flush=True)

    def on_created(self, event):
        if not event.is_directory:
            if event.src_path.endswith('.replay'): self.process_replay(event.src_path)
            elif event.src_path.endswith('.csv'): self.process_csv(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            if event.dest_path.endswith('.replay'): self.process_replay(event.dest_path)
            elif event.dest_path.endswith('.csv'): self.process_csv(event.dest_path)

def catch_up_scan(handler, path):
    print("[Watcher] Lancement du scan de rattrapage (7 jours)...", flush=True)
    count = 0
    now = time.time()
    day_ago = now - (7 * 24 * 3600)
    
    try:
        if not os.path.exists(path): return
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            if not os.path.isfile(file_path): continue
            
            mtime = os.path.getmtime(file_path)
            if mtime > day_ago:
                if filename.endswith('.replay'):
                    handler.process_replay(file_path)
                    count += 1
                elif filename.endswith('.csv'):
                    handler.process_csv(file_path)
                    count += 1
    except Exception as e:
        print(f"[Watcher] Erreur pendant le scan : {e}", flush=True)
    
    print(f"[Watcher] Scan termine. {count} fichiers potentiels identifies.", flush=True)

if __name__ == "__main__":
    if not os.path.exists(DEMOS_PATH):
        print(f"WARNING: Dossier Demos absent : {DEMOS_PATH}", flush=True)
    else:
        event_handler = MatchHandler()
        catch_up_scan(event_handler, DEMOS_PATH)
        
        print(f"[Watcher] Surveillance active : {DEMOS_PATH}", flush=True)
        observer = Observer()
        observer.schedule(event_handler, DEMOS_PATH, recursive=False)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        print("[Watcher] Arrete.")
