"""Create authentication, team, and match tables.

Revision ID: 0001_teams_matches
Revises:
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_teams_matches"
down_revision = None
branch_labels = None
depends_on = None


user_role = sa.Enum("organizer", "manager", name="user_role")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_role", user_role, nullable=False),
        sa.UniqueConstraint("username"), sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.Date(), nullable=True), sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("win_points", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("draw_points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("loss_points", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_tournaments_status"),
        sa.CheckConstraint("win_points >= 0 AND draw_points >= 0 AND loss_points >= 0", name="ck_tournaments_points"),
        sa.CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_tournaments_dates"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tournaments_created_by_id", "tournaments", ["created_by_id"])
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"])
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False), sa.Column("logo_url", sa.String(length=500)),
        sa.Column("contact_info", sa.String(length=255)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tournament_id", "name", name="uq_team_name_per_tournament"),
    )
    op.create_index("ix_teams_tournament_id", "teams", ["tournament_id"])
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("jersey_number", sa.Integer()), sa.Column("position", sa.String(length=3)),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.CheckConstraint("jersey_number IS NULL OR jersey_number BETWEEN 1 AND 99", name="ck_players_jersey"),
        sa.CheckConstraint("position IS NULL OR position IN ('GK', 'DEF', 'MID', 'FWD')", name="ck_players_position"),
        sa.UniqueConstraint("team_id", "jersey_number", name="uq_player_jersey_per_team"),
    )
    op.create_index("ix_players_team_id", "players", ["team_id"])
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False), sa.Column("venue", sa.String(length=150)),
        sa.Column("home_score", sa.Integer()), sa.Column("away_score", sa.Integer()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("home_team_id <> away_team_id", name="ck_matches_different_teams"),
        sa.CheckConstraint("status IN ('scheduled', 'postponed', 'completed', 'cancelled')", name="ck_matches_status"),
        sa.CheckConstraint("home_score IS NULL OR home_score >= 0", name="ck_matches_home_score"),
        sa.CheckConstraint("away_score IS NULL OR away_score >= 0", name="ck_matches_away_score"),
        sa.CheckConstraint("(status = 'completed' AND home_score IS NOT NULL AND away_score IS NOT NULL) OR (status <> 'completed' AND home_score IS NULL AND away_score IS NULL)", name="ck_matches_score_status"),
    )
    op.create_index("ix_matches_tournament_id", "matches", ["tournament_id"])
    op.create_index("ix_matches_home_team_id", "matches", ["home_team_id"])
    op.create_index("ix_matches_away_team_id", "matches", ["away_team_id"])
    op.create_index("ix_matches_match_date", "matches", ["match_date"])
    op.create_table(
        "match_result_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("previous_home_score", sa.Integer()), sa.Column("previous_away_score", sa.Integer()),
        sa.Column("new_home_score", sa.Integer()), sa.Column("new_away_score", sa.Integer()),
        sa.Column("reason", sa.String(length=255)), sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_match_result_revisions_match_id", "match_result_revisions", ["match_id"])
    op.create_table(
        "match_goal_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scorer_id", sa.Integer(), sa.ForeignKey("players.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assist_player_id", sa.Integer(), sa.ForeignKey("players.id", ondelete="RESTRICT")),
        sa.Column("minute", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("minute BETWEEN 1 AND 120", name="ck_match_goal_events_minute"),
        sa.CheckConstraint("assist_player_id IS NULL OR assist_player_id <> scorer_id", name="ck_match_goal_events_different_players"),
    )
    op.create_index("ix_match_goal_events_match_id", "match_goal_events", ["match_id"])
    op.create_index("ix_match_goal_events_team_id", "match_goal_events", ["team_id"])
    op.create_index("ix_match_goal_events_scorer_id", "match_goal_events", ["scorer_id"])
    op.create_index("ix_match_goal_events_assist_player_id", "match_goal_events", ["assist_player_id"])


def downgrade() -> None:
    op.drop_table("match_goal_events")
    op.drop_table("match_result_revisions")
    op.drop_table("matches")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("tournaments")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
