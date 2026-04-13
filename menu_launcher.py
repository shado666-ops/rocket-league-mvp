import json
import os
import shutil
import subprocess
import sys
import time
import requests
import webbrowser
from datetime import datetime

# --- Configuration Paths ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable  # Fallback to current python if venv not found

DB_FILE = os.path.join(PROJECT_DIR, "data", "app.db")
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
BACKUPS_DIR = os.path.join(PROJECT_DIR, "backups")
PID_FILE = os.path.join(PROJECT_DIR, "tracker_pids.json")
REPLAY_DIR = os.path.join(os.environ.get('USERPROFILE', ''), "Documents", "My Games", "Rocket League", "TAGame", "Demos")

# --- ANSI Colors ---
C_RESET = "\033[0m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_WHITE = "\033[97m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"

def colorize(text, color): return f"{color}{text}{C_RESET}"

def clear_screen(): os.system("cls" if os.name == "nt" else "clear")

def is_process_running(name, is_python=True):
    """Vérifie si un processus tourne. name est le script ou l'exe."""
    try:
        if os.name == "nt":
            if is_python:
                # Pour les scripts python, on doit checker la commandline
                cmd = f'wmic process where "caption=\'python.exe\' and commandline like \'%{name}%\'" get commandline /format:list'
            else:
                # Pour les exe (ngrok), tasklist est plus fiable
                cmd = f'tasklist /FI "IMAGENAME eq {name}" /NH /FO CSV'
                
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
            if is_python:
                for line in output.splitlines():
                    if "CommandLine=" in line and name in line and "menu_launcher" not in line:
                        return True
            else:
                return name.lower() in output.lower()
        return False
    except: return False

def check_production_health():
    """Vérifie si le site en ligne répond."""
    try:
        response = requests.get("https://notre-club-rl.fr/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_process_states():
    return {
        "server_ok": check_production_health(),
        "watcher_ok": is_process_running("watcher.py"),
        "ngrok_ok": False # Ngrok plus utilisé en prod
    }

def get_ngrok_url():
    """Récupère l'URL publique de ngrok via son API locale."""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=1)
        if response.status_code == 200:
            tunnels = response.json().get("tunnels", [])
            if tunnels:
                return tunnels[0].get("public_url")
    except:
        pass
    return None

def get_club_members_count():
    try:
        # Add root to sys.path to ensure database/models are found
        root = os.path.dirname(os.path.abspath(__file__))
        if root not in sys.path: sys.path.insert(0, root)
            
        from database import SessionLocal
        from models import ClubMember
        db = SessionLocal()
        count = db.query(ClubMember).count()
        db.close()
        return colorize(str(count), C_WHITE)
    except Exception as e:
        return colorize("?", C_YELLOW)

def get_last_backup_info():
    if not os.path.exists(BACKUPS_DIR): return colorize("aucune", C_DIM)
    files = [os.path.join(BACKUPS_DIR, f) for f in os.listdir(BACKUPS_DIR) if f.endswith(".db")]
    if not files: return colorize("aucune", C_DIM)
    latest = max(files, key=os.path.getmtime)
    return colorize(datetime.fromtimestamp(os.path.getmtime(latest)).strftime("%d/%m/%Y %H:%M"), C_WHITE)

def show_header():
    states = get_process_states()
    
    def fmt_on_off(v): return colorize("EN LIGNE", C_GREEN) if v else colorize("HORS LIGNE", C_RED)
    def fmt_watcher(v): return colorize("ACTIF", C_GREEN) if v else colorize("INACTIF", C_RED)

    print(colorize("="*64, C_CYAN))
    print(colorize("               ROCKET LEAGUE MVP - MODE PRODUCTION", C_BOLD))
    print(colorize("="*64, C_CYAN))
    print(f"{'Site Production':<18}: {fmt_on_off(states['server_ok'])}")
    print(f"{'URL':<18}: {colorize('https://notre-club-rl.fr', C_CYAN)}")
    print(f"{'Watcher Replay':<18}: {fmt_watcher(states['watcher_ok'])}")
    
    print(colorize("-" * 64, C_DIM))
    
    exists = lambda p: colorize("present", C_GREEN) if os.path.exists(p) else colorize("absent", C_RED)
    print(f"{'Dossier replays':<18}: {exists(REPLAY_DIR)}")
    print(f"{'Dossier logs':<18}: {exists(LOGS_DIR)}")
    print(colorize("-" * 64, C_DIM))

def show_menu():
    print(f"{colorize('ACTIONS', C_CYAN)}")
    print(f" {colorize('1.', C_CYAN)} DEMARRER LE WATCHER (Tracker temps réel)")
    print(f" {colorize('2.', C_CYAN)} Arreter le Watcher")
    print(f" {colorize('3.', C_CYAN)} Ouvrir le Dashboard (https://notre-club-rl.fr)")
    print()
    print(f"{colorize('OUTILS', C_YELLOW)}")
    print(f" {colorize('4.', C_YELLOW)} Ouvrir le dossier des replays")
    print(f" {colorize('5.', C_YELLOW)} Ouvrir le dossier des logs")
    print()
    print(f" {colorize('6.', C_RED)} Quitter")
    print(colorize("-" * 64, C_DIM))
    print(colorize("Conseil : laisse le serveur tourner pour garder la page accessible.", C_DIM))

def start_server():
    states = get_process_states()
    if not states["server_ok"]:
        print(colorize("\nDémarrage du serveur FastAPI...", C_CYAN))
        cmd = f'start "RL_SERVER_WIN" "{PYTHON_EXE}" main.py'
        subprocess.Popen(cmd, cwd=PROJECT_DIR, shell=True)
        time.sleep(1.5)
        return True
    else:
        print(colorize("\nLe serveur est déjà lancé.", C_YELLOW))
        return False

def start_watcher():
    states = get_process_states()
    if not states["watcher_ok"]:
        print(colorize("Démarrage du Watcher...", C_CYAN))
        cmd = f'start "RL_WATCHER_WIN" "{PYTHON_EXE}" agent/watcher.py'
        subprocess.Popen(cmd, cwd=PROJECT_DIR, shell=True)
        time.sleep(1)
        return True
    else:
        print(colorize("\nLe watcher est déjà lancé.", C_YELLOW))
        return False

def start_tracker():
    """Démarre tout."""
    s = start_server()
    w = start_watcher()
    if s or w:
        print(colorize("\nSystème démarré.", C_GREEN))
        time.sleep(1)
        os.system("start http://localhost:8000")
    time.sleep(1)

def stop_process(pid_name, title_filter):
    """Méthode générique pour arrêter un processus."""
    try:
        # 1. Par PID
        pid_path = os.path.join(PROJECT_DIR, "data", pid_name)
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r") as f:
                    pid = f.read().strip()
                if pid:
                    os.system(f'taskkill /F /PID {pid} /T >nul 2>&1')
                    os.remove(pid_path)
                    return True
            except: pass

        # 2. Par Titre (Fallback)
        os.system(f'taskkill /F /FI "WINDOWTITLE eq {title_filter}*" /T >nul 2>&1')
        return True
    except:
        return False

def stop_watcher():
    print(colorize("\nArrêt du Watcher...", C_RED))
    stop_process("watcher.pid", "RL_WATCHER_WIN")
    print(colorize("Watcher arrêté.", C_GREEN))
    time.sleep(1)

def stop_tracker():
    print(colorize("\nArrêt complet (Serveur + Watcher)...", C_RED))
    stop_process("server.pid", "RL_SERVER_WIN")
    stop_process("watcher.pid", "RL_WATCHER_WIN")
    stop_ngrok()
    print(colorize("Tout est arrêté.", C_GREEN))
    time.sleep(1)

def start_ngrok():
    if is_process_running("ngrok.exe", is_python=False):
        print(colorize("\nNgrok est déjà en cours d'exécution.", C_CYAN))
        return

    # Lancement manuel de ngrok sur le port 8000
    print(colorize("\nDémarrage manuel de ngrok...", C_CYAN))
    print(colorize("Note: Ngrok sera lié au serveur (port 8000).", C_DIM))
    
    # On lance ngrok dans une nouvelle fenêtre pour ne pas bloquer le menu
    cmd = 'start "RL_NGROK_WIN" ngrok http 8000'
    os.system(cmd)
    
    time.sleep(2)

def stop_ngrok():
    print(colorize("\nArrêt de ngrok...", C_RED))
    # On tue par nom d'image et on force l'arrêt de l'arbre de processus
    os.system('taskkill /F /IM ngrok.exe /T >nul 2>&1')
    # Backup pour fermer les fenêtres CMD orphelines liées si elles existent
    os.system('taskkill /F /FI "WINDOWTITLE eq RL_NGROK_WIN*" /T >nul 2>&1')
    print(colorize("Ngrok arrêté.", C_GREEN))
    time.sleep(1.5)

def pause():
    input(colorize("\nAppuie sur Entree pour continuer...", C_YELLOW))

def reset_database():
    confirm = input(colorize("\nSupprimer toutes les données ? (o/n) : ", C_RED)).strip().lower()
    if confirm == 'o':
        # Selective clear to avoid file locking
        try:
            from database import SessionLocal
            from models import Match, Player, MatchPlayerStat, ClubMember
            db = SessionLocal()
            db.query(MatchPlayerStat).delete()
            db.query(Match).delete()
            db.query(Player).delete()
            db.query(ClubMember).delete()
            db.commit()
            db.close()
            print(colorize("Base de données réinitialisée.", C_GREEN))
        except Exception as e:
            print(colorize(f"Erreur : {e}", C_RED))

def manage_members(action):
    try:
        from database import SessionLocal
        from models import ClubMember
        db = SessionLocal()
        if action == "list":
            members = db.query(ClubMember).all()
            print(colorize("\nMembres du club :", C_BOLD))
            for m in members: print(f"- {m.display_name}")
        elif action == "add":
            name = input("Nom du nouveau membre : ").strip()
            if name:
                db.add(ClubMember(display_name=name, is_active=True))
                db.commit()
                print(colorize(f"Membre {name} ajouté.", C_GREEN))
        elif action == "delete":
            name = input("Nom du membre à supprimer : ").strip()
            member = db.query(ClubMember).filter(ClubMember.display_name == name).first()
            if member:
                db.delete(member)
                db.commit()
                print(colorize(f"Membre {name} supprimé.", C_GREEN) if member else colorize("Non trouvé.", C_YELLOW))
        db.close()
    except Exception as e:
        print(colorize(f"Erreur : {e}", C_RED))

def main_loop():
    while True:
        clear_screen()
        show_header()
        show_menu()
        choice = input(colorize("Choix : ", C_YELLOW)).strip()
        
        if choice == "1": start_watcher(); pause()
        elif choice == "2": stop_watcher(); pause()
        elif choice == "3": os.system("start https://notre-club-rl.fr")
        elif choice == "4": os.system(f"explorer \"{REPLAY_DIR}\"")
        elif choice == "5": os.system(f"explorer \"{LOGS_DIR}\"")
        elif choice == "6": break
        else:
            print(colorize("Option inconnue.", C_RED)); time.sleep(1)

if __name__ == "__main__":
    if os.name == "nt": os.system("") 
    main_loop()
