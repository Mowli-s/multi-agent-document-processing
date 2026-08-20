from typing import Any

from pydantic import BaseModel, Field


class ConfidenceValue(BaseModel):
    value: Any | None = None
    confidence: float = 0.0
    page_number: int | None = None
    polygon: list[float] | None = None


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: str = "ERROR"
    confidence: float | None = None


class ValidationResult(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class AuditEvent(BaseModel):
    agent: str
    action: str
    status: str
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Validated, provider-neutral handoff from extraction to validation."""

    document_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    spatial_data: dict[str, Any] = Field(default_factory=dict)
    raw_text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
