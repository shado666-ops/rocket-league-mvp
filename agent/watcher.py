import os
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
# Chemin vers le dossier des Demos local (à adapter si nécessaire)
USER_HOME = os.path.expanduser("~")
DEMOS_PATH = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")

# API Local du tracker (endpoint gérant l'upload du .replay ou les stats parsées)
API_UPLOAD_URL = "http://127.0.0.1:8000/api/matches/upload"
# Remarque : si le backend n'a pas été configuré pour parser le .replay (avec carball ou boxcars), 
# il faudra soit parser ici avant d'envoyer, soit implémenter la route côté backend.
# ---------------------

class ReplayHandler(FileSystemEventHandler):
    def process_replay(self, filepath):
        print(f"\n[Watcher] Nouveau replay detecte : {filepath}", flush=True)
        
        # Rocket League met parfois du temps à libérer le fichier `.replay`.
        # On attend un peu pour s'assurer qu'il est bien fermé et accessible.
        time.sleep(2)
        
        try:
            with open(filepath, 'rb') as f:
                # On prépare le fichier pour la requête POST
                files = {'replay_file': (os.path.basename(filepath), f, 'application/octet-stream')}
                
                print(f"[Watcher] Envoi a {API_UPLOAD_URL}...", flush=True)
                response = requests.post(API_UPLOAD_URL, files=files)
                
                if response.status_code in [200, 201]:
                    print("[Watcher] OK: Replay uploade avec succes !", flush=True)
                else:
                    print(f"[Watcher] ERROR: Echec de l'upload. Status: {response.status_code}, Reponse: {response.text}", flush=True)
        except Exception as e:
            print(f"[Watcher] WARNING: Erreur lors du traitement du replay : {e}", flush=True)

    def on_created(self, event):
        # On s'assure qu'il s'agit bien d'un fichier .replay valide
        if not event.is_directory and event.src_path.endswith('.replay'):
            self.process_replay(event.src_path)

if __name__ == "__main__":
    if not os.path.exists(DEMOS_PATH):
        print(f"WARNING: Le dossier Demos n'existe pas : {DEMOS_PATH}", flush=True)
        print("Veuillez vérifier votre installation Rocket League ou modifier le chemin dans watcher.py.", flush=True)
    else:
        print(f"Watcher demarre. Surveillance de : {DEMOS_PATH}", flush=True)
        event_handler = ReplayHandler()
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
