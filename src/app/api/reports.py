import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Report
from app.db.session import get_db_session
from app.schemas import ReportResponse
from app.services import summarize_csv

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    file: UploadFile = File(...),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Report:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        logger.warning("Rejected report upload with invalid filename: %s", file.filename)
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        summary = summarize_csv(await file.read())
    except (UnicodeDecodeError, ValueError) as error:
        logger.warning("Rejected invalid report CSV %s: %s", file.filename, error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    report = Report(filename=file.filename, **summary.__dict__)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    logger.info("Created report %s from %s", report.id, report.filename)
    return report


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[Report]:
    result = await session.execute(select(Report).order_by(Report.created_at.desc()))
    reports = list(result.scalars().all())
    logger.info("Listed %d reports", len(reports))
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        logger.warning("Report not found: %s", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    logger.info("Retrieved report %s", report_id)
    return report