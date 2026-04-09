import os
import sys

# Ajouter le chemin du projet au PYTHONPATH
sys.path.append(os.getcwd())

from database import SessionLocal
from app.services.stats_service import get_club_archives_data

db = SessionLocal()
try:
    data = get_club_archives_data(db)
    menu = data.get("archives_menu", [])
    print("--- ARCHIVES MENU ---")
    for item in menu:
        print(f"Formation: {item['name']} | Count: {item['count']} {item.get('count_label', '')} | Matches: {item['total_matches']}")
        if item['fid'] == 'tournaments':
            print(f"  Sessions: {item.get('total_sessions')}")
    
    # Check tournament detail
    detail = get_club_archives_data(db, category_fid="tournaments")
    tourney_groups = detail.get("formation", {}).get("groups", [])
    print("\n--- TOURNAMENTS DETAIL ---")
    print(f"Number of compositions: {len(tourney_groups)}")
    for g in tourney_groups:
        print(f"Comp: {g['composition']} | Sessions: {g['total']['sessions']} | Matches: {g['total']['matches']}")
        for s in g['sessions']:
            print(f"  Session: {s['date']} | Placement: {s['placement']} | Matches: {s['total_matches']}")
finally:
    db.close()
