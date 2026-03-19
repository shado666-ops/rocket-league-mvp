from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.stats_service import get_dashboard_data
from database import get_db

router = APIRouter(tags=["analytics"])
templates = Jinja2Templates(directory="templates")

@router.get("/analytics")
def analytics_page(request: Request, db: Session = Depends(get_db)):
    # On réutilise une partie des datas du dashboard (qui compile déjà les stats de club)
    # pour peupler la page analytique.
    data = get_dashboard_data(db)
    
    # Extraire les infos pertinentes depuis get_dashboard_data ou les recalculer
    # data["club_charts"] contient data.mates_frequency et data.winrate_with_mates
    
    # Calculs supplémentaires spécifiques à la page Analytics:
    # Meilleur Joueur (basé sur le winrate, en incluant le joueur principal)
    best_player = {"name": data["main_player_name"], "winrate": data["summary"]["winrate"]}
    if data.get("club_charts") and data["club_charts"].get("winrate_with_mates"):
        best_mate_candidate = data["club_charts"]["winrate_with_mates"][0]
        if best_mate_candidate["winrate"] > best_player["winrate"]:
            best_player = best_mate_candidate
        
    # Progression sur 20 matchs: on prend les 20 derniers du "history"
    recent_history = data.get("history", [])[:20]
    recent_winrate = 0
    if recent_history:
        wins = sum(1 for m in recent_history if m["result"] == "Victoire")
        recent_winrate = round((wins / len(recent_history)) * 100, 2)

    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "best_player": best_player,
            "recent_winrate": recent_winrate,
            "recent_matches_count": len(recent_history),
            **data,
        },
    )
