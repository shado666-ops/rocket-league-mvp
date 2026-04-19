from __future__ import annotations

import re
from datetime import datetime, timedelta

from collections import defaultdict
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import json
import app.services.private_service as ps
from models import ClubMember, Match, MatchPlayerStat, Player, Season, Setting, Notification

MAIN_PLAYER_NAME = "Shado666"


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def get_unread_notifications_count(db: Session) -> int:
    limit = datetime.utcnow() - timedelta(hours=48)
    return db.query(func.count(Notification.id)).filter(
        Notification.is_read.is_(False),
        Notification.created_at >= limit
    ).scalar() or 0


def get_club_name(db: Session) -> str:
    return get_setting(db, "club_name", "Mon Club")


def get_club_tag(db: Session) -> str:
    return get_setting(db, "club_tag", "CLUB")


def safe_div(a: float, b: float) -> float:
    return round(a / b, 2) if b else 0.0


def get_season_for_date(date: datetime, seasons: list[Season]) -> str:
    """Détermine à quelle saison appartient une date, sinon retourne le mois/année."""
    for s in seasons:
        if s.start_date <= date <= s.end_date:
            return s.name
    
    # Fallback to French month name
    months_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    return f"{months_fr[date.month]} {date.year}"


def calculate_performance_rating(winrate: float, score: float, goals: float, saves: float, assists: float, shots: float, playlist: str | None = None) -> int:
    playlist = (playlist or "").lower()
    
    # Defaults (3v3 bases)
    base_score = 400.0
    base_goals = 2.0
    base_saves = 2.0
    base_shots = 3.0
    base_assists = 1.0
    
    if "2v2" in playlist or "doubles" in playlist:
        base_score = 600.0
        base_goals = 3.0
        base_saves = 3.0
        base_shots = 4.0
        base_assists = 1.0
    elif "3v3" in playlist or "standard" in playlist:
        base_score = 400.0
        base_goals = 2.0
        base_saves = 2.0
        base_shots = 3.0
        base_assists = 1.0

    norm_score = min((score / base_score) * 100, 100.0)
    norm_goals = min((goals / base_goals) * 100, 100.0)
    norm_saves = min((saves / base_saves) * 100, 100.0)
    norm_assists = min((assists / base_assists) * 100, 100.0)
    norm_shots = min((shots / base_shots) * 100, 100.0)
    
    # Weighted formula (15% Win, 25% Score, 20% Goals, 10% Shots, 10% Assists, 20% Saves)
    rating = (winrate * 0.15) + (norm_score * 0.25) + (norm_goals * 0.20) + (norm_saves * 0.20) + (norm_shots * 0.10) + (norm_assists * 0.10)
    return int(round(rating))


def time_to_seconds(t_str: str | None) -> int:
    if not t_str or ":" not in t_str:
        return 0
    try:
        parts = t_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0
    except:
        return 0


def seconds_to_time(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}"


def get_active_club_member_map(db: Session) -> dict[str, str]:
    """Retourne un mapping pseudo -> display_name_principal pour tous les membres actifs."""
    # On utilise joinedload pour éviter le N+1 sur les aliases
    members = db.query(ClubMember).options(joinedload(ClubMember.aliases)).filter(ClubMember.is_active.is_(True)).all()
    mapping = {}
    for m in members:
        mapping[m.display_name] = m.display_name
        for a in m.aliases:
            mapping[a.pseudo] = m.display_name
    return mapping


def get_active_club_member_names(db: Session) -> list[str]:
    """Retourne uniquement les noms d'affichage principaux des membres actifs."""
    rows = (
        db.query(ClubMember.display_name)
        .filter(ClubMember.is_active.is_(True))
        .order_by(ClubMember.display_name.asc())
        .all()
    )
    return [row[0] for row in rows]


def get_player_rows(db: Session, player_name: str, exclude_casual: bool = False) -> list[MatchPlayerStat]:
    # Si c'est un membre du club, on récupère aussi ses pseudos/aliases
    member = db.query(ClubMember).filter(ClubMember.display_name == player_name).first()
    pseudos = [player_name]
    if member:
        pseudos += [a.pseudo for a in member.aliases]

    query = (
        db.query(MatchPlayerStat)
        .join(Player, MatchPlayerStat.player_id == Player.id)
        .join(Match, MatchPlayerStat.match_id == Match.id)
        .options(
            joinedload(MatchPlayerStat.player), 
            joinedload(MatchPlayerStat.match).joinedload(Match.player_stats)
        )
        .filter(Player.display_name.in_(pseudos))
    )
    
    if exclude_casual:
        query = query.filter(~Match.playlist.ilike("%casual%"))
        
    return (
        query
        .order_by(Match.played_at.asc(), Match.id.asc())
        .all()
    )


def build_player_summary(rows: list[MatchPlayerStat]) -> dict[str, float | int]:
    matches_count = len(rows)
    wins = sum(1 for r in rows if r.won)
    goals_total = sum(r.goals for r in rows)
    assists_total = sum(r.assists for r in rows)
    saves_total = sum(r.saves for r in rows)
    shots_total = sum(r.shots for r in rows)
    score_total = sum(r.score for r in rows)

    winrate = safe_div(wins * 100, matches_count)
    score_per_match = safe_div(score_total, matches_count)
    goals_per_match = safe_div(goals_total, matches_count)
    assists_per_match = safe_div(assists_total, matches_count)
    saves_per_match = safe_div(saves_total, matches_count)
    shots_per_match = safe_div(shots_total, matches_count)

    demolishes_total = sum(r.demolishes or 0 for r in rows)
    pads_total = sum(r.pads or 0 for r in rows)
    boost_total = sum(r.boost_usage or 0 for r in rows)
    possession_sec_total = sum(time_to_seconds(r.possession_time) for r in rows)

    demolishes_per_match = safe_div(demolishes_total, matches_count)
    pads_per_match = safe_div(pads_total, matches_count)
    boost_per_match = safe_div(boost_total, matches_count)
    possession_per_match = seconds_to_time(safe_div(possession_sec_total, matches_count))
    
    # Calculate MVPs
    mvps_total = 0
    for r in rows:
        match_stats = r.match.player_stats
        if not match_stats: continue
        
        # Winning team MVP: highest score on the winning team
        winning_team = next((s.team for s in match_stats if s.won), None)
        if winning_team is not None:
            # Find max score on winning team
            mvp_stat = max([s for s in match_stats if s.team == winning_team], key=lambda s: s.score)
            if mvp_stat.player_id == r.player_id:
                mvps_total += 1
        else:
            # Non-standard game (all lost or all unknown), highest score is MVP
            mvp_stat = max(match_stats, key=lambda s: s.score)
            if mvp_stat.player_id == r.player_id:
                mvps_total += 1

    # Distinguish 2v2 and 3v3 by calculating the average of individual match ratings
    individual_ratings = []
    for r in rows:
        match_rating = calculate_performance_rating(
            winrate=100.0 if r.won else 0.0,
            score=float(r.score),
            goals=float(r.goals),
            saves=float(r.saves),
            assists=float(r.assists),
            shots=float(r.shots),
            playlist=r.match.playlist
        )
        individual_ratings.append(match_rating)
    
    performance_rating = int(round(mean(individual_ratings))) if individual_ratings else 0

    # Calculate Records (Max in a single match)
    goals_max = max([r.goals for r in rows]) if rows else 0
    shots_max = max([r.shots for r in rows]) if rows else 0
    assists_max = max([r.assists for r in rows]) if rows else 0
    saves_max = max([r.saves for r in rows]) if rows else 0

    # Calculate Shooting Ratio
    shooting_percentage = safe_div(goals_total * 100, shots_total)

    return {
        "matches_together": matches_count,
        "winrate": winrate,
        "goals_per_match": goals_per_match,
        "assists_per_match": assists_per_match,
        "saves_per_match": saves_per_match,
        "shots_per_match": shots_per_match,
        "goals_max": goals_max,
        "assists_max": assists_max,
        "saves_max": saves_max,
        "shots_max": shots_max,
        "shooting_percentage": shooting_percentage,
        "score_per_match": score_per_match,
        "demolishes_per_match": demolishes_per_match,
        "pads_per_match": pads_per_match,
        "boost_per_match": boost_per_match,
        "possession_per_match": possession_per_match,
        "performance_rating": performance_rating,
        "mvps": mvps_total,
    }


def get_match_category_and_name(match: Match, member_map: dict[str, str]) -> tuple[str, str]:
    playlist_lower = match.playlist.lower()
    is_private_name = "private" in playlist_lower or "privé" in playlist_lower
    
    t0_club = sum(1 for ps in match.player_stats if ps.team == 0 and member_map.get(ps.player.display_name))
    t1_club = sum(1 for ps in match.player_stats if ps.team == 1 and member_map.get(ps.player.display_name))
    is_private_composition = (t0_club > 0 and t1_club > 0)
    
    is_private = is_private_name or is_private_composition
    is_tournament = "tourn" in playlist_lower
    club_memb_count = t0_club + t1_club
    
    category = "other"
    cat_name = match.playlist
    if is_tournament:
        category = "tournaments"
        cat_name = "Tournois"
    elif is_private:
        category = "private"
        cat_name = "Matchs privés"
    elif "3v3" in playlist_lower or "standard" in playlist_lower:
        if club_memb_count >= 3: 
            category = "3v3_club"
            cat_name = "Entre nous (3v3)"
        elif club_memb_count > 0: 
            category = "3v3_random"
            cat_name = "Avec Random (3v3)"
    elif "2v2" in playlist_lower or "doubles" in playlist_lower:
        if club_memb_count >= 2: 
            category = "2v2_club"
            cat_name = "Entre nous (2v2)"
    elif "4v4" in playlist_lower or "chaos" in playlist_lower:
        category = "4v4_club"
        cat_name = "Mode Chaos (4v4)"
    elif "1v1" in playlist_lower or "duel" in playlist_lower:
        category = "1v1_ranked"
        cat_name = "Duel"
    elif "casual" in playlist_lower:
        category = "casual"
        cat_name = "Casual"
    
    return category, cat_name

def build_player_history_and_charts(rows: list[MatchPlayerStat], member_map: dict[str, str] = None) -> dict[str, Any]:
    history = []
    rating_chart = []
    score_chart = []
    goals_chart = []
    assists_chart = []
    saves_chart = []
    shots_chart = []
    demolishes_chart = []
    boost_chart = []
    possession_chart = []
    goals_saves_chart = []
    score_by_playlist: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rating_by_playlist: dict[str, list[dict[str, Any]]] = defaultdict(list)

    playlist_counter: dict[str, int] = defaultdict(int)
    playlist_scores: dict[str, list[int]] = defaultdict(list)

    wins = 0

    for row in rows:
        if row.won:
            wins += 1

        match_rating = calculate_performance_rating(
            winrate=100.0 if row.won else 0.0,
            score=float(row.score),
            goals=float(row.goals),
            saves=float(row.saves),
            assists=float(row.assists),
            shots=float(row.shots),
            playlist=row.match.playlist
        )

        category = "other"
        cat_name = row.match.playlist
        if member_map:
            category, cat_name = get_match_category_and_name(row.match, member_map)

        history.append(
            {
                "match_id": row.match.id,
                "date": row.match.played_at.strftime("%d/%m/%Y %H:%M"),
                "played_at_iso": row.match.played_at.isoformat(),
                "playlist": cat_name,
                "category": category,
                "cat_name": cat_name,
                "result": "Victoire" if row.won else "Défaite",
                "goals": row.goals,
                "assists": row.assists,
                "saves": row.saves,
                "shots": row.shots,
                "score": row.score,
                "demolishes": row.demolishes or 0,
                "possession_time": row.possession_time or "0:00",
                "rating": match_rating,
            }
        )

        label = row.match.played_at.strftime("%d/%m %H:%M")
        rating_chart.append({"label": label, "value": match_rating})
        score_chart.append({"label": label, "value": row.score})
        goals_chart.append({"label": label, "value": row.goals})
        assists_chart.append({"label": label, "value": row.assists})
        saves_chart.append({"label": label, "value": row.saves})
        shots_chart.append({"label": label, "value": row.shots})
        demolishes_chart.append({"label": label, "value": row.demolishes or 0})
        boost_chart.append({"label": label, "value": row.boost_usage or 0})
        possession_chart.append({"label": label, "value": time_to_seconds(row.possession_time)})
        goals_saves_chart.append(
            {
                "label": label,
                "goals": row.goals,
                "assists": row.assists,
                "saves": row.saves,
                "shots": row.shots,
            }
        )

        playlist_counter[cat_name] += 1
        playlist_scores[cat_name].append(row.score)
        score_by_playlist[cat_name].append({"label": label, "value": row.score})
        rating_by_playlist[cat_name].append({"label": label, "value": match_rating})

    matches_count = len(rows)

    matches_by_playlist = [
        {"playlist": playlist, "matches": count}
        for playlist, count in playlist_counter.items()
    ]
    matches_by_playlist.sort(key=lambda x: x["playlist"])

    avg_score_by_playlist = [
        {"playlist": playlist, "avg_score": round(mean(scores), 2)}
        for playlist, scores in playlist_scores.items()
    ]
    avg_score_by_playlist.sort(key=lambda x: x["playlist"])

    return {
        "history": list(reversed(history)),
        "charts": {
            "rating": rating_chart,
            "score": score_chart,
            "score_by_playlist": dict(score_by_playlist),
            "rating_by_playlist": dict(rating_by_playlist),
            "goals": goals_chart,
            "assists": assists_chart,
            "saves": saves_chart,
            "shots": shots_chart,
            "demolishes": demolishes_chart,
            "boost": boost_chart,
            "possession": possession_chart,
            "goals_saves": goals_saves_chart,
            "matches_by_playlist": matches_by_playlist,
            "avg_score_by_playlist": avg_score_by_playlist,
            "radar": [
                safe_div(sum(r.goals for r in rows), matches_count),
                safe_div(sum(r.saves for r in rows), matches_count),
                safe_div(sum(r.shots for r in rows), matches_count),
                safe_div(sum(r.assists for r in rows), matches_count),
            ],
            "pie": [wins, matches_count - wins],
        },
    }


def get_club_overview_data(db: Session, limit: int | None = 20) -> dict[str, Any]:
    member_map = get_active_club_member_map(db)
    all_pseudos = list(member_map.keys())
    primary_names = get_active_club_member_names(db)

    club_stats = (
        db.query(MatchPlayerStat)
        .join(Player, MatchPlayerStat.player_id == Player.id)
        .join(Match, MatchPlayerStat.match_id == Match.id)
        .options(joinedload(MatchPlayerStat.player), joinedload(MatchPlayerStat.match).joinedload(Match.player_stats))
        .filter(Player.display_name.in_(all_pseudos))
        .order_by(Match.played_at.desc(), Match.id.desc())
        .all()
    )

    club_rows_by_match: dict[int, list[MatchPlayerStat]] = defaultdict(list)
    for stat in club_stats:
        club_rows_by_match[stat.match_id].append(stat)

    mates_frequency = []
    winrate_with_mates = []

    for mate_name in primary_names:
        # On regroupe les stats de tous les pseudos de ce membre
        mate_rows = [s for s in club_stats if member_map.get(s.player.display_name) == mate_name]
        if not mate_rows:
            continue

        played = len(mate_rows)
        wins = sum(1 for s in mate_rows if s.won)

        mates_frequency.append({"name": mate_name, "matches": played})
        winrate_with_mates.append({"name": mate_name, "winrate": safe_div(wins * 100, played)})

    mates_frequency.sort(key=lambda x: x["matches"], reverse=True)
    winrate_with_mates.sort(key=lambda x: x["winrate"], reverse=True)

    # Historique et calculs de charts selon la limite
    query = db.query(Match).order_by(Match.played_at.desc(), Match.id.desc())
    if limit is not None:
        query = query.limit(limit)
    sorted_matches = query.all()
    # On les remet en ordre chronologique pour l'affichage cohérent si besoin, 
    # mais club_history sera inversé à la fin.
    sorted_matches.reverse() 

    # Re-calculer les stats club uniquement sur ces 20 derniers matchs pour les graphs
    recent_mates_freq: dict[str, int] = defaultdict(int)
    recent_mates_wins: dict[str, int] = defaultdict(int)
    
    match_ids_20 = [m.id for m in sorted_matches]
    recent_club_stats = [s for s in club_stats if s.match_id in match_ids_20]

    for mate_name in primary_names:
        mate_recent_rows = [s for s in recent_club_stats if member_map.get(s.player.display_name) == mate_name]
        if mate_recent_rows:
            played = len(mate_recent_rows)
            wins = sum(1 for s in mate_recent_rows if s.won)
            recent_mates_freq[mate_name] = played
            recent_mates_wins[mate_name] = wins

    mates_frequency_recent = [{"name": n, "matches": c} for n, c in recent_mates_freq.items()]
    winrate_with_mates_recent = [{"name": n, "winrate": safe_div(recent_mates_wins[n] * 100, recent_mates_freq[n])} for n in recent_mates_freq]

    mates_frequency_recent.sort(key=lambda x: x["matches"], reverse=True)
    winrate_with_mates_recent.sort(key=lambda x: x["winrate"], reverse=True)

    club_history = []

    for match in sorted_matches:
        rows = club_rows_by_match.get(match.id, [])
        if not rows:
            continue

        playlist_lower = match.playlist.lower()
        is_private_name = "private" in playlist_lower or "privé" in playlist_lower
        
        # Fallback detection by composition: club members on both teams?
        t0_club = sum(1 for ps in match.player_stats if ps.team == 0 and member_map.get(ps.player.display_name))
        t1_club = sum(1 for ps in match.player_stats if ps.team == 1 and member_map.get(ps.player.display_name))
        is_private_composition = (t0_club > 0 and t1_club > 0)
        
        is_private = is_private_name or is_private_composition
        
        team0 = []
        team1 = []
        player_list = []
        if is_private:
            team0 = sorted([member_map.get(ps.player.display_name, ps.player.display_name) for ps in match.player_stats if ps.team == 0])
            team1 = sorted([member_map.get(ps.player.display_name, ps.player.display_name) for ps in match.player_stats if ps.team == 1])
            players_str = " / ".join(team0) + " Vs " + " / ".join(team1)
        else:
            player_list = sorted({member_map.get(r.player.display_name, r.player.display_name) for r in rows})
            if ("3v3" in playlist_lower or "standard" in playlist_lower) and len(player_list) == 2:
                player_list.append("Random")
            players_str = ", ".join(player_list)

        # Calcul du score du match
        match_score = ""
        if is_private:
            # Pour les privates, on affiche Score Team 0 - Score Team 1 pour correspondre à l'ordre des joueurs
            s0 = sum(ps.goals for ps in match.player_stats if ps.team == 0)
            s1 = sum(ps.goals for ps in match.player_stats if ps.team == 1)
            match_score = f"{s0} - {s1}"
        else:
            # Score standard : Si le club gagne on affiche Gagnant - Perdant
            won = any(r.won for r in rows)
            winner_goals = sum(ps.goals for ps in match.player_stats if ps.won)
            loser_goals = sum(ps.goals for ps in match.player_stats if not ps.won)
            match_score = f"{winner_goals} - {loser_goals}" if won else f"{loser_goals} - {winner_goals}"

        # Identify category (fid) for styling
        is_tournament = "tourn" in playlist_lower
        club_memb_count = len({member_map.get(r.player.display_name) for r in rows if member_map.get(r.player.display_name)})
        
        category = "other"
        if is_tournament:
            category = "tournaments"
        category, cat_name = get_match_category_and_name(match, member_map)

        club_history.append(
            {
                "match_id": match.id,
                "date": match.played_at.strftime("%d/%m/%Y %H:%M"),
                "played_at_iso": match.played_at.isoformat(),
                "playlist": cat_name,
                "category": category,
                "players": players_str,
                "player_list": player_list,
                "team0": team0,
                "team1": team1,
                "is_private": is_private,
                "result": "Privé" if is_private else ("Victoire" if any(r.won for r in rows) else "Défaite"),
                "match_score": match_score,
                "goals": sum(r.goals for r in rows),
                "assists": sum(r.assists for r in rows),
                "saves": sum(r.saves for r in rows),
                "shots": sum(r.shots for r in rows),
                "demolishes": sum(r.demolishes or 0 for r in rows),
                "possession_time": seconds_to_time(sum(time_to_seconds(r.possession_time) for r in rows))
            }

        )

    return {
        "club_names": primary_names,
        "club_history": list(reversed(club_history)),
        "club_charts": {
            "mates_frequency": mates_frequency[:10],
            "winrate_with_mates": winrate_with_mates[:10],
        },
    }


