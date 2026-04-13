import os
import json
import subprocess
from typing import Dict, Any

class BoxcarsService:
    """
    Service pour parser les replays Rocket League via Boxcars (rrrocket).
    Inclut un mode simulation si le binaire rrrocket.exe est absent.
    """
    
    # Chemin par défaut pour rrrocket (automatiquement surchargé par l'env RRROCKET_PATH en Docker)
    RRROCKET_EXE = os.getenv("RRROCKET_PATH", "parsers/boxcars/rrrocket")

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
                    raise Exception("Boxcars n'a pas renvoyé un JSON valide.")
            else:
                stderr_text = result.stderr or ""
                print(f"[Boxcars] Erreur rrrocket (code {result.returncode}): {stderr_text}")
                raise Exception(f"Boxcars a échoué avec le code {result.returncode}. Erreur: {stderr_text}")
        except Exception as e:
            print(f"[Boxcars] Exception lors du parsing : {e}")
            raise
