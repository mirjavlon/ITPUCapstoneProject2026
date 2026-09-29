from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.dependencies import db_dependency, get_current_user, optional_user_dependency
from app.models.match import GoalEvent
from app.models.player import Player
from app.models.team import Team
from app.models.user import User
from app.schemas.player import PlayerCreate, PlayerResponse, PlayerStatsResponse, PlayerUpdate
from app.services.player_stats import get_player_stats
from app.services.visibility import require_tournament_access, visible_tournament_ids
from app.services.ownership import require_owned_team

router = APIRouter(prefix="/api/players", tags=["players"])


def require_team_manager(team: Team, user: User) -> None:
    if user.is_organizer:
        require_owned_team(team, user)
    elif team.manager_id != user.id:
        raise HTTPException(status_code=403, detail="You may only manage players on your assigned teams")


@router.get("/", response_model=list[PlayerResponse])
def list_players(db: db_dependency, current_user: optional_user_dependency, team_id: int | None = Query(None)):
    query = db.query(Player).join(Team).filter(Team.tournament_id.in_(visible_tournament_ids(current_user)))
    if team_id is not None:
        query = query.filter(Player.team_id == team_id)
    return query.order_by(Player.name).all()


@router.post("/", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
def create_player(
    payload: PlayerCreate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_user)],
):
    team = db.get(Team, payload.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    require_team_manager(team, current_user)
    player = Player(**payload.model_dump())
    db.add(player)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Jersey number already belongs to this team")
    db.refresh(player)
    return player


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: db_dependency, current_user: optional_user_dependency):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    require_tournament_access(db, player.team.tournament_id, current_user)
    return player


@router.get("/{player_id}/stats", response_model=PlayerStatsResponse)
def get_stats(player_id: int, db: db_dependency, current_user: optional_user_dependency):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    require_tournament_access(db, player.team.tournament_id, current_user)
    return get_player_stats(db, player)


@router.patch("/{player_id}", response_model=PlayerResponse)
def update_player(
    player_id: int,
    payload: PlayerUpdate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_user)],
):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    require_team_manager(player.team, current_user)
    values = payload.model_dump(exclude_unset=True)
    if "team_id" in values and values["team_id"] != player.team_id:
        target = db.get(Team, values["team_id"])
        if not target:
            raise HTTPException(status_code=404, detail="Target team not found")
        require_team_manager(target, current_user)
        if target.tournament_id != player.team.tournament_id:
            raise HTTPException(status_code=409, detail="Players cannot move between tournaments")
        if db.query(GoalEvent.id).filter(
            or_(GoalEvent.scorer_id == player_id, GoalEvent.assist_player_id == player_id)
        ).first():
            raise HTTPException(status_code=409, detail="Players with recorded goals or assists cannot change teams")
    for key, value in values.items():
        setattr(player, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Jersey number already belongs to this team")
    return player


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(
    player_id: int,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_user)],
):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    require_team_manager(player.team, current_user)
    has_statistics = db.query(GoalEvent.id).filter(
        or_(GoalEvent.scorer_id == player_id, GoalEvent.assist_player_id == player_id)
    ).first()
    if has_statistics:
        raise HTTPException(status_code=409, detail="Players with recorded goals or assists cannot be removed")
    db.delete(player)
    db.commit()
    return None
