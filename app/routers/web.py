import hmac
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, or_

from app.config import settings
from app.dependencies import db_dependency
from app.models.match import GoalEvent, Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import AccountType, User
from app.routers.matches import (
    create_goal_event as api_create_goal_event,
    create_match as api_create_match,
    delete_goal_event as api_delete_goal_event,
    delete_match as api_delete_match,
    record_score as api_record_score,
    update_match as api_update_match,
    withdraw_result as api_withdraw_result,
)
from app.routers.players import (
    create_player as api_create_player,
    delete_player as api_delete_player,
    update_player as api_update_player,
)
from app.routers.teams import create_team as api_create_team, delete_team as api_delete_team, update_team as api_update_team
from app.routers.tournaments import (
    create_tournament as api_create_tournament,
    update_tournament as api_update_tournament,
    update_tournament_status as api_update_tournament_status,
)
from app.schemas.match import GoalEventCreate, MatchCreate, MatchResultWithdraw, MatchScoreUpdate, MatchUpdate
from app.schemas.player import PlayerCreate, PlayerUpdate
from app.schemas.team import TeamCreate, TeamUpdate
from app.schemas.tournament import TournamentCreate, TournamentStatusUpdate, TournamentUpdate
from app.services.standings import calculate_standings
from app.services.player_stats import calculate_top_scorers, get_player_stats
from app.services.ownership import owns_tournament
from app.services.visibility import can_view_tournament, visible_tournament_ids
from app.utils.security import create_access_token, decode_access_token, get_password_hash, verify_password


router = APIRouter(tags=["website"], include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")
local_timezone = ZoneInfo(settings.APP_TIMEZONE)


def local_datetime(value: datetime | None, format_string: str = "%d %b %Y, %H:%M") -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=local_timezone)
    return value.astimezone(local_timezone).strftime(format_string)


templates.env.filters["local_datetime"] = local_datetime


def safe_next(value: str | None, default: str = "/dashboard") -> str:
    if not value:
        return default
    decoded = unquote(value)
    if decoded.startswith("//") or "\\" in decoded or any(ord(char) < 32 or ord(char) == 127 for char in decoded):
        return default
    try:
        parsed = urlparse(decoded)
    except ValueError:
        return default
    return value if not parsed.scheme and not parsed.netloc and value.startswith("/") else default


def verify_csrf(request: Request, submitted: str) -> None:
    expected = request.cookies.get("csrf_token", "")
    if not expected or not expected.isascii() or not submitted.isascii() or not hmac.compare_digest(expected, submitted):
        raise HTTPException(status_code=403, detail="This form expired. Refresh the page and try again.")


def current_user(request: Request, db) -> User | None:
    token = request.cookies.get("access_token")
    user_id = decode_access_token(token) if token else None
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user if user and user.is_active else None


def flash(request: Request, message: str, category: str = "success") -> None:
    messages = request.session.setdefault("messages", [])
    messages.append({"message": message, "category": category})
    request.session["messages"] = messages


def context(request: Request, db, **values) -> dict:
    return {
        "request": request,
        "csrf_token": request.state.csrf_token,
        "current_user": current_user(request, db),
        "messages": request.session.pop("messages", []),
        **values,
    }


def render(request: Request, db, template_name: str, *, status_code: int = 200, **values):
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context(request, db, **values),
        status_code=status_code,
    )


def require_user(request: Request, db, *, admin: bool = False) -> User | RedirectResponse:
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
    if admin and not user.is_organizer:
        return render(
            request,
            db,
            "error.html",
            status_code=403,
            title="Access denied",
            message="Only tournament organizers can use this page.",
        )
    return user


def error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, ValidationError):
        message = exc.errors()[0].get("msg", "Invalid value")
        return message.removeprefix("Value error, ")
    return "The operation could not be completed."


def parse_local_match_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_timezone)
    return parsed


def can_manage_team(user: User, team: Team) -> bool:
    return owns_tournament(team.tournament, user) if user.is_organizer else team.manager_id == user.id


