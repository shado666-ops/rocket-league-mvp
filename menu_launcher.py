import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")

LAUNCHER_SCRIPT = os.path.join(PROJECT_DIR, "launcher.py")
STOP_SCRIPT = os.path.join(PROJECT_DIR, "stop_tracker.py")

DB_FILE = os.path.join(PROJECT_DIR, "data", "app.db")
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
BACKUPS_DIR = os.path.join(PROJECT_DIR, "backups")
PID_FILE = os.path.join(PROJECT_DIR, "tracker_pids.json")

SERVER_LOG = os.path.join(LOGS_DIR, "server.log")
WATCHER_LOG = os.path.join(LOGS_DIR, "watcher.log")

REPLAY_DIR = r"C:\Users\perno\Documents\My Games\Rocket League\TAGame\Demos"

COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{COLOR_RESET}"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input(colorize("\nAppuie sur Entree pour continuer...", COLOR_YELLOW))


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


def read_pid_data() -> dict:
    if not os.path.exists(PID_FILE):
        return {}

    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_process_states() -> dict:
    data = read_pid_data()

    launcher_pid = data.get("launcher_pid")
    server_pid = data.get("server_pid")
    watcher_pid = data.get("watcher_pid")

    launcher_ok = bool(launcher_pid) and is_pid_running(launcher_pid)
    server_ok = bool(server_pid) and is_pid_running(server_pid)
    watcher_ok = bool(watcher_pid) and is_pid_running(watcher_pid)

    return {
        "launcher_pid": launcher_pid,
        "server_pid": server_pid,
        "watcher_pid": watcher_pid,
        "launcher_ok": launcher_ok,
        "server_ok": server_ok,
        "watcher_ok": watcher_ok,
    }


def get_tracker_status() -> str:
    states = get_process_states()

    if states["launcher_ok"] or states["server_ok"] or states["watcher_ok"]:
        if states["server_ok"] and states["watcher_ok"]:
            return "en cours"
        return "partiellement lance"

    return "arrete"


def format_status(status: str) -> str:
    if status == "en cours":
        return colorize(status, COLOR_GREEN)
    if status == "partiellement lance":
        return colorize(status, COLOR_YELLOW)
    if status == "arrete":
        return colorize(status, COLOR_RED)
    return colorize(status, COLOR_CYAN)


def format_on_off(value: bool) -> str:
    return colorize("ON", COLOR_GREEN) if value else colorize("OFF", COLOR_RED)


def print_rule(char: str = "=", width: int = 64, color: str = COLOR_CYAN) -> None:
    print(colorize(char * width, color))


def section_title(title: str, color: str) -> None:
    print(colorize(title, color))


def print_item(number: int, label: str, color: str) -> None:
    print(f"{colorize(f'{number:>2}.', color)} {label}")


def get_last_backup_info() -> str:
    if not os.path.exists(BACKUPS_DIR):
        return colorize("aucune", COLOR_DIM)

    files = [
        os.path.join(BACKUPS_DIR, f)
        for f in os.listdir(BACKUPS_DIR)
        if f.endswith(".db")
    ]
    if not files:
        return colorize("aucune", COLOR_DIM)

    latest = max(files, key=os.path.getmtime)
    dt = datetime.fromtimestamp(os.path.getmtime(latest)).strftime("%d/%m/%Y %H:%M")
    return colorize(dt, COLOR_WHITE)


