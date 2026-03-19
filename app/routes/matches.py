import os
import json
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import Match, MatchPlayerStat, Player
from schemas import MatchIngestPayload, PlayerStatIn
from app.websocket_manager import manager
from app.services.ballchasing_service import BallchasingService

router = APIRouter(tags=["matches"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "Rocket League MVP Tracker"}


@router.post("/api/matches")
async def ingest_match(payload: MatchIngestPayload, db: Session = Depends(get_db)):
    existing = db.query(Match).filter(Match.replay_id == payload.replay_id).first()
    if existing:
        return {
            "status": "ignored",
            "reason": "replay already exists",
            "match_id": existing.id,
        }

    if not payload.players:
        raise HTTPException(status_code=400, detail="Payload vide : aucun joueur fourni.")

    match = Match(
        replay_id=payload.replay_id,
        playlist=payload.playlist,
        result=payload.result,
        played_at=payload.played_at or datetime.utcnow(),
        ballchasing_id=payload.ballchasing_id,
        ballchasing_url=payload.ballchasing_url,
    )
    db.add(match)
    db.flush()

    for player_stat in payload.players:
        player = db.query(Player).filter(Player.display_name == player_stat.display_name).first()
        if not player:
            player = Player(display_name=player_stat.display_name)
            db.add(player)
            db.flush()

        row = MatchPlayerStat(
            match_id=match.id,
            player_id=player.id,
            team=player_stat.team,
            goals=player_stat.goals,
            assists=player_stat.assists,
            saves=player_stat.saves,
            shots=player_stat.shots,
            score=player_stat.score,
            won=player_stat.won,
        )
        db.add(row)

    db.commit()
    db.refresh(match)

    await manager.broadcast("refresh")

    return {
        "status": "created",
        "match_id": match.id,
        "replay_id": match.replay_id,
    }

@router.get("/api/latest-match-id")
def get_latest_match_id(db: Session = Depends(get_db)):
    last_match = db.query(Match).order_by(Match.id.desc()).first()
    return {"latest_id": last_match.id if last_match else 0}

@router.post("/api/matches/upload")
async def upload_replay(replay_file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload_dir = os.path.join(os.getcwd(), "uploaded_replays")
    parsed_dir = os.path.join(upload_dir, "parsed")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(parsed_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, replay_file.filename)
    
    try:
        content = await replay_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Optional: Upload to Ballchasing
        bc_id = None
        bc_url = None
        try:
            bc_res = BallchasingService.upload_replay(file_path)
            if bc_res:
                bc_id = bc_res.get("id")
                bc_url = f"https://ballchasing.com/replay/{bc_id}" if bc_id else None
        except Exception as e:
            print(f"Ballchasing upload failed: {e}")

        # Appel à RocketRP (avec -f pour fast mode afin d'éviter les erreurs de netstream)
        ROCKETRP_EXE = r"C:\Users\perno\Desktop\Rocket-League-MVP-Propre\parsers\rocketrp\RocketRP.CLI.exe"
        process = subprocess.run([ROCKETRP_EXE, "-r", file_path, "-o", parsed_dir, "-f"], capture_output=True, text=True)
        
        # Le nom du fichier json généré par RocketRP
        json_filename = os.path.splitext(replay_file.filename)[0] + ".json"
        json_path = os.path.join(parsed_dir, json_filename)
        
        if not os.path.exists(json_path):
            raise Exception(f"Le fichier JSON n'a pas été généré par RocketRP. Sortie: {process.stderr or process.stdout}")
            
        with open(json_path, "r", encoding="utf-8") as jf:
            replay_data = json.load(jf)
            
        props = replay_data.get("Properties", {})
        
        # Extraction Stats
        team0_score = props.get("Team0Score", 0)
        team1_score = props.get("Team1Score", 0)
        winning_team = 0 if team0_score > team1_score else 1
        
        players = []
        for p in props.get("PlayerStats", []):
            players.append(PlayerStatIn(
                display_name=p.get("Name", "Unknown"),
                team=p.get("Team", 0),
                goals=p.get("Goals", 0),
                assists=p.get("Assists", 0),
                saves=p.get("Saves", 0),
                shots=p.get("Shots", 0),
                score=p.get("Score", 0),
                won=(p.get("Team", 0) == winning_team)
            ))
            
        team_size = props.get("TeamSize", 3)
        match_type_dict = props.get("MatchType", {})
        match_type = match_type_dict.get("Value", "") if isinstance(match_type_dict, dict) else ""
        
        # Identification simplifiée
        replay_name = props.get("ReplayName", "").lower()
        display_type = match_type
        
        if match_type == "Online":
            if any(kw in replay_name for kw in ["ranked", "classe", "classé"]):
                display_type = "Ranked"
            elif any(kw in replay_name for kw in ["casual", "casu", "occasionnel"]):
                display_type = "Casual"
                
        playlist = f"{team_size}v{team_size}"
        if display_type:
            playlist += f" ({display_type})"
        
        played_at_str = props.get("Date", "")
        played_at = None
        if played_at_str:
            try:
                played_at = datetime.strptime(played_at_str, "%Y-%m-%d %H-%M-%S")
            except Exception:
                pass
                
        replay_id = props.get("Id", "") or os.path.splitext(replay_file.filename)[0]
        
        # Payload pour Ingest
        payload = MatchIngestPayload(
            replay_id=replay_id,
            played_at=played_at,
            playlist=playlist,
            result="Import", # Simplification. Le dashboard calculera le "Victoire/Défaite" selon si main_player était in winning_team
            players=players,
            ballchasing_id=bc_id,
            ballchasing_url=bc_url
        )
        
        res = await ingest_match(payload, db)
        return res
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload/parsing: {str(e)}")


@router.post("/api/matches/{match_id}/fetch-ballchasing-stats")
async def fetch_ballchasing_stats(match_id: int, db: Session = Depends(get_db)):
    """Récupère les stats avancées Ballchasing pour un match spécifique."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match non trouvé")
    
    if not match.ballchasing_id:
        raise HTTPException(status_code=400, detail="Ce match n'a pas d'ID Ballchasing")
    
    replay_data = BallchasingService.get_replay_data(match.ballchasing_id)
    if not replay_data:
        raise HTTPException(status_code=500, detail="Impossible de récupérer les données de Ballchasing (le replay est peut-être encore en cours de traitement)")
    
    updated_count = 0
    for stat_row in match.player_stats:
        player_name = stat_row.player.display_name
        bc_stats = BallchasingService.extract_player_stats(replay_data, player_name)
        
        if bc_stats:
            stat_row.boost_collected = bc_stats.get("boost_collected")
            stat_row.boost_stolen = bc_stats.get("boost_stolen")
            stat_row.time_zero_boost = bc_stats.get("time_zero_boost")
            stat_row.time_full_boost = bc_stats.get("time_full_boost")
            stat_row.time_defensive_third = bc_stats.get("time_defensive_third")
            stat_row.time_neutral_third = bc_stats.get("time_neutral_third")
            stat_row.time_offensive_third = bc_stats.get("time_offensive_third")
            stat_row.avg_speed = bc_stats.get("avg_speed")
            stat_row.time_supersonic = bc_stats.get("time_supersonic")
            updated_count += 1
            
    db.commit()
    return {"status": "success", "players_updated": updated_count}


@router.post("/api/matches/fetch-all-ballchasing-stats")
async def fetch_all_ballchasing_stats(db: Session = Depends(get_db)):
    """Tente de récupérer les stats avancées pour tous les matchs qui ont un ID Ballchasing mais pas encore de stats boost."""
    # On cherche les MatchPlayerStat qui n'ont pas de boost_collected
    pending_stats = db.query(MatchPlayerStat).filter(
        MatchPlayerStat.boost_collected == None
    ).join(Match).filter(
        Match.ballchasing_id != None
    ).all()
    
    # On groupe par match pour éviter de faire plusieurs appels API pour le même match
    match_ids = list(set([s.match_id for s in pending_stats]))
    
    matches_updated = 0
    total_players_updated = 0
    
    for m_id in match_ids:
        try:
            # On appelle directement le code métier de fetch_ballchasing_stats pour éviter l'overhead HTTP interne
            match = db.query(Match).filter(Match.id == m_id).first()
            if not match or not match.ballchasing_id:
                continue
                
            replay_data = BallchasingService.get_replay_data(match.ballchasing_id)
            if not replay_data:
                continue
                
            p_updated = 0
            for stat_row in match.player_stats:
                player_name = stat_row.player.display_name
                bc_stats = BallchasingService.extract_player_stats(replay_data, player_name)
                if bc_stats:
                    stat_row.boost_collected = bc_stats.get("boost_collected")
                    stat_row.boost_stolen = bc_stats.get("boost_stolen")
                    stat_row.time_zero_boost = bc_stats.get("time_zero_boost")
                    stat_row.time_full_boost = bc_stats.get("time_full_boost")
                    stat_row.time_defensive_third = bc_stats.get("time_defensive_third")
                    stat_row.time_neutral_third = bc_stats.get("time_neutral_third")
                    stat_row.time_offensive_third = bc_stats.get("time_offensive_third")
                    stat_row.avg_speed = bc_stats.get("avg_speed")
                    stat_row.time_supersonic = bc_stats.get("time_supersonic")
                    p_updated += 1
            
            if p_updated > 0:
                matches_updated += 1
                total_players_updated += p_updated
                db.commit()
        except Exception as e:
            print(f"Error fetching stats for match {m_id}: {e}")
            continue
            
    return {
        "status": "done",
        "matches_processed": len(match_ids),
        "matches_updated": matches_updated,
        "total_players_updated": total_players_updated
    }