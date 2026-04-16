from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
import os
from datetime import datetime, timedelta
from app.dependencies import get_current_user
import models
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Match, MatchPlayerStat, Player
from schemas import MatchIngestPayload, PlayerStatIn
from app.websocket_manager import manager
from app.services.csv_service import CSVService
from app.services.stats_service import check_and_update_rankings, get_active_club_member_map, get_match_detail_data, get_unread_notifications_count, get_club_name, get_club_tag

router = APIRouter(tags=["matches"])
templates = Jinja2Templates(directory="templates")


@router.get("/matches/{match_id}")
def match_detail(match_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    data = get_match_detail_data(db, match_id)
    if not data:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    
    # Common data for layout
    unread_notifications_count = get_unread_notifications_count(db)
    club_name = get_club_name(db)
    club_tag = get_club_tag(db)
    
    return templates.TemplateResponse(
        request=request,
        name="match_detail.html",
        context={
            "club_name": club_name,
            "club_tag": club_tag,
            "user": current_user
        },
    )


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "Rocket League MVP Tracker"}


@router.post("/api/matches")
async def ingest_match(payload: MatchIngestPayload, db: Session = Depends(get_db)):
    # 1. Tentative de correspondance exacte par replay_id
    match = db.query(Match).filter(Match.replay_id == payload.replay_id).first()
    
    # 2. Si pas de correspondance exacte, tentative par date + joueurs (fusion CSV/Replay)
    if not match and payload.played_at:
        tolerance = timedelta(seconds=45) # BakkesMod et Replays peuvent avoir un petit décalage
        start = payload.played_at - tolerance
        end = payload.played_at + tolerance
        
        similar_matches = db.query(Match).filter(Match.played_at.between(start, end)).all()
        for m in similar_matches:
            existing_players = [ps.player.display_name for ps in m.player_stats]
            payload_players = [p.display_name for p in payload.players]
            if set(existing_players).intersection(set(payload_players)):
                match = m
                break

    if match:
        # Match déjà existant : on enrichit les données
        if match.replay_id.startswith("game_stats_") and not payload.replay_id.startswith("game_stats_"):
            match.replay_id = payload.replay_id
        
        # Enrichment: Replay should override generic CSV labels
        is_replay = not payload.replay_id.startswith("game_stats_")
        is_generic = match.playlist == "unknown" or match.playlist == "BakkesMod CSV" or "Private" in match.playlist
        
        if payload.playlist != "unknown" and (is_generic or is_replay):
            match.playlist = payload.playlist
            
        # Harmonisation et détection 3v3 Ranked+R
        playlist_lower = payload.playlist.lower()
        if ("3v3" in playlist_lower or "standard" in playlist_lower) and "ranked" in playlist_lower:
            member_map = get_active_club_member_map(db)
            all_pseudos = set(member_map.keys())
            
            # Compte des membres du club par équipe
            teams_club_count = {}
            for p in payload.players:
                if p.display_name in all_pseudos:
                    teams_club_count[p.team] = teams_club_count.get(p.team, 0) + 1
            
            # On cherche l'équipe avec le plus de membres du club (notre équipe)
            max_club_on_team = max(teams_club_count.values()) if teams_club_count else 0
            
            if 0 < max_club_on_team < 3:
                payload.playlist = "3v3 (Ranked+R)"
            else:
                payload.playlist = "3v3 (Ranked)"
            
            match.playlist = payload.playlist

        # Detect private matches by composition if still generic
        if match.playlist == "unknown" or match.playlist == "BakkesMod CSV":
            member_map = get_active_club_member_map(db)
            all_pseudos = set(member_map.keys())
            
            # Count club members on each team
            team0_club = sum(1 for p in payload.players if p.team == 0 and p.display_name in all_pseudos)
            team1_club = sum(1 for p in payload.players if p.team == 1 and p.display_name in all_pseudos)
            total_players = len(payload.players)
            total_club = team0_club + team1_club

            if (team0_club > 0 and team1_club > 0) or (total_club == total_players and total_players > 0):
                # Detected as private
                blue_size = sum(1 for p in payload.players if p.team == 0)
                orange_size = sum(1 for p in payload.players if p.team == 1)
                match.playlist = f"{blue_size}v{orange_size} Private"

        for p_in in payload.players:
            for ps in match.player_stats:
                if ps.player.display_name == p_in.display_name:
                    if p_in.demolishes is not None: ps.demolishes = p_in.demolishes
                    if p_in.pads is not None: ps.pads = p_in.pads
                    if p_in.boost_usage is not None: ps.boost_usage = p_in.boost_usage
                    if p_in.possession_time is not None: ps.possession_time = p_in.possession_time
                    break
        db.commit()
        return {"status": "enriched", "match_id": match.id, "replay_id": match.replay_id}

    if not payload.players and os.getenv("ENV") != "production":
        raise HTTPException(status_code=400, detail="Payload vide : aucun joueur fourni.")

    # Harmonisation et détection 3v3 Ranked+R pour nouveaux matchs
    playlist_lower = payload.playlist.lower()
    if ("3v3" in playlist_lower or "standard" in playlist_lower) and "ranked" in playlist_lower:
        member_map = get_active_club_member_map(db)
        all_pseudos = set(member_map.keys())
        
        teams_club_count = {}
        for p in payload.players:
            if p.display_name in all_pseudos:
                teams_club_count[p.team] = teams_club_count.get(p.team, 0) + 1
        
        max_club_on_team = max(teams_club_count.values()) if teams_club_count else 0
        
        if 0 < max_club_on_team < 3:
            payload.playlist = "3v3 (Ranked+R)"
        else:
            payload.playlist = "3v3 (Ranked)"

    match = Match(
        replay_id=payload.replay_id,
        playlist=payload.playlist,
        result=payload.result,
        played_at=payload.played_at or datetime.utcnow(),
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
            demolishes=player_stat.demolishes,
            pads=player_stat.pads,
            boost_usage=player_stat.boost_usage,
            possession_time=player_stat.possession_time,
        )
        db.add(row)

    db.commit()
    db.refresh(match)

    # Vérification des changements dans le Hall of Fame
    check_and_update_rankings(db, match_filter="public")
    check_and_update_rankings(db, match_filter="private")

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

