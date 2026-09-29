from fastapi import APIRouter

from app.dependencies import db_dependency, optional_user_dependency
from app.schemas.match import StandingRow
from app.services.standings import calculate_standings
from app.services.visibility import require_tournament_access

router = APIRouter(prefix="/api/standings", tags=["standings"])


@router.get("/{tournament_id}", response_model=list[StandingRow])
def get_standings(tournament_id: int, db: db_dependency, current_user: optional_user_dependency):
    tournament = require_tournament_access(db, tournament_id, current_user)
    return calculate_standings(db, tournament)


@router.get("/", response_model=list[StandingRow])
def get_standings_by_query(tournament_id: int, db: db_dependency, current_user: optional_user_dependency):
    return get_standings(tournament_id, db, current_user)
