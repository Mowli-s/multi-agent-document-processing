import json
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.models.state import DocumentState
from app.services.blob_storage import (
    BlobStorageService,
)


logger = logging.getLogger(__name__)


def output_agent(
    state: DocumentState,
) -> DocumentState:

    try:

        settings = get_settings()
        blob_service = BlobStorageService()

        state.setdefault("audit_trail", []).append(
            {
                "agent": "output",
                "action": "store_results",
                "status": "STARTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {},
            }
        )

        final_output = {
            "document_id": state[
                "document_id"
            ],

            "file_name": state[
                "file_name"
            ],

            "input_blob_url": state["input_blob_url"],

            "document_type": state[
                "document_type"
            ],

            "classification": {
                "type": state[
                    "document_type"
                ],
                "confidence": state.get(
                    "classification_confidence",
                    0.0,
                ),
            },

            "extraction": {
                "data": state.get(
                    "extracted_data",
                    {},
                ),
                "field_confidence": state.get(
                    "field_confidence",
                    {},
                ),
                "spatial_data": state.get(
                    "spatial_data",
                    {},
                ),
                "documents": state.get("extracted_documents", []),
            },

            "validation": {
                "passed": state.get(
                    "validation_passed",
                    False,
                ),
                "issues": state.get(
                    "validation_results",
                    [],
                ),
            },

            "enrichment": {
                "data": state.get(
                    "enriched_data",
                    {},
                ),
                "summary": state.get(
                    "summary",
                    "",
                ),
            },

            "human_review": {
                "status": state.get(
                    "human_review_status"
                ),
                "corrections": state.get(
                    "human_corrections",
                    {},
                ),
            },

            "processed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        state["final_output"] = final_output

        report = {
            "document_id": state[
                "document_id"
            ],
            "document_type": state[
                "document_type"
            ],
            "classification_confidence": state.get(
                "classification_confidence",
                0.0,
            ),
            "field_confidence": state.get(
                "field_confidence",
                {},
            ),
            "validation_results": state.get(
                "validation_results",
                [],
            ),
            "human_review_required": state.get(
                "requires_human_review",
                False,
            ),
            "audit_trail": state.get(
                "audit_trail",
                [],
            ),
        }

        state["processing_report"] = report

        output_blob = (
            f"{state['document_id']}.json"
        )

        report_blob = (
            f"{state['document_id']}_report.json"
        )

        blob_service.upload_text(
            settings.azure_storage_output_container,
            output_blob,
            json.dumps(
                final_output,
                indent=2,
                default=str,
            ),
        )

        state["audit_trail"][-1].update(
            {
                "status": "SUCCESS",
                "details": {
                    "input_blob_url": state["input_blob_url"],
                    "output_blob": output_blob,
                    "report_blob": report_blob,
                },
            }
        )

        blob_service.upload_text(
            settings.azure_storage_report_container,
            report_blob,
            json.dumps(
                report,
                indent=2,
                default=str,
            ),
        )

        return state

    except Exception as exc:

        logger.exception(
            "Output agent failed"
        )

        state["error"] = str(exc)
        state["error_agent"] = "output"

        return state
