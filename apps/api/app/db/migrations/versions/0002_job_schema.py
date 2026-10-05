"""Add job and job_matches tables (Phase 2 — Job Intelligence)

Revision ID: 0002_job_schema
Revises: 0001_initial_schema
Create Date: 2026-10-01

Note: SQLite integration tests use Base.metadata.create_all, so the ORM
models fully define the schema there. This migration handles PostgreSQL
production deployments.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_job_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── jobs ─────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_job_id", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("company", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("remote_type", sa.String(length=50), nullable=True),
        sa.Column("employment_type", sa.String(length=50), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=10), nullable=True),
        sa.Column("salary_period", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("mandatory_skills", sa.Text(), nullable=True),
        sa.Column("preferred_skills", sa.Text(), nullable=True),
        sa.Column("education_requirements", sa.Text(), nullable=True),
        sa.Column("experience_requirements", sa.Text(), nullable=True),
        sa.Column("certifications", sa.Text(), nullable=True),
        sa.Column("work_authorization_required", sa.Boolean(), nullable=True),
        sa.Column("sponsorship_required", sa.Boolean(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized", sa.Boolean(), nullable=False),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_source_job_id", "jobs", ["source_job_id"])
    op.create_index("ix_jobs_source_url", "jobs", ["source_url"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index("ix_jobs_freshness_status", "jobs", ["freshness_status"])
    op.create_index("ix_jobs_content_hash", "jobs", ["content_hash"])
    op.create_index("ix_jobs_deleted_at", "jobs", ["deleted_at"])

    # ── job_matches ───────────────────────────────────────────────────────────
    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("eligible", sa.String(length=20), nullable=False),
        sa.Column("hard_constraints_passed", sa.Boolean(), nullable=False),
        sa.Column("hard_constraints_failed", sa.Text(), nullable=True),
        sa.Column("skill_match_score", sa.Float(), nullable=True),
        sa.Column("semantic_similarity", sa.Float(), nullable=True),
        sa.Column("matched_requirements", sa.Text(), nullable=True),
        sa.Column("missing_requirements", sa.Text(), nullable=True),
        sa.Column("skill_gaps", sa.Text(), nullable=True),
        sa.Column("representation_gaps", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate_match"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_candidate_id", "job_matches", ["candidate_id"])
    op.create_index("ix_job_matches_eligible", "job_matches", ["eligible"])


def downgrade() -> None:
    op.drop_table("job_matches")
    op.drop_table("jobs")
