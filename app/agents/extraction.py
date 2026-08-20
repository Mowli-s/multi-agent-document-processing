import logging
from datetime import datetime, timezone

from app.models.state import DocumentState
from app.models.common import ExtractionResult
from app.models.contract import ContractData
from app.models.resume import ResumeData
from app.services.document_intelligence import (
    DocumentIntelligenceService,
)
from app.services.azure_openai import AzureOpenAIService


logger = logging.getLogger(__name__)


MODEL_MAPPING = {
    "invoice": "prebuilt-invoice",
    "receipt": "prebuilt-receipt",
    "contract": "prebuilt-layout",
    "resume": "prebuilt-layout",
}

SEMANTIC_MODELS = {
    "contract": ContractData,
    "resume": ResumeData,
}


def _run_extraction(
    state: DocumentState,
    document_type: str,
) -> DocumentState:

    try:

        service = DocumentIntelligenceService()

        model_id = MODEL_MAPPING[document_type]

        result = service.analyze_file(
            file_path=state["file_path"],
            model_id=model_id,
        )

        extracted_data = result["fields"]
        if document_type in SEMANTIC_MODELS:
            schema = SEMANTIC_MODELS[document_type]
            semantic_result = AzureOpenAIService().structured_completion(
                system_prompt=(
                    "Extract only facts present in the OCR text. Return the requested "
                    "structured schema, use null or empty lists for missing values, and "
                    "do not invent facts."
                ),
                user_prompt=(
                    f"Document type: {document_type}\n\nOCR text:\n"
                    f"{result['raw_text'][:24000]}"
                ),
                response_model=schema,
            )
            extracted_data = semantic_result.model_dump(mode="json")

        extraction = ExtractionResult(
            document_type=document_type,
            data=extracted_data,
            field_confidence=result["field_confidence"],
            spatial_data=result["spatial_data"],
            raw_text=result["raw_text"],
            tables=result["tables"],
            documents=result["documents"],
        )
        state["raw_text"] = extraction.raw_text
        state["raw_tables"] = extraction.tables
        state["extracted_documents"] = extraction.documents
        state["extracted_data"] = extraction.data
        state["field_confidence"] = extraction.field_confidence
        state["spatial_data"] = extraction.spatial_data

        state.setdefault("audit_trail", []).append(
            {
                "agent": "extraction",
                "action": f"{document_type}_extraction",
                "status": "SUCCESS",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "details": {
                    "model": model_id,
                    "field_count": len(
                        result["fields"]
                    ),
                },
            }
        )

        return state

    except Exception as exc:

        logger.exception(
            "Extraction failed type=%s",
            state.get("document_type"),
        )

        state["error"] = str(exc)
        state["error_agent"] = (
            f"{document_type}_extraction"
        )

        state.setdefault("audit_trail", []).append(
            {
                "agent": "extraction",
                "action": f"{document_type}_extraction",
                "status": "FAILED",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "details": {
                    "error": str(exc),
                },
            }
        )

        return {
            **state,
            "status": "failed",
            "failed_agent": f"{state.get('document_type', 'unknown')}_extraction",
            "error": str(exc),
        }


def invoice_extraction_agent(
    state: DocumentState,
) -> DocumentState:

    return _run_extraction(
        state,
        "invoice",
    )


def receipt_extraction_agent(
    state: DocumentState,
) -> DocumentState:

    return _run_extraction(
        state,
        "receipt",
    )


def contract_extraction_agent(
    state: DocumentState,
) -> DocumentState:

    return _run_extraction(
        state,
        "contract",
    )


def resume_extraction_agent(
    state: DocumentState,
) -> DocumentState:

    return _run_extraction(
        state,
        "resume",
    )
