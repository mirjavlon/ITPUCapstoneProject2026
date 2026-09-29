from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User


def require_owned_tournament(db: Session, tournament_id: int, user: User) -> Tournament:
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if not user.is_organizer or tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage tournaments you created")
    return tournament


def require_owned_team(team: Team, user: User) -> None:
    if not user.is_organizer or team.tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage teams in tournaments you created")


def require_owned_match(match: Match, user: User) -> None:
    if not user.is_organizer or match.tournament.created_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage matches in tournaments you created")


def owns_tournament(tournament: Tournament, user: User | None) -> bool:
    return bool(user and user.is_organizer and tournament.created_by_id == user.id)
