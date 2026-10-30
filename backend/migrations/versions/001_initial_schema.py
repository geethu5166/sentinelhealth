"""Initial complete schema with extensions, PostGIS, tables, and RLS policies.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Tenants & Auth
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("settings", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("external_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_external_id", "users", ["external_id"])

    membership_role_enum = postgresql.ENUM(
        "public_health_analyst",
        "occupational_health_analyst",
        "workplace_safety_manager",
        "data_steward",
        "privacy_officer",
        "platform_admin",
        "regulator",
        name="membership_role",
        create_type=False,
    )
    membership_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", membership_role_enum, nullable=False),
        sa.Column("scopes", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", "role", name="uq_membership_user_tenant_role"),
    )
    op.create_index("ix_memberships_user_tenant", "memberships", ["user_id", "tenant_id"])

    op.create_table(
        "role_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(50), nullable=False),
        sa.Column("scope_value", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_role_scopes_membership", "role_scopes", ["membership_id"])

    # 3. Geographies
    geography_level_enum = postgresql.ENUM("district", "sub_district", "ward", "site", name="geography_level", create_type=False)
    geography_level_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "geographies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("level", geography_level_enum, nullable=False),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", nullable=True)),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("population_estimate", sa.Integer(), nullable=True),
        sa.Column("population_year", sa.Integer(), nullable=True),
        sa.Column("properties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_geography_tenant_code"),
    )
    op.create_index("ix_geographies_tenant_level", "geographies", ["tenant_id", "level"])

    op.create_table(
        "geography_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", nullable=True)),
        sa.Column("properties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "workplaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("site_type", sa.String(100), nullable=False),
        sa.Column("location", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", nullable=True)),
        sa.Column("address_text", sa.Text(), nullable=True),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("worker_count_estimate", sa.Integer(), nullable=True),
        sa.Column("worker_count_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("properties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_workplace_tenant_code"),
    )
    op.create_index("ix_workplaces_tenant", "workplaces", ["tenant_id"])

    op.create_table(
        "workplace_geography_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("workplace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workplaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("mapping_version", sa.String(50), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Data Sources & Signals
    signal_family_enum = postgresql.ENUM("environmental", "clinical_service", "workforce", "workplace_safety", "laboratory", name="signal_family", create_type=False)
    signal_family_enum.create(op.get_bind(), checkfirst=True)
    source_type_enum = postgresql.ENUM("connector", "file_upload", "api", name="source_type", create_type=False)
    source_type_enum.create(op.get_bind(), checkfirst=True)
    ingestion_status_enum = postgresql.ENUM("pending", "validating", "accepted", "partial", "rejected", "failed", name="ingestion_status", create_type=False)
    ingestion_status_enum.create(op.get_bind(), checkfirst=True)
    location_basis_enum = postgresql.ENUM("residence", "workplace", "exposure_site", "facility", "catchment", "model_grid", "unknown", name="location_basis", create_type=False)
    location_basis_enum.create(op.get_bind(), checkfirst=True)
    location_confidence_enum = postgresql.ENUM("exact", "mapped", "estimated", "unknown", name="location_confidence", create_type=False)
    location_confidence_enum.create(op.get_bind(), checkfirst=True)
    data_label_enum = postgresql.ENUM("real", "synthetic", "modelled", "observed", name="data_label", create_type=False)
    data_label_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("signal_family", signal_family_enum, nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("expected_cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("freshness_threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_data_source_tenant_code"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", ingestion_status_enum, server_default="pending", nullable=False),
        sa.Column("records_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_accepted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_quarantined", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ingestion_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("error_type", sa.String(100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "signal_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_record_id", sa.String(255), nullable=False),
        sa.Column("record_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("signal_family", signal_family_enum, nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("numerator", sa.Numeric(14, 4), nullable=True),
        sa.Column("denominator", sa.Numeric(14, 4), nullable=True),
        sa.Column("denominator_unit", sa.String(50), nullable=True),
        sa.Column("contributor_count", sa.Integer(), nullable=True),
        sa.Column("contributor_definition", sa.String(255), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("forecast_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lead_horizon_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("forecast_provider", sa.String(100), nullable=True),
        sa.Column("forecast_model", sa.String(100), nullable=True),
        sa.Column("native_temporal_resolution", sa.String(50), nullable=True),
        sa.Column("native_spatial_resolution", sa.String(50), nullable=True),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("workplace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workplaces.id"), nullable=True),
        sa.Column("location_basis", location_basis_enum, server_default="unknown", nullable=False),
        sa.Column("location_confidence", location_confidence_enum, server_default="unknown", nullable=False),
        sa.Column("mapping_version", sa.String(50), nullable=True),
        sa.Column("quality_flags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("completeness", sa.Numeric(5, 4), nullable=True),
        sa.Column("provenance", sa.String(255), nullable=True),
        sa.Column("data_label", data_label_enum, server_default="observed", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_signal_record_lookup", "signal_records", ["tenant_id", "source_id", "metric_code", "period_start"])
    op.create_index("ix_signal_record_geo", "signal_records", ["tenant_id", "geography_id", "period_start"])

    op.create_table(
        "signal_record_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("signal_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signal_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("numerator", sa.Numeric(14, 4), nullable=True),
        sa.Column("denominator", sa.Numeric(14, 4), nullable=True),
        sa.Column("quality_flags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("change_reason", sa.String(500), nullable=True),
    )

    # 5. Quality Snapshots
    op.create_table(
        "quality_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completeness_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("freshness_minutes", sa.Integer(), nullable=True),
        sa.Column("records_expected", sa.Integer(), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=True),
        sa.Column("invalid_count", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("issues", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. Analytics: Features, Baselines, Detection Runs
    op.create_table(
        "feature_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=False),
        sa.Column("workplace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workplaces.id"), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aggregation_method", sa.String(50), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("denominator", sa.Numeric(14, 4), nullable=True),
        sa.Column("rate", sa.Numeric(14, 6), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("contributor_count", sa.Integer(), nullable=True),
        sa.Column("data_label", sa.String(50), server_default="observed", nullable=False),
        sa.Column("quality_flags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_feature_windows_lookup", "feature_windows", ["tenant_id", "metric_code", "geography_id", "window_start"])

    baseline_model_type_enum = postgresql.ENUM("recent_history", "poisson", "negative_binomial", "binomial", name="baseline_model_type", create_type=False)
    baseline_model_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "baseline_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=True),
        sa.Column("model_type", baseline_model_type_enum, nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("fitting_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fitting_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_snapshot_hash", sa.String(128), nullable=True),
        sa.Column("diagnostics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("baseline_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("baseline_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("parameters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("diagnostics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("fitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    detection_run_type_enum = postgresql.ENUM("scheduled", "replay", "manual", name="detection_run_type", create_type=False)
    detection_run_type_enum.create(op.get_bind(), checkfirst=True)
    detection_run_status_enum = postgresql.ENUM("pending", "running", "completed", "failed", name="detection_run_status", create_type=False)
    detection_run_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "detection_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_type", detection_run_type_enum, nullable=False),
        sa.Column("status", detection_run_status_enum, server_default="pending", nullable=False),
        sa.Column("scoring_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inputs_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration_version", sa.String(50), nullable=False),
        sa.Column("results_summary", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. Playbooks & Recommendations
    playbook_status_enum = postgresql.ENUM("draft", "approved", "retired", name="playbook_approval_status", create_type=False)
    playbook_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "playbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("hazard", sa.String(100), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("evidence_requirements", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("contraindications", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("action_tiers", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("approval_status", playbook_status_enum, server_default="draft", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_link", sa.String(500), nullable=True),
        sa.Column("source_review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "playbook_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. Alerts & Evidence
    hazard_enum = postgresql.ENUM("heat_illness", "respiratory_air_quality", "infectious_disease", "workplace_safety", "data_quality", name="hazard", create_type=False)
    hazard_enum.create(op.get_bind(), checkfirst=True)
    evidence_class_enum = postgresql.ENUM("environmental_watch", "corroborated_health_warning", "uncorroborated_health_anomaly", "safety_escalation", "insufficient_data", "data_quality_issue", name="evidence_class", create_type=False)
    evidence_class_enum.create(op.get_bind(), checkfirst=True)
    alert_severity_enum = postgresql.ENUM("advisory", "watch", "warning", "critical", "emergency", name="alert_severity", create_type=False)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)
    alert_status_enum = postgresql.ENUM("new", "acknowledged", "investigating", "action_planned", "monitoring", "resolved", "dismissed_data_issue", "dismissed_not_actionable", "reopened", name="alert_status", create_type=False)
    alert_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hazard", hazard_enum, nullable=False),
        sa.Column("evidence_class", evidence_class_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("status", alert_status_enum, server_default="new", nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id"), nullable=False),
        sa.Column("workplace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workplaces.id"), nullable=True),
        sa.Column("target_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_revision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("episode_key", sa.String(255), nullable=True),
        sa.Column("episode_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("episode_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsible_role", sa.String(100), nullable=True),
        sa.Column("evidence_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("evidence_score_components", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("suppression_status", sa.String(50), nullable=True),
        sa.Column("suppression_reason", sa.String(500), nullable=True),
        sa.Column("suppression_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppressed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("detection_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("detection_runs.id"), nullable=True),
        sa.Column("baseline_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("baseline_models.id"), nullable=True),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("playbooks.id"), nullable=True),
        sa.Column("privacy_policy_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alert_tenant_hazard_status", "alerts", ["tenant_id", "hazard", "status"])
    op.create_index("ix_alert_tenant_episode", "alerts", ["tenant_id", "episode_key"])

    op.create_table(
        "alert_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_family", sa.String(100), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("observed_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("expected_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("excess", sa.Numeric(14, 4), nullable=True),
        sa.Column("rate_difference", sa.Numeric(14, 6), nullable=True),
        sa.Column("standardised_residual", sa.Numeric(10, 4), nullable=True),
        sa.Column("prediction_interval_lower", sa.Numeric(14, 4), nullable=True),
        sa.Column("prediction_interval_upper", sa.Numeric(14, 4), nullable=True),
        sa.Column("ewma_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("ewma_threshold", sa.Numeric(14, 4), nullable=True),
        sa.Column("baseline_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("baseline_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("native_temporal_resolution", sa.String(50), nullable=True),
        sa.Column("native_spatial_resolution", sa.String(50), nullable=True),
        sa.Column("source_freshness_minutes", sa.Integer(), nullable=True),
        sa.Column("completeness", sa.Numeric(5, 4), nullable=True),
        sa.Column("location_uncertainty", sa.String(100), nullable=True),
        sa.Column("denominator_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("denominator_unit", sa.String(50), nullable=True),
        sa.Column("data_label", sa.String(50), server_default="observed", nullable=False),
        sa.Column("model_type", sa.String(100), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("threshold_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "alert_state_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(50), nullable=True),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("event_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "alert_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 9. Recommendations & Preventive Tasks
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("playbooks.id"), nullable=True),
        sa.Column("playbook_version", sa.String(50), nullable=True),
        sa.Column("action_tier", sa.String(50), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("accountable_role", sa.String(100), nullable=False),
        sa.Column("approval_role", sa.String(100), nullable=True),
        sa.Column("completion_evidence_required", sa.String(500), nullable=True),
        sa.Column("review_window_hours", sa.Integer(), nullable=True),
        sa.Column("assumptions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    task_status_enum = postgresql.ENUM("pending", "accepted", "in_progress", "completed", "rejected", "overdue", name="task_status", create_type=False)
    task_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "preventive_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendations.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_role", sa.String(100), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", task_status_enum, server_default="pending", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_evidence", sa.Text(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("approval_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_tenant_status", "preventive_tasks", ["tenant_id", "status"])

    op.create_table(
        "task_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("preventive_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(50), nullable=True),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. Investigations & Outcomes
    op.create_table(
        "investigation_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("findings", sa.Text(), nullable=False),
        sa.Column("root_cause_category", sa.String(100), nullable=True),
        sa.Column("contributing_factors", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("is_final", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "outcome_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_type", sa.String(100), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("denominator", sa.Numeric(14, 4), nullable=True),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("data_label", sa.String(50), server_default="synthetic", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. Notifications
    notification_type_enum = postgresql.ENUM("alert_new", "alert_escalation", "task_assigned", "task_overdue", "task_reminder", "system", name="notification_type_enum", create_type=False)
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    notification_channel_enum = postgresql.ENUM("in_app", "email", name="notification_channel_enum", create_type=False)
    notification_channel_enum.create(op.get_bind(), checkfirst=True)
    notification_status_enum = postgresql.ENUM("pending", "sent", "failed", "expired", name="notification_status_enum", create_type=False)
    notification_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("preventive_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("recipient_role", sa.String(100), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", notification_channel_enum, server_default="in_app", nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_template", sa.String(100), nullable=False),
        sa.Column("body_params", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("status", notification_status_enum, server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notification_outbox.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", notification_channel_enum, nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 12. Privacy, Export & Audit
    disclosure_decision_status_enum = postgresql.ENUM("approved", "denied", "partial", name="disclosure_decision_status_enum", create_type=False)
    disclosure_decision_status_enum.create(op.get_bind(), checkfirst=True)
    export_job_status_enum = postgresql.ENUM("pending", "processing", "ready", "downloaded", "expired", "denied", name="export_job_status_enum", create_type=False)
    export_job_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "privacy_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_type", sa.String(50), server_default="default", nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("rules", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "disclosure_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_type", sa.String(100), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metric_codes", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("time_range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", disclosure_decision_status_enum, nullable=False),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("export_type", sa.String(50), nullable=False),
        sa.Column("parameters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("status", export_job_status_enum, server_default="pending", nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_hash", sa.String(128), nullable=True),
        sa.Column("privacy_policy_version", sa.String(50), nullable=False),
        sa.Column("disclosure_reviewed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_created", "audit_events", ["tenant_id", "created_at"])
    op.create_index("ix_audit_events_resource", "audit_events", ["resource_type", "resource_id"])

    # 13. Replay & Evaluation
    replay_status_enum = postgresql.ENUM("pending", "running", "completed", "failed", name="replay_status_enum", create_type=False)
    replay_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "replay_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hazard", sa.String(50), nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("reference_events", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("data_label", sa.String(50), server_default="synthetic", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "reference_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("replay_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hazard", sa.String(50), nullable=False),
        sa.Column("geography_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("onset_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("evidence_basis", sa.Text(), nullable=False),
        sa.Column("earliest_useful_action_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "replay_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("replay_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", replay_status_enum, server_default="pending", nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("results_summary", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("replay_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("replay_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("numerator", sa.Numeric(14, 4), nullable=True),
        sa.Column("denominator", sa.Numeric(14, 4), nullable=True),
        sa.Column("eligible_observation_time", sa.String(100), nullable=True),
        sa.Column("uncertainty_lower", sa.Numeric(14, 4), nullable=True),
        sa.Column("uncertainty_upper", sa.Numeric(14, 4), nullable=True),
        sa.Column("is_estimable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 14. Row-Level Security (RLS) setup
    rls_tables = [
        "signal_records",
        "alerts",
        "preventive_tasks",
        "geographies",
        "workplaces",
        "notification_outbox",
        "export_jobs",
        "audit_events",
        "feature_windows",
        "baseline_models",
        "detection_runs",
        "quality_snapshots",
    ]

    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            );
            """
        )

    # Protected domain alias views for observations & tasks
    op.execute("CREATE OR REPLACE VIEW observations WITH (security_invoker = true) AS SELECT * FROM signal_records;")
    op.execute("CREATE OR REPLACE VIEW tasks WITH (security_invoker = true) AS SELECT * FROM preventive_tasks;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sentinel_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON observations TO sentinel_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON tasks TO sentinel_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS tasks CASCADE;")
    op.execute("DROP VIEW IF EXISTS observations CASCADE;")
    tables = [
        "evaluation_results",
        "replay_runs",
        "reference_events",
        "replay_scenarios",
        "audit_events",
        "export_jobs",
        "disclosure_decisions",
        "privacy_policies",
        "notification_deliveries",
        "notification_outbox",
        "outcome_metrics",
        "investigation_reviews",
        "task_events",
        "preventive_tasks",
        "recommendations",
        "alert_relationships",
        "alert_state_events",
        "alert_evidences",
        "alerts",
        "playbook_versions",
        "playbooks",
        "detection_runs",
        "model_versions",
        "baseline_models",
        "feature_windows",
        "quality_snapshots",
        "signal_record_versions",
        "signal_records",
        "ingestion_errors",
        "ingestion_runs",
        "data_sources",
        "workplace_geography_links",
        "workplaces",
        "geography_versions",
        "geographies",
        "role_scopes",
        "memberships",
        "users",
        "tenants",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    enums = [
        "membership_role",
        "geography_level",
        "signal_family",
        "source_type",
        "ingestion_status",
        "location_basis",
        "location_confidence",
        "data_label",
        "baseline_model_type",
        "detection_run_type",
        "detection_run_status",
        "playbook_approval_status",
        "hazard",
        "evidence_class",
        "alert_severity",
        "alert_status",
        "task_status",
        "notification_type_enum",
        "notification_channel_enum",
        "notification_status_enum",
        "disclosure_decision_status_enum",
        "export_job_status_enum",
        "replay_status_enum",
    ]
    for enum_name in enums:
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE;")

