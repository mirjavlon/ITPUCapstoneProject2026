import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountType(str, enum.Enum):
    ORGANIZER = "organizer"
    MANAGER = "manager"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type", values_callable=lambda e: [m.value for m in e]),
        default=AccountType.MANAGER,
        server_default=AccountType.MANAGER.value,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    managed_teams = relationship("Team", back_populates="manager", foreign_keys="Team.manager_id")
    created_tournaments = relationship(
        "Tournament", back_populates="created_by", foreign_keys="Tournament.created_by_id"
    )

    @property
    def is_organizer(self) -> bool:
        return self.account_type == AccountType.ORGANIZER
