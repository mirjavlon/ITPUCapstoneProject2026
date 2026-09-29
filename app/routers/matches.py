from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_

from app.dependencies import db_dependency, get_current_organizer, optional_user_dependency
from app.models.match import GoalEvent, Match, MatchResultRevision
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.match import (
    MatchCreate,
    GoalEventCreate,
    GoalEventResponse,
    MatchResponse,
    MatchResultWithdraw,
    MatchScoreUpdate,
    MatchUpdate,
    ResultRevisionResponse,
)
from app.services.visibility import require_tournament_access, visible_tournament_ids
from app.services.ownership import require_owned_match, require_owned_tournament

router = APIRouter(prefix="/api/matches", tags=["matches"])


def get_match_or_404(db: db_dependency, match_id: int, *, lock: bool = False) -> Match:
    query = db.query(Match).filter(Match.id == match_id)
    if lock:
        # Web handlers may already have loaded this match before acquiring the lock.
        query = query.populate_existing().with_for_update()
    match = query.first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


def serialize_goal_event(event: GoalEvent) -> dict:
    return {
        "id": event.id,
        "match_id": event.match_id,
        "team_id": event.team_id,
        "team_name": event.team.name,
        "scorer_id": event.scorer_id,
        "scorer_name": event.scorer.name,
        "assist_player_id": event.assist_player_id,
        "assist_player_name": event.assist_player.name if event.assist_player else None,
        "minute": event.minute,
        "created_at": event.created_at,
    }


def validate_teams(db: db_dependency, tournament_id: int, home_team_id: int, away_team_id: int) -> None:
    if home_team_id == away_team_id:
        raise HTTPException(status_code=422, detail="A team cannot play itself")
    teams = db.query(Team).filter(
        Team.id.in_([home_team_id, away_team_id]),
        Team.tournament_id == tournament_id,
        Team.is_active.is_(True),
    ).all()
    if len(teams) != 2:
        raise HTTPException(status_code=422, detail="Both teams must be active in this tournament")


def validate_schedule_conflict(
    db: db_dependency,
    match_date,
    home_team_id: int,
    away_team_id: int,
    venue: str | None,
    exclude_match_id: int | None = None,
) -> None:
    query = db.query(Match).filter(
        Match.match_date == match_date,
        Match.status.in_(["scheduled", "completed"]),
        or_(
            Match.home_team_id.in_([home_team_id, away_team_id]),
            Match.away_team_id.in_([home_team_id, away_team_id]),
            Match.venue == venue if venue else False,
        ),
    )
    if exclude_match_id is not None:
        query = query.filter(Match.id != exclude_match_id)
    if query.first():
        raise HTTPException(status_code=409, detail="A team or venue already has a match at this time")