def can_manage_match(user: User, match: Match) -> bool:
    return owns_tournament(match.tournament, user)


def selectable_tournaments(db, user: User):
    query = db.query(Tournament).filter(Tournament.status != "archived")
    if user.is_organizer:
        return query.filter(Tournament.created_by_id == user.id).order_by(Tournament.name).all()
    return query.filter(Tournament.id.in_(visible_tournament_ids(user))).order_by(Tournament.name).all()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: db_dependency):
    tournaments = db.query(Tournament).filter(Tournament.status == "published").order_by(
        Tournament.start_date.asc().nullslast(), Tournament.name
    ).all()
    cards = []
    now = datetime.now(local_timezone)
    for tournament in tournaments:
        next_match = db.query(Match).filter(
            Match.tournament_id == tournament.id,
            Match.status == "scheduled",
            Match.match_date >= now,
        ).order_by(Match.match_date).first()
        cards.append(
            {
                "tournament": tournament,
                "team_count": db.query(func.count(Team.id)).filter(
                    Team.tournament_id == tournament.id, Team.is_active.is_(True)
                ).scalar(),
                "match_count": db.query(func.count(Match.id)).filter(Match.tournament_id == tournament.id).scalar(),
                "next_match": next_match,
            }
        )
    return render(request, db, "home.html", cards=cards)


@router.get("/tournaments/{tournament_id}", response_class=HTMLResponse)
def tournament_page(tournament_id: int, request: Request, db: db_dependency):
    tournament = db.get(Tournament, tournament_id)
    user = current_user(request, db)
    if not tournament or not can_view_tournament(db, tournament_id, user):
        return render(request, db, "error.html", status_code=404, title="Tournament not found", message="This tournament is not available.")
    teams = db.query(Team).filter(Team.tournament_id == tournament_id, Team.is_active.is_(True)).order_by(Team.name).all()
    fixtures = db.query(Match).filter(Match.tournament_id == tournament_id).order_by(Match.match_date).all()
    return render(
        request,
        db,
        "tournament.html",
        tournament=tournament,
        teams=teams,
        fixtures=fixtures,
        standings=calculate_standings(db, tournament),
        top_scorers=calculate_top_scorers(db, tournament),
    )


@router.get("/teams/{team_id}", response_class=HTMLResponse)
def team_page(team_id: int, request: Request, db: db_dependency):
    team = db.get(Team, team_id)
    user = current_user(request, db)
    if not team or not can_view_tournament(db, team.tournament_id, user):
        return render(request, db, "error.html", status_code=404, title="Team not found", message="This team is not available.")
    players = db.query(Player).filter(Player.team_id == team_id).order_by(Player.jersey_number.asc().nullslast(), Player.name).all()
    matches = db.query(Match).filter(or_(Match.home_team_id == team_id, Match.away_team_id == team_id)).order_by(Match.match_date).all()
    player_stats = {player.id: get_player_stats(db, player) for player in players}
    return render(
        request,
        db,
        "team.html",
        team=team,
        players=players,
        matches=matches,
        player_stats=player_stats,
    )


