import re
import unicodedata
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import db_dependency, get_current_organizer, optional_user_dependency
from app.models.match import Match
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.player import TopScorerResponse
from app.schemas.tournament import (
    TournamentCreate,
    TournamentResponse,
    TournamentStatusUpdate,
    TournamentUpdate,
)
from app.services.player_stats import calculate_top_scorers
from app.services.ownership import require_owned_tournament
from app.services.visibility import require_tournament_access

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


def generate_tournament_slug(db: db_dependency, name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    base_slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:110]
    if len(base_slug) < 2:
        raise HTTPException(status_code=422, detail="Tournament name must contain at least two letters or numbers")

    slug = base_slug
    suffix = 2
    while db.query(Tournament.id).filter(Tournament.slug == slug).first():
        slug = f"{base_slug[:120 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return slug


@router.get("/", response_model=list[TournamentResponse])
def list_tournaments(db: db_dependency):
    return db.query(Tournament).filter(Tournament.status == "published").order_by(
        Tournament.start_date.asc().nullslast(), Tournament.name
    ).all()


@router.get("/manage", response_model=list[TournamentResponse])
def list_all_tournaments(
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
    include_archived: bool = Query(False),
):
    query = db.query(Tournament).filter(Tournament.created_by_id == current_user.id)
    if not include_archived:
        query = query.filter(Tournament.status != "archived")
    return query.order_by(Tournament.start_date.asc().nullslast(), Tournament.name).all()


@router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament(tournament_id: int, db: db_dependency, current_user: optional_user_dependency):
    return require_tournament_access(db, tournament_id, current_user)


@router.get("/{tournament_id}/top-scorers", response_model=list[TopScorerResponse])
def get_top_scorers(tournament_id: int, db: db_dependency, current_user: optional_user_dependency):
    tournament = require_tournament_access(db, tournament_id, current_user)
    return calculate_top_scorers(db, tournament)


@router.post("/", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    values = payload.model_dump(exclude={"slug"})
    tournament = Tournament(
        **values,
        slug=generate_tournament_slug(db, payload.name),
        created_by_id=current_user.id,
    )
    db.add(tournament)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not generate a unique public URL. Please try again.")
    db.refresh(tournament)
    return tournament


@router.patch("/{tournament_id}", response_model=TournamentResponse)
def update_tournament(
    tournament_id: int,
    payload: TournamentUpdate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = require_owned_tournament(db, tournament_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    scoring_fields = {"win_points", "draw_points", "loss_points"}
    scoring_changed = any(
        field in values and values[field] != getattr(tournament, field)
        for field in scoring_fields
    )
    if scoring_changed and db.query(Match.id).filter(
        Match.tournament_id == tournament_id,
        (Match.status == "completed") | Match.revisions.any(),
    ).first():
        raise HTTPException(status_code=409, detail="Scoring rules cannot change after results are recorded")
    start_date = values.get("start_date", tournament.start_date)
    end_date = values.get("end_date", tournament.end_date)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    for key, value in values.items():
        setattr(tournament, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tournament details could not be saved")
    return tournament


@router.patch("/{tournament_id}/status", response_model=TournamentResponse)
def update_tournament_status(
    tournament_id: int,
    payload: TournamentStatusUpdate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = require_owned_tournament(db, tournament_id, current_user)
    tournament.status = payload.status
    db.commit()
    return tournament
