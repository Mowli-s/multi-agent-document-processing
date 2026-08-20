import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.state import DocumentState
from app.services.azure_openai import (
    AzureOpenAIService,
)


logger = logging.getLogger(__name__)


class EnrichmentResult(BaseModel):

    normalized_data: dict = Field(
        default_factory=dict
    )

    summary: str = ""

    inferred_fields: dict = Field(
        default_factory=dict
    )


def enrichment_agent(
    state: DocumentState,
) -> DocumentState:

    try:

        service = AzureOpenAIService()

        document_type = state[
            "document_type"
        ]

        extracted_data = state.get(
            "extracted_data",
            {},
        )

        prompt = f"""
You are a document data enrichment agent.

Document type:
{document_type}

Extracted data:
{extracted_data}

Validation issues:
{state.get("validation_results", [])}

Perform the following:

1. Normalize dates to YYYY-MM-DD when possible.
2. Normalize currency codes to ISO-style codes.
3. Normalize addresses where possible.
4. Infer missing values only when strongly supported.
5. Do not invent facts.
6. Generate a short document summary.

Return only the structured response.
"""

        result = service.structured_completion(
            system_prompt=(
                "You are a reliable enterprise "
                "document enrichment agent."
            ),
            user_prompt=prompt,
            response_model=EnrichmentResult,
        )

        state["enriched_data"] = (
            result.normalized_data
        )

        state["summary"] = result.summary

        state.setdefault(
            "audit_trail",
            [],
        ).append(
            {
                "agent": "enrichment",
                "action": "llm_enrichment",
                "status": "SUCCESS",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "details": {
                    "inferred_fields": (
                        result.inferred_fields
                    )
                },
            }
        )

        return state

    except Exception as exc:

        logger.exception(
            "Enrichment failed"
        )

        state["error"] = str(exc)
        state["error_agent"] = "enrichment"

        return state