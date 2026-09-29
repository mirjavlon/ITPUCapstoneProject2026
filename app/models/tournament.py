from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_tournaments_status"),
        CheckConstraint("win_points >= 0 AND draw_points >= 0 AND loss_points >= 0", name="ck_tournaments_points"),
        CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_tournaments_dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    # ``unique=True`` already provides the lookup index in PostgreSQL.
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    win_points: Mapped[int] = mapped_column(default=3, server_default="3")
    draw_points: Mapped[int] = mapped_column(default=1, server_default="1")
    loss_points: Mapped[int] = mapped_column(default=0, server_default="0")

    teams = relationship("Team", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")
    created_by = relationship("User", back_populates="created_tournaments", foreign_keys=[created_by_id])
