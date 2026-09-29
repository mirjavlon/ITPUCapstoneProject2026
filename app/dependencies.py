from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import AccountType, User
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

async def get_optional_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: db_dependency,
) -> User | None:
    token = token or request.cookies.get("access_token")
    user_id = decode_access_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    return user if user and user.is_active else None


optional_user_dependency = Annotated[User | None, Depends(get_optional_user)]


async def get_current_user(current_user: optional_user_dependency):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if current_user is None:
        raise credentials_exception
    return current_user

async def get_current_organizer(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type != AccountType.ORGANIZER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")
    return current_user
