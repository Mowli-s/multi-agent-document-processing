from datetime import datetime, timezone

from app.models.state import DocumentState


def unsupported_document_agent(state: DocumentState) -> DocumentState:
    """Finish safely when the classifier cannot identify a supported type."""
    state["status"] = "unsupported"
    state.setdefault("audit_trail", []).append(
        {
            "agent": "unsupported_document",
            "action": "fallback",
            "status": "UNSUPPORTED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {"document_type": state.get("document_type")},
        }
    )
    return state
