import os
import requests
from typing import Optional, Dict, Any

BALLCHASING_API_KEY = os.getenv("BALLCHASING_API_KEY")
BALLCHASING_API_URL = "https://ballchasing.com/api"

class BallchasingService:
    @staticmethod
    def upload_replay(file_path: str, visibility: str = "public") -> Optional[Dict[str, Any]]:
        """
        Uploads a replay file to ballchasing.com.
        """
        if not BALLCHASING_API_KEY:
            print("Ballchasing API Key not found in environment variables.")
            return None

        headers = {"Authorization": BALLCHASING_API_KEY}
        params = {"visibility": visibility}
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{BALLCHASING_API_URL}/upload",
                    headers=headers,
                    params=params,
                    files=files
                )
            
            if response.status_code == 201:
                return response.json()
            elif response.status_code == 409:
                # Replay already exists
                return response.json()
            else:
                print(f"Error uploading to Ballchasing: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during Ballchasing upload: {e}")
            return None

    @staticmethod
    def get_replay_data(ballchasing_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed replay data (including advanced stats) from ballchasing.com.
        """
        if not BALLCHASING_API_KEY:
            return None

        headers = {"Authorization": BALLCHASING_API_KEY}
        
        try:
            response = requests.get(
                f"{BALLCHASING_API_URL}/replays/{ballchasing_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching from Ballchasing: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during Ballchasing fetch: {e}")
            return None
    @staticmethod
    def extract_player_stats(replay_data: Dict[str, Any], player_name: str) -> Optional[Dict[str, Any]]:
        """
        Extracts specific advanced stats for a player from the full replay data.
        """
        teams = ["blue", "orange"]
        for team_color in teams:
            team = replay_data.get(team_color, {})
            players = team.get("players", [])
            for p in players:
                # Ballchasing names can have different casing or sometimes platform suffixes
                # Using a loose match if needed, but display_name should match.
                if p.get("name").lower() == player_name.lower():
                    stats = p.get("stats", {})
                    
                    # Flatten the nested stats from Ballchasing
                    boost = stats.get("boost", {})
                    pos = stats.get("positioning", {})
                    mvmt = stats.get("movement", {})
                    
                    return {
                        "boost_collected": boost.get("amount_collected"),
                        "boost_stolen": boost.get("amount_stolen_big") + boost.get("amount_stolen_small") if "amount_stolen_big" in boost else None,
                        "time_zero_boost": boost.get("time_zero_boost"),
                        "time_full_boost": boost.get("time_full_boost"),
                        "time_defensive_third": pos.get("time_defensive_third"),
                        "time_neutral_third": pos.get("time_neutral_third"),
                        "time_offensive_third": pos.get("time_offensive_third"),
                        "avg_speed": mvmt.get("avg_speed"),
                        "time_supersonic": mvmt.get("time_supersonic_speed")
                    }
        return None