def get_match_detail_data(db: Session, match_id: int) -> dict[str, Any] | None:
    match = (
        db.query(Match)
        .options(joinedload(Match.player_stats).joinedload(MatchPlayerStat.player))
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        return None

    member_map = get_active_club_member_map(db)
    
    # Identify teams and MVP
    player_stats = match.player_stats
    winning_team = next((s.team for s in player_stats if s.won), None)
    if winning_team is not None:
        mvp_stat = max([s for s in player_stats if s.team == winning_team], key=lambda ps: ps.score)
    else:
        mvp_stat = max(player_stats, key=lambda ps: ps.score)
        
    mvp_id = mvp_stat.player_id
    
    # Split players by team
    teams: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ps in player_stats:
        p_name = ps.player.display_name
        primary_name = member_map.get(p_name, p_name)
        teams[ps.team].append({
            "name": p_name,
            "primary_name": primary_name,
            "is_club_member": p_name in member_map,
            "score": ps.score,
            "goals": ps.goals,
            "assists": ps.assists,
            "saves": ps.saves,
            "shots": ps.shots,
            "demolishes": ps.demolishes or 0,
            "possession": ps.possession_time or "0:00",
            "is_mvp": ps.player_id == mvp_id,
            "won": ps.won
        })
        
    # Sort teams by score
    for team_id in teams:
        teams[team_id].sort(key=lambda x: x["score"], reverse=True)
        
    # Determine which team is Blue (0) and Orange (1)
    # If standard RL, 0=Blue, 1=Orange
    blue_team = teams.get(0, [])
    orange_team = teams.get(1, [])
    
    blue_score = sum(p["goals"] for p in blue_team)
    orange_score = sum(p["goals"] for p in orange_team)
    
    return {
        "match_id": match.id,
        "date": match.played_at.strftime("%d/%m/%Y %H:%M:%S"),
        "playlist": match.playlist,
        "blue_team": blue_team,
        "orange_team": orange_team,
        "blue_score": blue_score,
        "orange_score": orange_score,
        "winner": "Blue" if blue_score > orange_score else ("Orange" if orange_score > blue_score else "Tie"),
        "mvp_name": mvp_stat.player.display_name
    }


def get_club_archives_data(db: Session, category_fid: str | None = None) -> dict[str, Any]:
    member_map = get_active_club_member_map(db)
    all_pseudos = set(member_map.keys())
    
    matches = (
        db.query(Match)
        .options(joinedload(Match.player_stats).joinedload(MatchPlayerStat.player))
        .order_by(Match.played_at.asc())
        .all()
    )

    # Dictionary to store stats for each formation
    # key: formation_id (e.g. "3v3_club", "3v3_random", etc.)
    # value: { formation_name, player_combinations: { "Player A / Player B": { seasons: { "Season name": stats } } } }
    archives: dict[str, Any] = {
        "2v2_club": {"name": "Entre nous (2v2)", "groups": {}},
        "3v3_club": {"name": "Entre nous (3v3)", "groups": {}},
        "3v3_random": {"name": "Avec Random (3v3)", "groups": {}},
        "4v4_club": {"name": "Mode Chaos (4v4)", "groups": {}},
        "private": {"name": "Matchs privés", "groups": {}},
        "tournaments": {"name": "Tournois", "groups": {}}, 
    }

    # Map pour collecter les matchs de tournoi par session
    # Touche: (date, frozenset(membres_du_club))
    tourney_sessions_map: dict[tuple, list] = defaultdict(list)

    # Map pour collecter les matchs par série private
    # Clé: combination_name
    private_current_series: dict[str, dict] = {}
    
    # Get main player for perspective in private games
    main_player_name = MAIN_PLAYER_NAME

    # Suivi pour scinder les sessions de tournoi si besoin
    # (s_date, membres) -> {"idx": 0, "last_time": datetime, "last_won": bool}
    last_tourney_info = {}

    for match in matches:
        # Determine formation and player set
        player_stats = match.player_stats
        if not player_stats or len(player_stats) < 2: continue
        
        # Identify MVP (highest score on the winning team)
        winning_team = next((s.team for s in player_stats if s.won), None)
        if winning_team is not None:
            mvp_pseudo = max([s for s in player_stats if s.team == winning_team], key=lambda ps: ps.score).player.display_name
        else:
            mvp_pseudo = max(player_stats, key=lambda ps: ps.score).player.display_name
        
        # MVP member name
        mvp_member = member_map.get(mvp_pseudo, mvp_pseudo)
        
        # Filter players on the winning team (if win) or whichever team has club members
        # Usually club members play on the same team. Let's find teams with club members.
        teams: dict[int, list[str]] = defaultdict(list)
        teams_club_members: dict[int, list[str]] = defaultdict(list)
        team_won: dict[int, bool] = {}

        for s in player_stats:
            p_pseudo = s.player.display_name
            p_member = member_map.get(p_pseudo)
            
            # Store pseudo representatively for teams display
            teams[s.team].append(p_member if p_member else p_pseudo)
            
            if p_pseudo in all_pseudos:
                teams_club_members[s.team].append(p_member) # Use primary name
            team_won[s.team] = s.won

        playlist_lower = match.playlist.lower()
        is_tournament = "tournoi" in playlist_lower or "tournament" in playlist_lower
        is_ranked = "ranked" in playlist_lower or is_tournament
        is_private = "private" in playlist_lower or "privé" in playlist_lower

        if not (is_ranked or is_private):
            continue

        # --- GESTION SPÉCIFIQUE DES TOURNOIS (REGROUPEMENT PAR SESSION) ---
        if is_tournament:
            # On cherche l'équipe qui contient au moins un membre du club
            club_team_id = None
            for team_id, members in teams_club_members.items():
                if members:
                    club_team_id = team_id
                    break
            
            if club_team_id is not None:
                membres = frozenset(teams_club_members[club_team_id])
                s_date = match.played_at.date()
                group_key = (s_date, membres)
                
                # Logique de scission si nécessaire
                if group_key not in last_tourney_info:
                    last_tourney_info[group_key] = {"idx": 0, "last_time": None, "last_won": True}
                
                info = last_tourney_info[group_key]
                if info["last_time"]:
                    gap = (match.played_at - info["last_time"]).total_seconds() / 60
                    # On scinde si :
                    # 1. Plus d'une heure d'écart
                    # 2. Défaite au dernier match ET plus de 10 min d'écart (élimination + Second Chance)
                    if gap > 60 or (not info["last_won"] and gap > 10):
                        info["idx"] += 1
                
                # Mise à jour pour le prochain match de ce groupe
                info["last_time"] = match.played_at
                info["last_won"] = team_won[club_team_id]

                # On identifie la session par la date, l'équipe exacte et l'index de session
                session_key = (s_date, membres, info["idx"])
                tourney_sessions_map[session_key].append({
                    "match": match,
                    "club_team_id": club_team_id,
                    "teams": teams,
                    "team_won": team_won,
                    "mvp_pseudo": mvp_pseudo
                })
            continue

        # --- SPECIAL HANDLING FOR PRIVATE MATCHES (Series BO) ---
        if is_private and len(teams) >= 2:
            team_ids = list(teams.keys())
            t0, t1 = team_ids[0], team_ids[1]
            t0_players = teams[t0]
            t1_players = teams[t1]
            
            # Determine perspective team
            our_team_id = t0
            if main_player_name:
                if main_player_name in t1_players: our_team_id = t1
                elif main_player_name not in t0_players:
                    if " / ".join(sorted(t1_players)) < " / ".join(sorted(t0_players)): our_team_id = t1
            else:
                if " / ".join(sorted(t1_players)) < " / ".join(sorted(t0_players)): our_team_id = t1
            
            their_team_id = t1 if our_team_id == t0 else t0
            our_team_names = sorted(teams[our_team_id])
            their_team_names = sorted(teams[their_team_id])
            
            format_str = f"{len(our_team_names)}v{len(their_team_names)}"
            combination_name = f"[{format_str}] " + " et ".join(our_team_names) + " Vs " + " et ".join(their_team_names)
            fid = "private"
            
            if combination_name not in archives[fid]["groups"]:
                archives[fid]["groups"][combination_name] = {
                    "series_list": [], # Use series_list instead of matches
                    "streaks": {"current_win": 0, "current_loss": 0, "max_win": 0, "max_loss": 0}
                }
            
            match_data = {
                "id": match.id,
                "date": match.played_at,
                "won": team_won[our_team_id],
                "playlist": match.playlist,
                "goals_scored": sum(ps.goals for ps in player_stats if ps.team == our_team_id),
                "goals_conceded": sum(ps.goals for ps in player_stats if ps.team == their_team_id),
                "individual": {member_map.get(ps.player.display_name, ps.player.display_name): {
                    "score": ps.score, "goals": ps.goals, "assists": ps.assists, "saves": ps.saves, "shots": ps.shots,
                    "is_mvp": ps.player.display_name == mvp_pseudo
                } for ps in player_stats}
            }
            
            # Grouping Logic into Series
            last_series = private_current_series.get(combination_name)
            
            # Use an 8-hour gap to keep sessions together across midnight.
            # A series ends immediately if someone hits 4 wins (BO7).
            
            need_new_series = True
            if last_series:
                gap = (match.played_at - last_series["last_time"])
                is_same_session = gap < timedelta(hours=8)
                
                # Calculate current wins in the last_series
                our_wins = sum(1 for g in last_series["games"] if g["won"])
                their_wins = len(last_series["games"]) - our_wins
                is_concluded = (our_wins >= 4 or their_wins >= 4)
                
                if is_same_session and not is_concluded:
                    # Continue current series
                    last_series["games"].append(match_data)
                    last_series["last_time"] = match.played_at
                    need_new_series = False
            
            if need_new_series:
                new_series = {
                    "games": [match_data],
                    "start_time": match.played_at,
                    "last_time": match.played_at,
                    "format": "Série"
                }
                archives[fid]["groups"][combination_name]["series_list"].append(new_series)
                private_current_series[combination_name] = new_series
                
            continue # Important: don't process via standard loop

        # --- STANDARD HANDLING (1 entry per winning team/club formation) ---
        for team_id, members in teams.items():
            club_memb = teams_club_members.get(team_id, [])
            if not club_memb: continue # No club member on this team

            fid = None
            if is_tournament:
                fid = "tournaments"
            elif "3v3" in playlist_lower or "standard" in playlist_lower:
                if len(club_memb) >= 3: fid = "3v3_club"
                elif 0 < len(club_memb) < 3: fid = "3v3_random"
            elif "2v2" in playlist_lower or "doubles" in playlist_lower:
                if len(club_memb) >= 2: fid = "2v2_club"
            elif "4v4" in playlist_lower or "chaos" in playlist_lower:
                if len(club_memb) >= 2: fid = "4v4_club"

            if not fid: continue

            # Group within fid by the specific combination of club members (using primary names)
            sorted_m = sorted(club_memb)
            if ("3v3" in playlist_lower or "standard" in playlist_lower) and 0 < len(club_memb) < 3:
                sorted_m.append("Random")
                
            combination_name = " / ".join(sorted_m)
            if combination_name not in archives[fid]["groups"]:
                archives[fid]["groups"][combination_name] = {
                    "matches": [],
                    "streaks": {"current_win": 0, "current_loss": 0, "max_win": 0, "max_loss": 0}
                }
            
            # For filtering player_stats, we need the pseudos that belong to the members in this team
            # But we already have member names in club_memb. 
            # We want to keep only stats for players who are in this club formation.
            
            archives[fid]["groups"][combination_name]["matches"].append({
                "date": match.played_at,
                "won": team_won[team_id],
                "playlist": match.playlist,
                "goals_scored": sum(ps.goals for ps in player_stats if ps.team == team_id),
                "goals_conceded": sum(ps.goals for ps in player_stats if ps.team != team_id),
                "individual": {member_map.get(ps.player.display_name, ps.player.display_name): {
                    "score": ps.score, "goals": ps.goals, "assists": ps.assists, "saves": ps.saves, "shots": ps.shots,
                    "is_mvp": ps.player.display_name == mvp_pseudo
                } for ps in player_stats if member_map.get(ps.player.display_name) in club_memb}
            })

    # --- TRAITEMENT DES SESSIONS DE TOURNOI (DÉDUCTION DU CLASSEMENT) ---
    for (s_date, s_members_set, s_idx), s_matches_data in tourney_sessions_map.items():
        # Trier les matchs par heure
        s_matches_data.sort(key=lambda x: x["match"].played_at)
        
        # Identifier les rounds et BO3
        rounds = []
        for m_data in s_matches_data:
            match = m_data["match"]
            club_team_id = m_data["club_team_id"]
            opponent_team_id = 1 if club_team_id == 0 else 0
            
            # Nom de l'adversaire
            opponent_display = " / ".join(sorted(m_data["teams"][opponent_team_id]))
            
            if not rounds or rounds[-1]["opponent"] != opponent_display:
                rounds.append({
                    "opponent": opponent_display,
                    "games": []
                })
            
            rounds[-1]["games"].append({
                "match": match,
                "won": m_data["team_won"][club_team_id],
                "score_club": sum(ps.goals for ps in match.player_stats if ps.team == club_team_id),
                "score_opp": sum(ps.goals for ps in match.player_stats if ps.team == opponent_team_id),
                "mvp_pseudo": m_data["mvp_pseudo"],
                "date_str": match.played_at.strftime("%H:%M")
            })

        # Déduire le classement final
        placement = "Inconnu"
        last_round_idx = len(rounds)
        last_round = rounds[-1]
        wins_in_last = sum(1 for g in last_round["games"] if g["won"])
        losses_in_last = sum(1 for g in last_round["games"] if not g["won"])
        
        won_last_series = wins_in_last > losses_in_last
        
        if not won_last_series:
            # Éliminé au tour N
            if last_round_idx == 1: placement = "Top 32"
            elif last_round_idx == 2: placement = "Top 16"
            elif last_round_idx == 3: placement = "Top 8"
            elif last_round_idx == 4: placement = "Top 4"
            elif last_round_idx >= 5: placement = "Finaliste"
        else:
            # Vainqueur ? (5 tours gagnés minimum pour 32 joueurs)
            if last_round_idx >= 5:
                placement = "Vainqueur"
            else:
                tour_names = ["16èmes", "8èmes", "Quarts", "Demis", "Finale"]
                next_tour = tour_names[last_round_idx] if last_round_idx < len(tour_names) else "Suivant"
                placement = f"Qualifié en {next_tour}"

        # Cumuler stats individuelles de la session
        session_individual = defaultdict(lambda: {"score": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "mvps": 0, "matches": 0})
        for r in rounds:
            for g in r["games"]:
                for ps in g["match"].player_stats:
                    p_disp = ps.player.display_name
                    p_name = member_map.get(p_disp, p_disp)
                    if p_name in s_members_set:
                        s = session_individual[p_name]
                        s["score"] += ps.score
                        s["goals"] += ps.goals
                        s["assists"] += ps.assists
                        s["saves"] += ps.saves
                        s["shots"] += ps.shots
                        s["matches"] += 1
                        if p_disp == g["mvp_pseudo"]:
                            s["mvps"] += 1
        
        # Convertir en format compatible templates (statistiques moyennes)
        players_stats_list = []
        for p_name in sorted(list(s_members_set)):
            v = session_individual[p_name]
            players_stats_list.append({
                "name": p_name,
                "matches": v["matches"],
                "score": v["score"],
                "avg_score": safe_div(v["score"], v["matches"]),
                "goals": v["goals"],
                "avg_goals": safe_div(v["goals"], v["matches"]),
                "assists": v["assists"],
                "avg_assists": safe_div(v["assists"], v["matches"]),
                "saves": v["saves"],
                "avg_saves": safe_div(v["saves"], v["matches"]),
                "shots": v["shots"],
                "avg_shots": safe_div(v["shots"], v["matches"]),
                "ratio": safe_div(v["goals"] * 100, v["shots"]),
                "mvp_count": v["mvps"]
            })

        sorted_m = sorted(list(s_members_set))
        # Si c'est un tournoi 3v3 et qu'il n'y a que 2 membres, on ajoute "Random" pour le regroupement
        playlist_sample = s_matches_data[0]["match"].playlist.lower()
        if ("3v3" in playlist_sample or "standard" in playlist_sample) and len(sorted_m) == 2:
            sorted_m.append("Random")
            
        comp_name = " / ".join(sorted_m)
        if comp_name not in archives["tournaments"]["groups"]:
            archives["tournaments"]["groups"][comp_name] = {
                "sessions": [],
                "total": {"matches": 0, "wins": 0, "losses": 0, "sessions": 0}
            }
        
        g = archives["tournaments"]["groups"][comp_name]
        g["sessions"].append({
            "date": s_date.strftime("%d/%m/%Y"),
            "start_time": s_matches_data[0]["match"].played_at,
            "composition": comp_name,
            "placement": placement,
            "rounds": rounds,
            "total_matches": len(s_matches_data),
            "players": players_stats_list
        })
        
        # Accumulate totals for the composition summary
        g["total"]["matches"] += len(s_matches_data)
        g["total"]["sessions"] += 1
        # Deduction: if won last series in tournament, count as tournament win? 
        # Or just track if became "Vainqueur"
        if placement == "Vainqueur":
            g["total"]["wins"] += 1
        else:
            g["total"]["losses"] += 1

    # Trier les sessions dans chaque groupe par date décroissante
    for comp_name in archives["tournaments"]["groups"]:
        archives["tournaments"]["groups"][comp_name]["sessions"].sort(key=lambda x: x["start_time"], reverse=True)

    # Fetch all user-defined seasons
    seasons_meta = db.query(Season).order_by(Season.start_date.desc()).all()

    # Now calculate advanced stats for each group
    formatted_archives = []
    for fid, f_data in archives.items():
        if fid == "tournaments":
            # Tournaments use groups now
            group_list_tourney = []
            for comp_name, comp_data in f_data["groups"].items():
                group_list_tourney.append({
                    "composition": comp_name,
                    "clean_composition": comp_name,
                    "sessions": comp_data["sessions"],
                    "total": comp_data["total"]
                })
            
            # Sort compositions by number of matches
            group_list_tourney.sort(key=lambda x: x["total"]["matches"], reverse=True)

            formatted_archives.append({
                "fid": fid,
                "name": f_data["name"],
                "groups": group_list_tourney
            })
            continue

        # Case where no matches found, we still keep the category if desired by user
        group_list = []
        for comp_name, comp_data in f_data["groups"].items():
            if fid == "private":
                # Special Series logic for Private games
                series_list_data = comp_data["series_list"]
                
                for series in series_list_data:
                    our_wins = sum(1 for g in series["games"] if g["won"])
                    their_wins = len(series["games"]) - our_wins
                    series["score_str"] = f"{our_wins} - {their_wins}"
                    series["our_wins"] = our_wins
                    series["their_wins"] = their_wins
                    series["won_series"] = (our_wins > their_wins)
                    
                    # Format detection
                    if our_wins >= 4 or their_wins >= 4: series["format"] = "BO7"
                    elif our_wins >= 3 or their_wins >= 3: series["format"] = "BO5"
                    elif our_wins >= 2 or their_wins >= 2: series["format"] = "BO3"
                    elif len(series["games"]) == 1: series["format"] = "Match unique"
                    else: series["format"] = "Série"
                
                    # Flatten matches for season grouping logic below
                    matches_list = []
                    for s in series_list_data:
                        matches_list.extend(s["games"])
                
                # Summary for private games
                comp_data["series_summary"] = {
                    "total": len(series_list_data),
                    "wins": sum(1 for s in series_list_data if s["won_series"]),
                    "losses": sum(1 for s in series_list_data if not s["won_series"])
                }
            else:
                matches_list = comp_data["matches"]
            
            streaks = comp_data["streaks"]
            
            # Calculate streaks and group by season
            seasons_stats: dict[str, Any] = {} # Key: Season Name
            current_win = 0
            current_loss = 0
            
            for m in matches_list:
                # Streak logic
                if m["won"]:
                    current_win += 1
                    current_loss = 0
                    if current_win > streaks["max_win"]: streaks["max_win"] = current_win
                else:
                    current_loss += 1
                    current_win = 0
                    if current_loss > streaks["max_loss"]: streaks["max_loss"] = current_loss

                season_key = get_season_for_date(m["date"], seasons_meta)
                if season_key not in seasons_stats:
                    seasons_stats[season_key] = {
                        "name": season_key, 
                        "total": {"matches": 0, "wins": 0, "losses": 0, "goals_scored": 0, "goals_conceded": 0},
                        "players": {}
                    }
                
                s_players = seasons_stats[season_key]["players"]
                for p_name, p_stats in m["individual"].items():
                    if p_name not in s_players:
                        s_players[p_name] = {"score": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "mvps": 0}
                    for k in ["score", "goals", "assists", "saves", "shots"]:
                        s_players[p_name][k] += p_stats[k]
                    if p_stats.get("is_mvp"):
                        s_players[p_name]["mvps"] += 1

                t = seasons_stats[season_key]["total"]
                t["matches"] += 1
                if m["won"]: t["wins"] += 1
                else: t["losses"] += 1
                t["goals_scored"] += m["goals_scored"]
                t["goals_conceded"] += m["goals_conceded"]

            # Finalize season stats
            season_list = []
            for s_key, s_data in seasons_stats.items():
                t = s_data["total"]
                season_list.append({
                    "name": s_key,
                    "matches": t["matches"],
                    "wins": t["wins"],
                    "losses": t["losses"],
                    "winrate": safe_div(t["wins"] * 100, t["matches"]),
                    "lossrate": safe_div(t["losses"] * 100, t["matches"]),
                    "goals_scored": t["goals_scored"],
                    "goals_conceded": t["goals_conceded"],
                    "avg_scored": safe_div(t["goals_scored"], t["matches"]),
                    "avg_conceded": safe_div(t["goals_conceded"], t["matches"]),
                    "players": [
                        {
                            "name": p, 
                            "matches": t["matches"],
                            "score": v["score"],
                            "avg_score": safe_div(v["score"], t["matches"]),
                            "goals": v["goals"],
                            "avg_goals": safe_div(v["goals"], t["matches"]),
                            "assists": v["assists"],
                            "avg_assists": safe_div(v["assists"], t["matches"]),
                            "saves": v["saves"],
                            "avg_saves": safe_div(v["saves"], t["matches"]),
                            "shots": v["shots"],
                            "avg_shots": safe_div(v["shots"], t["matches"]),
                            "ratio": safe_div(v["goals"] * 100, v["shots"]) if v["shots"] > 0 else 0,
                            "mvp_count": v["mvps"]
                        } for p, v in s_data["players"].items()
                    ]
                })

                # Sort players by their appearance in the composition string
                # Remove [XvY] prefix for private games
                clean_comp = re.sub(r'^\[.*?\]\s*', '', comp_name)
                comp_parts = clean_comp.replace(' Vs ', ' et ').replace(' / ', ' et ').split(' et ')
                ordered_names = [p.strip() for p in comp_parts]
                
                # We only want to sort players who are actually in the season data
                season_list[-1]["players"].sort(key=lambda p: ordered_names.index(p["name"]) if p["name"] in ordered_names else 999)
            
            # Custom sort for seasons: User defined seasons first (by date), then fallback months
            # Simplified sort for now
            season_list.sort(key=lambda x: x["name"], reverse=True) 

            # Format parsing for UI: separate [XvY] from names
            m = re.match(r'^(\[.*?\])\s*(.*)', comp_name)
            if m:
                format_prefix = m.group(1)
                clean_comp = m.group(2)
            else:
                format_prefix = ""
                clean_comp = comp_name

            group_list.append({
                "composition": comp_name,
                "format_prefix": format_prefix,
                "clean_composition": clean_comp,
                "seasons": season_list,
                "series": comp_data.get("series_list", []),
                "series_summary": comp_data.get("series_summary", {}), # Add summary to the group data
                "max_win_streak": streaks["max_win"],
                "max_loss_streak": streaks["max_loss"],
                "total": {
                    "matches": sum(s["matches"] for s in season_list),
                    "wins": sum(s["wins"] for s in season_list),
                    "losses": sum(s["losses"] for s in season_list),
                    "goals_scored": sum(s["goals_scored"] for s in season_list),
                    "goals_conceded": sum(s["goals_conceded"] for s in season_list),
                    "avg_scored": safe_div(sum(s["goals_scored"] for s in season_list), sum(s["matches"] for s in season_list) if season_list else 1),
                    "avg_conceded": safe_div(sum(s["goals_conceded"] for s in season_list), sum(s["matches"] for s in season_list) if season_list else 1),
                }
            })
        
        formatted_archives.append({
            "fid": fid,
            "name": f_data["name"],
            "groups": group_list if fid != "tournaments" else group_list_tourney,
            "sessions": []
        })

    # IF category_fid is provided, filter and return ONLY that category
    if category_fid:
        cat_data = next((a for a in formatted_archives if a["fid"] == category_fid), None)
        return {"formation": cat_data} if cat_data else {}
    
    # ELSE, Return menu data (summary for each category)
    menu = []
    for a in formatted_archives:
        total_matches = sum(g["total"]["matches"] for g in a["groups"])
        total_wins = sum(g["total"]["wins"] for g in a["groups"])
        
        if a["fid"] == "tournaments":
            total_sessions = sum(g["total"]["sessions"] for g in a["groups"])
            menu.append({
                "fid": a["fid"],
                "name": a["name"],
                "count": len(a["groups"]),
                "count_label": "compositions",
                "total_matches": total_matches,
                "total_sessions": total_sessions
            })
        else:
            menu.append({
                "fid": a["fid"],
                "name": a["name"],
                "count": len(a["groups"]),
                "count_label": "compositions",
                "total_matches": total_matches,
                "winrate": safe_div(total_wins * 100, total_matches)
            })
    
    return {"archives_menu": menu}


def get_seasons(db: Session):
    return db.query(Season).order_by(Season.start_date.desc()).all()


def add_season(db: Session, name: str, start_date: datetime, end_date: datetime):
    season = Season(name=name, start_date=start_date, end_date=end_date)
    db.add(season)
    db.commit()
    return season


def delete_season(db: Session, season_id: int):
    season = db.query(Season).filter(Season.id == season_id).first()
    if season:
        db.delete(season)
        db.commit()
    return season


def get_dashboard_data(db: Session, limit: int | None = 20) -> dict[str, Any]:
    # On exclut casual par défaut pour les stats globales du dashboard
    player_rows = get_player_rows(db, MAIN_PLAYER_NAME, exclude_casual=True)
    
    # Harmonisation : On ne garde que les derniers matchs demandés pour le dashboard
    recent_player_rows = player_rows[-limit:] if limit is not None else player_rows
    
    player_summary = build_player_summary(player_rows)
    player_data = build_player_history_and_charts(recent_player_rows)
    club_data = get_club_overview_data(db, limit=limit)
    all_club_members = get_all_club_members(db)
    seasons = get_seasons(db)
    club_name = get_club_name(db)


    # Get unread notifications
    unread_notifications_count = get_unread_notifications_count(db)

    return {
        "main_player_name": MAIN_PLAYER_NAME,
        "club_name": club_name,
        "club_tag": get_club_tag(db),
        "unread_notifications_count": unread_notifications_count,
        "summary": {
            "total_matches": player_summary["matches_together"],
            "winrate": player_summary["winrate"],
            "goals_per_match": player_summary["goals_per_match"],
            "assists_per_match": player_summary["assists_per_match"],
            "saves_per_match": player_summary["saves_per_match"],
            "shots_per_match": player_summary["shots_per_match"],
            "score_per_match": player_summary["score_per_match"],
            "performance_rating": player_summary["performance_rating"],
        },
        "history": player_data["history"],
        "charts": {
            "rating": player_data["charts"]["rating"],
            "score": player_data["charts"]["score"],
            "score_by_playlist": player_data["charts"]["score_by_playlist"],
            "goals": player_data["charts"]["goals"],
            "assists": player_data["charts"]["assists"],
            "saves": player_data["charts"]["saves"],
            "shots": player_data["charts"]["shots"],
            "matches_by_playlist": player_data["charts"]["matches_by_playlist"],
            "avg_score_by_playlist": player_data["charts"]["avg_score_by_playlist"],
            "radar": player_data["charts"]["radar"],
            "pie": player_data["charts"]["pie"],
        },
        "club_names": club_data["club_names"],
        "club_history": club_data["club_history"],
        "club_charts": club_data["club_charts"],
        "all_club_members": all_club_members,
        "seasons": seasons,
    }


def get_mate_detail_data(db: Session, mate_name: str) -> dict[str, Any] | None:
    unread_notifications_count = get_unread_notifications_count(db)
    if mate_name != MAIN_PLAYER_NAME:
        member = (
            db.query(ClubMember)
            .filter(
                ClubMember.display_name == mate_name,
                ClubMember.is_active.is_(True),
            )
            .first()
        )
        if not member:
            return None

    rows = get_player_rows(db, mate_name)
    
    # Split rows into functional categories using private_service
    private_rows = ps.filter_private_rows(rows)
    
    # Ranked: Only Ranked/Competitive playlists
    ranked_rows = ps.filter_ranked_rows(rows)
    
    # Global: Everything EXCEPT Casual (Includes Ranked + Private + Tournament + etc)
    global_rows = ps.filter_non_casual_rows(rows)
    
    # Recent: Latest 20 RANKED matches (as requested)
    recent_rows = ranked_rows[-20:]
    
    # Tournament: Only tournament playlists
    tournament_rows = ps.filter_tournament_rows(rows)
    
    member_map = get_active_club_member_map(db)

    # Calculate Summaries and Indicators
    summary_recent = build_player_summary(recent_rows)
    extra_recent = build_player_history_and_charts(recent_rows, member_map)
    indicators_recent = build_progress_indicators(summary_recent)

    summary_global = build_player_summary(global_rows)
    extra_global = build_player_history_and_charts(global_rows, member_map)
    indicators_global = build_progress_indicators(summary_global)
    
    summary_ranked = build_player_summary(ranked_rows)
    extra_ranked = build_player_history_and_charts(ranked_rows, member_map)
    indicators_ranked = build_progress_indicators(summary_ranked)
    
    summary_private = build_player_summary(private_rows)
    extra_private = build_player_history_and_charts(private_rows, member_map)
    indicators_private = build_progress_indicators(summary_private)

    summary_tournament = build_player_summary(tournament_rows)
    extra_tournament = build_player_history_and_charts(tournament_rows, member_map)
    indicators_tournament = build_progress_indicators(summary_tournament)

    club_name = get_club_name(db)
    seasons_meta = db.query(Season).order_by(Season.start_date.desc()).all()

    return {
        "mate_name": mate_name,
        "is_main_player": (mate_name == MAIN_PLAYER_NAME),
        "club_name": club_name,
        "club_tag": get_club_tag(db),
        "summary": summary_recent,
        "summary_global": summary_global,
        "summary_ranked": summary_ranked,
        "summary_private": summary_private,
        "summary_tournament": summary_tournament,
        "history": extra_recent["history"],
        "history_global": extra_global["history"],
        "history_ranked": extra_ranked["history"],
        "history_private": extra_private["history"],
        "history_tournament": extra_tournament["history"],
        "charts": extra_recent["charts"],
        "charts_global": extra_global["charts"],
        "charts_ranked": extra_ranked["charts"],
        "charts_private": extra_private["charts"],
        "charts_tournament": extra_tournament["charts"],
        "indicators": indicators_recent,
        "indicators_global": indicators_global,
        "indicators_ranked": indicators_ranked,
        "indicators_private": indicators_private,
        "indicators_tournament": indicators_tournament,
        "seasons_stats": get_seasonal_stats_for_rows(global_rows, seasons_meta, member_map),
        "seasons_stats_ranked": get_seasonal_stats_for_rows(ranked_rows, seasons_meta, member_map),
        "seasons_stats_private": get_seasonal_stats_for_rows(private_rows, seasons_meta, member_map),
        "seasons_stats_tournament": get_seasonal_stats_for_rows(tournament_rows, seasons_meta, member_map),
        "unread_notifications_count": get_unread_notifications_count(db),
    }

def get_seasonal_stats_for_rows(rows: list[MatchPlayerStat], seasons_meta: list[Season], member_map: dict[str, str] = None) -> list[dict[str, Any]]:
    # key: season_name -> key: cat_name -> stats + category id
    seasonal_data = defaultdict(lambda: defaultdict(lambda: {
        "matches": 0, "wins": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "score": 0, "mvps": 0, "category": "other"
    }))

    for r in rows:
        season_name = get_season_for_date(r.match.played_at, seasons_meta)
        
        category = "other"
        cat_name = r.match.playlist
        if member_map:
            category, cat_name = get_match_category_and_name(r.match, member_map)
        
        # Calculate if this player was MVP
        all_stats = r.match.player_stats
        winning_team = next((ps.team for ps in all_stats if ps.won), None)
        if winning_team is not None:
            winning_team_stats = [ps for ps in all_stats if ps.team == winning_team]
            if winning_team_stats:
                max_score = max((ps.score for ps in winning_team_stats), default=0)
                is_mvp = (r.team == winning_team and r.score == max_score)
            else:
                is_mvp = False
        else:
            if all_stats:
                max_overall = max((ps.score for ps in all_stats), default=0)
                is_mvp = (r.score == max_overall)
            else:
                is_mvp = False

        s = seasonal_data[season_name][cat_name]
        s["matches"] += 1
        s["category"] = category
        if r.won: s["wins"] += 1
        s["goals"] += r.goals
        s["assists"] += r.assists
        s["saves"] += r.saves
        s["shots"] += r.shots
        s["score"] += r.score
        if is_mvp: s["mvps"] += 1

    formatted_seasons = []
    season_names_in_order = [s.name for s in seasons_meta]
    for s_name in seasonal_data.keys():
        if s_name not in season_names_in_order:
            season_names_in_order.append(s_name)
    
    season_names_in_order.sort(reverse=True)

    for s_name in season_names_in_order:
        if s_name not in seasonal_data: continue
        
        playlists_list = []
        total_s = {"matches": 0, "wins": 0, "goals": 0, "assists": 0, "saves": 0, "shots": 0, "score": 0, "mvps": 0}
        
        for p_name, p_stats in seasonal_data[s_name].items():
            playlists_list.append({
                "playlist": p_name,
                "category": p_stats.get("category", "other"),
                "matches": p_stats["matches"],
                "winrate": safe_div(p_stats["wins"] * 100, p_stats["matches"]),
                "goals_avg": safe_div(p_stats["goals"], p_stats["matches"]),
                "assists_avg": safe_div(p_stats["assists"], p_stats["matches"]),
                "saves_avg": safe_div(p_stats["saves"], p_stats["matches"]),
                "shots_avg": safe_div(p_stats["shots"], p_stats["matches"]),
                "score_avg": safe_div(p_stats["score"], p_stats["matches"]),
                "ratio": safe_div(p_stats["goals"] * 100, p_stats["shots"]),
                "mvps": p_stats["mvps"],
            })
            for k in total_s: total_s[k] += p_stats[k]
        
        playlists_list.sort(key=lambda x: x["matches"], reverse=True)
        
        formatted_seasons.append({
            "name": s_name,
            "playlists": playlists_list,
            "total": {
                "matches": total_s["matches"],
                "winrate": safe_div(total_s["wins"] * 100, total_s["matches"]),
                "goals_avg": safe_div(total_s["goals"], total_s["matches"]),
                "assists_avg": safe_div(total_s["assists"], total_s["matches"]),
                "saves_avg": safe_div(total_s["saves"], total_s["matches"]),
                "shots_avg": safe_div(total_s["shots"], total_s["matches"]),
                "score_avg": safe_div(total_s["score"], total_s["matches"]),
                "ratio": safe_div(total_s["goals"] * 100, total_s["shots"]),
                "mvps": total_s["mvps"],
            }
        })

    return formatted_seasons

def build_progress_indicators(summary: dict[str, float | int]) -> dict[str, dict[str, float | str]]:
    if not summary:
        summary = {}
        
    def safe_float(val: Any) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    winrate = safe_float(summary.get("winrate", 0))
    score_per_match = safe_float(summary.get("score_per_match", 0))
    goals_per_match = safe_float(summary.get("goals_per_match", 0))
    saves_per_match = safe_float(summary.get("saves_per_match", 0))
    shots_per_match = safe_float(summary.get("shots_per_match", 0))
    assists_per_match = safe_float(summary.get("assists_per_match", 0))

    return {
        "winrate": {
            "label": "Taux de Victoire",
            "value": round(winrate, 2),
            "percent": min(round(winrate, 2), 100),
        },
        "score": {
            "label": "Score / match",
            "value": round(score_per_match, 2),
            "percent": min(round((score_per_match / 500) * 100, 2), 100),
        },
        "goals": {
            "label": "Buts / match",
            "value": round(goals_per_match, 2),
            "percent": min(round((goals_per_match / 2) * 100, 2), 100),
        },
        "shots": {
            "label": "Tirs / match",
            "value": round(shots_per_match, 2),
            "percent": min(round((shots_per_match / 4) * 100, 2), 100),
        },
        "assists": {
            "label": "Passes / match",
            "value": round(assists_per_match, 2),
            "percent": min(round((assists_per_match / 1) * 100, 2), 100),
        },
        "saves": {
            "label": "Arrêts / match",
            "value": round(saves_per_match, 2),
            "percent": min(round((saves_per_match / 2.5) * 100, 2), 100),
        },
    }

def get_all_club_members(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(ClubMember)
        .options(joinedload(ClubMember.aliases))
        .order_by(ClubMember.display_name.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "display_name": row.display_name,
            "favorite_car": row.favorite_car,
            "is_active": row.is_active,
            "aliases": [{"id": a.id, "pseudo": a.pseudo} for a in row.aliases],
            "stats": build_player_summary(get_player_rows(db, row.display_name, exclude_casual=True))
        }
        for row in rows
    ]

def get_rankings_data(db: Session, min_matches: int = 5, match_filter: str = "all") -> dict[str, Any]:
    """Calculates rankings for all club members across various stats."""
    
    def format_val(val: Any) -> str:
        if isinstance(val, (int, float)):
            rounded = round(val, 2)
            # Se fosse um número inteiro (ex: 12.0), mostra sem decimais
            if rounded == int(rounded):
                return str(int(rounded))
            return str(rounded)
        return str(val)

    primary_names = get_active_club_member_names(db)
    
    # We always include the main player
    if MAIN_PLAYER_NAME not in primary_names:
        primary_names.append(MAIN_PLAYER_NAME)

    # 2. Composition la plus jouée (excluding private games)
    member_map = get_active_club_member_map(db)
    all_pseudos = set(member_map.keys())
    
    matches_all = (
        db.query(Match)
        .options(joinedload(Match.player_stats).joinedload(MatchPlayerStat.player))
        .order_by(Match.played_at.asc())
        .all()
    )

    composition_counts = defaultdict(int)
    composition_wins = defaultdict(int)
    composition_streaks = defaultdict(lambda: {"current": 0, "max": 0})
    for match in matches_all:
        player_stats = match.player_stats
        if not player_stats: continue
        
        playlist_lower = (match.playlist or "").lower()
        
        playlist_lower = (match.playlist or "").lower()
        
        # Consistent filtering based on match_filter
        if match_filter == "public":
            # Pour la colonne Classé, on ne veut que du classé compétitif pur
            # Pas de casual, pas de privé, pas de tournoi
            if ps.is_casual_match(playlist_lower) or ps.is_private_match(playlist_lower) or ps.is_tournament_match(playlist_lower):
                continue
        elif match_filter == "private":
            # Pour la colonne Privé, on ne veut que du privé
            if not ps.is_private_match(playlist_lower):
                continue

        # Club members by team
        teams_club = defaultdict(list)
        team_won = {}
        for s in player_stats:
            p_pseudo = s.player.display_name
            if p_pseudo in all_pseudos:
                teams_club[s.team].append(member_map[p_pseudo])
            team_won[s.team] = s.won
        
        for team_id, members in teams_club.items():
            if len(members) >= 2: # Only groups of 2 or more
                sorted_m = sorted(members)
                if ("3v3" in playlist_lower or "standard" in playlist_lower) and len(members) == 2:
                    sorted_m.append("Random")
                
                comp_key = " / ".join(sorted_m)
                composition_counts[comp_key] += 1
                if team_won.get(team_id):
                    composition_wins[comp_key] += 1
                    composition_streaks[comp_key]["current"] += 1
                    if composition_streaks[comp_key]["current"] > composition_streaks[comp_key]["max"]:
                        composition_streaks[comp_key]["max"] = composition_streaks[comp_key]["current"]
                else:
                    composition_streaks[comp_key]["current"] = 0

    sorted_compositions = sorted([{"name": k, "count": v} for k, v in composition_counts.items()], key=lambda x: x["count"], reverse=True)
    for c in sorted_compositions:
        c["display_value"] = f"{c['count']} matchs"
    best_composition = sorted_compositions[:3]

    # Calculate winrates for compositions with at least 5 matches
    win_compositions = []
    for k, v in composition_counts.items():
        if v >= 5: # Threshold for stability
            winrate = safe_div(composition_wins[k] * 100, v)
            win_compositions.append({"name": k, "winrate": winrate, "wins": composition_wins[k], "count": v})
            
    sorted_win_compositions = sorted(win_compositions, key=lambda x: x["winrate"], reverse=True)
    for c in sorted_win_compositions:
        c["display_value"] = f"{format_val(c['winrate'])}% win"
    best_win_composition = sorted_win_compositions[:3]

    # Calculate streaks for compositions
    sorted_streak_compositions = sorted([{"name": k, "streak": v["max"]} for k, v in composition_streaks.items()], key=lambda x: x["streak"], reverse=True)
    for c in sorted_streak_compositions:
        c["display_value"] = f"{c['streak']} victoires"
    best_streak_composition = sorted_streak_compositions[:3]

    all_stats = []
    for name in primary_names:
        # On exclut casual pour les classements également
        rows = get_player_rows(db, name, exclude_casual=True)
        
        # Apply match_filter to rows
        if match_filter != "all":
            filtered_rows = []
            for r in rows:
                playlist_lower = (r.match.playlist or "").lower()
                if match_filter == "public":
                    # Uniquement du classé pur (exclut casual, privé, tournoi)
                    if not (ps.is_casual_match(playlist_lower) or ps.is_private_match(playlist_lower) or ps.is_tournament_match(playlist_lower)):
                        filtered_rows.append(r)
                elif match_filter == "private":
                    if ps.is_private_match(playlist_lower):
                        filtered_rows.append(r)
            rows = filtered_rows

        if len(rows) < min_matches:
            continue
            
        summary = build_player_summary(rows)
        # Convert possession "m:ss" to seconds for sorting
        possession_sec = sum(time_to_seconds(r.possession_time) for r in rows) / len(rows)
        
        # Calculate Shooting accuracy ratio (goals/shots)
        total_goals = sum(r.goals for r in rows)
        total_shots = sum(r.shots for r in rows)
        shooting_ratio = safe_div(total_goals * 100, total_shots)

        all_stats.append({
            "name": name,
            "matches": len(rows),
            "winrate": summary["winrate"],
            "goals": summary["goals_per_match"],
            "shots": summary["shots_per_match"],
            "shooting_ratio": shooting_ratio,
            "assists": summary["assists_per_match"],
            "saves": summary["saves_per_match"],
            "demolitions": summary["demolishes_per_match"],
            "possession_sec": possession_sec,
            "possession": summary["possession_per_match"],
            "score": summary["score_per_match"],
            "rating": summary["performance_rating"],
            "mvps": summary["mvps"],
        })

    if not all_stats:
        return {}

    def get_top(stat_key: str, suffix: str = "", reverse: bool = True):
        sorted_list = sorted(all_stats, key=lambda x: x[stat_key], reverse=reverse)
        top_3 = []
        for item in sorted_list[:3]:
            # Criamos uma cópia para evitar modificar o objeto original compartilhado entre rankings
            item_copy = item.copy()
            val = item_copy[stat_key]
            item_copy["display_value"] = f"{format_val(val)}{suffix}"
            top_3.append(item_copy)
        return top_3

    return {
        "best_overall": get_top("rating", "/100"),
        "best_mvp": get_top("mvps", " MVPs"),
        "best_winrate": get_top("winrate", "%"),
        "best_score": get_top("score", " pts"),
        "best_buteur": get_top("goals", " buts"),
        "best_tireur": get_top("shooting_ratio", "%"),
        "best_harceleur": get_top("shots", " tirs"),
        "best_passeur": get_top("assists", " passes"),
        "best_gardien": get_top("saves", " arrêts"),
        "best_demolisseur": get_top("demolitions", " démos"),
        "best_ballchaser": get_top("possession_sec", "s"), # Simplified possession
        "worst_tireur": get_top("shooting_ratio", "%", reverse=False),
        "worst_score": get_top("score", " pts", reverse=False),
        "best_composition": best_composition,
        "best_win_composition": best_win_composition,
        "best_streak_composition": best_streak_composition,
    }


def check_and_update_rankings(db: Session, match_filter: str = "public"):
    """Compare current Hall of Fame with the last snapshot and generate notifications."""
    from app.services.stats_service import get_rankings_data, get_setting, set_setting
    
    current_rankings = get_rankings_data(db, min_matches=5, match_filter=match_filter)
    if not current_rankings:
        return

    # Convert the ranking data to a simple format for comparison: Category -> [Top 1, Top 2, Top 3]
    current_snapshot = {}
    for cat, players in current_rankings.items():
        if isinstance(players, list):
            current_snapshot[cat] = [p["name"] for p in players]

    # Use separate snapshots for Public (Classé) and Private (Privé)
    snapshot_key = f"last_rankings_snapshot_{match_filter}"
    last_snapshot_json = get_setting(db, snapshot_key, "{}")
    
    try:
        last_snapshot = json.loads(last_snapshot_json)
    except:
        last_snapshot = {}

    notifications = []
    
    # Badge based on type
    color_class = "badge-classe" if match_filter == "public" else "badge-prive"
    label = "Classé" if match_filter == "public" else "Privé"
    badge_html = f'<span class="notif-badge-type {color_class}">{label}</span> '

    friendly_category_names = {
        "best_overall": "Maître de l'Arène",
        "best_mvp": "Meilleur Joueur",
        "best_winrate": "Roi de la Win",
        "best_score": "Scoreur Moyen",
        "best_buteur": "Meilleur Buteur",
        "best_tireur": "Meilleur Tireur",
        "best_harceleur": "Harceleur des cages",
        "best_passeur": "Meilleur Passeur",
        "best_gardien": "Meilleur Gardien",
        "best_demolisseur": "Pro de la démolition",
        "best_ballchaser": "Ballchaser Ultime",
        "worst_tireur": "Pied le plus Carré",
        "worst_score": "Plus gros Branleur",
        "best_composition": "Compo la plus jouée",
        "best_win_composition": "Compo la plus efficace",
        "best_streak_composition": "Série Royale",
    }

    category_emojis = {
        "best_overall": "👑",
        "best_mvp": "🌟",
        "best_winrate": "🏆",
        "best_score": "📊",
        "best_buteur": "⚽",
        "best_tireur": "🎯",
        "best_harceleur": "🏹",
        "best_passeur": "👟",
        "best_gardien": "🛡️",
        "best_demolisseur": "💥",
        "best_ballchaser": "🏎️",
        "worst_tireur": "👞",
        "worst_score": "😴",
        "best_composition": "🧩",
        "best_win_composition": "⚡",
        "best_streak_composition": "🔥",
    }

    for cat, new_top_names in current_snapshot.items():
        if not new_top_names: continue
        
        old_top_names = last_snapshot.get(cat, [])
        new_top_1 = new_top_names[0]
        old_top_1 = old_top_names[0] if old_top_names else None

        # On ne notifie que si le Top 1 a changé
        if new_top_1 != old_top_1:
            cat_name = friendly_category_names.get(cat, cat)
            emoji = category_emojis.get(cat, "📢")
            notifications.append(f'<a href="/hof#ranking-{match_filter}-{cat}" class="notif-link">{badge_html}{emoji} **{new_top_1}** s\'empare de la **1ère place** en **{cat_name}** !</a>')

    # Add notifications to DB
    for msg in notifications:
        db.add(Notification(message=msg, type="hall_of_fame"))
    
    # Update snapshot for this filter
    set_setting(db, snapshot_key, json.dumps(current_snapshot))
    db.commit()
