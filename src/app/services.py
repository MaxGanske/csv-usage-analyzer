import csv
import io
import logging
import math
from dataclasses import dataclass

REQUIRED_HEADERS = {
    "request_id",
    "service",
    "status_code",
    "latency_ms",
    "tokens_used",
}
MIN_STATUS_CODE = 100
MAX_STATUS_CODE = 599
MAX_TOKENS_USED = 10_000
MAX_LATENCY_MS = 10_000
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportSummary:
    request_count: int
    total_tokens: int
    average_latency_ms: float
    successful_requests: int
    failed_requests: int


def summarize_csv(contents: bytes) -> ReportSummary:
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        logger.warning("Rejected non-UTF-8 CSV upload")
        raise ValueError("CSV file must be UTF-8 encoded") from error

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    if headers != REQUIRED_HEADERS:
        logger.warning("Rejected CSV with invalid headers")
        missing = sorted(REQUIRED_HEADERS - headers)
        unexpected = sorted(headers - REQUIRED_HEADERS)
        details = []
        if missing:
            details.append(f"missing headers: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected headers: {', '.join(unexpected)}")
        raise ValueError("Invalid CSV headers; " + "; ".join(details))

    request_count = 0
    total_tokens = 0
    total_latency = 0.0
    successful_requests = 0
    failed_requests = 0

    for row_number, row in enumerate(reader, start=2):
        if any(value is None for value in row.values()) or any(
            not (value or "").strip() for value in row.values()
        ):
            logger.warning("Rejected CSV row %d with empty values", row_number)
            raise ValueError(f"Row {row_number} contains empty values")
        try:
            status_code = int(row["status_code"])
            latency_ms = float(row["latency_ms"])
            tokens_used = int(row["tokens_used"])
        except (TypeError, ValueError) as error:
            logger.warning("Rejected CSV row %d with invalid numeric values", row_number)
            raise ValueError(f"Row {row_number} contains invalid numeric values") from error

        if not MIN_STATUS_CODE <= status_code <= MAX_STATUS_CODE:
            logger.warning("Rejected CSV row %d with invalid status code", row_number)
            raise ValueError(f"Row {row_number} has an invalid status_code")
        if not math.isfinite(latency_ms) or latency_ms < 0 or latency_ms > MAX_LATENCY_MS:
            logger.warning("Rejected CSV row %d with invalid latency", row_number)
            raise ValueError(f"Row {row_number} has an invalid latency_ms")
        if tokens_used < 0 or tokens_used > MAX_TOKENS_USED:
            logger.warning("Rejected CSV row %d with invalid token count", row_number)
            raise ValueError(f"Row {row_number} has an invalid tokens_used")

        request_count += 1
        total_tokens += tokens_used
        total_latency += latency_ms
        if status_code < 400:
            successful_requests += 1
        else:
            failed_requests += 1

    if request_count == 0:
        raise ValueError("CSV file must contain at least one data row")

    return ReportSummary(
        request_count=request_count,
        total_tokens=total_tokens,
        average_latency_ms=round(total_latency / request_count, 2),
        successful_requests=successful_requests,
        failed_requests=failed_requests,
    )