@router.get("/players/{player_id}/stats", response_class=HTMLResponse)
def player_stats_page(player_id: int, request: Request, db: db_dependency):
    player = db.get(Player, player_id)
    user = current_user(request, db)
    if not player or not can_view_tournament(db, player.team.tournament_id, user):
        return render(
            request,
            db,
            "error.html",
            status_code=404,
            title="Player not found",
            message="This player's statistics are not available.",
        )
    contributions = (
        db.query(GoalEvent)
        .join(Match, Match.id == GoalEvent.match_id)
        .filter(
            Match.status == "completed",
            or_(GoalEvent.scorer_id == player.id, GoalEvent.assist_player_id == player.id),
        )
        .order_by(Match.match_date.desc(), GoalEvent.minute.desc(), GoalEvent.id.desc())
        .all()
    )
    return render(
        request,
        db,
        "player_stats.html",
        player=player,
        stats=get_player_stats(db, player),
        contributions=contributions,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: db_dependency, next: str | None = None):
    if current_user(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, db, "login.html", next_path=safe_next(next), error=None)


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    db: db_dependency,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next_path: str = Form("/dashboard"),
):
    verify_csrf(request, csrf_token)
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return render(request, db, "login.html", status_code=401, next_path=safe_next(next_path), error="Incorrect username or password.")
    token = create_access_token(user.id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    response = RedirectResponse(safe_next(next_path), status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: db_dependency):
    if current_user(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, db, "register.html", error=None, form={})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    db: db_dependency,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    from app.schemas.user import UserCreate

    verify_csrf(request, csrf_token)
    form = {"username": username, "email": email}
    try:
        payload = UserCreate(
            username=username.strip(), email=email.strip(), password=password, account_type=AccountType.MANAGER
        )
    except ValidationError as exc:
        return render(request, db, "register.html", status_code=422, error=exc.errors()[0]["msg"], form=form)
    existing = db.query(User).filter(or_(User.username == payload.username, User.email == payload.email)).first()
    if existing:
        return render(request, db, "register.html", status_code=409, error="That username or email is already registered.", form=form)
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        account_type=AccountType.MANAGER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    flash(request, "Account created. You can sign in now.")
    return RedirectResponse("/login", status_code=303)


@router.get("/register-organizer", response_class=HTMLResponse)
def organizer_register_page(request: Request, db: db_dependency):
    if current_user(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, db, "organizer_register.html", error=None, form={})


@router.post("/register-organizer", response_class=HTMLResponse)
def organizer_register_submit(
    request: Request,
    db: db_dependency,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    from app.schemas.user import UserCreate

    verify_csrf(request, csrf_token)
    form = {"username": username, "email": email}
    try:
        payload = UserCreate(
            username=username.strip(), email=email.strip(), password=password, account_type=AccountType.ORGANIZER
        )
    except ValidationError as exc:
        return render(request, db, "organizer_register.html", status_code=422, error=exc.errors()[0]["msg"], form=form)
    existing = db.query(User).filter(or_(User.username == payload.username, User.email == payload.email)).first()
    if existing:
        return render(request, db, "organizer_register.html", status_code=409, error="That username or email is already registered.", form=form)
    db.add(User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        account_type=AccountType.ORGANIZER,
        is_active=True,
    ))
    db.commit()
    flash(request, "Organizer account created. You can sign in now.")
    return RedirectResponse("/login", status_code=303)


@router.post("/logout")
def logout(request: Request, db: db_dependency, csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: db_dependency):
    user = require_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if not isinstance(user, User):
        return user
    tournaments = (
        db.query(Tournament).filter(Tournament.created_by_id == user.id)
        .order_by(Tournament.start_date.desc().nullslast(), Tournament.name).all()
        if user.is_organizer else []
    )
    teams = (
        db.query(Team).join(Tournament).filter(Tournament.created_by_id == user.id).order_by(Team.name).all()
        if user.is_organizer else db.query(Team).filter(Team.manager_id == user.id).order_by(Team.name).all()
    )
    managed_players = (
        db.query(Player)
        .join(Team)
        .filter(Team.manager_id == user.id)
        .order_by(Team.name, Player.jersey_number.asc().nullslast(), Player.name)
        .all()
        if not user.is_organizer
        else []
    )
    upcoming = db.query(Match).join(Tournament).filter(
        Match.status == "scheduled",
        Tournament.created_by_id == user.id,
    ).order_by(Match.match_date).limit(6).all() if user.is_organizer else []
    return render(
        request,
        db,
        "dashboard.html",
        user=user,
        tournaments=tournaments,
        teams=teams,
        player_stats=[get_player_stats(db, player) for player in managed_players],
        upcoming=upcoming,
        totals={
            "tournaments": len(tournaments) if user.is_organizer else len({team.tournament_id for team in teams}),
            "teams": len(teams) if user.is_organizer else len(teams),
            "players": db.query(func.count(Player.id)).join(Team).join(Tournament).filter(Tournament.created_by_id == user.id).scalar() if user.is_organizer else db.query(func.count(Player.id)).join(Team).filter(Team.manager_id == user.id).scalar(),
            "matches": db.query(func.count(Match.id)).join(Tournament).filter(Tournament.created_by_id == user.id).scalar() if user.is_organizer else db.query(func.count(Match.id)).join(Tournament).filter(Tournament.id.in_([team.tournament_id for team in teams] or [-1])).scalar(),
        },
    )


@router.get("/dashboard/tournaments/new", response_class=HTMLResponse)
def tournament_create_page(request: Request, db: db_dependency):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    return render(request, db, "tournament_form.html", tournament=None, error=None, form={}, teams=[], matches=[])


@router.post("/dashboard/tournaments/new", response_class=HTMLResponse)
def tournament_create_submit(
    request: Request,
    db: db_dependency,
    name: str = Form(...),
    slug: str = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    win_points: int = Form(3),
    draw_points: int = Form(1),
    loss_points: int = Form(0),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    form = {
        "name": name,
        "slug": slug,
        "start_date": start_date,
        "end_date": end_date,
        "win_points": win_points,
        "draw_points": draw_points,
        "loss_points": loss_points,
    }
    try:
        payload = TournamentCreate(
            name=name.strip(),
            slug=slug.strip().lower(),
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            win_points=win_points,
            draw_points=draw_points,
            loss_points=loss_points,
        )
        tournament = api_create_tournament(payload, db, user)
    except (ValidationError, HTTPException, ValueError) as exc:
        return render(request, db, "tournament_form.html", status_code=422, tournament=None, error=error_text(exc), form=form, teams=[], matches=[])
    flash(request, "Tournament created.")
    return RedirectResponse(f"/dashboard/tournaments/{tournament.id}/edit", status_code=303)


@router.get("/dashboard/tournaments/{tournament_id}/edit", response_class=HTMLResponse)
def tournament_edit_page(tournament_id: int, request: Request, db: db_dependency):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    tournament = db.get(Tournament, tournament_id)
    if not tournament or not owns_tournament(tournament, user):
        return render(request, db, "error.html", status_code=403 if tournament else 404, title="Tournament unavailable", message="You cannot manage this tournament.")
    teams = db.query(Team).filter(Team.tournament_id == tournament_id).order_by(Team.name).all()
    matches = db.query(Match).filter(Match.tournament_id == tournament_id).order_by(Match.match_date).all()
    return render(request, db, "tournament_form.html", tournament=tournament, error=None, form={}, teams=teams, matches=matches)


@router.post("/dashboard/tournaments/{tournament_id}/edit", response_class=HTMLResponse)
def tournament_edit_submit(
    tournament_id: int,
    request: Request,
    db: db_dependency,
    name: str = Form(...),
    slug: str = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    win_points: int = Form(3),
    draw_points: int = Form(1),
    loss_points: int = Form(0),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    tournament = db.get(Tournament, tournament_id)
    if not tournament or not owns_tournament(tournament, user):
        return render(request, db, "error.html", status_code=403 if tournament else 404, title="Tournament unavailable", message="You cannot manage this tournament.")
    form = {"name": name, "slug": slug, "start_date": start_date, "end_date": end_date, "win_points": win_points, "draw_points": draw_points, "loss_points": loss_points}
    try:
        payload = TournamentUpdate(
            name=name.strip(), slug=slug.strip().lower(),
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            win_points=win_points, draw_points=draw_points, loss_points=loss_points,
        )
        api_update_tournament(tournament_id, payload, db, user)
    except (ValidationError, HTTPException, ValueError) as exc:
        teams = db.query(Team).filter(Team.tournament_id == tournament_id).order_by(Team.name).all()
        matches = db.query(Match).filter(Match.tournament_id == tournament_id).order_by(Match.match_date).all()
        return render(request, db, "tournament_form.html", status_code=422, tournament=tournament, error=error_text(exc), form=form, teams=teams, matches=matches)
    flash(request, "Tournament details updated.")
    return RedirectResponse(f"/dashboard/tournaments/{tournament_id}/edit", status_code=303)


@router.post("/dashboard/tournaments/{tournament_id}/status")
def tournament_status_submit(
    tournament_id: int,
    request: Request,
    db: db_dependency,
    tournament_status: str = Form(...),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    try:
        api_update_tournament_status(tournament_id, TournamentStatusUpdate(status=tournament_status), db, user)
        flash(request, f"Tournament marked {tournament_status}.")
    except (ValidationError, HTTPException) as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/tournaments/{tournament_id}/edit", status_code=303)


@router.get("/dashboard/teams/new", response_class=HTMLResponse)
def team_create_page(request: Request, db: db_dependency, tournament_id: int | None = None):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    tournaments = selectable_tournaments(db, user)
    managers = db.query(User).filter(User.is_active.is_(True), User.account_type == AccountType.MANAGER).order_by(User.username).all() if user.is_organizer else []
    return render(request, db, "team_form.html", team=None, error=None, form={"tournament_id": tournament_id}, tournaments=tournaments, managers=managers, players=[])


@router.post("/dashboard/teams/new", response_class=HTMLResponse)
def team_create_submit(
    request: Request,
    db: db_dependency,
    tournament_id: int = Form(...),
    name: str = Form(...),
    manager_id: str = Form(""),
    contact_info: str = Form(""),
    logo_url: str = Form(""),
    csrf_token: str = Form(...),
):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    form = {"tournament_id": tournament_id, "name": name, "manager_id": manager_id, "contact_info": contact_info, "logo_url": logo_url}
    try:
        payload = TeamCreate(
            tournament_id=tournament_id,
            name=name.strip(),
            manager_id=int(manager_id) if manager_id and user.is_organizer else None,
            contact_info=contact_info.strip() or None,
            logo_url=logo_url.strip() or None,
        )
        team = api_create_team(payload, db, user)
    except (ValidationError, HTTPException, ValueError) as exc:
        tournaments = selectable_tournaments(db, user)
        managers = db.query(User).filter(User.is_active.is_(True), User.account_type == AccountType.MANAGER).order_by(User.username).all() if user.is_organizer else []
        return render(request, db, "team_form.html", status_code=422, team=None, error=error_text(exc), form=form, tournaments=tournaments, managers=managers, players=[])
    flash(request, "Team registered.")
    return RedirectResponse(f"/dashboard/teams/{team.id}/edit", status_code=303)


@router.get("/dashboard/teams/{team_id}/edit", response_class=HTMLResponse)
def team_edit_page(team_id: int, request: Request, db: db_dependency):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    team = db.get(Team, team_id)
    if not team or not can_manage_team(user, team):
        return render(request, db, "error.html", status_code=403 if team else 404, title="Team unavailable", message="You cannot manage this team.")
    tournaments = selectable_tournaments(db, user)
    managers = db.query(User).filter(User.is_active.is_(True), User.account_type == AccountType.MANAGER).order_by(User.username).all() if user.is_organizer else []
    players = db.query(Player).filter(Player.team_id == team_id).order_by(Player.jersey_number.asc().nullslast(), Player.name).all()
    return render(request, db, "team_form.html", team=team, error=None, form={}, tournaments=tournaments, managers=managers, players=players)


@router.post("/dashboard/teams/{team_id}/edit", response_class=HTMLResponse)
def team_edit_submit(
    team_id: int,
    request: Request,
    db: db_dependency,
    name: str = Form(...),
    manager_id: str = Form(""),
    contact_info: str = Form(""),
    logo_url: str = Form(""),
    is_active: str | None = Form(None),
    csrf_token: str = Form(...),
):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    team = db.get(Team, team_id)
    if not team or not can_manage_team(user, team):
        return render(request, db, "error.html", status_code=403 if team else 404, title="Team unavailable", message="You cannot manage this team.")
    try:
        values = {
            "name": name.strip(), "contact_info": contact_info.strip() or None, "logo_url": logo_url.strip() or None,
        }
        if user.is_organizer:
            values.update({"manager_id": int(manager_id) if manager_id else None, "is_active": is_active == "on"})
        api_update_team(team_id, TeamUpdate(**values), db, user)
    except (ValidationError, HTTPException, ValueError) as exc:
        flash(request, error_text(exc), "error")
    else:
        flash(request, "Team details updated.")
    return RedirectResponse(f"/dashboard/teams/{team_id}/edit", status_code=303)


@router.post("/dashboard/teams/{team_id}/delete")
def team_delete_submit(team_id: int, request: Request, db: db_dependency, csrf_token: str = Form(...)):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    team = db.get(Team, team_id)
    destination = f"/dashboard/tournaments/{team.tournament_id}/edit" if team and user.is_organizer else "/dashboard"
    try:
        api_delete_team(team_id, db, user)
        flash(request, "Team removed. Teams with match history are archived.")
    except HTTPException as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(destination, status_code=303)


@router.get("/dashboard/teams/{team_id}/players/new", response_class=HTMLResponse)
def player_create_page(team_id: int, request: Request, db: db_dependency):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    team = db.get(Team, team_id)
    if not team or not can_manage_team(user, team):
        return render(request, db, "error.html", status_code=403 if team else 404, title="Team unavailable", message="You cannot manage this roster.")
    return render(request, db, "player_form.html", player=None, team=team, error=None, form={})


@router.post("/dashboard/teams/{team_id}/players/new", response_class=HTMLResponse)
def player_create_submit(
    team_id: int,
    request: Request,
    db: db_dependency,
    name: str = Form(...),
    jersey_number: str = Form(""),
    position: str = Form(""),
    csrf_token: str = Form(...),
):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    team = db.get(Team, team_id)
    if not team or not can_manage_team(user, team):
        return render(request, db, "error.html", status_code=403 if team else 404, title="Team unavailable", message="You cannot manage this roster.")
    form = {"name": name, "jersey_number": jersey_number, "position": position}
    try:
        api_create_player(
            PlayerCreate(name=name.strip(), team_id=team_id, jersey_number=int(jersey_number) if jersey_number else None, position=position or None),
            db,
            user,
        )
    except (ValidationError, HTTPException, ValueError) as exc:
        return render(request, db, "player_form.html", status_code=422, player=None, team=team, error=error_text(exc), form=form)
    flash(request, "Player added to the roster.")
    return RedirectResponse(f"/dashboard/teams/{team_id}/edit", status_code=303)


@router.get("/dashboard/players/{player_id}/edit", response_class=HTMLResponse)
def player_edit_page(player_id: int, request: Request, db: db_dependency):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    player = db.get(Player, player_id)
    if not player or not can_manage_team(user, player.team):
        return render(request, db, "error.html", status_code=403 if player else 404, title="Player unavailable", message="You cannot manage this player.")
    return render(request, db, "player_form.html", player=player, team=player.team, error=None, form={})


@router.post("/dashboard/players/{player_id}/edit", response_class=HTMLResponse)
def player_edit_submit(
    player_id: int,
    request: Request,
    db: db_dependency,
    name: str = Form(...),
    jersey_number: str = Form(""),
    position: str = Form(""),
    csrf_token: str = Form(...),
):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    player = db.get(Player, player_id)
    if not player or not can_manage_team(user, player.team):
        return render(request, db, "error.html", status_code=403 if player else 404, title="Player unavailable", message="You cannot manage this player.")
    team_id = player.team_id
    try:
        api_update_player(
            player_id,
            PlayerUpdate(name=name.strip(), jersey_number=int(jersey_number) if jersey_number else None, position=position or None),
            db,
            user,
        )
        flash(request, "Player details updated.")
    except (ValidationError, HTTPException, ValueError) as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/teams/{team_id}/edit", status_code=303)


@router.post("/dashboard/players/{player_id}/delete")
def player_delete_submit(player_id: int, request: Request, db: db_dependency, csrf_token: str = Form(...)):
    user = require_user(request, db)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    player = db.get(Player, player_id)
    team_id = player.team_id if player else None
    try:
        api_delete_player(player_id, db, user)
        flash(request, "Player removed from the roster.")
    except HTTPException as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/teams/{team_id}/edit" if team_id else "/dashboard", status_code=303)


@router.get("/dashboard/matches/new", response_class=HTMLResponse)
def match_create_page(request: Request, db: db_dependency, tournament_id: int | None = None):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    tournaments = selectable_tournaments(db, user)
    teams = db.query(Team).join(Tournament).filter(
        Team.is_active.is_(True), Tournament.created_by_id == user.id
    ).order_by(Team.name).all()
    return render(request, db, "match_form.html", match=None, error=None, form={"tournament_id": tournament_id}, tournaments=tournaments, teams=teams)


@router.post("/dashboard/matches/new", response_class=HTMLResponse)
def match_create_submit(
    request: Request,
    db: db_dependency,
    tournament_id: int = Form(...),
    home_team_id: int = Form(...),
    away_team_id: int = Form(...),
    match_date: str = Form(...),
    venue: str = Form(""),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    form = {"tournament_id": tournament_id, "home_team_id": home_team_id, "away_team_id": away_team_id, "match_date": match_date, "venue": venue}
    try:
        payload = MatchCreate(
            tournament_id=tournament_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            match_date=parse_local_match_datetime(match_date),
            venue=venue.strip() or None,
        )
        match = api_create_match(payload, db, user)
    except (ValidationError, HTTPException, ValueError) as exc:
        tournaments = selectable_tournaments(db, user)
        teams = db.query(Team).join(Tournament).filter(
            Team.is_active.is_(True), Tournament.created_by_id == user.id
        ).order_by(Team.name).all()
        return render(request, db, "match_form.html", status_code=422, match=None, error=error_text(exc), form=form, tournaments=tournaments, teams=teams)
    flash(request, "Fixture scheduled.")
    return RedirectResponse(f"/dashboard/tournaments/{match.tournament_id}/edit", status_code=303)


@router.get("/dashboard/matches/{match_id}/edit", response_class=HTMLResponse)
def match_edit_page(match_id: int, request: Request, db: db_dependency):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    match = db.get(Match, match_id)
    if not match or not can_manage_match(user, match):
        return render(request, db, "error.html", status_code=403 if match else 404, title="Match unavailable", message="You cannot manage this fixture.")
    return render(request, db, "match_form.html", match=match, error=None, form={}, tournaments=[match.tournament], teams=[match.home_team, match.away_team])


@router.post("/dashboard/matches/{match_id}/edit", response_class=HTMLResponse)
def match_edit_submit(
    match_id: int,
    request: Request,
    db: db_dependency,
    match_date: str = Form(...),
    venue: str = Form(""),
    match_status: str = Form("scheduled"),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    match = db.get(Match, match_id)
    if not match or not can_manage_match(user, match):
        return render(request, db, "error.html", status_code=403 if match else 404, title="Match unavailable", message="You cannot manage this fixture.")
    try:
        api_update_match(
            match_id,
            MatchUpdate(match_date=parse_local_match_datetime(match_date), venue=venue.strip() or None, status=match_status),
            db,
            user,
        )
        flash(request, "Fixture updated.")
    except (ValidationError, HTTPException, ValueError) as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/tournaments/{match.tournament_id}/edit", status_code=303)


@router.get("/dashboard/matches/{match_id}/score", response_class=HTMLResponse)
def match_score_page(match_id: int, request: Request, db: db_dependency):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    match = db.get(Match, match_id)
    if not match or not can_manage_match(user, match):
        return render(request, db, "error.html", status_code=403 if match else 404, title="Match unavailable", message="You cannot manage this fixture.")
    return render(request, db, "score_form.html", match=match, error=None)


@router.post("/dashboard/matches/{match_id}/score", response_class=HTMLResponse)
def match_score_submit(
    match_id: int,
    request: Request,
    db: db_dependency,
    home_score: int = Form(...),
    away_score: int = Form(...),
    expected_version: int = Form(...),
    reason: str = Form(""),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    try:
        match = api_record_score(
            match_id,
            MatchScoreUpdate(home_score=home_score, away_score=away_score, expected_version=expected_version, reason=reason.strip() or None),
            db,
            user,
        )
    except (ValidationError, HTTPException) as exc:
        match = db.get(Match, match_id)
        if not match:
            return render(request, db, "error.html", status_code=404, title="Match not found", message="The fixture may have been removed.")
        if not can_manage_match(user, match):
            return render(request, db, "error.html", status_code=403, title="Match unavailable", message="You cannot manage this fixture.")
        return render(request, db, "score_form.html", status_code=422, match=match, error=error_text(exc))
    flash(request, "Result saved. Standings are up to date.")
    return RedirectResponse(f"/dashboard/matches/{match.id}/goals", status_code=303)


@router.get("/dashboard/matches/{match_id}/goals", response_class=HTMLResponse)
def match_goals_page(match_id: int, request: Request, db: db_dependency):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    match = db.get(Match, match_id)
    if not match or not can_manage_match(user, match):
        return render(
            request,
            db,
            "error.html",
            status_code=403 if match else 404,
            title="Match unavailable",
            message="You cannot manage this fixture.",
        )
    if match.status != "completed":
        flash(request, "Record the final score before adding scorers and assists.", "error")
        return RedirectResponse(f"/dashboard/matches/{match.id}/score", status_code=303)
    return render(
        request,
        db,
        "goal_events.html",
        match=match,
        events=match.goal_events,
        home_players=sorted(match.home_team.players, key=lambda player: (player.jersey_number or 100, player.name)),
        away_players=sorted(match.away_team.players, key=lambda player: (player.jersey_number or 100, player.name)),
        error=None,
    )


@router.post("/dashboard/matches/{match_id}/goals")
def match_goals_submit(
    match_id: int,
    request: Request,
    db: db_dependency,
    scorer_id: int = Form(...),
    assist_player_id: str = Form(""),
    minute: int = Form(...),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    try:
        api_create_goal_event(
            match_id,
            GoalEventCreate(
                scorer_id=scorer_id,
                assist_player_id=int(assist_player_id) if assist_player_id else None,
                minute=minute,
            ),
            db,
            user,
        )
        flash(request, "Goal scorer and assist saved.")
    except (ValidationError, HTTPException, ValueError) as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/matches/{match_id}/goals", status_code=303)


@router.post("/dashboard/matches/{match_id}/goals/{goal_event_id}/delete")
def match_goal_delete_submit(
    match_id: int,
    goal_event_id: int,
    request: Request,
    db: db_dependency,
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    try:
        api_delete_goal_event(match_id, goal_event_id, db, user)
        flash(request, "Goal detail removed.")
    except HTTPException as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(f"/dashboard/matches/{match_id}/goals", status_code=303)


@router.post("/dashboard/matches/{match_id}/withdraw")
def match_withdraw_submit(
    match_id: int,
    request: Request,
    db: db_dependency,
    expected_version: int = Form(...),
    reason: str = Form(...),
    csrf_token: str = Form(...),
):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    match = db.get(Match, match_id)
    destination = f"/dashboard/tournaments/{match.tournament_id}/edit" if match else "/dashboard"
    try:
        api_withdraw_result(match_id, MatchResultWithdraw(expected_version=expected_version, reason=reason.strip()), db, user)
        flash(request, "Result withdrawn. The match is scheduled again.")
    except (ValidationError, HTTPException) as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(destination, status_code=303)


@router.post("/dashboard/matches/{match_id}/delete")
def match_delete_submit(match_id: int, request: Request, db: db_dependency, csrf_token: str = Form(...)):
    user = require_user(request, db, admin=True)
    if not isinstance(user, User):
        return user
    verify_csrf(request, csrf_token)
    match = db.get(Match, match_id)
    destination = f"/dashboard/tournaments/{match.tournament_id}/edit" if match else "/dashboard"
    try:
        api_delete_match(match_id, db, user)
        flash(request, "Fixture removed.")
    except HTTPException as exc:
        flash(request, error_text(exc), "error")
    return RedirectResponse(destination, status_code=303)
