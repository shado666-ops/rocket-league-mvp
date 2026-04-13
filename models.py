from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
import enum

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

    # Advanced stats from CSV
    demolishes = Column(Integer, nullable=True)
    pads = Column(Integer, nullable=True)
    boost_usage = Column(Float, nullable=True)

    possession_time = Column(String, nullable=True)

    match = relationship("Match", back_populates="player_stats")
    player = relationship("Player", back_populates="stats")


class ClubMember(Base):
    __tablename__ = "club_members"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, unique=True, nullable=False, index=True)
    favorite_car = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    aliases = relationship("PlayerAlias", back_populates="member", cascade="all, delete-orphan")


class PlayerAlias(Base):
    __tablename__ = "player_aliases"

    id = Column(Integer, primary_key=True, index=True)
    pseudo = Column(String, unique=True, nullable=False, index=True)
    club_member_id = Column(Integer, ForeignKey("club_members.id", ondelete="CASCADE"), nullable=False)

    member = relationship("ClubMember", back_populates="aliases")


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    type = Column(String, nullable=True) # e.g. "hall_of_fame"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_read = Column(Boolean, nullable=False, default=False)

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.MEMBER)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Lien optionnel vers la fiche joueur du club
    linked_member_id = Column(Integer, ForeignKey("club_members.id", ondelete="SET NULL"), nullable=True)
    member = relationship("ClubMember")