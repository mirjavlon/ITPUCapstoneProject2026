from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_user, get_current_user_optional
from app.models.matches import Match
from app.models.teams import Team
from app.models.tournament import Tournament
from app.models.users import User, UserRole
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services.ownership import require_owned_team, require_owned_tournament
from app.services.visibility import require_tournament_access, visible_tournament_ids

router = APIRouter(prefix="/api/teams", tags=["teams"])


def require_team_manager(team: Team, user: User) -> None:
    if user.user_role == UserRole.ORGANIZER:
        require_owned_team(team, user)
    elif team.manager_id != user.id:
        raise HTTPException(status_code=403, detail="You may only manage your assigned teams")


def serialize_team(team: Team, user: User | None) -> TeamResponse:
    response = TeamResponse.model_validate(team)
    is_owner = user and user.user_role == UserRole.ORGANIZER and team.tournament.created_by_id == user.id
    is_manager = user and user.user_role == UserRole.MANAGER and team.manager_id == user.id
    if not (is_owner or is_manager):
        response.contact_info = None
    return response


@router.get("/", response_model=list[TeamResponse])
def list_teams(
    db: DbSession,
    tournament_id: int | None = Query(None),
    include_inactive: bool = Query(False),
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    query = db.query(Team).filter(Team.tournament_id.in_(visible_tournament_ids(current_user)))
    if tournament_id is not None:
        query = query.filter(Team.tournament_id == tournament_id)
    if not include_inactive:
        query = query.filter(Team.is_active.is_(True))
    return [serialize_team(team, current_user) for team in query.order_by(Team.name).all()]


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]):
    tournament = db.get(Tournament, payload.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    values = payload.model_dump()
    if current_user.user_role == UserRole.ORGANIZER:
        require_owned_tournament(db, tournament.id, current_user)
        if payload.manager_id is not None:
            manager = db.get(User, payload.manager_id)
            if not manager or not manager.is_active or manager.user_role != UserRole.MANAGER:
                raise HTTPException(status_code=404, detail="Active manager not found")
    else:
        require_tournament_access(db, tournament.id, current_user)
        if tournament.status == "archived":
            raise HTTPException(status_code=409, detail="Archived tournaments do not accept teams")
        values["manager_id"] = current_user.id
    team = Team(**values)
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Team name already exists in this tournament")
    db.refresh(team)
    return serialize_team(team, current_user)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: int, db: DbSession, current_user: Annotated[User | None, Depends(get_current_user_optional)] = None):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    require_tournament_access(db, team.tournament_id, current_user)
    return serialize_team(team, current_user)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(team_id: int, payload: TeamUpdate, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    require_team_manager(team, current_user)
    values = payload.model_dump(exclude_unset=True)
    if current_user.user_role == UserRole.MANAGER:
        values.pop("manager_id", None)
        values.pop("is_active", None)
    elif "manager_id" in values and values["manager_id"] is not None:
        manager = db.get(User, values["manager_id"])
        if not manager or not manager.is_active or manager.user_role != UserRole.MANAGER:
            raise HTTPException(status_code=404, detail="Active manager not found")
    for key, value in values.items():
        setattr(team, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Team name already exists in this tournament")
    return serialize_team(team, current_user)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: int, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    require_team_manager(team, current_user)
    has_matches = db.query(Match.id).filter(or_(Match.home_team_id == team_id, Match.away_team_id == team_id)).first()
    if has_matches:
        team.is_active = False
        db.commit()
        return None
    db.delete(team)
    db.commit()
    return None
