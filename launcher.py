import json
import os
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")

SERVER_LOG = os.path.join(PROJECT_DIR, "logs", "server.log")
WATCHER_LOG = os.path.join(PROJECT_DIR, "logs", "watcher.log")
PID_FILE = os.path.join(PROJECT_DIR, "tracker_pids.json")

MAIN_APP = "main:app"
WATCHER_SCRIPT = os.path.join(PROJECT_DIR, "agent", "watcher.py")


def ensure_dirs():
    os.makedirs(os.path.join(PROJECT_DIR, "logs"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "backups"), exist_ok=True)


def is_pid_running(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        output = result.stdout.strip()
        if not output:
            return False

        lowered = output.lower()
        if "aucune tache" in lowered or "no tasks are running" in lowered:
            return False

        return f'"{pid}"' in output or f",{pid}," in output
    except Exception:
        return False


def save_pids(server_pid: int, watcher_pid: int):
    data = {
        "launcher_pid": os.getpid(),
        "server_pid": server_pid,
        "watcher_pid": watcher_pid,
    }
    with open(PID_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    ensure_dirs()

    print("=== Rocket League MVP Launcher ===")
    print()
    print("Lancement du serveur FastAPI...")
    server_log = open(SERVER_LOG, "a", encoding="utf-8")
    env = {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", **os.environ}
    server = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", MAIN_APP, "--reload", "--ws", "websockets"],
        cwd=PROJECT_DIR,
        stdout=server_log,
        stderr=server_log,
        env=env,
    )

    time.sleep(2)

    print("Lancement du watcher de replay...")
    watcher_log = open(WATCHER_LOG, "a", encoding="utf-8")
    env = {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", **os.environ}
    watcher = subprocess.Popen(
        [PYTHON_EXE, WATCHER_SCRIPT],
        cwd=PROJECT_DIR,
        stdout=watcher_log,
        stderr=watcher_log,
        env=env,
    )

    save_pids(server.pid, watcher.pid)

    print("Ouverture du dashboard...")
    subprocess.Popen(["cmd", "/c", "start", "", "http://127.0.0.1:8000"], shell=False)

    print()
    print("Tracker lance")
    print(f"Dashboard : http://127.0.0.1:8000")
    print(f"PID file : {PID_FILE}")
    print(f"Logs serveur : {SERVER_LOG}")
    print(f"Logs watcher : {WATCHER_LOG}")
    print()
    print("Cette fenetre se fermera automatiquement quand le tracker sera arrete.")
    print()

    try:
        while True:
            server_alive = is_pid_running(server.pid)
            watcher_alive = is_pid_running(watcher.pid)

            if not server_alive and not watcher_alive:
                print("Serveur et watcher arretes. Fermeture du launcher...")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nInterruption clavier detectee, fermeture du launcher.")
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

    sys.exit(0)


if __name__ == "__main__":
    main()