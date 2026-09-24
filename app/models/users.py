from sqlalchemy import Boolean, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    ORGANIZER = "organizer"
    MANAGER = "manager"

class User(Base):
    """The account record used by the login endpoint.

    Passwords are stored as bcrypt hashes; the plaintext password is never
    persisted.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    user_role: Mapped[str] = mapped_column(Enum(UserRole), name = "user_role")
