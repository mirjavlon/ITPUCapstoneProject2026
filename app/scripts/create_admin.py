import argparse
import getpass

from sqlalchemy import or_

from app.database import SessionLocal
from app.models.user import AccountType, User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first mini-football administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    arguments = parser.parse_args()
    password = getpass.getpass("Password: ")
    data = UserCreate(
        username=arguments.username,
        email=arguments.email,
        password=password,
        account_type=AccountType.ORGANIZER,
    )

    with SessionLocal() as db:
        existing = db.query(User).filter(or_(User.username == data.username, User.email == data.email)).first()
        if existing:
            raise SystemExit("A user with that username or email already exists")
        db.add(
            User(
                username=data.username,
                email=data.email,
                hashed_password=get_password_hash(data.password),
                account_type=AccountType.ORGANIZER,
                is_active=True,
            )
        )
        db.commit()
    print(f"Administrator '{data.username}' created")


if __name__ == "__main__":
    main()
