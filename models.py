from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, unique=True, nullable=False, index=True)

    stats = relationship("MatchPlayerStat", back_populates="player", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    replay_id = Column(String, unique=True, nullable=False, index=True)
    playlist = Column(String, nullable=False, default="unknown")
    result = Column(String, nullable=False, default="unknown")  # win / loss / unknown
    played_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    ballchasing_id = Column(String, nullable=True)
    ballchasing_url = Column(String, nullable=True)

    player_stats = relationship("MatchPlayerStat", back_populates="match", cascade="all, delete-orphan")


class MatchPlayerStat(Base):
    __tablename__ = "match_player_stats"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_match_player"),
    )

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)

    team = Column(Integer, nullable=False, default=0)
    goals = Column(Integer, nullable=False, default=0)
    assists = Column(Integer, nullable=False, default=0)
    saves = Column(Integer, nullable=False, default=0)
    shots = Column(Integer, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=0)
    won = Column(Boolean, nullable=False, default=False)
    
    # Advanced stats from Ballchasing
    boost_collected = Column(Integer, nullable=True)
    boost_stolen = Column(Integer, nullable=True)
    time_zero_boost = Column(Integer, nullable=True)  # in seconds or milliseconds depending on API
    time_full_boost = Column(Integer, nullable=True)
    time_defensive_third = Column(Integer, nullable=True)
    time_neutral_third = Column(Integer, nullable=True)
    time_offensive_third = Column(Integer, nullable=True)
    avg_speed = Column(Integer, nullable=True)
    time_supersonic = Column(Integer, nullable=True)

    match = relationship("Match", back_populates="player_stats")
    player = relationship("Player", back_populates="stats")


class ClubMember(Base):
    __tablename__ = "club_members"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)