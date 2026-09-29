from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.teams import Team
from app.models.tournament import Tournament
from app.models.users import User, UserRole


def visible_tournament_ids(user: User | None):
    query = select(Tournament.id)
    published = Tournament.status == "published"
    if user and user.user_role == UserRole.ORGANIZER:
        return query.where(or_(published, Tournament.created_by_id == user.id))
    if user:
        assigned = select(Team.tournament_id).where(Team.manager_id == user.id)
        return query.where(or_(published, Tournament.id.in_(assigned)))
    return query.where(published)


def require_tournament_access(db: Session, tournament_id: int, user: User | None) -> Tournament:
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id,
        Tournament.id.in_(visible_tournament_ids(user)),
    ).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament
