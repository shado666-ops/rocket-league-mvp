from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from models import ClubMember, Match, MatchPlayerStat, Player

MAIN_PLAYER_NAME = "Shado666"


def safe_div(a: float, b: float) -> float:
    return round(a / b, 2) if b else 0.0


def calculate_performance_rating(winrate: float, score_per_match: float, goals_per_match: float, saves_per_match: float) -> int:
    norm_score = min((score_per_match / 500.0) * 100, 100.0)
    norm_goals = min((goals_per_match / 3.0) * 100, 100.0)
    norm_saves = min((saves_per_match / 3.0) * 100, 100.0)
    
    rating = (winrate * 0.35) + (norm_score * 0.30) + (norm_goals * 0.20) + (norm_saves * 0.15)
    return int(round(rating))


def get_active_club_member_names(db: Session) -> list[str]:
    rows = (
        db.query(ClubMember.display_name)
        .filter(ClubMember.is_active.is_(True))
        .order_by(ClubMember.display_name.asc())
        .all()
    )
    return [row[0] for row in rows]


def get_player_rows(db: Session, player_name: str) -> list[MatchPlayerStat]:
    return (
        db.query(MatchPlayerStat)
        .join(Player, MatchPlayerStat.player_id == Player.id)
        .join(Match, MatchPlayerStat.match_id == Match.id)
        .options(joinedload(MatchPlayerStat.player), joinedload(MatchPlayerStat.match))
        .filter(Player.display_name == player_name)
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
    
    performance_rating = calculate_performance_rating(
        winrate=winrate,
        score_per_match=score_per_match,
        goals_per_match=goals_per_match,
        saves_per_match=saves_per_match
    )

    return {
        "matches_together": matches_count,
        "winrate": winrate,
        "goals_per_match": goals_per_match,
        "assists_per_match": assists_per_match,
        "saves_per_match": saves_per_match,
        "shots_per_match": shots_per_match,
        "score_per_match": score_per_match,
        "performance_rating": performance_rating,
    }


def build_player_history_and_charts(rows: list[MatchPlayerStat]) -> dict[str, Any]:
    history = []
    rating_chart = []
    score_chart = []
    goals_chart = []
    assists_chart = []
    saves_chart = []
    shots_chart = []
    goals_saves_chart = []
    score_by_playlist: dict[str, list[dict[str, Any]]] = defaultdict(list)

    playlist_counter: dict[str, int] = defaultdict(int)
    playlist_scores: dict[str, list[int]] = defaultdict(list)

    wins = 0

    for row in rows:
        if row.won:
            wins += 1

        match_rating = calculate_performance_rating(
            winrate=100.0 if row.won else 0.0,
            score_per_match=float(row.score),
            goals_per_match=float(row.goals),
            saves_per_match=float(row.saves)
        )

        history.append(
            {
                "match_id": row.match.id,
                "date": row.match.played_at.strftime("%d/%m/%Y %H:%M"),
                "playlist": row.match.playlist,
                "result": "Victoire" if row.won else "Défaite",
                "goals": row.goals,
                "assists": row.assists,
                "saves": row.saves,
                "shots": row.shots,
                "score": row.score,
                "rating": match_rating,
                "ballchasing_url": row.match.ballchasing_url,
                "boost_collected": row.boost_collected,
                "boost_stolen": row.boost_stolen,
                "time_zero_boost": row.time_zero_boost,
                "time_full_boost": row.time_full_boost,
                "time_defensive_third": row.time_defensive_third,
                "time_neutral_third": row.time_neutral_third,
                "time_offensive_third": row.time_offensive_third,
                "avg_speed": row.avg_speed,
                "time_supersonic": row.time_supersonic,
            }
        )

        label = row.match.played_at.strftime("%d/%m %H:%M")
        rating_chart.append({"label": label, "value": match_rating})
        score_chart.append({"label": label, "value": row.score})
        goals_chart.append({"label": label, "value": row.goals})
        assists_chart.append({"label": label, "value": row.assists})
        saves_chart.append({"label": label, "value": row.saves})
        shots_chart.append({"label": label, "value": row.shots})
        goals_saves_chart.append(
            {
                "label": label,
                "goals": row.goals,
                "saves": row.saves,
            }
        )

        playlist_counter[row.match.playlist] += 1
        playlist_scores[row.match.playlist].append(row.score)
        score_by_playlist[row.match.playlist].append({"label": label, "value": row.score})

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
            "goals": goals_chart,
            "assists": assists_chart,
            "saves": saves_chart,
            "shots": shots_chart,
            "goals_saves": goals_saves_chart,
            "matches_by_playlist": matches_by_playlist,
            "avg_score_by_playlist": avg_score_by_playlist,
            "radar": [
                safe_div(sum(r.goals for r in rows), matches_count),
                safe_div(sum(r.assists for r in rows), matches_count),
                safe_div(sum(r.saves for r in rows), matches_count),
                safe_div(sum(r.shots for r in rows), matches_count),
                safe_div(sum(r.score for r in rows), matches_count),
            ],
            "pie": [wins, matches_count - wins],
        },
    }


