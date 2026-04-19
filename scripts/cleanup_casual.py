import sys
import os

# Ajout du répertoire parent au path pour importer database et models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Match
import sqlalchemy

def cleanup_casual():
    db = SessionLocal()
    try:
        print("[Cleanup] Recherche des matchs Casual...")
        
        # On cherche tous les matchs dont la playlist contient "Casual"
        casual_matches = db.query(Match).filter(Match.playlist.like("%Casual%")).all()
        count = len(casual_matches)
        
        if count == 0:
            print("[Cleanup] Aucun match Casual trouvé. La base est déjà propre !")
            return

        print(f"[Cleanup] {count} matchs Casual identifiés. Suppression en cours...")
        
        for match in casual_matches:
            db.delete(match)
        
        db.commit()
        print(f"[Cleanup] SUCCESS: {count} matchs (et leurs statistiques) ont été supprimés.")
        
    except Exception as e:
        db.rollback()
        print(f"[Cleanup] ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("Êtes-vous sûr de vouloir supprimer TOUS les matchs Casual ? (y/n): ")
    if confirm.lower() == 'y':
        cleanup_casual()
    else:
        print("[Cleanup] Opération annulée.")
