import json
import os
import subprocess
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(PROJECT_DIR, "tracker_pids.json")


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


def terminate_pid(pid: int, label: str) -> None:
    if not pid:
        print(f"{label} : PID absent.")
        return

    if not is_pid_running(pid):
        print(f"{label} deja arrete (PID {pid}).")
        return

    print(f"Arret de {label} (PID {pid})...")

    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    for _ in range(10):
        if not is_pid_running(pid):
            print(f"{label} arrete.")
            return
        time.sleep(0.5)

    print(f"{label} semble encore actif apres tentative d'arret.")


def main() -> None:
    print("\n=== Arret Rocket League MVP Tracker ===\n")

    if not os.path.exists(PID_FILE):
        print("Aucun fichier PID trouve.")
        print("Le tracker n'est peut-etre pas lance, ou le fichier a deja ete supprime.")
        return

    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"Impossible de lire le fichier PID : {exc}")
        return

    launcher_pid = data.get("launcher_pid")
    server_pid = data.get("server_pid")
    watcher_pid = data.get("watcher_pid")

    terminate_pid(watcher_pid, "watcher")
    terminate_pid(server_pid, "serveur FastAPI")

    time.sleep(2)

    if launcher_pid and is_pid_running(launcher_pid):
        print(f"Launcher encore actif (PID {launcher_pid}).")
        print("Il devrait se fermer automatiquement.")
    else:
        print("Launcher deja ferme ou en cours de fermeture.")

    try:
        os.remove(PID_FILE)
        print("Fichier PID supprime.")
    except OSError:
        print("Impossible de supprimer le fichier PID, ou deja supprime.")

    print()
    print("Tracker arrete proprement.")


if __name__ == "__main__":
    main()