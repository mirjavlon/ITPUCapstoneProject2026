from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.models.tournament import Tournament


@dataclass
class MutableStanding:
    team_id: int
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0


def calculate_standings(db: Session, tournament: Tournament) -> list[dict]:
    teams = db.query(Team).filter(Team.tournament_id == tournament.id).all()
    rows = {team.id: MutableStanding(team_id=team.id, team_name=team.name) for team in teams}
    matches = db.query(Match).filter(
        Match.tournament_id == tournament.id,
        Match.status == "completed",
    ).all()

    for match in matches:
        if match.home_team_id not in rows or match.away_team_id not in rows:
            continue
        home = rows[match.home_team_id]
        away = rows[match.away_team_id]
        home.played += 1
        away.played += 1
        home.goals_for += match.home_score
        home.goals_against += match.away_score
        away.goals_for += match.away_score
        away.goals_against += match.home_score
        if match.home_score > match.away_score:
            home.wins += 1
            away.losses += 1
            home.points += tournament.win_points
            away.points += tournament.loss_points
        elif match.home_score < match.away_score:
            away.wins += 1
            home.losses += 1
            away.points += tournament.win_points
            home.points += tournament.loss_points
        else:
            home.draws += 1
            away.draws += 1
            home.points += tournament.draw_points
            away.points += tournament.draw_points

    ordered = sorted(
        rows.values(),
        key=lambda row: (-row.points, -(row.goals_for - row.goals_against), -row.goals_for, row.team_name.casefold()),
    )
    output: list[dict] = []
    previous_key: tuple[int, int, int] | None = None
    previous_position = 0
    for index, row in enumerate(ordered, start=1):
        ranking_key = (row.points, row.goals_for - row.goals_against, row.goals_for)
        if ranking_key != previous_key:
            previous_position = index
            previous_key = ranking_key
        output.append(
            {
                "position": previous_position,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "played": row.played,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "goal_difference": row.goals_for - row.goals_against,
                "points": row.points,
            }
        )
    return output
