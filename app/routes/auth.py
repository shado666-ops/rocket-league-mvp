from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import traceback
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from app.services.auth_service import verify_password, get_password_hash, create_access_token

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            print(f"[Auth] Échec connexion pour {username} (Utilisateur introuvable ou mauvais mdp)")
            return templates.TemplateResponse(
                request=request, 
                name="login.html", 
                context={"error": "Identifiants incorrects"}
            )
    except Exception as e:
        print(f"[Auth] Erreur critique lors du login : {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Erreur interne serveur lors du login")
    
    if not user.is_approved and user.role != "admin":
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Votre compte est en attente d'approbation par l'admin."}
        )

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Vérifier si l'utilisateur existe déjà
        print(f"[Auth] Tentative d'inscription : {username}")
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            return templates.TemplateResponse(
                request=request, 
                name="register.html", 
                context={"error": "Ce pseudo est déjà utilisé."}
            )

        # Création du nouvel utilisateur
        hashed_pwd = get_password_hash(password)
        new_user = models.User(
            username=username,
            hashed_password=hashed_pwd,
            role="member",
            is_approved=False
        )
        
        member = db.query(models.ClubMember).filter(models.ClubMember.display_name == username).first()
        if member:
            print(f"[Auth] Liaison automatique avec le membre ID {member.id}")
            new_user.linked_member_id = member.id

        db.add(new_user)
        db.commit()
        print(f"[Auth] Inscription réussie pour {username}")

        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"success": "Inscription réussie ! Veuillez attendre l'approbation de l'administrateur."}
        )
    except Exception as e:
        print(f"[Auth] Erreur critique lors de l'inscription : {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response
