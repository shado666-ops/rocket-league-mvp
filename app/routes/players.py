from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.services.stats_service import MAIN_PLAYER_NAME, get_dashboard_data, get_mate_detail_data, get_club_archives_data
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
@router.get("/joueurs")
def club_page(request: Request, db: Session = Depends(get_db)):
    data = get_dashboard_data(db)
    return templates.TemplateResponse(
        "club.html",
        {
            "request": request,
            **data,
        },
    )


@router.get("/club")
def archives_page(request: Request, db: Session = Depends(get_db)):
    data = get_dashboard_data(db, limit=None)
    archive_data = get_club_archives_data(db) # This now returns the menu
    return templates.TemplateResponse(
        "archives.html",
        {
            "request": request,
            **data,
            **archive_data,
        },
    )


@router.get("/club/{fid}")
def archives_detail_page(fid: str, request: Request, db: Session = Depends(get_db)):
    data = get_dashboard_data(db, limit=None)
    category_data = get_club_archives_data(db, category_fid=fid)
    if not category_data:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")
    
    return templates.TemplateResponse(
        "archives_detail.html",
        {
            "request": request,
            **data,
            **category_data,
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
        return RedirectResponse(url="/joueurs", status_code=303)

    existing = db.query(ClubMember).filter(ClubMember.display_name == display_name).first()
    if existing:
        existing.is_active = True
    else:
        db.add(ClubMember(display_name=display_name, is_active=True))

    db.commit()
    return RedirectResponse(url="/joueurs", status_code=303)


@router.post("/club-members/{mate_name}/toggle")
def toggle_club_member(mate_name: str, db: Session = Depends(get_db)):
    if mate_name == MAIN_PLAYER_NAME:
        return RedirectResponse(url="/joueurs", status_code=303)

    member = db.query(ClubMember).filter(ClubMember.display_name == mate_name).first()
    if member:
        member.is_active = not member.is_active
        db.commit()
    return RedirectResponse(url="/joueurs", status_code=303)

@router.post("/club-members/{mate_name}/delete")
def delete_club_member(mate_name: str, db: Session = Depends(get_db)):
    if mate_name == MAIN_PLAYER_NAME:
        return RedirectResponse(url="/joueurs", status_code=303)

    member = db.query(ClubMember).filter(ClubMember.display_name == mate_name).first()
    if member:
        db.delete(member)
        db.commit()

    return RedirectResponse(url="/club", status_code=303)


@router.post("/seasons/add")
def add_season_route(
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    db: Session = Depends(get_db)
):
    from datetime import datetime
    try:
        from app.services.stats_service import add_season
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        add_season(db, name, start, end)
    except Exception as e:
        print(f"Error adding season: {e}")
    
    return RedirectResponse(url="/admin/ui", status_code=303)


@router.post("/seasons/{season_id}/delete")
def delete_season_route(season_id: int, db: Session = Depends(get_db)):
    from app.services.stats_service import delete_season
    delete_season(db, season_id)
    return RedirectResponse(url="/admin/ui", status_code=303)