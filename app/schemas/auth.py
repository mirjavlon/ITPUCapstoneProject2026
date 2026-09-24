from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    user_role: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    user_role: str
    is_active: bool

    class Config:
        from_attributes = True
        orm_mode = True

