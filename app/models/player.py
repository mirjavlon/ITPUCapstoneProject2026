from sqlalchemy import true
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, ForeignKey

from app.database import Base

class Player(Base):
    __tablename__ = "players"
    

    id: Mapped[int] = mapped_column(primary_key=true)
    name: Mapped[str] = mapped_column(String(50))
    jersey_number: Mapped[int] = mapped_column()
    position: Mapped[str] = mapped_column(String(3))
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    