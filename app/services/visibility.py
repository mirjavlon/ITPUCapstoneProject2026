from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User


def visible_tournament_ids(user: User | None):
    query = select(Tournament.id)
    published = Tournament.status == "published"
    if user and user.is_organizer:
        return query.where(or_(published, Tournament.created_by_id == user.id))
    if user:
        assigned = select(Team.tournament_id).where(Team.manager_id == user.id)
        return query.where(or_(published, Tournament.id.in_(assigned)))
    return query.where(published)


def can_view_tournament(db: Session, tournament_id: int, user: User | None) -> bool:
    return db.query(Tournament.id).filter(
        Tournament.id == tournament_id,
        Tournament.id.in_(visible_tournament_ids(user)),
    ).first() is not None


def require_tournament_access(db: Session, tournament_id: int, user: User | None) -> Tournament:
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id,
        Tournament.id.in_(visible_tournament_ids(user)),
    ).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament
