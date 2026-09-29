from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

class PlayerBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    jersey_number: int | None = Field(default=None, ge=1, le=99)
    position: Literal["GK", "DEF", "MID", "FWD"] | None = None

class PlayerCreate(PlayerBase):
    team_id: int

class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    jersey_number: int | None = Field(default=None, ge=1, le=99)
    position: Literal["GK", "DEF", "MID", "FWD"] | None = None
    team_id: int | None = None

    @field_validator("name", "team_id")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

class PlayerResponse(PlayerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int


class PlayerStatsResponse(BaseModel):
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    tournament_id: int
    tournament_name: str
    goals: int
    assists: int


class TopScorerResponse(PlayerStatsResponse):
    position: int
