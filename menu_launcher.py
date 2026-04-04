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

def get_process_states():
    return {
        "server_ok": is_process_running("main.py"),
        "watcher_ok": is_process_running("watcher.py"),
        "ngrok_ok": is_process_running("ngrok.exe", is_python=False)
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
    all_ok = states["server_ok"] and states["watcher_ok"]
    status = "en cours" if all_ok else ("partiellement lance" if states["server_ok"] or states["watcher_ok"] else "arrete")
    
    def fmt_status(s):
        if s == "en cours": return colorize(s, C_GREEN)
        if s == "partiellement lance": return colorize(s, C_YELLOW)
        return colorize(s, C_RED)

    def fmt_on_off(v): return colorize("ON", C_GREEN) if v else colorize("OFF", C_RED)

    print(colorize("="*64, C_CYAN))
    print(colorize("               ROCKET LEAGUE MVP - MENU PRO", C_BOLD))
    print(colorize("="*64, C_CYAN))
    print(f"{'Tracker':<18}: {fmt_status(status)}")
    print(f"{'Serveur FastAPI':<18}: {fmt_on_off(states['server_ok'])}")
    print(f"{'Watcher replay':<18}: {fmt_on_off(states['watcher_ok'])}")
    
    ngrok_url = get_ngrok_url() if states["ngrok_ok"] else None
    public_status = colorize(ngrok_url, C_CYAN) if ngrok_url else fmt_on_off(False)
    print(f"{'Accès Public (ngrok)':<18}: {public_status}")
    
    print(colorize("-" * 64, C_DIM))
    
    exists = lambda p: colorize("presente" if "db" in p else "present", C_GREEN) if os.path.exists(p) else colorize("absente" if "db" in p else "absent", C_RED)
    print(f"{'Base de donnees':<18}: {exists(DB_FILE)}")
    print(f"{'Dossier replays':<18}: {exists(REPLAY_DIR)}")
    print(f"{'Dossier logs':<18}: {exists(LOGS_DIR)}")
    print(f"{'Membres du club':<18}: {get_club_members_count()}")
    print(f"{'Derniere backup':<18}: {get_last_backup_info()}")
    print(colorize("-" * 64, C_DIM))

def show_menu():
    print(f"{colorize('TRACKER', C_CYAN)}")
    print(f" {colorize('1.', C_CYAN)} Demarrer le tracker")
    print(f" {colorize('2.', C_CYAN)} Ouvrir le dashboard")
    print(f" {colorize('3.', C_CYAN)} Voir le statut detaille (API)")
    print(f" {colorize('4.', C_CYAN)} Sauvegarder la base")
    print(f" {colorize('5.', C_CYAN)} Reset la base")
    print(f" {colorize('6.', C_CYAN)} Ouvrir le dossier des replays")
    print(f" {colorize('7.', C_CYAN)} Arreter le tracker")
    print()
    print(f"{colorize('CLUB', C_GREEN)}")
    print(f" {colorize('8.', C_GREEN)} Voir les membres du club")
    print(f" {colorize('9.', C_GREEN)} Ajouter un membre du club")
    print(f" {colorize('10.', C_GREEN)} Supprimer un membre du club")
    print()
    print(f"{colorize('LOGS', C_MAGENTA)}")
    print(f" {colorize('11.', C_MAGENTA)} Ouvrir le dossier des logs")
    print(f" {colorize('12.', C_MAGENTA)} Ouvrir server.log")
    print(f" {colorize('13.', C_MAGENTA)} Ouvrir watcher.log")
    print(f" {colorize('14.', C_MAGENTA)} Vider les logs")
    print()
    print(f"{colorize('DISTANT (NGROK)', C_YELLOW)}")
    print(f" {colorize('15.', C_YELLOW)} Démarrer ngrok (accès public)")
    print(f" {colorize('16.', C_YELLOW)} Arrêter ngrok")
    print()
    print(f" {colorize('17.', C_RED)} Quitter")
    print(colorize("-" * 64, C_DIM))
    print(colorize("Conseil : demarre le tracker avant d'ouvrir le dashboard.", C_DIM))

def start_tracker():
    states = get_process_states()
    
    if not states["server_ok"]:
        print(colorize("\nDémarrage du serveur FastAPI...", C_CYAN))
        # Unique title for robust killing, scripts will no longer override it
        cmd = f'start "RL_SERVER_WIN" "{PYTHON_EXE}" main.py'
        subprocess.Popen(cmd, cwd=PROJECT_DIR, shell=True)
    
    if not states["watcher_ok"]:
        print(colorize("Démarrage du Watcher...", C_CYAN))
        cmd = f'start "RL_WATCHER_WIN" "{PYTHON_EXE}" agent/watcher.py'
        subprocess.Popen(cmd, cwd=PROJECT_DIR, shell=True)
    
    # The status will be refreshed on next loop thanks to is_window_running
    print(colorize("\nTracker démarré dans de nouvelles fenêtres.", C_GREEN))
    
    # Auto-open dashboard
    time.sleep(2)
    os.system("start http://localhost:8000")
    
    # Note: Ngrok est maintenant lancé automatiquement par main.py
    
    time.sleep(1.5)

def stop_tracker():
    print(colorize("\nArrêt des processus Rocket League Tracker...", C_RED))
    try:
        # 1. Kill by PIDs (Stored in data/*.pid) - Most reliable method
        for pid_name in ["server.pid", "watcher.pid"]:
            pid_path = os.path.join(PROJECT_DIR, "data", pid_name)
            if os.path.exists(pid_path):
                try:
                    with open(pid_path, "r") as f:
                        pid = f.read().strip()
                    if pid:
                        # /T kills the tree (including the CMD window starting it)
                        os.system(f'taskkill /F /PID {pid} /T >nul 2>&1')
                        os.remove(pid_path)
                except: pass

        # 2. Fallback by titles (for windows started but whose scripts didn't write PID yet)
        os.system('taskkill /F /FI "WINDOWTITLE eq RL_SERVER_WIN*" /T >nul 2>&1')
        os.system('taskkill /F /FI "WINDOWTITLE eq RL_WATCHER_WIN*" /T >nul 2>&1')
        
        # Auto-stop ngrok
        stop_ngrok()
        
    except: pass
    
    print(colorize("Processus arrêtés.", C_GREEN))
    time.sleep(1.5)

    if is_process_running("ngrok.exe", is_python=False):
        print(colorize("\nNgrok est déjà en cours d'exécution.", C_CYAN))
        return

    print(colorize("\nNgrok sera lancé automatiquement par le serveur (Option 1).", C_YELLOW))
    print(colorize("Il apparaîtra directement dans la fenêtre du serveur.", C_WHITE))
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
        
        if choice == "1": start_tracker(); pause()
        elif choice == "2": os.system("start http://localhost:8000")
        elif choice == "3": os.system("start http://localhost:8000/docs"); pause()
        elif choice == "4": 
             os.system(f"{PYTHON_EXE} -c \"import shutil, os, datetime; ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); os.makedirs('backups', exist_ok=True); shutil.copy2('data/app.db', f'backups/app_backup_{{ts}}.db'); print('Backup OK')\"")
             pause()
        elif choice == "5": reset_database(); pause()
        elif choice == "6": os.system(f"explorer \"{REPLAY_DIR}\"")
        elif choice == "7": stop_tracker(); pause()
        elif choice == "8": manage_members("list"); pause()
        elif choice == "9": manage_members("add"); pause()
        elif choice == "10": manage_members("delete"); pause()
        elif choice == "11": os.system(f"explorer \"{LOGS_DIR}\"")
        elif choice == "12": os.system(f"notepad \"{LOGS_DIR}/server.log\"")
        elif choice == "13": os.system(f"notepad \"{LOGS_DIR}/watcher.log\"")
        elif choice == "14": 
            for f in ["server.log", "watcher.log"]:
                with open(os.path.join(LOGS_DIR, f), "w") as log: log.write(f"--- Cleared at {datetime.now()} ---\n")
            print("Logs vidés."); pause()
        elif choice == "15": start_ngrok(); pause()
        elif choice == "16": stop_ngrok(); pause()
        elif choice == "17": break
        else:
            print(colorize("Option inconnue.", C_RED)); time.sleep(1)

if __name__ == "__main__":
    if os.name == "nt": os.system("") 
    main_loop()
