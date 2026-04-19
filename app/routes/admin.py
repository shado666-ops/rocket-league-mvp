import os
import shutil
import time
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.dependencies import get_current_user, get_current_admin

from database import SessionLocal, engine, Base
import models
from models import ClubMember, Match, Player, MatchPlayerStat
from schemas import LogSyncPayload
from app.services.stats_service import get_seasons, set_setting, get_club_name, get_club_tag
import models

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- UI ---
from sqlalchemy.orm import joinedload

@router.get("/ui", response_class=HTMLResponse)
async def admin_ui(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin)):
    members = db.query(ClubMember).options(joinedload(ClubMember.aliases)).all()
    backups_dir = "backups"
    last_backup = "Aucune"
    if os.path.exists(backups_dir):
        files = [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.endswith(".db")]
        if files:
            latest = max(files, key=os.path.getmtime)
            last_backup = datetime.fromtimestamp(os.path.getmtime(latest)).strftime("%d/%m/%Y %H:%M")
    
    seasons = get_seasons(db)
    
    from app.services.stats_service import get_unread_notifications_count
    unread_notifications_count = get_unread_notifications_count(db)

    # Gestion des utilisateurs
    pending_users = db.query(models.User).filter(models.User.is_approved == False).all()
    approved_users = db.query(models.User).filter(models.User.is_approved == True, models.User.role != "admin").all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "members": members,
            "last_backup": last_backup,
            "seasons": seasons,
            "club_name": get_club_name(db),
            "club_tag": get_club_tag(db),
            "unread_notifications_count": unread_notifications_count,
            "pending_users": pending_users,
            "approved_users": approved_users,
            "user": current_user
        }
    )

# --- SETTINGS ---
@router.post("/settings")
async def update_settings(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    for key, value in data.items():
        set_setting(db, key, value)
    return {"status": "ok"}

# --- DATABASE ---
@router.post("/backup")
async def backup_db():
    try:
        if not os.path.exists("backups"):
            os.makedirs("backups")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/app_backup_{timestamp}.db"
        shutil.copy2("data/app.db", backup_path)
        return {"status": "ok", "message": f"Sauvegarde créée : {backup_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_db(db: Session = Depends(get_db)):
    try:
        # Simple reset: clear tables instead of deleting file to avoid locking issues
        db.query(MatchPlayerStat).delete()
        db.query(Match).delete()
        db.query(Player).delete()
        db.query(ClubMember).delete()
        db.commit()
        
        # Re-seed basic members
        from main import seed_database
        seed_database()
        
        return {"status": "ok", "message": "Base de données réinitialisée."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- LOGS ---
@router.get("/logs")
async def get_logs():
    from collections import deque
    logs = {"server": "", "watcher": ""}
    try:
        if os.path.exists("logs/server.log"):
            with open("logs/server.log", "r", encoding="utf-8", errors="replace") as f:
                logs["server"] = "".join(deque(f, 100)) # Last 100 lines efficiently
        
        if os.path.exists("logs/watcher.log"):
            with open("logs/watcher.log", "r", encoding="utf-8", errors="replace") as f:
                logs["watcher"] = "".join(deque(f, 100))
                
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/logs/watcher_sync")
async def sync_watcher_logs(payload: LogSyncPayload, current_admin: models.User = Depends(get_current_admin)):
    """Reçoit les logs du watcher local et les écrit dans le fichier logs/watcher.log du serveur."""
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/watcher.log", "w", encoding="utf-8") as f:
            f.write(payload.log_content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logs/clear")
async def clear_logs():
    try:
        for log_file in ["logs/server.log", "logs/watcher.log"]:
            if os.path.exists(log_file):
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"--- Log cleared at {datetime.now()} ---\n")
        return {"status": "ok", "message": "Logs effacés."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MEMBERS ---
@router.get("/members")
async def list_members(db: Session = Depends(get_db)):
    return db.query(ClubMember).all()

@router.post("/members")
async def add_member(name: str, db: Session = Depends(get_db)):
    exists = db.query(ClubMember).filter(ClubMember.display_name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ce membre existe déjà.")
    
    new_member = ClubMember(display_name=name, is_active=True)
    db.add(new_member)
    db.commit()
    return {"status": "ok"}

@router.post("/members/{name}/car")
async def update_member_car(name: str, car: str, db: Session = Depends(get_db)):
    member = db.query(ClubMember).filter(ClubMember.display_name == name).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membre introuvable.")
    
    member.favorite_car = car
    db.commit()
    return {"status": "ok"}

@router.delete("/members/{name}")
async def delete_member(name: str, db: Session = Depends(get_db)):
    member = db.query(ClubMember).filter(ClubMember.display_name == name).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membre introuvable.")
    
    db.delete(member)
    db.commit()
    return {"status": "ok"}


# --- ALIASES ---
@router.post("/members/{member_id}/aliases")
async def add_alias(member_id: int, pseudo: str, db: Session = Depends(get_db)):
    exists = db.query(models.PlayerAlias).filter(models.PlayerAlias.pseudo == pseudo).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"Le pseudo '{pseudo}' est déjà utilisé.")
    
    new_alias = models.PlayerAlias(pseudo=pseudo, club_member_id=member_id)
    db.add(new_alias)
    db.commit()
    return {"status": "ok"}


@router.delete("/aliases/{alias_id}")
async def delete_alias(alias_id: int, db: Session = Depends(get_db)):
    alias = db.query(models.PlayerAlias).filter(models.PlayerAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias introuvable.")
    
    db.delete(alias)
    db.commit()
    return {"status": "ok"}
@router.post("/users/approve/{user_id}")
async def approve_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_approved = True
        db.commit()
    return RedirectResponse(url="/admin/ui", status_code=303)

@router.post("/users/delete/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/admin/ui", status_code=303)
