from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlayerStatIn(BaseModel):
    display_name: str = Field(..., min_length=1)
    team: int = 0
    goals: int = 0
    assists: int = 0
    saves: int = 0
    shots: int = 0
    score: int = 0
    won: bool = False


class MatchIngestPayload(BaseModel):
    replay_id: str = Field(..., min_length=1)
    playlist: str = "unknown"
    result: str = "unknown"
    played_at: Optional[datetime] = None
    ballchasing_id: Optional[str] = None
    ballchasing_url: Optional[str] = None
    players: List[PlayerStatIn]


class ClubMemberCreate(BaseModel):
    display_name: str = Field(..., min_length=1)
    is_active: bool = True


class ClubMemberOut(BaseModel):
    id: int
    display_name: str
    is_active: bool

    class Config:
        from_attributes = True