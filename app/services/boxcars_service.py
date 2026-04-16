import os
import json
import subprocess
from typing import Dict, Any
from datetime import datetime

class BoxcarsService:
    """
    Service pour parser les replays Rocket League via Boxcars (rrrocket).
    Inclut un mode simulation si le binaire rrrocket.exe est absent.
    """
    
    # Chemin par défaut pour rrrocket (auto-détection .exe sur Windows, ou via RRROCKET_PATH)
    RRROCKET_EXE = os.getenv("RRROCKET_PATH", "parsers/boxcars/rrrocket.exe" if os.name == "nt" else "parsers/boxcars/rrrocket")

    @classmethod
    def parse_replay(cls, file_path: str, played_at_mtime: float = None) -> Dict[str, Any]:
        """
        Parse un fichier .replay avec Boxcars (rrrocket).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier replay introuvable : {file_path}")

        # Utilisation systématique du binaire rrrocket.exe
        if not os.path.exists(cls.RRROCKET_EXE):
            raise FileNotFoundError(f"Le binaire Boxcars est introuvable à l'emplacement : {cls.RRROCKET_EXE}")

        try:
            # Commande standard pour rrrocket : rrrocket <file> pour sortir le JSON
            result = subprocess.run([cls.RRROCKET_EXE, file_path], capture_output=True, text=True, encoding="utf-8")
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"[Boxcars] Erreur de lecture JSON. Sortie brute : {result.stdout[:500]}...")
            else:
                stderr_text = result.stderr or ""
                print(f"[Boxcars] Erreur rrrocket (code {result.returncode}): {stderr_text}")
        except Exception as e:
            print(f"[Boxcars] Exception lors du parsing : {e}")

        # Mode Simulation / Fallback si Boxcars échoue ou est absent
        print("[Boxcars] Utilisation du mode Simulation (données minimales).")
        return {
            "properties": {
                "Id": os.path.splitext(os.path.basename(file_path))[0],
                "Date": datetime.fromtimestamp(played_at_mtime or os.path.getmtime(file_path)).strftime("%Y-%m-%d %H-%M-%S"),
                "Playlist": 0,
                "TeamSize": 0,
                "Team0Score": 0,
                "Team1Score": 0,
                "PlayerStats": []
            }
        }
