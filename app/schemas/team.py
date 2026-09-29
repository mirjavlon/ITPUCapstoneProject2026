from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    logo_url: str | None = Field(default=None, max_length=500)
    contact_info: str | None = Field(default=None, max_length=255)


class TeamCreate(TeamBase):
    tournament_id: int
    manager_id: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    logo_url: str | None = Field(default=None, max_length=500)
    contact_info: str | None = Field(default=None, max_length=255)
    manager_id: int | None = None
    is_active: bool | None = None

    @field_validator("name", "is_active")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class TeamResponse(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    manager_id: int | None
    is_active: bool
