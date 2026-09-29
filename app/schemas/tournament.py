from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TournamentBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    start_date: date | None = None
    end_date: date | None = None
    win_points: int = Field(default=3, ge=0, le=10)
    draw_points: int = Field(default=1, ge=0, le=10)
    loss_points: int = Field(default=0, ge=0, le=10)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    start_date: date | None = None
    end_date: date | None = None
    win_points: int | None = Field(default=None, ge=0, le=10)
    draw_points: int | None = Field(default=None, ge=0, le=10)
    loss_points: int | None = Field(default=None, ge=0, le=10)

    @field_validator("name", "slug", "win_points", "draw_points", "loss_points")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class TournamentStatusUpdate(BaseModel):
    status: Literal["draft", "published", "archived"]


class TournamentResponse(TournamentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
