# Pydantic response contracts for the public report endpoints.
# These schemas keep database objects separate from the external API shape.
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    """Serialized report summary returned by create, list, and detail endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    created_at: datetime
    request_count: int
    total_tokens: int
    average_latency_ms: float
    successful_requests: int
    failed_requests: int