from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("team_id", "jersey_number", name="uq_player_jersey_per_team"),
        CheckConstraint("jersey_number IS NULL OR jersey_number BETWEEN 1 AND 99", name="ck_players_jersey"),
        CheckConstraint("position IS NULL OR position IN ('GK', 'DEF', 'MID', 'FWD')", name="ck_players_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    jersey_number: Mapped[int | None] = mapped_column(nullable=True)
    position: Mapped[str | None] = mapped_column(String(3), nullable=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)

    team = relationship("Team", back_populates="players")
    scored_goal_events = relationship(
        "GoalEvent", foreign_keys="GoalEvent.scorer_id", back_populates="scorer"
    )
    assisted_goal_events = relationship(
        "GoalEvent", foreign_keys="GoalEvent.assist_player_id", back_populates="assist_player"
    )
