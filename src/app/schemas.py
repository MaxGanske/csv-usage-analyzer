from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    created_at: datetime
    request_count: int
    total_tokens: int
    average_latency_ms: float
    successful_requests: int
    failed_requests: int
    failure_rate: float
    service_breakdown: dict[str, dict[str, Any]]