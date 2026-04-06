import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.stats_service import get_club_archives_data
from database import SessionLocal
import json

def verify():
    db = SessionLocal()
    try:
        data = get_club_archives_data(db)
        tourneys = next((f for f in data if f['fid'] == 'tournaments'), None)
        if not tourneys:
            print("Erreur : catégorie 'tournaments' non trouvée.")
            return
            
        print(f"Nombre de sessions de tournoi : {len(tourneys['sessions'])}")
        for i, session in enumerate(tourneys['sessions']):
            print(f"\n--- SESSION {i+1} : {session['date']} ---")
            print(f"Composition : {session['composition']}")
            print(f"Classement : {session['placement']}")
            print(f"Matchs : {session['total_matches']}")
            for ri, rd in enumerate(session['rounds']):
                print(f"  Round {ri+1} vs {rd['opponent']} : {len(rd['games'])} match(s)")
                for gi, g in enumerate(rd['games']):
                    res = 'Gagné' if g['won'] else 'Perdu'
                    print(f"    Match {gi+1} ({g['date_str']}) : {res} ({g['score_club']}-{g['score_opp']})")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
