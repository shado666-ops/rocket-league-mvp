import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
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
from app.dependencies import get_current_user
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import ClubMember

def seed_database():
    """Initialise les membres de base du club s'ils n'existent pas."""
    db: Session = SessionLocal()
    try:
        primary_members = ["Shado666", "Kalibakbak", "Ezy", "JulienYo"]
        for name in primary_members:
            exists = db.query(ClubMember).filter(ClubMember.display_name == name).first()
            if not exists:
                print(f"[Seeding] Ajout du membre : {name}")
                db.add(ClubMember(display_name=name, is_active=True))
        db.commit()
    except Exception as e:
        print(f"[Seeding] Erreur : {e}")
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
seed_database()

# Authentication imports moved to app/dependencies.py

app = FastAPI(title="Rocket League MVP Tracker")

# Configuration and get_current_user moved to app/dependencies.py

# Appliquer la sécurité UNIQUEMENT sur le routeur admin
app.include_router(admin_router, dependencies=[Depends(get_current_user)])
# Les autres sont publics
app.include_router(matches_router)
app.include_router(players_router)
app.include_router(analytics_router)
app.include_router(pepites_router)
app.include_router(notifications_router)

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