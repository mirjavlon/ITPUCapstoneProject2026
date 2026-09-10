# ITPUCapstoneProject2026

## Mini-Football Tournament Management

A full-stack tournament management application for community mini-football competitions. It provides a public results website for spectators, role-based dashboards for organizers and team managers, and a REST API built with FastAPI and PostgreSQL.

## Features

### Public spectator experience
Spectators do not need an account. They can:
- Browse published tournaments.
- View standings calculated from completed matches.
- Check fixtures, results, dates, venues, and match status.
- View participating teams and player rosters.
- See goal scorers, assists, player statistics, and each tournament's top scorers.

### Organizer tools
Anyone can create an organizer account. Each tournament records the organizer who created it, and organizers can manage only their own tournaments. They can:
- Create, edit, publish, archive, and preview their tournaments.
- Configure win, draw, and loss points for their tournaments.
- Create teams, assign managers, and manage fixtures in their tournaments.
- Record, correct, and withdraw results, including goal details, in their tournaments.
- Review result revision history for their tournaments.

*The database field for an organizer is currently named is_admin; the user-facing website calls this role Organizer.*

### Manager tools
Managers can register through the public registration page. They can:
- Register a team in a published tournament, or a draft tournament where they already manage a team.
- Edit teams assigned to their account.
- Add, edit, and remove players from their assigned teams.
- Open a statistics page for every player showing goals and assists.
- View tournament schedules, results, and standings.

*Managers cannot manage tournaments, fixtures, scores, other users, or another manager's team.*

## Technology
- Python 3.10+
- FastAPI and Uvicorn
- SQLAlchemy ORM
- PostgreSQL in development and production
- Alembic database migrations
- Pydantic validation
- JWT authentication with bcrypt password hashing
- Jinja2 templates and Bootstrap 5
- unittest/pytest-compatible automated tests

## Project structure

```text
app/
├── main.py                 FastAPI application and middleware
├── config.py               Environment-based settings
├── database.py             SQLAlchemy engine and sessions
├── dependencies.py         Database and authentication dependencies
├── models/                 SQLAlchemy database models
├── schemas/                Pydantic request and response models
├── routers/                API and website routes
├── services/               Standings and player-statistics calculations
├── scripts/                Organizer and demo-data commands
└── utils/security.py       Password and JWT helpers
alembic/                    Database migrations
static/                     Website CSS and browser assets
templates/                  Jinja2 page templates
tests/                      Backend and frontend workflow tests
```
