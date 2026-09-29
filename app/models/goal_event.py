from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GoalEvent(Base):
    __tablename__ = "match_goal_events"
    __table_args__ = (
        CheckConstraint("minute BETWEEN 1 AND 120", name="ck_match_goal_events_minute"),
        CheckConstraint("assist_player_id IS NULL OR assist_player_id <> scorer_id", name="ck_match_goal_events_different_players"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    scorer_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"), index=True)
    assist_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"), nullable=True, index=True)
    minute: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    match = relationship("Match", back_populates="goal_events")
    team = relationship("Team", back_populates="goal_events")
    scorer = relationship("Player", foreign_keys=[scorer_id], back_populates="scored_goal_events")
    assist_player = relationship("Player", foreign_keys=[assist_player_id], back_populates="assisted_goal_events")
