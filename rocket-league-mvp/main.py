import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from app.websocket_manager import manager
import os
import time

from app.routes.matches import router as matches_router
from app.routes.players import router as players_router
from app.routes.analytics import router as analytics_router
from app.routes.pepites import router as pepites_router
from app.routes.admin import router as admin_router
from app.routes.notifications import router as notifications_router
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

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets

app = FastAPI(title="Rocket League MVP Tracker")

security = HTTPBasic()

# Configuration des identifiants (à changer ou mettre en env var)
USER_ADMIN = os.getenv("ADMIN_USER", "admin")
PASS_ADMIN = os.getenv("ADMIN_PASSWORD", "rltracker")

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USER_ADMIN)
    correct_password = secrets.compare_digest(credentials.password, PASS_ADMIN)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Appliquer la sécurité sur tous les routeurs
app.include_router(matches_router, dependencies=[Depends(get_current_user)])
app.include_router(players_router, dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, dependencies=[Depends(get_current_user)])
app.include_router(pepites_router, dependencies=[Depends(get_current_user)])
app.include_router(admin_router, dependencies=[Depends(get_current_user)])
app.include_router(notifications_router, dependencies=[Depends(get_current_user)])

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
        
    import uvicorn
    # Lancement du serveur sur le port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# Optionnel : si tu ajoutes un dossier static plus tard
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass