"""Ingestion upload and job status API routes."""

import io
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.connectors.base import NormalizedRecord
from app.db.session import get_db
from app.ingestion.service import IngestionService
from app.models.signal import DataSource, IngestionRun
from app.schemas.auth import UserInfo
from app.schemas.signal import IngestionRunRead

router = APIRouter(prefix="/ingestions", tags=["ingestion"])


@router.post("/upload", response_model=IngestionRunRead, dependencies=[Depends(require_role(["data_steward", "platform_admin"]))])
async def upload_ingestion_file(
    source_id: uuid.UUID = Form(...),
    idempotency_key: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Processes an uploaded aggregate CSV file through validation and ingestion."""
    # Find source
    src_res = await db.execute(
        select(DataSource).where(
            DataSource.id == source_id,
            DataSource.tenant_id == current_user.current_tenant_id,
        )
    )
    source = src_res.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CSV file format: {str(e)}")

    # Convert dataframe rows to NormalizedRecord objects
    records = []
    for idx, row in df.iterrows():
        p_start = pd.to_datetime(row["period_start"]).to_pydatetime()
        p_end = pd.to_datetime(row["period_end"]).to_pydatetime()
        obs_at = pd.to_datetime(row.get("observed_at", row["period_end"])).to_pydatetime()
        src_avail = pd.to_datetime(row.get("source_available_at", obs_at)).to_pydatetime()

        rec = NormalizedRecord(
            source_record_id=str(row.get("source_record_id", f"up_{idx}")),
            metric_code=str(row.get("metric_code", source.code)),
            signal_family=source.signal_family.value,
            value=float(row["value"]),
            unit=str(row["unit"]),
            numerator=float(row["numerator"]) if pd.notna(row.get("numerator")) else None,
            denominator=float(row["denominator"]) if pd.notna(row.get("denominator")) else None,
            denominator_unit=str(row["denominator_unit"]) if pd.notna(row.get("denominator_unit")) else None,
            contributor_count=int(row["contributor_count"]) if pd.notna(row.get("contributor_count")) else None,
            contributor_definition=str(row.get("contributor_definition", "encounters")),
            period_start=p_start,
            period_end=p_end,
            observed_at=obs_at,
            source_available_at=src_avail,
            geography_id=str(row["geography_id"]) if pd.notna(row.get("geography_id")) else None,
            workplace_id=str(row["workplace_id"]) if pd.notna(row.get("workplace_id")) else None,
            location_basis=str(row.get("location_basis", "workplace")),
            location_confidence=str(row.get("location_confidence", "exact")),
            data_label=str(row.get("data_label", "synthetic")),
            provenance="file_upload",
        )
        records.append(rec)

    service = IngestionService(db)
    run = await service.run_ingestion(
        tenant_id=current_user.current_tenant_id,
        source=source,
        records=records,
        idempotency_key=idempotency_key,
    )
    return run


@router.get("/{run_id}", response_model=IngestionRunRead)
async def get_ingestion_run(
    run_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves ingestion run details, accepted/rejected counts, and error summaries."""
    query = select(IngestionRun).where(
        IngestionRun.id == run_id,
        IngestionRun.tenant_id == current_user.current_tenant_id,
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion run not found")
    return run

