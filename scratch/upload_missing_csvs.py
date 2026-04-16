import os
import requests
from datetime import datetime
import sys

# API Config
API_CSV_URL = "https://notre-club-rl.fr/api/matches/upload_csv"
ADMIN_USER = os.getenv("ADMIN_USER", "Shado666")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cloudff7!")

# Paths
USER_HOME = os.path.expanduser("~")
DEMOS_PATH = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")

if not os.path.exists(DEMOS_PATH):
    DEMOS_PATH = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

def upload_missing_csvs():
    print(f"--- SYNCHRONISATION DES FICHIERS CSV (IDENTIFICATION) ---")
    print(f"Scanning {DEMOS_PATH} for CSVs since 13/04...")
    
    target_ts = datetime(2026, 4, 13, 0, 0).timestamp()
    
    if not os.path.exists(DEMOS_PATH):
        print(f"ERROR: Dossier introuvable : {DEMOS_PATH}")
        return

    files = [f for f in os.listdir(DEMOS_PATH) if f.endswith('.csv')]
    to_process = []
    
    for f in files:
        path = os.path.join(DEMOS_PATH, f)
        mtime = os.path.getmtime(path)
        if mtime > target_ts:
            to_process.append((f, path, mtime))
            
    print(f"Found {len(to_process)} CSV files to sync.")
    
    success_count = 0
    # Trier par date
    for name, path, mtime in sorted(to_process, key=lambda x: x[2]):
        print(f"Uploading {name}...", end="", flush=True)
        try:
            with open(path, 'rb') as f:
                files_payload = {'csv_file': (name, f, 'text/csv')}
                r = requests.post(
                    API_CSV_URL,
                    files=files_payload,
                    auth=(ADMIN_USER, ADMIN_PASSWORD),
                    timeout=30
                )

            if r.status_code in [200, 201]:
                print(f"  -> SUCCESS", flush=True)
                success_count += 1
            else:
                print(f"  -> ERROR {r.status_code}: {r.text[:100]}", flush=True)

        except Exception as e:
            print(f"  -> EXCEPTION: {e}", flush=True)
            
    print(f"\nTermine ! {success_count} fichiers CSV synchronises. Les matchs devraient maintenant etre identifies sur le site.")

if __name__ == "__main__":
    upload_missing_csvs()
