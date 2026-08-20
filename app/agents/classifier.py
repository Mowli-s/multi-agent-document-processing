import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from app.models.state import DocumentState
from app.services.document_intelligence import (
    DocumentIntelligenceService,
)
from app.services.azure_openai import AzureOpenAIService
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


SUPPORTED_TYPES = {"invoice", "receipt", "contract", "resume"}


class ClassificationResult(BaseModel):
    document_type: str = Field(description="invoice, receipt, contract, resume, or unsupported")
    confidence: float = Field(ge=0.0, le=1.0)


def _audit(
    state: DocumentState,
    status: str,
    details: dict[str, Any],
) -> list[dict[str, Any]]:

    events = state.get("audit_trail", [])

    events.append(
        {
            "agent": "classifier",
            "action": "document_classification",
            "status": status,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "details": details,
        }
    )

    return events


def classifier_agent(
    state: DocumentState,
) -> DocumentState:

    try:

        file_path = state["file_path"]

        # Read the uploaded content first; classification does not trust a
        # file name, which can be inaccurate or absent.
        read_result = DocumentIntelligenceService().analyze_file(
            file_path=file_path,
            model_id="prebuilt-read",
        )
        service = AzureOpenAIService()
        system_prompt = (
            "Classify enterprise documents. Return only invoice, receipt, "
            "contract, resume, or unsupported. Do not guess when content is unclear."
        )
        image_extensions = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
        if Path(file_path).suffix.lower() in image_extensions:
            classification = service.vision_structured_completion(
                system_prompt=system_prompt,
                user_prompt=f"Classify this uploaded document: {state['file_name']}",
                image_path=file_path,
                response_model=ClassificationResult,
            )
        else:
            classification = service.structured_completion(
                system_prompt=system_prompt,
                user_prompt=(
                    f"File name: {state['file_name']}\n\nDocument text:\n"
                    f"{read_result['raw_text'][:12000]}"
                ),
                response_model=ClassificationResult,
            )
        document_type = classification.document_type.lower().strip()
        confidence = classification.confidence

        if document_type not in SUPPORTED_TYPES:
            document_type = "unsupported"

        state["document_type"] = document_type
        state["classification_confidence"] = confidence

        state["audit_trail"] = _audit(
            state,
            "SUCCESS",
            {
                "document_type": document_type,
                "confidence": confidence,
            },
        )

        return state

    except Exception as exc:

        logger.exception("Classification failed")

        state["error"] = str(exc)
        state["error_agent"] = "classifier"

        state["audit_trail"] = _audit(
            state,
            "FAILED",
            {"error": str(exc)},
        )

        return state
