import sys
import os

# Ajout du répertoire parent au path pour importer database et models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Match, MatchPlayerStat, Player
import sqlalchemy

def fix_discrepancy():
    db = SessionLocal()
    try:
        print("[Fix] Analyse de l'écart de matchs...")
        
        # 1. Trouver les matchs sans Shado666
        shado_player = db.query(Player).filter(Player.display_name == "Shado666").first()
        if not shado_player:
            print("[Fix] Erreur: Joueur Shado666 introuvable en base.")
            return

        all_matches = db.query(Match).all()
        to_delete = []

        for m in all_matches:
            # Vérifier si Shado666 est dans ce match
            is_shado_present = db.query(MatchPlayerStat).filter(
                MatchPlayerStat.match_id == m.id,
                MatchPlayerStat.player_id == shado_player.id
            ).first() is not None
            
            # Vérifier si c'est un match Casual résiduel (insensible à la casse)
            is_casual = "casual" in (m.playlist or "").lower()
            
            if not is_shado_present or is_casual:
                reason = "Sans Shado666" if not is_shado_present else f"Casual résiduel ({m.playlist})"
                print(f"[Fix] Match ID {m.id} identifié comme intrus. Raison: {reason}")
                to_delete.append(m)

        if not to_delete:
            print("[Fix] Aucun match intrus trouvé. L'écart vient peut-être d'ailleurs.")
            return

        print(f"\n[Fix] {len(to_delete)} matchs identifiés pour suppression.")
        confirm = input("Voulez-vous supprimer ces matchs pour harmoniser les compteurs ? (y/n): ")
        
        if confirm.lower() == 'y':
            for m in to_delete:
                db.delete(m)
            db.commit()
            print(f"[Fix] SUCCESS: {len(to_delete)} matchs supprimés. Votre compteur devrait maintenant être à {len(all_matches) - len(to_delete)}.")
        else:
            print("[Fix] Opération annulée.")
            
    except Exception as e:
        db.rollback()
        print(f"[Fix] ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_discrepancy()
