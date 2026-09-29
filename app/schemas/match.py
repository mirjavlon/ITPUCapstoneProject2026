from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

class MatchBase(BaseModel):
    tournament_id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime
    venue: str | None = Field(default=None, max_length=150)

class MatchCreate(MatchBase):
    @field_validator("match_date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("match_date must include a timezone offset")
        return value

class MatchUpdate(BaseModel):
    match_date: datetime | None = None
    venue: str | None = Field(default=None, max_length=150)
    status: Literal["scheduled", "postponed", "cancelled"] | None = None

    @field_validator("match_date", "status")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("match_date")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("match_date must include a timezone offset")
        return value

class MatchScoreUpdate(BaseModel):
    home_score: int = Field(ge=0, le=99)
    away_score: int = Field(ge=0, le=99)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None


class MatchResultWithdraw(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value

class MatchResponse(MatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    home_score: int | None = None
    away_score: int | None = None
    status: str
    version: int


class ResultRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    changed_by_id: int | None
    previous_home_score: int | None
    previous_away_score: int | None
    new_home_score: int | None
    new_away_score: int | None
    reason: str | None
    changed_at: datetime


class GoalEventCreate(BaseModel):
    scorer_id: int
    assist_player_id: int | None = None
    minute: int = Field(ge=1, le=120)


class GoalEventResponse(BaseModel):
    id: int
    match_id: int
    team_id: int
    team_name: str
    scorer_id: int
    scorer_name: str
    assist_player_id: int | None
    assist_player_name: str | None
    minute: int
    created_at: datetime


class StandingRow(BaseModel):
    position: int
    team_id: int
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