def get_club_members_count() -> str:
    if not os.path.exists(PYTHON_EXE):
        return colorize("?", COLOR_YELLOW)

    code = r"""
from database import SessionLocal
from models import ClubMember

db = SessionLocal()
try:
    print(db.query(ClubMember).count())
finally:
    db.close()
"""
    try:
        result = subprocess.run(
            [PYTHON_EXE, "-c", code],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        value = result.stdout.strip()
        return colorize(value if value else "0", COLOR_WHITE)
    except Exception:
        return colorize("?", COLOR_YELLOW)


def show_header() -> None:
    states = get_process_states()
    status = get_tracker_status()

    print_rule("=", 64, COLOR_CYAN)
    print(colorize("               ROCKET LEAGUE MVP - MENU PRO", COLOR_BOLD))
    print_rule("=", 64, COLOR_CYAN)

    print(f"{colorize('Tracker', COLOR_WHITE):<18}: {format_status(status)}")
    print(f"{colorize('Launcher', COLOR_WHITE):<18}: {format_on_off(states['launcher_ok'])}")
    print(f"{colorize('Serveur FastAPI', COLOR_WHITE):<18}: {format_on_off(states['server_ok'])}")
    print(f"{colorize('Watcher replay', COLOR_WHITE):<18}: {format_on_off(states['watcher_ok'])}")
    print_rule("-", 64, COLOR_DIM)

    db_state = colorize("presente", COLOR_GREEN) if os.path.exists(DB_FILE) else colorize("absente", COLOR_RED)
    replay_state = colorize("present", COLOR_GREEN) if os.path.exists(REPLAY_DIR) else colorize("absent", COLOR_RED)
    logs_state = colorize("present", COLOR_GREEN) if os.path.exists(LOGS_DIR) else colorize("absent", COLOR_RED)

    print(f"{colorize('Base de donnees', COLOR_WHITE):<18}: {db_state}")
    print(f"{colorize('Dossier replays', COLOR_WHITE):<18}: {replay_state}")
    print(f"{colorize('Dossier logs', COLOR_WHITE):<18}: {logs_state}")
    print(f"{colorize('Membres du club', COLOR_WHITE):<18}: {get_club_members_count()}")
    print(f"{colorize('Derniere backup', COLOR_WHITE):<18}: {get_last_backup_info()}")

    print_rule("-", 64, COLOR_DIM)


def show_menu() -> None:
    section_title("TRACKER", COLOR_CYAN)
    print_item(1, "Demarrer le tracker", COLOR_CYAN)
    print_item(2, "Ouvrir le dashboard", COLOR_CYAN)
    print_item(3, "Voir le statut detaille", COLOR_CYAN)
    print_item(4, "Sauvegarder la base", COLOR_CYAN)
    print_item(5, "Reset la base", COLOR_CYAN)
    print_item(6, "Ouvrir le dossier des replays", COLOR_CYAN)
    print_item(7, "Arreter le tracker", COLOR_CYAN)
    print()

    section_title("CLUB", COLOR_GREEN)
    print_item(8, "Voir les membres du club", COLOR_GREEN)
    print_item(9, "Ajouter un membre du club", COLOR_GREEN)
    print_item(10, "Supprimer un membre du club", COLOR_GREEN)
    print()

    section_title("LOGS", COLOR_MAGENTA)
    print_item(11, "Ouvrir le dossier des logs", COLOR_MAGENTA)
    print_item(12, "Ouvrir server.log", COLOR_MAGENTA)
    print_item(13, "Ouvrir watcher.log", COLOR_MAGENTA)
    print_item(14, "Vider les logs", COLOR_MAGENTA)
    print()

    print_item(15, "Quitter", COLOR_RED)
    print_rule("-", 64, COLOR_DIM)
    print(colorize("Conseil : demarre le tracker avant d'ouvrir le dashboard.", COLOR_DIM))


def start_tracker() -> None:
    print(colorize("\nLancement du tracker...", COLOR_CYAN))

    if not os.path.exists(PYTHON_EXE):
        print(colorize("Python du venv introuvable.", COLOR_RED))
        return

    if not os.path.exists(LAUNCHER_SCRIPT):
        print(colorize("launcher.py introuvable.", COLOR_RED))
        return

    subprocess.Popen(
        ["cmd", "/c", "start", "Rocket League MVP Launcher", PYTHON_EXE, LAUNCHER_SCRIPT],
        cwd=PROJECT_DIR,
        shell=False,
    )

    time.sleep(2)
    print(colorize("Launcher demarre dans une nouvelle fenetre.", COLOR_GREEN))


def stop_tracker() -> None:
    print(colorize("\nArret du tracker...", COLOR_CYAN))

    stop_script = os.path.join(PROJECT_DIR, "stop_tracker.py")
    if not os.path.exists(PYTHON_EXE) or not os.path.exists(stop_script):
        print(colorize("Impossible de trouver stop_tracker.py ou python.exe.", COLOR_RED))
        return

    result = subprocess.run(
        [PYTHON_EXE, stop_script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(colorize(result.stderr.strip(), COLOR_RED))

    print(colorize("\nSi launcher.py est a jour, sa fenetre va se fermer automatiquement.", COLOR_GREEN))


def reset_database() -> None:
    if not os.path.exists(DB_FILE):
        print(colorize("\nBase deja absente.", COLOR_YELLOW))
        return

    confirm = input(colorize("\nSupprimer la base de donnees ? (o/n) : ", COLOR_YELLOW)).strip().lower()
    if confirm != "o":
        print(colorize("Annule.", COLOR_YELLOW))
        return

    try:
        os.remove(DB_FILE)
        print(colorize("Base supprimee.", COLOR_GREEN))
    except Exception as exc:
        print(colorize(f"Erreur suppression DB : {exc}", COLOR_RED))


def open_dashboard() -> None:
    subprocess.Popen(["cmd", "/c", "start", "", "http://127.0.0.1:8000"], shell=False)
    print(colorize("\nDashboard ouvert dans le navigateur.", COLOR_GREEN))


def show_status() -> None:
    status = get_tracker_status()
    states = get_process_states()

    print(colorize("\n=== STATUT DETAILLE DU TRACKER ===", COLOR_BOLD))
    print(f"Tracker global     : {format_status(status)}")
    print(f"Launcher           : {format_on_off(states['launcher_ok'])}   PID={states['launcher_pid']}")
    print(f"Serveur FastAPI    : {format_on_off(states['server_ok'])}   PID={states['server_pid']}")
    print(f"Watcher replay     : {format_on_off(states['watcher_ok'])}   PID={states['watcher_pid']}")

    print()
    print(
        f"Base de donnees    : "
        f"{colorize('presente', COLOR_GREEN) if os.path.exists(DB_FILE) else colorize('absente', COLOR_RED)}"
    )
    print(
        f"Dossier logs       : "
        f"{colorize('present', COLOR_GREEN) if os.path.exists(LOGS_DIR) else colorize('absent', COLOR_RED)}"
    )
    print(
        f"Dossier backups    : "
        f"{colorize('present', COLOR_GREEN) if os.path.exists(BACKUPS_DIR) else colorize('absent', COLOR_YELLOW)}"
    )

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(colorize("\nContenu tracker_pids.json :", COLOR_BOLD))
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(colorize(f"Impossible de lire le fichier PID : {exc}", COLOR_RED))
    else:
        print(colorize("\nAucun fichier PID present.", COLOR_YELLOW))


def open_replays_folder() -> None:
    if not os.path.exists(REPLAY_DIR):
        print(colorize(f"\nDossier replays introuvable : {REPLAY_DIR}", COLOR_RED))
        return
    subprocess.Popen(["explorer", REPLAY_DIR])
    print(colorize("Dossier replays ouvert.", COLOR_GREEN))


def open_logs_folder() -> None:
    if not os.path.exists(LOGS_DIR):
        print(colorize("\nDossier logs introuvable.", COLOR_RED))
        return
    subprocess.Popen(["explorer", LOGS_DIR])
    print(colorize("Dossier logs ouvert.", COLOR_GREEN))


def backup_database() -> None:
    if not os.path.exists(DB_FILE):
        print(colorize("\nAucune base a sauvegarder.", COLOR_RED))
        return

    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUPS_DIR, f"app_backup_{timestamp}.db")
    shutil.copy2(DB_FILE, backup_path)
    print(colorize(f"\nSauvegarde creee : {backup_path}", COLOR_GREEN))


def open_file_if_exists(path: str) -> None:
    if not os.path.exists(path):
        print(colorize(f"\nFichier introuvable : {path}", COLOR_RED))
        return
    os.startfile(path)


def clear_logs() -> None:
    os.makedirs(LOGS_DIR, exist_ok=True)
    for path in [SERVER_LOG, WATCHER_LOG]:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
    print(colorize("\nLogs vides.", COLOR_GREEN))


def run_inline_python(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON_EXE, "-c", code],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )


def list_club_members() -> None:
    code = r"""
from database import SessionLocal
from models import ClubMember

db = SessionLocal()
try:
    members = db.query(ClubMember).order_by(ClubMember.display_name.asc()).all()
    if not members:
        print("Aucun membre du club.")
    else:
        for m in members:
            status = "actif" if m.is_active else "inactif"
            print(f"- {m.display_name} ({status})")
finally:
    db.close()
"""
    result = run_inline_python(code)
    if result.stdout.strip():
        print("\n" + result.stdout.strip())
    if result.stderr.strip():
        print(colorize(result.stderr.strip(), COLOR_RED))


def add_club_member() -> None:
    name = input(colorize("\nPseudo du membre du club a ajouter : ", COLOR_YELLOW)).strip()
    if not name:
        print(colorize("Aucun pseudo saisi.", COLOR_RED))
        return

    code = rf"""
from database import Base, SessionLocal, engine
from models import ClubMember

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    existing = db.query(ClubMember).filter(ClubMember.display_name == {name!r}).first()
    if existing:
        print("Ce membre existe deja.")
    else:
        db.add(ClubMember(display_name={name!r}, is_active=True))
        db.commit()
        print("Membre ajoute avec succes.")
finally:
    db.close()
"""
    result = run_inline_python(code)
    if result.stdout.strip():
        print("\n" + result.stdout.strip())
    if result.stderr.strip():
        print(colorize(result.stderr.strip(), COLOR_RED))


def remove_club_member() -> None:
    name = input(colorize("\nPseudo du membre du club a supprimer : ", COLOR_YELLOW)).strip()
    if not name:
        print(colorize("Aucun pseudo saisi.", COLOR_RED))
        return

    code = rf"""
from database import SessionLocal
from models import ClubMember

db = SessionLocal()
try:
    member = db.query(ClubMember).filter(ClubMember.display_name == {name!r}).first()
    if not member:
        print("Membre introuvable.")
    else:
        db.delete(member)
        db.commit()
        print("Membre supprime avec succes.")
finally:
    db.close()
"""
    result = run_inline_python(code)
    if result.stdout.strip():
        print("\n" + result.stdout.strip())
    if result.stderr.strip():
        print(colorize(result.stderr.strip(), COLOR_RED))


def main() -> None:
    while True:
        clear_screen()
        show_header()
        show_menu()

        choice = input(colorize("\nChoix : ", COLOR_YELLOW)).strip()

        if choice == "1":
            start_tracker()
        elif choice == "2":
            open_dashboard()
        elif choice == "3":
            show_status()
        elif choice == "4":
            backup_database()
        elif choice == "5":
            reset_database()
        elif choice == "6":
            open_replays_folder()
        elif choice == "7":
            stop_tracker()
        elif choice == "8":
            list_club_members()
        elif choice == "9":
            add_club_member()
        elif choice == "10":
            remove_club_member()
        elif choice == "11":
            open_logs_folder()
        elif choice == "12":
            open_file_if_exists(SERVER_LOG)
        elif choice == "13":
            open_file_if_exists(WATCHER_LOG)
        elif choice == "14":
            clear_logs()
        elif choice == "15":
            print(colorize("\nFermeture du menu.", COLOR_RED))
            sys.exit(0)
        else:
            print(colorize("\nChoix invalide.", COLOR_RED))

        pause()


if __name__ == "__main__":
    main()