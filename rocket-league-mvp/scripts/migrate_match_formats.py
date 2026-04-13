import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import Match, MatchPlayerStat

def migrate_private_matches():
    db = SessionLocal()
    try:
        # Find all private matches
        private_matches = db.query(Match).filter(
            (Match.playlist.like("%Private%")) | 
            (Match.playlist.like("%Privé%"))
        ).all()
        
        print(f"Found {len(private_matches)} private matches to update.")
        
        updated_count = 0
        for match in private_matches:
            # Count blue and orange players
            blue_size = 0
            orange_size = 0
            for ps in match.player_stats:
                if ps.team == 0:
                    blue_size += 1
                elif ps.team == 1:
                    orange_size += 1
            
            new_format = f"{blue_size}v{orange_size} Private"
            
            if match.playlist != new_format:
                print(f"Updating Match {match.id}: '{match.playlist}' -> '{new_format}'")
                match.playlist = new_format
                updated_count += 1
        
        db.commit()
        print(f"Migration complete: {updated_count} matches updated.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_private_matches()
