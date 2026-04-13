"""
Service for handling logic specific to private Rocket League matches.
"""
from typing import Any

PRIVATE_KEYWORDS = ["private", "privé"]
RANKED_KEYWORDS = ["ranked", "compétition", "classement"]
CASUAL_KEYWORDS = ["casual"]
TOURNAMENT_KEYWORDS = ["tournament", "tournoi"]

def is_private_match(playlist: Any) -> bool:
    """
    Determines if a match is a private game based on its playlist name.
    """
    if playlist is None:
        return False
    playlist_lower = str(playlist).lower()
    return any(keyword in playlist_lower for keyword in PRIVATE_KEYWORDS)

def is_ranked_match(playlist: Any) -> bool:
    """
    Determines if a match is a ranked/competitive game.
    """
    if playlist is None:
        return False
    playlist_lower = str(playlist).lower()
    return any(keyword in playlist_lower for keyword in RANKED_KEYWORDS)

def is_casual_match(playlist: Any) -> bool:
    """
    Determines if a match is a casual game.
    """
    if playlist is None:
        return False
    playlist_lower = str(playlist).lower()
    return any(keyword in playlist_lower for keyword in CASUAL_KEYWORDS)

def is_tournament_match(playlist: Any) -> bool:
    """
    Determines if a match is a tournament game.
    """
    if playlist is None:
        return False
    playlist_lower = str(playlist).lower()
    return any(keyword in playlist_lower for keyword in TOURNAMENT_KEYWORDS)

def filter_private_rows(rows: list[Any]) -> list[Any]:
    """
    Filters a list of match player stats to return only private games.
    Assumes row object has a .match.playlist attribute.
    """
    return [r for r in rows if is_private_match(r.match.playlist)]

def filter_ranked_rows(rows: list[Any]) -> list[Any]:
    """
    Filters a list of match player stats to return only ranked games.
    """
    return [r for r in rows if is_ranked_match(r.match.playlist)]

def filter_non_casual_rows(rows: list[Any]) -> list[Any]:
    """
    Filters a list of match player stats to exclude casual games.
    """
    return [r for r in rows if not is_casual_match(r.match.playlist)]

def filter_tournament_rows(rows: list[Any]) -> list[Any]:
    """
    Filters a list of match player stats to return only tournament games.
    """
    return [r for r in rows if is_tournament_match(r.match.playlist)]