from app.services.boxcars_service import BoxcarsService

@router.post("/api/matches/upload")
async def upload_replay(replay_file: UploadFile = File(...), mtime: float = None, db: Session = Depends(get_db)):
    upload_dir = os.path.join(os.getcwd(), "uploaded_replays")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, replay_file.filename)
    
    try:
        content = await replay_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Appel à Boxcars (via BoxcarsService)
        replay_data = BoxcarsService.parse_replay(file_path, played_at_mtime=mtime)
            
        # Extraction des métadonnées (format Boxcars)
        props = replay_data.get("properties", {})
        if not props and "Properties" in replay_data:
            props = replay_data["Properties"]
            
        if not props.get("PlayerStats") and os.getenv("ENV") == "production":
            # Si le parsing a échoué (mode simulation) sur le serveur, on log l'erreur
            print(f"[Upload] ALERTE : Le parsing du replay {replay_file.filename} a échoué. Enregistrement dégradé.")
        team1_score = props.get("Team1Score", 0)
        winning_team = 0 if team0_score > team1_score else 1
        
        players = []
        # Boxcars PlayerStats mapping
        player_stats = props.get("PlayerStats", [])
        for p in player_stats:
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
            
        # Mappage des Playlist IDs Rocket League pour des libellés précis
        PLAYLIST_MAP = {
            1: "Duel (Casual)",
            2: "Doubles (Casual)",
            3: "Standard (Casual)",
            4: "Chaos (Casual)",
            6: "Private Match",
            7: "Season Match",
            8: "Offline Match",
            9: "Local Match",
            10: "Duel (Ranked)",
            11: "Doubles (Ranked)",
            12: "Solo Standard (Ranked)",
            13: "3v3 (Ranked)",
            15: "Snow Day",
            16: "Rocket Labs",
            17: "Hoops (Casual)",
            18: "Rumble (Casual)",
            19: "Dropshot (Casual)",
            22: "Tournament",
            23: "Dropshot (Ranked)",
            24: "Local Match",
            26: "Tutorial",
            27: "Hoops (Ranked)",
            28: "Rumble (Ranked)",
            29: "Snow Day (Ranked)",
            30: "Chaos (Ranked)",
            31: "Gridiron",
            34: "Knockout",
            38: "Heatseeker",
            41: "3v3 Tournament",
            43: "2v2 Tournament",
            45: "1v1 Tournament",
            47: "2v2 Tournament (Double Elim)",
            48: "3v3 Tournament (Double Elim)",
        }
        
        # Tentative d'extraction intelligente de l'ID de la playlist
        raw_playlist = props.get("Playlist")
        playlist_id = None
        
        if isinstance(raw_playlist, int):
            playlist_id = raw_playlist
        elif isinstance(raw_playlist, dict):
            # Boxcars peut renvoyer {"Value": ID}
            playlist_id = raw_playlist.get("Value")
        
        if playlist_id is not None and playlist_id in PLAYLIST_MAP:
            playlist = PLAYLIST_MAP[playlist_id]
            # Si c'est un match privé (ID 6), on précise le format
            if playlist_id == 6:
                blue_size = sum(1 for p in players if p.team == 0)
                orange_size = sum(1 for p in players if p.team == 1)
                playlist = f"{blue_size}v{orange_size} Private"
        else:
            # Diagnostic si non trouvé
            print(f"[Matches] AVERTISSEMENT : Playlist ID {playlist_id} non reconnu ou absent.")
            
            # Fallback sur l'ancienne méthode si l'ID est inconnu ou absent
            team_size = props.get("TeamSize", 0)
            
            # Extraction du type de match (Online, Private, etc.)
            match_type_raw = props.get("MatchType", "")
            match_type = ""
            if isinstance(match_type_raw, dict):
                match_type = match_type_raw.get("Value", "")
            else:
                match_type = str(match_type_raw)
            
            replay_name = props.get("ReplayName", "").lower()
            
            # Logique Demandée : Online -> Ranked, Tournament -> Tournament, Private -> Private, else Casual
            if match_type == "Online" or "online" in replay_name:
                display_type = "Ranked"
            elif match_type == "Tournament" or "tournoi" in replay_name or "tournament" in replay_name:
                display_type = "Tournament"
            elif match_type == "Private":
                display_type = "Private Match"
            else:
                # Selon l'utilisateur, si pas d'online c'est du Casual
                display_type = "Casual"
            
            # Détection dynamique du format pour les matchs privés
            if display_type == "Private Match":
                blue_size = sum(1 for p in players if p.team == 0)
                orange_size = sum(1 for p in players if p.team == 1)
                playlist = f"{blue_size}v{orange_size} Private"
            else:
                playlist = f"{team_size}v{team_size}" if team_size else "Inconnue"
                if display_type:
                    playlist += f" ({display_type})"
        
        played_at_str = props.get("Date", "")
        played_at = None
        if played_at_str:
            try:
                # Format souvent utilisé par les parsers
                played_at = datetime.strptime(played_at_str, "%Y-%m-%d %H-%M-%S")
            except Exception:
                pass
                
        replay_id = props.get("Id", "") or os.path.splitext(replay_file.filename)[0]
        
        payload = MatchIngestPayload(
            replay_id=replay_id,
            played_at=played_at,
            playlist=playlist,
            result="Imported (Boxcars)",
            players=players,
        )
        
        res = await ingest_match(payload, db)
        return res
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload/parsing Boxcars: {str(e)}")


@router.post("/api/matches/upload_csv")
async def upload_csv(csv_file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload_dir = os.path.join(os.getcwd(), "uploaded_replays")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, csv_file.filename)
    
    try:
        content = await csv_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Appel au service CSV
        match_data = CSVService.parse_match_csv(file_path)
            
        payload = MatchIngestPayload(
            replay_id=match_data["replay_id"],
            played_at=match_data["played_at"],
            playlist=match_data["playlist"],
            result=match_data["result"],
            # On convertit les dicts de joueurs en objets PlayerStatIn
            players=[PlayerStatIn(**p) for p in match_data["players"]],
        )
        
        res = await ingest_match(payload, db)
        return res
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du CSV : {str(e)}")