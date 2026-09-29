from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.match import GoalEvent, Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament


def get_player_stats(db: Session, player: Player) -> dict:
    goals = (
        db.query(func.count(GoalEvent.id))
        .join(Match, Match.id == GoalEvent.match_id)
        .filter(GoalEvent.scorer_id == player.id, Match.status == "completed")
        .scalar()
        or 0
    )
    assists = (
        db.query(func.count(GoalEvent.id))
        .join(Match, Match.id == GoalEvent.match_id)
        .filter(GoalEvent.assist_player_id == player.id, Match.status == "completed")
        .scalar()
        or 0
    )
    return {
        "player_id": player.id,
        "player_name": player.name,
        "team_id": player.team_id,
        "team_name": player.team.name,
        "tournament_id": player.team.tournament_id,
        "tournament_name": player.team.tournament.name,
        "goals": goals,
        "assists": assists,
    }


def calculate_top_scorers(db: Session, tournament: Tournament) -> list[dict]:
    goal_counts = (
        db.query(
            GoalEvent.scorer_id.label("player_id"),
            func.count(GoalEvent.id).label("goals"),
        )
        .join(Match, Match.id == GoalEvent.match_id)
        .filter(Match.tournament_id == tournament.id, Match.status == "completed")
        .group_by(GoalEvent.scorer_id)
        .subquery()
    )
    assist_counts = (
        db.query(
            GoalEvent.assist_player_id.label("player_id"),
            func.count(GoalEvent.id).label("assists"),
        )
        .join(Match, Match.id == GoalEvent.match_id)
        .filter(
            Match.tournament_id == tournament.id,
            Match.status == "completed",
            GoalEvent.assist_player_id.is_not(None),
        )
        .group_by(GoalEvent.assist_player_id)
        .subquery()
    )

    goals = func.coalesce(goal_counts.c.goals, 0)
    assists = func.coalesce(assist_counts.c.assists, 0)
    rows = (
        db.query(Player, Team, goals.label("goals"), assists.label("assists"))
        .join(Team, Team.id == Player.team_id)
        .outerjoin(goal_counts, goal_counts.c.player_id == Player.id)
        .outerjoin(assist_counts, assist_counts.c.player_id == Player.id)
        .filter(
            Team.tournament_id == tournament.id,
            or_(goals > 0, assists > 0),
        )
        .all()
    )
    ordered = sorted(rows, key=lambda row: (-row[2], -row[3], row[0].name.casefold()))

    output: list[dict] = []
    previous_key: tuple[int, int] | None = None
    previous_position = 0
    for index, (player, team, player_goals, player_assists) in enumerate(ordered, start=1):
        ranking_key = (player_goals, player_assists)
        if ranking_key != previous_key:
            previous_position = index
            previous_key = ranking_key
        output.append(
            {
                "position": previous_position,
                "player_id": player.id,
                "player_name": player.name,
                "team_id": team.id,
                "team_name": team.name,
                "tournament_id": tournament.id,
                "tournament_name": tournament.name,
                "goals": player_goals,
                "assists": player_assists,
            }
        )
    return output
