"""Signal ingestion, quality validation, and record versioning service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import NormalizedRecord
from app.models.signal import (
    DataSource,
    IngestionError,
    IngestionRun,
    IngestionStatus,
    LocationBasis,
    LocationConfidence,
    SignalFamily,
    SignalRecord,
    SignalRecordVersion,
)


class IngestionService:
    """
    Validates, ingests, and versions incoming aggregate signal data.
    Ensures idempotency, transactional consistency, and rejection of invalid data contracts.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_ingestion(
        self,
        tenant_id: uuid.UUID,
        source: DataSource,
        records: List[NormalizedRecord],
        idempotency_key: str,
    ) -> IngestionRun:
        # Check idempotency
        existing_run_res = await self.session.execute(
            select(IngestionRun).where(IngestionRun.idempotency_key == idempotency_key)
        )
        existing_run = existing_run_res.scalar_one_or_none()
        if existing_run:
            return existing_run

        run = IngestionRun(
            tenant_id=tenant_id,
            source_id=source.id,
            status=IngestionStatus.VALIDATING,
            records_received=len(records),
            records_accepted=0,
            records_rejected=0,
            records_quarantined=0,
            started_at=datetime.now(timezone.utc),
            idempotency_key=idempotency_key,
        )
        self.session.add(run)
        await self.session.flush()

        accepted_count = 0
        rejected_count = 0
        errors: List[IngestionError] = []

        now = datetime.now(timezone.utc)

        for idx, rec in enumerate(records):
            # Quality and Contract Validation
            is_valid, error_msg, field = self.validate_record(rec)
            if not is_valid:
                rejected_count += 1
                errors.append(
                    IngestionError(
                        run_id=run.id,
                        record_index=idx,
                        field_name=field,
                        error_type="CONTRACT_VIOLATION",
                        error_message=error_msg or "Unknown error",
                        raw_value=str(rec.value),
                    )
                )
                continue

            # Check if this source_record_id already exists (for versioning)
            existing_rec_res = await self.session.execute(
                select(SignalRecord).where(
                    SignalRecord.tenant_id == tenant_id,
                    SignalRecord.source_id == source.id,
                    SignalRecord.source_record_id == rec.source_record_id,
                    SignalRecord.is_current == True,  # noqa: E712
                )
            )
            existing_rec = existing_rec_res.scalar_one_or_none()

            geo_uuid = uuid.UUID(rec.geography_id) if rec.geography_id else None
            work_uuid = uuid.UUID(rec.workplace_id) if rec.workplace_id else None

            if existing_rec:
                # If value is unchanged, skip duplicate
                if existing_rec.value == Decimal(str(rec.value)):
                    continue

                # Create version record
                version_entry = SignalRecordVersion(
                    signal_record_id=existing_rec.id,
                    record_version=existing_rec.record_version,
                    value=existing_rec.value,
                    unit=existing_rec.unit,
                    numerator=existing_rec.numerator,
                    denominator=existing_rec.denominator,
                    quality_flags=existing_rec.quality_flags,
                    change_reason="Source revision ingested",
                )
                self.session.add(version_entry)

                # Update current record
                existing_rec.record_version += 1
                existing_rec.value = Decimal(str(rec.value))
                existing_rec.numerator = Decimal(str(rec.numerator)) if rec.numerator is not None else None
                existing_rec.denominator = Decimal(str(rec.denominator)) if rec.denominator is not None else None
                existing_rec.revised_at = now
                existing_rec.quality_flags = rec.quality_flags
            else:
                # Insert new signal record
                sig_record = SignalRecord(
                    tenant_id=tenant_id,
                    source_id=source.id,
                    source_record_id=rec.source_record_id,
                    record_version=1,
                    schema_version=source.schema_version,
                    signal_family=source.signal_family,
                    metric_code=rec.metric_code,
                    value=Decimal(str(rec.value)),
                    unit=rec.unit,
                    numerator=Decimal(str(rec.numerator)) if rec.numerator is not None else None,
                    denominator=Decimal(str(rec.denominator)) if rec.denominator is not None else None,
                    denominator_unit=rec.denominator_unit,
                    contributor_count=rec.contributor_count,
                    contributor_definition=rec.contributor_definition,
                    period_start=rec.period_start,
                    period_end=rec.period_end,
                    observed_at=rec.observed_at,
                    source_available_at=rec.source_available_at,
                    ingested_at=now,
                    geography_id=geo_uuid,
                    workplace_id=work_uuid,
                    location_basis=rec.location_basis if hasattr(LocationBasis, rec.location_basis.upper()) else LocationBasis.UNKNOWN,
                    location_confidence=rec.location_confidence if hasattr(LocationConfidence, rec.location_confidence.upper()) else LocationConfidence.UNKNOWN,
                    data_label=rec.data_label,
                    quality_flags=rec.quality_flags,
                    completeness=Decimal(str(rec.completeness)) if rec.completeness is not None else Decimal("1.0"),
                    provenance=rec.provenance,
                    is_current=True,
                )
                self.session.add(sig_record)

            accepted_count += 1

        if errors:
            self.session.add_all(errors)

        # Update run status
        run.records_accepted = accepted_count
        run.records_rejected = rejected_count
        run.completed_at = datetime.now(timezone.utc)
        if rejected_count == 0:
            run.status = IngestionStatus.ACCEPTED
        elif accepted_count > 0:
            run.status = IngestionStatus.PARTIAL
            run.error_summary = f"{rejected_count} records failed validation"
        else:
            run.status = IngestionStatus.REJECTED
            run.error_summary = "All records failed validation"

        await self.session.commit()
        return run

    @staticmethod
    def validate_record(rec: NormalizedRecord) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates contract rules on a normalized record."""
        # 1. Period start <= period end
        if rec.period_start > rec.period_end:
            return False, "period_start cannot be after period_end", "period_start"

        # 2. Denominator check: non-zero
        if rec.denominator is not None and rec.denominator <= 0:
            return False, "denominator must be strictly positive", "denominator"

        # 3. Value check: finite
        if rec.value is None or rec.value != rec.value:  # NaN check
            return False, "value must be a valid finite number", "value"

        # 4. Numerator / Denominator unit compatibility
        if rec.numerator is not None and rec.denominator is None:
            return False, "numerator provided without required denominator", "denominator"

        return True, None, None

