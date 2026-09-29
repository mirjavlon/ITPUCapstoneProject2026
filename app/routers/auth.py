from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.dependencies import DbSession, get_current_user
from app.models.users import User
from app.schemas.auth import Token, UserCreate, UserResponse
from app.utils.security import create_access_token, verify_password, get_password_hash


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: DbSession):
    """Register a new user."""
    user_exists = db.query(User).filter(
        (User.username == user_in.username) | (User.email == user_in.email)
    ).first()
    
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        user_role=user_in.user_role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """Authenticate a user and issue a signed bearer token.

    The endpoint accepts form fields named `username` and `password`, matching
    FastAPI's OAuth2 password-flow convention.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    access_token = create_access_token(
        user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get the currently logged in user."""
    return current_user
