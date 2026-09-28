from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_organizer, get_current_user_optional
from app.models.matches import Match
from app.models.tournament import Tournament
from app.models.users import User
from app.schemas.tournament import (
    TopScorerResponse,
    TournamentCreate,
    TournamentResponse,
    TournamentStatusUpdate,
    TournamentUpdate,
)
from app.services.ownership import require_owned_tournament
from app.services.player_stats import calculate_top_scorers
from app.services.visibility import require_tournament_access

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


@router.get("/", response_model=list[TournamentResponse])
def list_tournaments(db: DbSession):
    return db.query(Tournament).filter(Tournament.status == "published").order_by(
        Tournament.start_date.asc().nullslast(), Tournament.name
    ).all()


@router.get("/manage", response_model=list[TournamentResponse])
def list_managed_tournaments(
    db: DbSession,
    include_archived: bool = Query(False),
    current_user: Annotated[User, Depends(get_current_organizer)] = None,
):
    query = db.query(Tournament).filter(Tournament.created_by_id == current_user.id)
    if not include_archived:
        query = query.filter(Tournament.status != "archived")
    return query.order_by(Tournament.start_date.asc().nullslast(), Tournament.name).all()


@router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament(
    tournament_id: int, db: DbSession,
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    return require_tournament_access(db, tournament_id, current_user)


@router.get("/{tournament_id}/top-scorers", response_model=list[TopScorerResponse])
def get_top_scorers(
    tournament_id: int, db: DbSession,
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    return calculate_top_scorers(db, require_tournament_access(db, tournament_id, current_user))


@router.post("/", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreate, db: DbSession,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = Tournament(**payload.model_dump(), created_by_id=current_user.id)
    db.add(tournament)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tournament slug already exists")
    db.refresh(tournament)
    return tournament


@router.patch("/{tournament_id}", response_model=TournamentResponse)
def update_tournament(
    tournament_id: int, payload: TournamentUpdate, db: DbSession,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = require_owned_tournament(db, tournament_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    scoring_fields = {"win_points", "draw_points", "loss_points"}
    scoring_changed = any(field in values and values[field] != getattr(tournament, field) for field in scoring_fields)
    if scoring_changed and db.query(Match.id).filter(
        Match.tournament_id == tournament_id,
        (Match.status == "completed") | Match.revisions.any(),
    ).first():
        raise HTTPException(status_code=409, detail="Scoring rules cannot change after results are recorded")
    start_date, end_date = values.get("start_date", tournament.start_date), values.get("end_date", tournament.end_date)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    for key, value in values.items():
        setattr(tournament, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tournament slug already exists")
    return tournament


@router.patch("/{tournament_id}/status", response_model=TournamentResponse)
def update_tournament_status(
    tournament_id: int, payload: TournamentStatusUpdate, db: DbSession,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = require_owned_tournament(db, tournament_id, current_user)
    tournament.status = payload.status
    db.commit()
    return tournament
