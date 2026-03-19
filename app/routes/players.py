from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.services.stats_service import MAIN_PLAYER_NAME, get_dashboard_data, get_mate_detail_data
from database import get_db
from models import ClubMember

router = APIRouter(tags=["players"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    data = get_dashboard_data(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            **data,
        },
    )


@router.get("/mates/{mate_name}")
def mate_detail(mate_name: str, request: Request, db: Session = Depends(get_db)):
    data = get_mate_detail_data(db, mate_name)
    if not data:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")
    return templates.TemplateResponse(
        "mate_detail.html",
        {
            "request": request,
            **data,
        },
    )


@router.post("/club-members/add")
def add_club_member(
    display_name: str = Form(...),
    db: Session = Depends(get_db),
):
    display_name = display_name.strip()
    if not display_name:
        return RedirectResponse(url="/", status_code=303)

    existing = db.query(ClubMember).filter(ClubMember.display_name == display_name).first()
    if existing:
        existing.is_active = True
    else:
        db.add(ClubMember(display_name=display_name, is_active=True))

    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/club-members/{mate_name}/toggle")
def toggle_club_member(mate_name: str, db: Session = Depends(get_db)):
    if mate_name == MAIN_PLAYER_NAME:
        return RedirectResponse(url="/", status_code=303)

    member = db.query(ClubMember).filter(ClubMember.display_name == mate_name).first()
    if member:
        member.is_active = not member.is_active
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@router.post("/club-members/{mate_name}/delete")
def delete_club_member(mate_name: str, db: Session = Depends(get_db)):
    if mate_name == MAIN_PLAYER_NAME:
        return RedirectResponse(url="/", status_code=303)

    member = db.query(ClubMember).filter(ClubMember.display_name == mate_name).first()
    if member:
        db.delete(member)
        db.commit()

    return RedirectResponse(url="/", status_code=303)