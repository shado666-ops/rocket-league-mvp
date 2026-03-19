from database import SessionLocal
from models import ClubMember, Match, MatchPlayerStat, Player

db = SessionLocal()

print("\n=== CLUB MEMBERS ===")
for member in db.query(ClubMember).all():
    print(member.id, member.display_name, member.is_active)

print("\n=== MATCHES ===")
for match in db.query(Match).order_by(Match.id.asc()).all():
    print(match.id, match.replay_id, match.playlist, match.played_at)

print("\n=== MATCH PLAYER STATS ===")
rows = (
    db.query(MatchPlayerStat, Player, Match)
    .join(Player, MatchPlayerStat.player_id == Player.id)
    .join(Match, MatchPlayerStat.match_id == Match.id)
    .order_by(Match.id.asc(), Player.display_name.asc())
    .all()
)

for stat, player, match in rows:
    print(
        f"match_id={match.id} replay_id={match.replay_id} "
        f"player={player.display_name} goals={stat.goals} "
        f"assists={stat.assists} saves={stat.saves} shots={stat.shots} "
        f"score={stat.score} won={stat.won}"
    )

db.close()