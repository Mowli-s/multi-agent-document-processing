import logging
import json
from urllib.request import Request, urlopen
from datetime import datetime, timezone

from app.config import get_settings
from app.models.state import DocumentState


logger = logging.getLogger(__name__)


def error_handler_agent(state: DocumentState) -> DocumentState:
    error = state.get("error")
    failed_agent = state.get("failed_agent") or state.get("error_agent", "unknown")

    logger.error(
        "Pipeline failed. agent=%s error=%s",
        failed_agent,
        error,
    )

    webhook_url = get_settings().error_notification_webhook_url
    if webhook_url:
        try:
            request = Request(
                webhook_url,
                data=json.dumps(
                    {
                        "event": "document_processing_failed",
                        "document_id": state.get("document_id"),
                        "failed_agent": failed_agent,
                        "error": str(error),
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=5):
                pass
        except Exception:
            logger.exception("Failure notification webhook could not be delivered")

    audit_trail = state.get("audit_trail", [])

    audit_trail.append(
        {
            "agent": "error_handler",
            "action": "pipeline_failure",
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(error),
        }
    )

    return {
        **state,
        "status": "failed",
        "audit_trail": audit_trail,
    }
