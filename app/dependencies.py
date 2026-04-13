import os
import secrets
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from database import SessionLocal
from app.services.auth_service import decode_access_token
import models

security = HTTPBasic()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Système de secours (Watcher)
USER_ADMIN_SYS = os.getenv("ADMIN_USER", "admin")
PASS_ADMIN_SYS = os.getenv("ADMIN_PASSWORD", "rltracker")

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 1. Tentative via Cookie (Utilisateurs Web)
    token = request.cookies.get("access_token")
    if token:
        if token.startswith("Bearer "): token = token[7:]
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                if not user.is_approved and user.role != "admin":
                    raise HTTPException(status_code=403, detail="Compte en attente d'approbation")
                return user

    # 2. Tentative via Basic Auth (Watcher / API)
    # On n'autorise le Basic Auth que pour les routes commençant par /api/ 
    # pour éviter que les navigateurs n'utilisent leurs mots de passe sauvegardés sur le site web.
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic ") and "/api/" in request.url.path:
        try:
            from fastapi.security.utils import get_authorization_scheme_param
            scheme, param = get_authorization_scheme_param(auth_header)
            import base64
            decoded = base64.b64decode(param).decode("ascii")
            username, password = decoded.split(":")
            if secrets.compare_digest(username, USER_ADMIN_SYS) and secrets.compare_digest(password, PASS_ADMIN_SYS):
                # On retourne un objet User fictif pour le script
                return models.User(username=username, role="admin", is_approved=True)
            
            # Essayer avec un utilisateur réel en base
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                from app.services.auth_service import verify_password
                if verify_password(password, user.hashed_password):
                    if not user.is_approved and user.role != "admin":
                        raise HTTPException(status_code=403, detail="Compte en attente d'approbation")
                    return user
        except:
            pass

    # Si rien ne marche, on redirige vers le login (pour les pages HTML) ou 401 (pour l'API)
    if any(ext in request.url.path for ext in [".js", ".css", ".png", ".jpg"]):
        return None # Autoriser les assets statiques

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Non authentifié",
        headers={"WWW-Authenticate": "Basic"},
    )

async def get_current_admin(user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user
