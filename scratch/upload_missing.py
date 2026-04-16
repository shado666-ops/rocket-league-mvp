import os
import time
import requests
from datetime import datetime, timedelta

# API Config
API_UPLOAD_URL = "https://notre-club-rl.fr/api/matches/upload"
ADMIN_USER = os.getenv("ADMIN_USER", "Shado666")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cloudff7!")

# Paths
USER_HOME = os.path.expanduser("~")
DEMOS_PATH = os.path.join(USER_HOME, "Documents", "My Games", "Rocket League", "TAGame", "Demos")
if not os.path.exists(DEMOS_PATH):
    DEMOS_PATH = os.path.join(USER_HOME, "OneDrive", "Documents", "My Games", "Rocket League", "TAGame", "Demos")

def upload_missing():
    print(f"Scanning {DEMOS_PATH} for matches since 13/04...", flush=True)
    
    # Target date: 13/04/2026 00:00 (timestamp)
    target_ts = datetime(2026, 4, 13, 0, 0).timestamp()
    
    files = [f for f in os.listdir(DEMOS_PATH) if f.endswith('.replay')]
    to_upload = []
    
    for f in files:
        path = os.path.join(DEMOS_PATH, f)
        mtime = os.path.getmtime(path)
        if mtime > target_ts:
            to_upload.append((f, path, mtime))
            
    print(f"Found {len(to_upload)} potential matches to upload.", flush=True)
    
    success_count = 0
    for name, path, mtime in sorted(to_upload, key=lambda x: x[2]):
        print(f"Uploading {name} ({datetime.fromtimestamp(mtime)})...", end="", flush=True)
        try:
            with open(path, 'rb') as rb:
                r = requests.post(
                    f"{API_UPLOAD_URL}?mtime={mtime}",
                    files={'replay_file': (name, rb, 'application/octet-stream')},
                    auth=(ADMIN_USER, ADMIN_PASSWORD),
                    timeout=300
                )
                if r.status_code in [200, 201]:
                    print(f"  -> SUCCESS", flush=True)
                    success_count += 1
                elif r.status_code == 409:
                    print(f"  -> ALREADY EXISTS", flush=True)
                else:
                    print(f"  -> ERROR {r.status_code}: {r.text}", flush=True)
        except Exception as e:
            print(f"  -> EXCEPTION: {e}", flush=True)
            
    print(f"\nDone! {success_count} matches uploaded.", flush=True)

if __name__ == "__main__":
    upload_missing()
