from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Notification
from app.services.stats_service import get_unread_notifications_count, get_club_name, get_club_tag

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="templates")

# No security dependency here as notifications and their actions are public

@router.get("/")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    limit = datetime.utcnow() - timedelta(hours=48)
    notifications = db.query(Notification).filter(
        Notification.is_read.is_(False),
        Notification.created_at >= limit
    ).order_by(Notification.created_at.desc()).all()
    unread_notifications_count = len(notifications)
    
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "notifications": notifications,
            "unread_notifications_count": unread_notifications_count,
            "club_name": get_club_name(db),
            "club_tag": get_club_tag(db),
        }
    )

@router.post("/clear-all")
def clear_all_notifications(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"status": "ok"}

@router.post("/{notification_id}/read")
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    notification.is_read = True
    db.commit()
    return {"status": "ok"}

@router.get("/ids")
def get_active_notification_ids(db: Session = Depends(get_db)):
    limit = datetime.utcnow() - timedelta(hours=48)
    ids = db.query(Notification.id).filter(
        Notification.is_read.is_(False),
        Notification.created_at >= limit
    ).all()
    return [i[0] for i in ids]
