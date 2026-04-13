import os
import time
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_UPLOAD_URL = "https://notre-club-rl.fr/api/matches/upload"
API_UPLOAD_CSV_URL = "https://notre-club-rl.fr/api/matches/upload_csv"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "rltracker"

# Chemins possibles pour les Demos
USER_HOME = os.path.expanduser("~")
DEMOS_PATH = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")
if not os.path.exists(DEMOS_PATH):
    DEMOS_PATH = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

def force_sync():
    if not os.path.exists(DEMOS_PATH):
        print(f"Erreur : Dossier Demos introuvable ({DEMOS_PATH})")
        return

    print(f"Synchronisation des matchs depuis : {DEMOS_PATH}")
    
    # On cherche les fichiers modifiés depuis 24h (Replays et CSV)
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    replays_to_sync = []
    csv_to_sync = []
    for f in os.listdir(DEMOS_PATH):
        fpath = os.path.join(DEMOS_PATH, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        if mtime > yesterday:
            if f.endswith(".replay"):
                replays_to_sync.append((fpath, os.path.getmtime(fpath)))
            elif f.endswith(".csv"):
                csv_to_sync.append(fpath)

    print(f"Trouvé : {len(replays_to_sync)} replays et {len(csv_to_sync)} fichiers CSV récents.")
    
    success_count = 0
    fail_count = 0
    duplicate_count = 0

    # 1. Envoi des Replays
    print("\n--- Synchronisation des REPLAYS ---")
    for fpath, mtime in replays_to_sync:
        fname = os.path.basename(fpath)
        print(f"Envoi de {fname}...", end=" ", flush=True)
        try:
            with open(fpath, 'rb') as f:
                upload_files = {'replay_file': (fname, f, 'application/octet-stream')}
                url = f"{API_UPLOAD_URL}?mtime={mtime}"
                response = requests.post(url, files=upload_files, auth=(ADMIN_USER, ADMIN_PASSWORD), timeout=30)
                if response.status_code in [200, 201]:
                    print("OK")
                    success_count += 1
                elif response.status_code == 409:
                    print("DÉJÀ PRÉSENT")
                    duplicate_count += 1
                else:
                    print(f"ERREUR ({response.status_code})")
                    fail_count += 1
        except Exception as e:
            print(f"ERREUR : {e}")
            fail_count += 1

    # 2. Envoi des CSV
    print("\n--- Synchronisation des CSV ---")
    csv_success = 0
    for fpath in csv_to_sync:
        fname = os.path.basename(fpath)
        print(f"Envoi de {fname}...", end=" ", flush=True)
        try:
            with open(fpath, 'rb') as f:
                upload_files = {'csv_file': (fname, f, 'text/csv')}
                response = requests.post(API_UPLOAD_CSV_URL, files=upload_files, auth=(ADMIN_USER, ADMIN_PASSWORD), timeout=30)
                if response.status_code in [200, 201]:
                    print("OK")
                    csv_success += 1
                else:
                    print(f"ERREUR ({response.status_code})")
        except Exception as e:
            print(f"ERREUR : {e}")

    print("\n" + "="*40)
    print(f"RÉSUMÉ FINAL :")
    print(f"- Replays : {success_count} envoyés, {duplicate_count} doublons.")
    print(f"- CSV     : {csv_success} envoyés.")
    print(f"- Échecs  : {fail_count}")
    print("="*40)

if __name__ == "__main__":
    force_sync()
