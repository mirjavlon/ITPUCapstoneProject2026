from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.matches import Match
from app.models.teams import Team
from app.models.tournament import Tournament
from app.models.users import User, UserRole


def require_owned_tournament(db: Session, tournament_id: int, user: User) -> Tournament:
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if user.user_role != UserRole.ORGANIZER or tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage tournaments you created")
    return tournament


def require_owned_team(team: Team, user: User) -> None:
    if user.user_role != UserRole.ORGANIZER or team.tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage teams in tournaments you created")


def require_owned_match(match: Match, user: User) -> None:
    if user.user_role != UserRole.ORGANIZER or match.tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage matches in tournaments you created")