@router.get("/", response_model=list[MatchResponse])
def list_matches(
    db: db_dependency,
    current_user: optional_user_dependency,
    tournament_id: int | None = Query(None),
    match_status: str | None = Query(None, alias="status", pattern="^(scheduled|postponed|completed|cancelled)$"),
):
    query = db.query(Match).filter(Match.tournament_id.in_(visible_tournament_ids(current_user)))
    if tournament_id is not None:
        query = query.filter(Match.tournament_id == tournament_id)
    if match_status is not None:
        query = query.filter(Match.status == match_status)
    return query.order_by(Match.match_date, Match.id).all()


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def create_match(
    payload: MatchCreate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    tournament = db.get(Tournament, payload.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    require_owned_tournament(db, tournament.id, current_user)
    if tournament.status == "archived":
        raise HTTPException(status_code=409, detail="Archived tournaments cannot be scheduled")
    validate_teams(db, payload.tournament_id, payload.home_team_id, payload.away_team_id)
    validate_schedule_conflict(
        db, payload.match_date, payload.home_team_id, payload.away_team_id, payload.venue
    )
    match = Match(**payload.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, db: db_dependency, current_user: optional_user_dependency):
    match = get_match_or_404(db, match_id)
    require_tournament_access(db, match.tournament_id, current_user)
    return match


@router.get("/{match_id}/goals", response_model=list[GoalEventResponse])
def list_goal_events(match_id: int, db: db_dependency, current_user: optional_user_dependency):
    match = get_match_or_404(db, match_id)
    require_tournament_access(db, match.tournament_id, current_user)
    events = db.query(GoalEvent).filter(GoalEvent.match_id == match_id).order_by(
        GoalEvent.minute, GoalEvent.id
    ).all()
    return [serialize_goal_event(event) for event in events]


@router.post("/{match_id}/goals", response_model=GoalEventResponse, status_code=status.HTTP_201_CREATED)
def create_goal_event(
    match_id: int,
    payload: GoalEventCreate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id, lock=True)
    require_owned_match(match, current_user)
    if match.status != "completed":
        raise HTTPException(status_code=409, detail="Record the final score before adding goal details")

    scorer = db.get(Player, payload.scorer_id)
    if not scorer or scorer.team_id not in (match.home_team_id, match.away_team_id):
        raise HTTPException(status_code=422, detail="The scorer must belong to a team in this match")

    assist_player = None
    if payload.assist_player_id is not None:
        assist_player = db.get(Player, payload.assist_player_id)
        if not assist_player or assist_player.team_id != scorer.team_id:
            raise HTTPException(status_code=422, detail="The assister must belong to the scorer's team")
        if assist_player.id == scorer.id:
            raise HTTPException(status_code=422, detail="The scorer cannot assist their own goal")

    recorded_for_team = db.query(func.count(GoalEvent.id)).filter(
        GoalEvent.match_id == match.id,
        GoalEvent.team_id == scorer.team_id,
    ).scalar() or 0
    official_score = match.home_score if scorer.team_id == match.home_team_id else match.away_score
    if recorded_for_team >= official_score:
        raise HTTPException(
            status_code=409,
            detail="All goals in the official score already have a scorer",
        )

    event = GoalEvent(
        match_id=match.id,
        team_id=scorer.team_id,
        scorer_id=scorer.id,
        assist_player_id=assist_player.id if assist_player else None,
        minute=payload.minute,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return serialize_goal_event(event)


@router.delete("/{match_id}/goals/{goal_event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal_event(
    match_id: int,
    goal_event_id: int,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id)
    require_owned_match(match, current_user)
    event = db.query(GoalEvent).filter(
        GoalEvent.id == goal_event_id,
        GoalEvent.match_id == match_id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Goal event not found")
    db.delete(event)
    db.commit()
    return None


@router.patch("/{match_id}", response_model=MatchResponse)
def update_match(
    match_id: int,
    payload: MatchUpdate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id, lock=True)
    require_owned_match(match, current_user)
    if match.status == "completed":
        raise HTTPException(status_code=409, detail="Withdraw the result before rescheduling a completed match")
    values = payload.model_dump(exclude_unset=True)
    proposed_date = values.get("match_date", match.match_date)
    proposed_venue = values.get("venue", match.venue)
    if values.get("status", match.status) == "scheduled":
        if match.tournament.status == "archived":
            raise HTTPException(status_code=409, detail="Archived tournaments cannot be scheduled")
        validate_teams(db, match.tournament_id, match.home_team_id, match.away_team_id)
        validate_schedule_conflict(
            db,
            proposed_date,
            match.home_team_id,
            match.away_team_id,
            proposed_venue,
            exclude_match_id=match.id,
        )
    for key, value in values.items():
        setattr(match, key, value)
    match.version += 1
    db.commit()
    return match


@router.put("/{match_id}/score", response_model=MatchResponse)
def record_score(
    match_id: int,
    payload: MatchScoreUpdate,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id, lock=True)
    require_owned_match(match, current_user)
    if match.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Match was changed; reload it before saving the score")
    if match.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled matches cannot receive a score")
    if match.status != "completed":
        validate_schedule_conflict(
            db, match.match_date, match.home_team_id, match.away_team_id, match.venue,
            exclude_match_id=match.id,
        )
    recorded_goals = dict(
        db.query(GoalEvent.team_id, func.count(GoalEvent.id))
        .filter(GoalEvent.match_id == match.id)
        .group_by(GoalEvent.team_id)
        .all()
    )
    if recorded_goals.get(match.home_team_id, 0) > payload.home_score or recorded_goals.get(
        match.away_team_id, 0
    ) > payload.away_score:
        raise HTTPException(
            status_code=409,
            detail="Remove goal details that exceed the corrected score before saving",
        )
    changed = (match.home_score, match.away_score) != (payload.home_score, payload.away_score)
    if match.status == "completed" and not changed:
        return match
    if match.status == "completed" and changed and not payload.reason:
        raise HTTPException(status_code=422, detail="A reason is required when correcting a result")
    revision = MatchResultRevision(
        match_id=match.id,
        changed_by_id=current_user.id,
        previous_home_score=match.home_score,
        previous_away_score=match.away_score,
        new_home_score=payload.home_score,
        new_away_score=payload.away_score,
        reason=payload.reason,
    )
    match.home_score = payload.home_score
    match.away_score = payload.away_score
    match.status = "completed"
    match.version += 1
    db.add(revision)
    db.commit()
    return match


@router.post("/{match_id}/withdraw-result", response_model=MatchResponse)
def withdraw_result(
    match_id: int,
    payload: MatchResultWithdraw,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id, lock=True)
    require_owned_match(match, current_user)
    if match.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Match was changed; reload it before withdrawing the result")
    if match.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed results can be withdrawn")
    db.add(
        MatchResultRevision(
            match_id=match.id,
            changed_by_id=current_user.id,
            previous_home_score=match.home_score,
            previous_away_score=match.away_score,
            new_home_score=None,
            new_away_score=None,
            reason=payload.reason,
        )
    )
    match.home_score = None
    match.away_score = None
    match.status = "scheduled"
    match.version += 1
    db.query(GoalEvent).filter(GoalEvent.match_id == match.id).delete(synchronize_session=False)
    db.commit()
    return match


@router.get("/{match_id}/revisions", response_model=list[ResultRevisionResponse])
def list_revisions(
    match_id: int,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id)
    require_owned_match(match, current_user)
    return db.query(MatchResultRevision).filter(MatchResultRevision.match_id == match_id).order_by(
        MatchResultRevision.changed_at, MatchResultRevision.id
    ).all()


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(
    match_id: int,
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    match = get_match_or_404(db, match_id, lock=True)
    require_owned_match(match, current_user)
    if match.status == "completed":
        raise HTTPException(status_code=409, detail="Withdraw the result before deleting a completed match")
    if db.query(MatchResultRevision.id).filter(MatchResultRevision.match_id == match_id).first():
        raise HTTPException(status_code=409, detail="Matches with result history cannot be deleted; cancel the fixture instead")
    db.delete(match)
    db.commit()
    return None
