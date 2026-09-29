from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id <> away_team_id", name="ck_matches_different_teams"),
        CheckConstraint("status IN ('scheduled', 'postponed', 'completed', 'cancelled')", name="ck_matches_status"),
        CheckConstraint("home_score IS NULL OR home_score >= 0", name="ck_matches_home_score"),
        CheckConstraint("away_score IS NULL OR away_score >= 0", name="ck_matches_away_score"),
        CheckConstraint(
            "(status = 'completed' AND home_score IS NOT NULL AND away_score IS NOT NULL) OR "
            "(status <> 'completed' AND home_score IS NULL AND away_score IS NULL)",
            name="ck_matches_score_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    venue: Mapped[str | None] = mapped_column(String(150), nullable=True)
    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled", server_default="scheduled")
    version: Mapped[int] = mapped_column(default=1, server_default="1")

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    revisions = relationship("MatchResultRevision", back_populates="match", cascade="all, delete-orphan")
    goal_events = relationship("GoalEvent", back_populates="match", cascade="all, delete-orphan", order_by="GoalEvent.minute, GoalEvent.id")
