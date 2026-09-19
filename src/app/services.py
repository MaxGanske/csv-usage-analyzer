import csv
import io
from dataclasses import dataclass

# CSV validation and report calculation service.
# It accepts file bytes and returns validated aggregate data without database access.


REQUIRED_HEADERS = {
    "request_id",
    "service",
    "status_code",
    "latency_ms",
    "tokens_used",
}


class CsvValidationError(ValueError):
    """Raised when an uploaded CSV violates the report input contract."""


@dataclass(frozen=True)
class ReportSummary:
    """Validated metrics that can be persisted as a report record."""

    request_count: int
    total_tokens: int
    average_latency_ms: float
    successful_requests: int
    failed_requests: int


def summarize_csv(contents: bytes) -> ReportSummary:
    """Validate CSV bytes and calculate the metrics required by the report API."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CsvValidationError("CSV file must be UTF-8 encoded") from error

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    if headers != REQUIRED_HEADERS:
        missing = sorted(REQUIRED_HEADERS - headers)
        unexpected = sorted(headers - REQUIRED_HEADERS)
        details = []
        if missing:
            details.append(f"missing headers: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected headers: {', '.join(unexpected)}")
        raise CsvValidationError("Invalid CSV headers; " + "; ".join(details))

    request_count = 0
    total_tokens = 0
    total_latency = 0.0
    successful_requests = 0
    failed_requests = 0

    for row_number, row in enumerate(reader, start=2):
        if any(value is None for value in row.values()) or any(
            not (value or "").strip() for value in row.values()
        ):
            raise CsvValidationError(f"Row {row_number} contains empty values")
        try:
            status_code = int(row["status_code"])
            latency_ms = float(row["latency_ms"])
            tokens_used = int(row["tokens_used"])
        except (TypeError, ValueError) as error:
            raise CsvValidationError(f"Row {row_number} contains invalid numeric values") from error

        if not 100 <= status_code <= 599:
            raise CsvValidationError(f"Row {row_number} has an invalid status_code")
        if latency_ms < 0 or tokens_used < 0:
            raise CsvValidationError(f"Row {row_number} has a negative metric")

        request_count += 1
        total_tokens += tokens_used
        total_latency += latency_ms
        if status_code < 400:
            successful_requests += 1
        else:
            failed_requests += 1

    if request_count == 0:
        raise CsvValidationError("CSV file must contain at least one data row")

    return ReportSummary(
        request_count=request_count,
        total_tokens=total_tokens,
        average_latency_ms=round(total_latency / request_count, 2),
        successful_requests=successful_requests,
        failed_requests=failed_requests,
    )