from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user
import models
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(tags=["pepites"])
templates = Jinja2Templates(directory="templates")

@router.get("/pepites")
async def pepites_page(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from app.services.stats_service import get_club_name, get_club_tag
    
    club_name = get_club_name(db)
    club_tag = get_club_tag(db)

    from app.services.stats_service import get_unread_notifications_count
    unread_notifications_count = get_unread_notifications_count(db)

    return templates.TemplateResponse(
        request=request,
        name="pepites.html",
        context={
            "club_name": club_name,
            "club_tag": club_tag,
            "unread_notifications_count": unread_notifications_count,
            "user": current_user,
        },
    )
