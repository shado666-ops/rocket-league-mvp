from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.stats_service import get_dashboard_data
from database import get_db

router = APIRouter(tags=["analytics"])
templates = Jinja2Templates(directory="templates")

@router.get("/hof")
def analytics_page(request: Request, db: Session = Depends(get_db)):
    from app.services.stats_service import get_rankings_data, get_club_name, get_club_tag, get_unread_notifications_count

    # On récupère les classements par stats (Public vs Privé)
    rankings_public = get_rankings_data(db, min_matches=5, match_filter="public")
    rankings_private = get_rankings_data(db, min_matches=5, match_filter="private")
    
    club_name = get_club_name(db)
    club_tag = get_club_tag(db)
    unread_notifications_count = get_unread_notifications_count(db)

    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "rankings_public": rankings_public,
            "rankings_private": rankings_private,
            "club_name": club_name,
            "club_tag": club_tag,
            "unread_notifications_count": unread_notifications_count,
        },
    )
