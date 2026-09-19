# REST endpoints for creating and reading reports.
# Update and delete operations are intentionally absent from this prototype.
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Report
from app.db.session import get_db_session
from app.schemas import ReportResponse
from app.services import CsvValidationError, summarize_csv

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    file: UploadFile = File(...),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Report:
    """Validate an uploaded CSV, calculate metrics, and persist a new report."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        summary = summarize_csv(await file.read())
    except CsvValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    report = Report(filename=file.filename, **summary.__dict__)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[Report]:
    """Return all stored reports with newest reports first."""
    result = await session.execute(select(Report).order_by(Report.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Report:
    """Return one report by identifier or raise a not-found response."""
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report