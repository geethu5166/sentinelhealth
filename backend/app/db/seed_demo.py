"""Synthetic demonstration database seeder.

Populates SentinelHealth with two cleanly isolated tenants:
1. district_health_authority: District clinical surveillance & regional environmental context
2. greenfield_industries: Workplace sickness absence, safety incidents, and plant micro-climate context

All generated data is explicitly synthetic for demonstration purposes only.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

# Set demo mode for local development/seeding
os.environ.setdefault("SENTINEL_ENVIRONMENT", "local")
os.environ["SENTINEL_DEMO_MODE"] = "true"

from app.core.config import settings
from app.db.base import Base
from app.db.session import async_session_factory, engine
from app.models.alert import (
    Alert,
    AlertEvidence,
    AlertSeverity,
    AlertStateEvent,
    AlertStatus,
    EvidenceClass,
    Hazard,
)
from app.models.geography import Geography, GeographyLevel, Workplace
from app.models.playbook import (
    Playbook,
    PlaybookApprovalStatus,
    PreventiveTask,
    Recommendation,
    TaskStatus,
)
from app.models.privacy import PrivacyPolicy
from app.models.signal import (
    DataSource,
    LocationBasis,
    LocationConfidence,
    SignalFamily,
    SignalRecord,
    SourceType,
)
from app.models.tenant import Membership, MembershipRole, Tenant, User


async def seed_demo():
    print("[*] Starting SentinelHealth demonstration seeder...")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        mig_engine = create_async_engine(settings.MIGRATION_DATABASE_URL)
        async with mig_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        seed_factory = async_sessionmaker(bind=mig_engine, class_=AsyncSession, expire_on_commit=False)
    except Exception as exc:
        print("[!] mig_engine failed:", type(exc).__name__, exc)
        mig_engine = None
        seed_factory = async_session_factory

    async with seed_factory() as session:
        # 1. Tenants (Clean separation of public health vs occupational health)
        res = await session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
        dha_tenant = res.scalar_one_or_none()
        if not dha_tenant:
            dha_tenant = Tenant(
                name="Dhanpur District Health Authority",
                slug="district_health_authority",
                display_name="District Health Authority (Public Surveillance)",
                is_active=True,
            )
            session.add(dha_tenant)

        res2 = await session.execute(select(Tenant).where(Tenant.slug == "greenfield_industries"))
        gfi_tenant = res2.scalar_one_or_none()
        if not gfi_tenant:
            gfi_tenant = Tenant(
                name="Greenfield Heavy Industries",
                slug="greenfield_industries",
                display_name="Greenfield Industries (Workplace Health & Safety)",
                is_active=True,
            )
            session.add(gfi_tenant)

        await session.flush()
        print(f"  + Tenant A: {dha_tenant.name} ({dha_tenant.id})")
        print(f"  + Tenant B: {gfi_tenant.name} ({gfi_tenant.id})")

        # 2. Users and Memberships
        users_data = [
            # Public Health Tenant Users
            {
                "email": "analyst@demo.local",
                "name": "Dr. Aisha Rao",
                "role": MembershipRole.PUBLIC_HEALTH_ANALYST,
                "sub": "demo-sub-analyst",
                "tenant": dha_tenant,
            },
            {
                "email": "privacy@demo.local",
                "name": "Siddharth Verma",
                "role": MembershipRole.PRIVACY_OFFICER,
                "sub": "demo-sub-privacy",
                "tenant": dha_tenant,
            },
            # Greenfield Occupational Health Users
            {
                "email": "safety@greenfield.local",
                "name": "Vikram Patel",
                "role": MembershipRole.WORKPLACE_SAFETY_MANAGER,
                "sub": "demo-sub-safety",
                "tenant": gfi_tenant,
            },
            {
                "email": "occhealth@greenfield.local",
                "name": "Nurse Sunita Deshmukh",
                "role": MembershipRole.OCCUPATIONAL_HEALTH_ANALYST,
                "sub": "demo-sub-occhealth",
                "tenant": gfi_tenant,
            },
        ]

        for ud in users_data:
            res_u = await session.execute(select(User).where(User.email == ud["email"]))
            u = res_u.scalar_one_or_none()
            if not u:
                u = User(email=ud["email"], display_name=ud["name"], external_id=ud["sub"], is_active=True)
                session.add(u)
                await session.flush()

            mem_res = await session.execute(
                select(Membership).where(Membership.user_id == u.id, Membership.tenant_id == ud["tenant"].id)
            )
            if not mem_res.scalar_one_or_none():
                mem = Membership(user_id=u.id, tenant_id=ud["tenant"].id, role=ud["role"], is_active=True)
                session.add(mem)

            print(f"  + User: {ud['email']} -> {ud['tenant'].name} ({ud['role'].value})")

        # 3. Geographies
        # Tenant A: District hierarchy
        res_g = await session.execute(select(Geography).where(Geography.code == "DIST-DHANPUR", Geography.tenant_id == dha_tenant.id))
        dhanpur_geo = res_g.scalar_one_or_none()
        if not dhanpur_geo:
            dhanpur_geo = Geography(
                tenant_id=dha_tenant.id,
                code="DIST-DHANPUR",
                name="Dhanpur District",
                level=GeographyLevel.DISTRICT,
                population_estimate=850000,
                population_year=2024,
                is_active=True,
            )
            session.add(dhanpur_geo)
            await session.flush()

        # Tenant B: Industrial Zone Geography
        res_gb = await session.execute(select(Geography).where(Geography.code == "ZONE-LAKSHMI", Geography.tenant_id == gfi_tenant.id))
        lakshmi_zone = res_gb.scalar_one_or_none()
        if not lakshmi_zone:
            lakshmi_zone = Geography(
                tenant_id=gfi_tenant.id,
                code="ZONE-LAKSHMI",
                name="Lakshmi Industrial Zone",
                level=GeographyLevel.SUB_DISTRICT,
                population_estimate=45000,
                population_year=2024,
                is_active=True,
            )
            session.add(lakshmi_zone)
            await session.flush()

        # 4. Workplaces (Only Tenant B owns industrial workplace sites)
        res_w = await session.execute(select(Workplace).where(Workplace.code == "SITE-STEEL-01", Workplace.tenant_id == gfi_tenant.id))
        steel_workplace = res_w.scalar_one_or_none()
        if not steel_workplace:
            steel_workplace = Workplace(
                tenant_id=gfi_tenant.id,
                code="SITE-STEEL-01",
                name="Lakshmi Steel Works - Furnace & Fabrication",
                site_type="heavy_industrial",
                geography_id=lakshmi_zone.id,
                worker_count_estimate=3400,
                is_active=True,
            )
            session.add(steel_workplace)
            await session.flush()

        # Small workplace site for suppression demonstration
        res_w_small = await session.execute(select(Workplace).where(Workplace.code == "SITE-SUBSTATION-02", Workplace.tenant_id == gfi_tenant.id))
        small_workplace = res_w_small.scalar_one_or_none()
        if not small_workplace:
            small_workplace = Workplace(
                tenant_id=gfi_tenant.id,
                code="SITE-SUBSTATION-02",
                name="Electrical Substation 4 (Restricted Site)",
                site_type="infrastructure",
                geography_id=lakshmi_zone.id,
                worker_count_estimate=6,  # Under 10 contributors threshold!
                is_active=True,
            )
            session.add(small_workplace)
            await session.flush()

        print(f"  + Workplaces created for Tenant B: {steel_workplace.name}, {small_workplace.name}")

        # 5. Data Sources (Cleanly isolated per tenant)
        # Tenant A: Environmental + District Clinical Hospital Network
        dha_sources = {
            "ENV-REGIONAL-WEATHER": DataSource(
                tenant_id=dha_tenant.id,
                code="ENV-REGIONAL-WEATHER",
                name="Regional Weather & Heat Index Feed",
                signal_family=SignalFamily.ENVIRONMENTAL,
                source_type=SourceType.CONNECTOR,
                provider="Open-Meteo / IMD Regional Model",
                schema_version="1.0.0",
                expected_cadence_minutes=60,
                freshness_threshold_minutes=180,
                is_active=True,
            ),
            "CLIN-DISTRICT-HEAT": DataSource(
                tenant_id=dha_tenant.id,
                code="CLIN-DISTRICT-HEAT",
                name="District Emergency Heat Contacts",
                signal_family=SignalFamily.CLINICAL_SERVICE,
                source_type=SourceType.FILE_UPLOAD,
                provider="Dhanpur Hospital Network",
                schema_version="1.0.0",
                expected_cadence_minutes=1440,
                freshness_threshold_minutes=2880,
                is_active=True,
            ),
        }
        for code, src in dha_sources.items():
            res_s = await session.execute(select(DataSource).where(DataSource.code == code, DataSource.tenant_id == dha_tenant.id))
            if not res_s.scalar_one_or_none():
                session.add(src)
                await session.flush()

        # Tenant B: Local Weather + Workplace Absence + Workplace First Aid Incident Reports
        gfi_sources = {
            "ENV-PLANT-WEATHER": DataSource(
                tenant_id=gfi_tenant.id,
                code="ENV-PLANT-WEATHER",
                name="Plant Weather Station (WBGT)",
                signal_family=SignalFamily.ENVIRONMENTAL,
                source_type=SourceType.CONNECTOR,
                provider="On-site Davis WBGT Sensor",
                schema_version="1.0.0",
                expected_cadence_minutes=15,
                freshness_threshold_minutes=60,
                is_active=True,
            ),
            "WORK-ABSENCE-STEEL": DataSource(
                tenant_id=gfi_tenant.id,
                code="WORK-ABSENCE-STEEL",
                name="Lakshmi Steel Shift Sickness Absence",
                signal_family=SignalFamily.WORKFORCE,
                source_type=SourceType.FILE_UPLOAD,
                provider="Greenfield HR/EHS Shift Portal",
                schema_version="1.0.0",
                expected_cadence_minutes=1440,
                freshness_threshold_minutes=2880,
                is_active=True,
            ),
            "WORK-SAFETY-INCIDENTS": DataSource(
                tenant_id=gfi_tenant.id,
                code="WORK-SAFETY-INCIDENTS",
                name="Workplace First-Aid & Heat Incidents",
                signal_family=SignalFamily.WORKPLACE_SAFETY,
                source_type=SourceType.FILE_UPLOAD,
                provider="Plant Occupational Health Clinic",
                schema_version="1.0.0",
                expected_cadence_minutes=1440,
                freshness_threshold_minutes=2880,
                is_active=True,
            ),
        }
        for code, src in gfi_sources.items():
            res_s = await session.execute(select(DataSource).where(DataSource.code == code, DataSource.tenant_id == gfi_tenant.id))
            if not res_s.scalar_one_or_none():
                session.add(src)
                await session.flush()

        print("  + Data Sources successfully created and isolated per tenant")

        # 6. Playbooks (Isolated per tenant)
        # Playbook for Tenant A (District Public Health Warning)
        res_pb_a = await session.execute(select(Playbook).where(Playbook.tenant_id == dha_tenant.id, Playbook.hazard == "heat_illness"))
        pb_a = res_pb_a.scalar_one_or_none()
        if not pb_a:
            pb_a = Playbook(
                tenant_id=dha_tenant.id,
                hazard="heat_illness",
                jurisdiction="district_public_health",
                sector="community_health",
                version=1,
                approval_status=PlaybookApprovalStatus.APPROVED,
                source_link="https://www.who.int/heat-advisory",
                source_review_date=datetime.now(timezone.utc),
                action_tiers={
                    "tier_1_advisory": {
                        "title": "Public Health Advisory: Heat Warning",
                        "action": "Issue community hydration warnings and open district shaded cooling shelters.",
                        "accountable_role": "public_health_analyst",
                        "review_window_hours": 24,
                    }
                },
            )
            session.add(pb_a)

        # Playbook for Tenant B (Workplace Industrial Heat Safety Protocol)
        res_pb_b = await session.execute(select(Playbook).where(Playbook.tenant_id == gfi_tenant.id, Playbook.hazard == "heat_illness"))
        pb_b = res_pb_b.scalar_one_or_none()
        if not pb_b:
            pb_b = Playbook(
                tenant_id=gfi_tenant.id,
                hazard="heat_illness",
                jurisdiction="occupational_safety",
                sector="heavy_manufacturing",
                version=1,
                approval_status=PlaybookApprovalStatus.APPROVED,
                source_link="https://www.osha.gov/heat-exposure",
                source_review_date=datetime.now(timezone.utc),
                action_tiers={
                    "tier_2_adjusted_operations": {
                        "title": "Execute Heat Protocol: Work-Rest Cycles & Hydration Stations",
                        "action": "Implement mandatory 15-minute shaded rest per hour; provide chilled electrolyte drinks; suspend non-essential furnace tasks during peak hours (12:00-15:00).",
                        "accountable_role": "workplace_safety_manager",
                        "review_window_hours": 12,
                    }
                },
            )
            session.add(pb_b)

        await session.flush()
        print("  + Playbooks created for both tenants")

        # 7. Privacy Policies
        for t in [dha_tenant, gfi_tenant]:
            res_pp = await session.execute(select(PrivacyPolicy).where(PrivacyPolicy.tenant_id == t.id))
            if not res_pp.scalar_one_or_none():
                session.add(
                    PrivacyPolicy(
                        tenant_id=t.id,
                        policy_type="default",
                        version="0.1.0",
                        rules={
                            "min_contributors": 10,
                            "suppress_range_min": 1,
                            "suppress_range_max": 4,
                            "complementary_suppression": True,
                        },
                        is_active=True,
                    )
                )

        # 8. Seed Signals (30-day baseline + 3-day event)
        now = datetime.now(timezone.utc)
        print("  + Seeding isolated 30-day baseline and heat-event signals...")

        for day_offset in range(30, -1, -1):
            day_time = now - timedelta(days=day_offset)
            is_event_period = day_offset <= 3

            # --- TENANT A: Regional Weather (42.5C event vs 32C baseline) ---
            temp_val = 42.5 if is_event_period else 32.0 + (day_offset % 3) * 0.5
            session.add(
                SignalRecord(
                    tenant_id=dha_tenant.id,
                    source_id=dha_sources["ENV-REGIONAL-WEATHER"].id,
                    source_record_id=f"dha_weather_{day_time.strftime('%Y%m%d')}",
                    record_version=1,
                    schema_version="1.0.0",
                    signal_family=SignalFamily.ENVIRONMENTAL,
                    metric_code="apparent_temperature",
                    value=Decimal(str(temp_val)),
                    unit="celsius",
                    period_start=day_time.replace(hour=0, minute=0, second=0),
                    period_end=day_time.replace(hour=23, minute=59, second=59),
                    observed_at=day_time,
                    source_available_at=day_time,
                    geography_id=dhanpur_geo.id,
                    location_basis=LocationBasis.MODEL_GRID,
                    location_confidence=LocationConfidence.ESTIMATED,
                    data_label="synthetic",
                    is_current=True,
                )
            )

            # --- TENANT A: District Emergency Heat Contacts (38 event vs 12 baseline) ---
            clin_val = 38 if is_event_period else 12 + (day_offset % 4)
            session.add(
                SignalRecord(
                    tenant_id=dha_tenant.id,
                    source_id=dha_sources["CLIN-DISTRICT-HEAT"].id,
                    source_record_id=f"dha_clin_{day_time.strftime('%Y%m%d')}",
                    record_version=1,
                    schema_version="1.0.0",
                    signal_family=SignalFamily.CLINICAL_SERVICE,
                    metric_code="heat_exhaustion_contacts",
                    value=Decimal(str(clin_val)),
                    unit="encounters",
                    numerator=Decimal(str(clin_val)),
                    denominator=Decimal("1500"),
                    denominator_unit="total_hospital_encounters",
                    contributor_count=clin_val,
                    contributor_definition="unique_daily_patients",
                    period_start=day_time.replace(hour=0, minute=0, second=0),
                    period_end=day_time.replace(hour=23, minute=59, second=59),
                    observed_at=day_time,
                    source_available_at=day_time,
                    geography_id=dhanpur_geo.id,
                    location_basis=LocationBasis.FACILITY,
                    location_confidence=LocationConfidence.MAPPED,
                    data_label="synthetic",
                    is_current=True,
                )
            )

            # --- TENANT B: Plant Local WBGT (34.2C event vs 27.5C baseline) ---
            wbgt_val = 34.2 if is_event_period else 27.5 + (day_offset % 3) * 0.4
            session.add(
                SignalRecord(
                    tenant_id=gfi_tenant.id,
                    source_id=gfi_sources["ENV-PLANT-WEATHER"].id,
                    source_record_id=f"gfi_wbgt_{day_time.strftime('%Y%m%d')}",
                    record_version=1,
                    schema_version="1.0.0",
                    signal_family=SignalFamily.ENVIRONMENTAL,
                    metric_code="wet_bulb_globe_temperature",
                    value=Decimal(str(wbgt_val)),
                    unit="celsius",
                    period_start=day_time.replace(hour=0, minute=0, second=0),
                    period_end=day_time.replace(hour=23, minute=59, second=59),
                    observed_at=day_time,
                    source_available_at=day_time,
                    geography_id=lakshmi_zone.id,
                    workplace_id=steel_workplace.id,
                    location_basis=LocationBasis.WORKPLACE,
                    location_confidence=LocationConfidence.EXACT,
                    data_label="synthetic",
                    is_current=True,
                )
            )

            # --- TENANT B: Steel Works Sickness Absence (82 worker-days vs 24 baseline) ---
            work_val = 82 if is_event_period else 24 + (day_offset % 5)
            session.add(
                SignalRecord(
                    tenant_id=gfi_tenant.id,
                    source_id=gfi_sources["WORK-ABSENCE-STEEL"].id,
                    source_record_id=f"gfi_abs_{day_time.strftime('%Y%m%d')}",
                    record_version=1,
                    schema_version="1.0.0",
                    signal_family=SignalFamily.WORKFORCE,
                    metric_code="sickness_absence_worker_days",
                    value=Decimal(str(work_val)),
                    unit="worker_days",
                    numerator=Decimal(str(work_val)),
                    denominator=Decimal("3400"),
                    denominator_unit="scheduled_worker_days",
                    contributor_count=work_val,
                    contributor_definition="distinct_absent_workers",
                    period_start=day_time.replace(hour=0, minute=0, second=0),
                    period_end=day_time.replace(hour=23, minute=59, second=59),
                    observed_at=day_time,
                    source_available_at=day_time,
                    geography_id=lakshmi_zone.id,
                    workplace_id=steel_workplace.id,
                    location_basis=LocationBasis.WORKPLACE,
                    location_confidence=LocationConfidence.EXACT,
                    data_label="synthetic",
                    is_current=True,
                )
            )

            # --- TENANT B: Workplace First Aid Heat Incidents (7 incidents vs 0 baseline) ---
            incident_val = 7 if is_event_period else 0
            session.add(
                SignalRecord(
                    tenant_id=gfi_tenant.id,
                    source_id=gfi_sources["WORK-SAFETY-INCIDENTS"].id,
                    source_record_id=f"gfi_inc_{day_time.strftime('%Y%m%d')}",
                    record_version=1,
                    schema_version="1.0.0",
                    signal_family=SignalFamily.WORKPLACE_SAFETY,
                    metric_code="heat_first_aid_incidents",
                    value=Decimal(str(incident_val)),
                    unit="incidents",
                    numerator=Decimal(str(incident_val)),
                    denominator=Decimal("3400"),
                    denominator_unit="worker_shifts",
                    contributor_count=incident_val,
                    contributor_definition="injured_workers_treated",
                    period_start=day_time.replace(hour=0, minute=0, second=0),
                    period_end=day_time.replace(hour=23, minute=59, second=59),
                    observed_at=day_time,
                    source_available_at=day_time,
                    geography_id=lakshmi_zone.id,
                    workplace_id=steel_workplace.id,
                    location_basis=LocationBasis.WORKPLACE,
                    location_confidence=LocationConfidence.EXACT,
                    data_label="synthetic",
                    is_current=True,
                )
            )

        # 9. Create Active Demonstration Alerts (One per tenant)
        # Alert 1: Tenant A (District Public Health Warning)
        res_al_a = await session.execute(select(Alert).where(Alert.tenant_id == dha_tenant.id))
        if not res_al_a.scalar_one_or_none():
            alert_a = Alert(
                tenant_id=dha_tenant.id,
                hazard=Hazard.HEAT_ILLNESS,
                evidence_class=EvidenceClass.CORROBORATED_HEALTH_WARNING,
                severity=AlertSeverity.WARNING,
                status=AlertStatus.NEW,
                geography_id=dhanpur_geo.id,
                workplace_id=None,  # Public health alerts do not target private employers
                target_period_start=now - timedelta(days=2),
                target_period_end=now,
                first_detected_at=now - timedelta(hours=8),
                latest_revision_at=now,
                episode_key=f"{dha_tenant.id}:heat_illness:{dhanpur_geo.id}",
                episode_window_start=now - timedelta(days=2),
                episode_window_end=now + timedelta(days=1),
                responsible_role="public_health_analyst",
                evidence_score=Decimal("84.0"),
                evidence_score_components={
                    "reasons": [
                        "Regional apparent temperature (42.5°C) exceeded screening threshold (40.0°C).",
                        "District emergency heat contacts (38 visits) exceeded expected baseline (13.5 visits, z=3.8).",
                    ],
                    "contributing_families": ["environmental", "clinical_service"],
                },
                playbook_id=pb_a.id,
                privacy_policy_version="0.1.0",
            )
            session.add(alert_a)
            await session.flush()

            # Evidences for Tenant A
            session.add_all([
                AlertEvidence(
                    alert_id=alert_a.id,
                    signal_family="environmental",
                    metric_code="apparent_temperature",
                    observed_value=Decimal("42.5000"),
                    expected_value=Decimal("33.2000"),
                    excess=Decimal("9.3000"),
                    standardised_residual=Decimal("3.8000"),
                    ewma_value=Decimal("3.4000"),
                    source_freshness_minutes=30,
                    data_label="synthetic",
                    model_type="recent_history_weekday_matched",
                ),
                AlertEvidence(
                    alert_id=alert_a.id,
                    signal_family="clinical_service",
                    metric_code="heat_exhaustion_contacts",
                    observed_value=Decimal("38.0000"),
                    expected_value=Decimal("13.5000"),
                    excess=Decimal("24.5000"),
                    standardised_residual=Decimal("3.8000"),
                    ewma_value=Decimal("3.5000"),
                    denominator_value=Decimal("1500.0000"),
                    denominator_unit="total_hospital_encounters",
                    source_freshness_minutes=60,
                    data_label="synthetic",
                    model_type="poisson_glm",
                ),
            ])

        # Alert 2: Tenant B (Greenfield Industrial Heat Safety Escalation)
        res_al_b = await session.execute(select(Alert).where(Alert.tenant_id == gfi_tenant.id))
        if not res_al_b.scalar_one_or_none():
            alert_b = Alert(
                tenant_id=gfi_tenant.id,
                hazard=Hazard.HEAT_ILLNESS,
                evidence_class=EvidenceClass.SAFETY_ESCALATION,
                severity=AlertSeverity.WARNING,
                status=AlertStatus.NEW,
                geography_id=lakshmi_zone.id,
                workplace_id=steel_workplace.id,
                target_period_start=now - timedelta(days=2),
                target_period_end=now,
                first_detected_at=now - timedelta(hours=4),
                latest_revision_at=now,
                episode_key=f"{gfi_tenant.id}:heat_illness:{steel_workplace.id}",
                episode_window_start=now - timedelta(days=2),
                episode_window_end=now + timedelta(days=1),
                responsible_role="workplace_safety_manager",
                evidence_score=Decimal("88.5"),
                evidence_score_components={
                    "reasons": [
                        "On-site WBGT index (34.2°C) reached OSHA High Heat Safety Threshold (32.2°C).",
                        "Lakshmi Steel shift absence (82 worker-days) exceeded expected baseline (24.2 worker-days, z=4.1).",
                        "Plant first-aid logged 7 acute heat exhaustion/cramp treatments in heavy fabrication.",
                    ],
                    "contributing_families": ["environmental", "workforce", "workplace_safety"],
                },
                playbook_id=pb_b.id,
                privacy_policy_version="0.1.0",
            )
            session.add(alert_b)
            await session.flush()

            # Evidences for Tenant B
            session.add_all([
                AlertEvidence(
                    alert_id=alert_b.id,
                    signal_family="environmental",
                    metric_code="wet_bulb_globe_temperature",
                    observed_value=Decimal("34.2000"),
                    expected_value=Decimal("28.1000"),
                    excess=Decimal("6.1000"),
                    standardised_residual=Decimal("3.5000"),
                    ewma_value=Decimal("3.2000"),
                    source_freshness_minutes=15,
                    data_label="synthetic",
                    model_type="recent_history_weekday_matched",
                ),
                AlertEvidence(
                    alert_id=alert_b.id,
                    signal_family="workforce",
                    metric_code="sickness_absence_worker_days",
                    observed_value=Decimal("82.0000"),
                    expected_value=Decimal("24.2000"),
                    excess=Decimal("57.8000"),
                    standardised_residual=Decimal("4.1000"),
                    ewma_value=Decimal("3.9000"),
                    denominator_value=Decimal("3400.0000"),
                    denominator_unit="scheduled_worker_days",
                    source_freshness_minutes=45,
                    data_label="synthetic",
                    model_type="poisson_glm",
                ),
                AlertEvidence(
                    alert_id=alert_b.id,
                    signal_family="workplace_safety",
                    metric_code="heat_first_aid_incidents",
                    observed_value=Decimal("7.0000"),
                    expected_value=Decimal("0.5000"),
                    excess=Decimal("6.5000"),
                    standardised_residual=Decimal("4.5000"),
                    ewma_value=Decimal("4.2000"),
                    denominator_value=Decimal("3400.0000"),
                    denominator_unit="worker_shifts",
                    source_freshness_minutes=30,
                    data_label="synthetic",
                    model_type="poisson_glm",
                ),
            ])

            # Preventive Task for Tenant B Safety Manager
            rec_b = Recommendation(
                alert_id=alert_b.id,
                playbook_id=pb_b.id,
                playbook_version=pb_b.version,
                action_tier="tier_2_adjusted_operations",
                recommended_action="Implement mandatory 15-minute shaded rest per hour; provide chilled electrolyte drinks; suspend non-essential furnace tasks during peak hours (12:00-15:00).",
                accountable_role="workplace_safety_manager",
                approval_role="occupational_health_analyst",
                completion_evidence_required="Site inspection checklist confirming shaded rest breaks and hydration stations.",
                review_window_hours=12,
                assumptions={
                    "electrolyte_supplies_present": True,
                    "shaded_recovery_stations_active": True,
                    "nurse_station_staffed": True,
                },
            )
            session.add(rec_b)
            await session.flush()

            session.add(
                PreventiveTask(
                    tenant_id=gfi_tenant.id,
                    alert_id=alert_b.id,
                    recommendation_id=rec_b.id,
                    title="Implement Mandatory Shaded Rest Cycles & Hydration Stations (Lakshmi Steel)",
                    description=rec_b.recommended_action,
                    assigned_role="workplace_safety_manager",
                    status=TaskStatus.PENDING,
                    priority=2,
                    due_at=now + timedelta(hours=12),
                    approval_required=True,
                )
            )

        await session.commit()
        print("[+] Synthetic demonstration seed completed successfully with complete tenant isolation!")


if __name__ == "__main__":
    asyncio.run(seed_demo())
