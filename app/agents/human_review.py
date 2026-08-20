import logging
from datetime import datetime, timezone

from langgraph.types import interrupt
from app.models.state import DocumentState


logger = logging.getLogger(__name__)


def human_review_agent(state: DocumentState) -> DocumentState:

    review_request = {
        "document_id": state["document_id"],
        "document_type": state["document_type"],
        "extracted_data": state.get(
            "extracted_data",
            {},
        ),
        "validation_results": state.get(
            "validation_results",
            [],
        ),
        "message": (
            "Human review is required. "
            "Approve or provide corrections."
        ),
    }

    human_response = interrupt(
        review_request
    )

    if not human_response:

        state["human_review_status"] = (
            "REJECTED"
        )

        state["requires_human_review"] = True
        state["error"] = "Human review rejected the document"
        state["error_agent"] = "human_review"
        state.setdefault("audit_trail", []).append(
            {
                "agent": "human_review",
                "action": "human_approval",
                "status": "REJECTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {},
            }
        )
        return state

    state["human_review_status"] = (
        "APPROVED"
    )

    state["human_corrections"] = (
        human_response.get(
            "corrections",
            {},
        )
    )

    if state["human_corrections"]:

        state["extracted_data"].update(
            state["human_corrections"]
        )

    state["requires_human_review"] = False

    state.setdefault(
        "audit_trail",
        [],
    ).append(
        {
            "agent": "human_review",
            "action": "human_approval",
            "status": "APPROVED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "corrections": (
                    state["human_corrections"]
                )
            },
        }
    )

    return state
