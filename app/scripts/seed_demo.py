from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import AccountType, User


TOURNAMENT_SLUG = "tashkent-mini-football-cup-2026"

TEAM_PLAYERS = {
    "Tashkent Falcons": ["Aziz Karimov", "Bekzod Aliyev", "Jasur Rakhimov", "Sardor Usmonov", "Temur Akhmedov"],
    "Samarkand Stars": ["Akmal Yuldashev", "Bobur Ergashev", "Davron Ismailov", "Farrukh Sobirov", "Kamron Saidov"],
    "Bukhara Lions": ["Alisher Kadirov", "Diyor Mamatov", "Eldor Tursunov", "Ibrohim Rasulov", "Murod Nazarov"],
    "Fergana United": ["Abbos Sattorov", "Dilshod Khasanov", "Javohir Mirzayev", "Nodir Hamidov", "Oybek Salimov"],
    "Khiva Guardians": ["Asadbek Rahmonov", "Doniyor Umarov", "Ilhom Abdullayev", "Rustam Holmatov", "Shahzod Nematov"],
    "Navoi Comets": ["Anvar Gafurov", "Firdavs Oripov", "Komil Juraev", "Sanjar Fayziyev", "Ulugbek Hakimov"],
    "Andijan Eagles": ["Abror Vohidov", "Behruz Qosimov", "Jamshid Yoqubov", "Sherzod Madaminov", "Zafar Toshpulatov"],
    "Nukus Wolves": ["Alimjan Bekmuratov", "Daulet Ametov", "Jandos Utegenov", "Miras Allambergenov", "Timur Kallibekov"],
}

POSITIONS = ["GK", "DEF", "MID", "FWD", "FWD"]
JERSEY_NUMBERS = [1, 4, 7, 9, 10]


def main() -> None:
    timezone = ZoneInfo("Asia/Tashkent")
    with SessionLocal() as db:
        if db.query(Tournament).filter(Tournament.slug == TOURNAMENT_SLUG).first():
            raise SystemExit(f"Tournament '{TOURNAMENT_SLUG}' already exists; no records were added")
        organizer = (
            db.query(User)
            .filter(User.account_type == AccountType.ORGANIZER, User.is_active.is_(True))
            .order_by(User.id)
            .first()
        )
        if not organizer:
            raise SystemExit("Create an organizer account before adding demo data")

        tournament = Tournament(
            created_by_id=organizer.id,
            name="Tashkent Mini-Football Cup 2026",
            slug=TOURNAMENT_SLUG,
            status="published",
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 30),
            win_points=3,
            draw_points=1,
            loss_points=0,
        )
        db.add(tournament)
        db.flush()

        teams: dict[str, Team] = {}
        for team_name, player_names in TEAM_PLAYERS.items():
            team = Team(name=team_name, tournament_id=tournament.id, is_active=True)
            db.add(team)
            db.flush()
            teams[team_name] = team
            for name, number, position in zip(player_names, JERSEY_NUMBERS, POSITIONS, strict=True):
                db.add(Player(name=name, jersey_number=number, position=position, team_id=team.id))

        fixtures = [
            ("Tashkent Falcons", "Samarkand Stars", datetime(2026, 9, 12, 18, 0, tzinfo=timezone), "Central Arena"),
            ("Bukhara Lions", "Fergana United", datetime(2026, 9, 12, 20, 0, tzinfo=timezone), "Central Arena"),
            ("Khiva Guardians", "Navoi Comets", datetime(2026, 9, 13, 18, 0, tzinfo=timezone), "University Sports Hall"),
            ("Andijan Eagles", "Nukus Wolves", datetime(2026, 9, 13, 20, 0, tzinfo=timezone), "University Sports Hall"),
        ]
        for home_name, away_name, match_date, venue in fixtures:
            db.add(
                Match(
                    tournament_id=tournament.id,
                    home_team_id=teams[home_name].id,
                    away_team_id=teams[away_name].id,
                    match_date=match_date,
                    venue=venue,
                    status="scheduled",
                )
            )
        db.commit()

    print("Created 1 published tournament, 8 teams, 40 players, and 4 scheduled matches")


if __name__ == "__main__":
    main()
