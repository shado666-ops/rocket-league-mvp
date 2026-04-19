import datetime
import sys

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
    
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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

print(f"\n--- [Watcher] Demarrage le {datetime.datetime.now()} ---", flush=True)
print(f"[Watcher] Dossier cible identifie : {DEMOS_PATH}", flush=True)

# API du tracker (Production VPS)
API_UPLOAD_URL = "https://notre-club-rl.fr/api/matches/upload"
API_UPLOAD_CSV_URL = "https://notre-club-rl.fr/api/matches/upload_csv"

# Authentification
ADMIN_USER = os.getenv("ADMIN_USER", "Shado666")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cloudff7!")

class MatchHandler(FileSystemEventHandler):
    def process_replay(self, filepath):
        if not filepath.endswith('.replay'): return
        print(f"\n[Watcher] >>> Traitement replay : {os.path.basename(filepath)}", flush=True)
        
        # Attendre que le fichier soit libéré
        time.sleep(2)
        
        try:
            mtime = os.path.getmtime(filepath)
            with open(filepath, 'rb') as f:
                files = {'replay_file': (os.path.basename(filepath), f, 'application/octet-stream')}
                upload_url = f"{API_UPLOAD_URL}?mtime={mtime}"
                
                response = requests.post(
                    upload_url, 
                    files=files, 
                    auth=(ADMIN_USER, ADMIN_PASSWORD),
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    print(f"[Watcher] SUCCESS: {os.path.basename(filepath)} traite.", flush=True)
                elif response.status_code == 409:
                    print(f"[Watcher] SKIP: {os.path.basename(filepath)} deja existant.", flush=True)
                else:
                    print(f"[Watcher] API ERROR: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"[Watcher] SYSTEM ERROR (Replay): {e}", flush=True)
 
    def process_csv(self, filepath):
        if not filepath.endswith('.csv'): return
        print(f"\n[Watcher] >>> Traitement CSV : {os.path.basename(filepath)}", flush=True)
        time.sleep(1)
        
        try:
            with open(filepath, 'rb') as f:
                files = {'csv_file': (os.path.basename(filepath), f, 'text/csv')}
                response = requests.post(
                    API_UPLOAD_CSV_URL, 
                    files=files, 
                    auth=(ADMIN_USER, ADMIN_PASSWORD),
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    print(f"[Watcher] SUCCESS: CSV {os.path.basename(filepath)} traite.", flush=True)
                else:
                    print(f"[Watcher] API ERROR: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"[Watcher] SYSTEM ERROR (CSV): {e}", flush=True)

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
        
        # Scan de rattrapage au démarrage
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
