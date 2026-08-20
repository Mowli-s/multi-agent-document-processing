from typing import Any, TypedDict


class DocumentState(TypedDict, total=False):

    # ---------------------------------------------------------
    # Document
    # ---------------------------------------------------------

    document_id: str
    file_name: str
    file_path: str
    blob_path: str
    input_blob_url: str

    # ---------------------------------------------------------
    # Classification
    # ---------------------------------------------------------

    document_type: str
    classification_confidence: float
    status: str

    # ---------------------------------------------------------
    # Document Intelligence
    # ---------------------------------------------------------

    raw_text: str
    raw_tables: list[dict[str, Any]]
    extracted_documents: list[dict[str, Any]]

    extracted_data: dict[str, Any]
    field_confidence: dict[str, Any]
    spatial_data: dict[str, Any]

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    validation_results: list[dict[str, Any]]
    validation_passed: bool

    # ---------------------------------------------------------
    # Enrichment
    # ---------------------------------------------------------

    enriched_data: dict[str, Any]
    summary: str

    # ---------------------------------------------------------
    # Human review
    # ---------------------------------------------------------

    requires_human_review: bool
    human_review_status: str
    human_corrections: dict[str, Any]

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    final_output: dict[str, Any]
    processing_report: dict[str, Any]

    # ---------------------------------------------------------
    # Audit
    # ---------------------------------------------------------

    audit_trail: list[dict[str, Any]]

    # ---------------------------------------------------------
    # Error
    # ---------------------------------------------------------

    error: str
    error_agent: str
    failed_agent: str