def get_club_overview_data(db: Session) -> dict[str, Any]:
    club_names = get_active_club_member_names(db)

    club_stats = (
        db.query(MatchPlayerStat)
        .join(Player, MatchPlayerStat.player_id == Player.id)
        .join(Match, MatchPlayerStat.match_id == Match.id)
        .options(joinedload(MatchPlayerStat.player), joinedload(MatchPlayerStat.match))
        .filter(Player.display_name.in_(club_names))
        .order_by(Match.played_at.desc(), Match.id.desc())
        .all()
    )

    club_rows_by_match: dict[int, list[MatchPlayerStat]] = defaultdict(list)
    for stat in club_stats:
        club_rows_by_match[stat.match_id].append(stat)

    mates_frequency = []
    winrate_with_mates = []

    print(f"DEBUG: club_names={club_names}, MAIN_PLAYER={MAIN_PLAYER_NAME}", flush=True)
    for mate_name in club_names:
        # Exclusion TRÈS robuste du joueur principal
        if mate_name.strip().lower() == MAIN_PLAYER_NAME.strip().lower() or \
           mate_name.strip().lower() == "shado666": # Fallback hardcoded
            print(f"DEBUG: Skipping {mate_name} (main player - confirmed)", flush=True)
            continue
            
        print(f"DEBUG: Analyzing mate: '{mate_name}'", flush=True)
        mate_rows = [s for s in club_stats if s.player.display_name == mate_name]
        if not mate_rows:
            continue

        played = len(mate_rows)
        wins = sum(1 for s in mate_rows if s.won)

        mates_frequency.append({"name": mate_name, "matches": played})
        winrate_with_mates.append({"name": mate_name, "winrate": safe_div(wins * 100, played)})

    mates_frequency.sort(key=lambda x: x["matches"], reverse=True)
    winrate_with_mates.sort(key=lambda x: x["winrate"], reverse=True)

    club_history = []
    sorted_matches = (
        db.query(Match)
        .order_by(Match.played_at.asc(), Match.id.asc())
        .all()
    )

    for match in sorted_matches:
        rows = club_rows_by_match.get(match.id, [])
        if not rows:
            continue

        club_history.append(
            {
                "match_id": match.id,
                "date": match.played_at.strftime("%d/%m/%Y %H:%M"),
                "playlist": match.playlist,
                "players": ", ".join(sorted({r.player.display_name for r in rows})),
                "result": "Victoire" if any(r.won for r in rows) else "Défaite",
                "score": sum(r.score for r in rows),
                "goals": sum(r.goals for r in rows),
                "assists": sum(r.assists for r in rows),
                "saves": sum(r.saves for r in rows),
                "shots": sum(r.shots for r in rows),
                "ballchasing_url": match.ballchasing_url,
                "boost_collected": sum(r.boost_collected for r in rows if r.boost_collected is not None),
                "boost_stolen": sum(r.boost_stolen for r in rows if r.boost_stolen is not None),
                "avg_speed": sum(r.avg_speed for r in rows if r.avg_speed is not None) / len([r for r in rows if r.avg_speed is not None]) if any(r.avg_speed is not None for r in rows) else None,
            }
        )

    return {
        "club_names": club_names,
        "club_history": list(reversed(club_history)),
        "club_charts": {
            "mates_frequency": mates_frequency[:10],
            "winrate_with_mates": winrate_with_mates[:10],
        },
    }


def get_dashboard_data(db: Session) -> dict[str, Any]:
    player_rows = get_player_rows(db, MAIN_PLAYER_NAME)
    player_summary = build_player_summary(player_rows)
    player_data = build_player_history_and_charts(player_rows)
    club_data = get_club_overview_data(db)
    all_club_members = get_all_club_members(db)

    total_matches_in_db = db.query(func.count(Match.id)).scalar() or 0

    return {
        "main_player_name": MAIN_PLAYER_NAME,
        "summary": {
            "total_matches": player_summary["matches_together"],
            "winrate": player_summary["winrate"],
            "goals_per_match": player_summary["goals_per_match"],
            "assists_per_match": player_summary["assists_per_match"],
            "saves_per_match": player_summary["saves_per_match"],
            "shots_per_match": player_summary["shots_per_match"],
            "score_per_match": player_summary["score_per_match"],
            "performance_rating": player_summary["performance_rating"],
            "db_total_matches": total_matches_in_db,
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
    }


def get_mate_detail_data(db: Session, mate_name: str) -> dict[str, Any] | None:
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
    summary = build_player_summary(rows)
    extra = build_player_history_and_charts(rows)
    indicators = build_progress_indicators(summary)

    return {
        "mate_name": mate_name,
        "is_main_player": mate_name == MAIN_PLAYER_NAME,
        "summary": summary,
        "history": extra["history"],
        "charts": extra["charts"],
        "indicators": indicators,
    }

def build_progress_indicators(summary: dict[str, float | int]) -> dict[str, dict[str, float | str]]:
    winrate = float(summary.get("winrate", 0))
    score_per_match = float(summary.get("score_per_match", 0))
    goals_per_match = float(summary.get("goals_per_match", 0))
    saves_per_match = float(summary.get("saves_per_match", 0))
    shots_per_match = float(summary.get("shots_per_match", 0))

    return {
        "winrate": {
            "label": "Winrate",
            "value": round(winrate, 2),
            "percent": min(round(winrate, 2), 100),
        },
        "score": {
            "label": "Score / match",
            "value": round(score_per_match, 2),
            "percent": min(round((score_per_match / 1000) * 100, 2), 100),
        },
        "goals": {
            "label": "Goals / match",
            "value": round(goals_per_match, 2),
            "percent": min(round((goals_per_match / 5) * 100, 2), 100),
        },
        "saves": {
            "label": "Saves / match",
            "value": round(saves_per_match, 2),
            "percent": min(round((saves_per_match / 5) * 100, 2), 100),
        },
        "shots": {
            "label": "Shots / match",
            "value": round(shots_per_match, 2),
            "percent": min(round((shots_per_match / 8) * 100, 2), 100),
        },
    }

def get_all_club_members(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(ClubMember)
        .order_by(ClubMember.display_name.asc())
        .all()
    )
    return [
        {
            "display_name": row.display_name,
            "is_active": row.is_active,
        }
        for row in rows
    ]