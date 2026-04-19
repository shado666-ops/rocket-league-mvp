import os
import sys

# Logging configuration
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "server.log")

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        if self.log:
            self.log.write(message)
            self.log.flush()

    def flush(self):
        self.terminal.flush()
        if self.log:
            self.log.flush()

    def isatty(self):
        return self.terminal.isatty()

    def fileno(self):
        return self.terminal.fileno()

sys.stdout = Logger(LOG_FILE)
sys.stderr = sys.stdout

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, status
import models
from fastapi.staticfiles import StaticFiles
from app.websocket_manager import manager
import threading
import time
import subprocess

from app.routes.matches import router as matches_router
from app.routes.players import router as players_router
from app.routes.analytics import router as analytics_router
from app.routes.pepites import router as pepites_router
from app.routes.admin import router as admin_router
from app.routes.notifications import router as notifications_router
from app.routes.auth import router as auth_router
from app.dependencies import get_current_user, get_current_admin
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import ClubMember

app = FastAPI(title="Rocket League MVP Tracker")

def seed_database():
    """Initialise les membres de base du club et le compte admin s'ils n'existent pas."""
    db: Session = SessionLocal()
    try:
        # Membres du club
        primary_members = ["Shado666", "Kalibakbak", "Ezy", "JulienYo"]
        for name in primary_members:
            exists = db.query(models.ClubMember).filter(models.ClubMember.display_name == name).first()
            if not exists:
                print(f"[Seeding] Ajout du membre : {name}")
                db.add(models.ClubMember(display_name=name, is_active=True))
        
        print("[Seeding] Vérification du compte ADMIN...")
        from app.services.auth_service import get_password_hash
        admin_pseudo = "Shado666"
        admin_pass = "Cloudff7!"
        admin_exists = db.query(models.User).filter(models.User.username == admin_pseudo).first()
        if not admin_exists:
            print(f"[Seeding] Création du compte ADMIN : {admin_pseudo}")
            new_admin = models.User(
                username=admin_pseudo,
                hashed_password=get_password_hash(admin_pass),
                role="admin",
                is_approved=True
            )
            # Lier à la fiche membre du même nom
            member = db.query(models.ClubMember).filter(models.ClubMember.display_name == admin_pseudo).first()
            if member:
                new_admin.linked_member_id = member.id
            db.add(new_admin)
            print(f"[Seeding] Succès : compte ADMIN {admin_pseudo} créé.")
        else:
            print(f"[Seeding] Info : le compte ADMIN {admin_pseudo} existe déjà.")
            
        db.commit()
        print("[Seeding] Opération terminée avec succès.")
    except Exception as e:
        print(f"[Seeding] Erreur : {e}")
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
seed_database()

# Authentication imports moved to app/dependencies.py

# Routes publiques
app.include_router(auth_router)

# Routes protégées par rôle Admin
app.include_router(admin_router, dependencies=[Depends(get_current_admin)])

# Routes protégées (Membres & API)
app.include_router(matches_router, dependencies=[Depends(get_current_user)])
app.include_router(players_router, dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, dependencies=[Depends(get_current_user)])
app.include_router(pepites_router, dependencies=[Depends(get_current_user)])
app.include_router(notifications_router, dependencies=[Depends(get_current_user)])

# Redirection vers Login en cas d'erreur 401 (non authentifié)
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_redirect(request: Request, exc: HTTPException):
    # Si c'est une requête API (Watcher), on renvoie l'erreur 401 telle quelle
    # pour que l'authentification Basic puisse se déclencher sur le script.
    if "/api/" in request.url.path:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Non authentifié"},
            headers={"WWW-Authenticate": "Basic"}
        )
    
    # Pour le web, on redirige vers la page de login
    return RedirectResponse(url="/login")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintenir la connexion ouverte
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    # Save PID for the launcher to find and kill cleanly
    os.makedirs("data", exist_ok=True)
    with open("data/server.pid", "w") as f:
        f.write(str(os.getpid()))
        
    # Uniquement en mode développement
    if os.getenv("ENV") != "production":
        # Lancement de Ngrok en arrière-plan pour que les logs apparaissent ici
        def start_ngrok_bg():
            time.sleep(2) # Attendre que le serveur soit prêt
            print("\n" + "="*50)
            print("DÉMARRAGE NGROK (ACCÈS PUBLIC)...")
            print("="*50 + "\n")
            # On utilise os.system pour que la sortie soit visible dans cette console
            os.system("ngrok http 8000")

        ngrok_thread = threading.Thread(target=start_ngrok_bg, daemon=True)
        ngrok_thread.start()
        
    import uvicorn
    # Lancement du serveur sur le port 8000
    # On désactive le reload en production pour plus de stabilité
    is_prod = os.getenv("ENV") == "production"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=not is_prod)

# Optionnel : si tu ajoutes un dossier static plus tard
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass