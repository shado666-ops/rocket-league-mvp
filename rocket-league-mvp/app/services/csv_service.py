import csv
import os
from datetime import datetime
from typing import Any, Dict, List

class CSVService:
    @staticmethod
    def parse_match_csv(file_path: str) -> Dict[str, Any]:
        """
        Parses a BakkesMod Gamestats CSV file.
        Returns a dictionary compatible with MatchIngestPayload.
        """
        players_stats = []
        team_goals = {0: 0, 1: 0}
        match_timestamp = None
        
        # We can extract team names if present
        team_names = {0: "Team 0", 1: "Team 1"}

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract timestamp from the first row if not already set
                if not match_timestamp and row.get("Timestamp"):
                    try:
                        # Format: 2026-03-24_21-12-18
                        match_timestamp = datetime.strptime(row["Timestamp"], "%Y-%m-%d_%H-%M-%S")
                    except ValueError:
                        pass
                
                team_num = int(row.get("TeamNum", 0))
                goals = int(row.get("Goals", 0))
                team_goals[team_num] += goals
                
                if row.get("TeamName"):
                    team_names[team_num] = row["TeamName"]

                players_stats.append({
                    "display_name": row.get("PlayerName", "Unknown"),
                    "team": team_num,
                    "goals": goals,
                    "assists": int(row.get("Assists", 0)),
                    "saves": int(row.get("Saves", 0)),
                    "shots": int(row.get("Shots", 0)),
                    "score": int(row.get("Score", 0)),
                    "demolishes": int(row.get("Demolishes", 0)),
                    "pads": int(row.get("Pads", 0)),
                    "boost_usage": float(row.get("BoostUsage", 0)),
                    "possession_time": row.get("PossessionTime", "0:00"),
                    # "won" will be filled after determining the winner
                })


        # Determine winner
        winning_team = 0 if team_goals[0] > team_goals[1] else 1
        if team_goals[0] == team_goals[1]:
            winning_team = -1 # Draw (unlikely in RL except private/custom)

        for p in players_stats:
            p["won"] = (p["team"] == winning_team)

        # Generate a unique replay_id for the CSV if none exists
        # We use the filename or the timestamp
        basename = os.path.basename(file_path)
        replay_id = os.path.splitext(basename)[0]

        # Playlist name from filename if possible
        playlist = "BakkesMod CSV"
        
        return {
            "replay_id": replay_id,
            "played_at": match_timestamp or datetime.utcnow(),
            "playlist": playlist,
            "result": f"{team_goals[0]} - {team_goals[1]}",
            "players": players_stats
        }
