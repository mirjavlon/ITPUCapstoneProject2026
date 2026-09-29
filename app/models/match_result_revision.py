from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchResultRevision(Base):
    __tablename__ = "match_result_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_home_score: Mapped[int | None] = mapped_column(nullable=True)
    previous_away_score: Mapped[int | None] = mapped_column(nullable=True)
    new_home_score: Mapped[int | None] = mapped_column(nullable=True)
    new_away_score: Mapped[int | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    match = relationship("Match", back_populates="revisions")
