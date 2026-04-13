import os
# Save PID for the launcher
os.makedirs("data", exist_ok=True)
with open("data/watcher.pid", "w") as f:
    f.write(str(os.getpid()))
    
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
# Chemin vers le dossier des Demos local (à adapter si nécessaire)
USER_HOME = os.path.expanduser("~")
# Chemins possibles pour les Demos
STANDARD_DOCS = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")
ONEDRIVE_DOCS = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

if os.path.exists(STANDARD_DOCS):
    DEMOS_PATH = STANDARD_DOCS
elif os.path.exists(ONEDRIVE_DOCS):
    DEMOS_PATH = ONEDRIVE_DOCS
else:
    # Fallback par défaut
    DEMOS_PATH = STANDARD_DOCS

print(f"[Watcher] Dossier cible identifie : {DEMOS_PATH}", flush=True)

# API du tracker (Production VPS)
API_UPLOAD_URL = "https://notre-club-rl.fr/api/matches/upload"
API_UPLOAD_CSV_URL = "https://notre-club-rl.fr/api/matches/upload_csv"

# Authentification (doit correspondre à main.py)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rltracker")
# ---------------------

class MatchHandler(FileSystemEventHandler):
    def process_replay(self, filepath):
        print(f"\n[Watcher] >>> Nouveau replay detecte : {os.path.basename(filepath)}", flush=True)
        
        # On attend que Rocket League relâche le fichier
        time.sleep(3)
        
        try:
            # On récupère la date de modification originale avant d'envoyer
            mtime = os.path.getmtime(filepath)
            
            with open(filepath, 'rb') as f:
                files = {'replay_file': (os.path.basename(filepath), f, 'application/octet-stream')}
                
                # Envoi de la mtime en paramètre pour préserver la date du match
                upload_url_with_time = f"{API_UPLOAD_URL}?mtime={mtime}"
                
                print(f"[Watcher] Envoi vers {upload_url_with_time}...", flush=True)
                try:
                    response = requests.post(
                        upload_url_with_time, 
                        files=files, 
                        auth=(ADMIN_USER, ADMIN_PASSWORD),
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        print("[Watcher] SUCCESS: Replay traite avec succes par le backend.", flush=True)
                    else:
                        print(f"[Watcher] API ERROR: {response.status_code} - {response.text}", flush=True)
                except requests.exceptions.ConnectionError:
                    print(f"[Watcher] SERVER ERROR: Impossible de contacter le serveur à {API_UPLOAD_URL}.", flush=True)
                    print("[Watcher] Assurez-vous que le tracker (main.py) est bien lancé !", flush=True)
        except Exception as e:
            print(f"[Watcher] SYSTEM ERROR (Replay): {e}", flush=True)
 
    def process_csv(self, filepath):
        print(f"\n[Watcher] >>> Nouveau CSV detecte : {os.path.basename(filepath)}", flush=True)
        
        # On attend un peu pour être sûr que le fichier est complet
        time.sleep(2)
        
        try:
            with open(filepath, 'rb') as f:
                files = {'csv_file': (os.path.basename(filepath), f, 'text/csv')}
                
                print(f"[Watcher] Envoi vers {API_UPLOAD_CSV_URL}...", flush=True)
                try:
                    response = requests.post(
                        API_UPLOAD_CSV_URL, 
                        files=files, 
                        auth=(ADMIN_USER, ADMIN_PASSWORD),
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        print("[Watcher] SUCCESS: CSV traite avec succes par le backend.", flush=True)
                    else:
                        print(f"[Watcher] API ERROR: {response.status_code} - {response.text}", flush=True)
                except requests.exceptions.ConnectionError:
                    print(f"[Watcher] SERVER ERROR: Impossible de contacter le serveur à {API_UPLOAD_CSV_URL}.", flush=True)
        except Exception as e:
            print(f"[Watcher] SYSTEM ERROR (CSV): {e}", flush=True)

    def on_created(self, event):
        if not event.is_directory:
            if event.src_path.endswith('.replay'):
                self.process_replay(event.src_path)
            elif event.src_path.endswith('.csv'):
                self.process_csv(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            if event.dest_path.endswith('.replay'):
                self.process_replay(event.dest_path)
            elif event.dest_path.endswith('.csv'):
                self.process_csv(event.dest_path)

    def on_modified(self, event):
        # Optionnel : pour l'instant on se fie à on_created/on_moved
        pass


if __name__ == "__main__":
    if not os.path.exists(DEMOS_PATH):
        print(f"WARNING: Le dossier Demos n'existe pas : {DEMOS_PATH}", flush=True)
        print("Veuillez vérifier votre installation Rocket League ou modifier le chemin dans watcher.py.", flush=True)
    else:
        print(f"Watcher demarre. Surveillance de : {DEMOS_PATH}", flush=True)
        event_handler = MatchHandler()
        observer = Observer()
        observer.schedule(event_handler, DEMOS_PATH, recursive=False)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        print("Watcher arrêté.")
