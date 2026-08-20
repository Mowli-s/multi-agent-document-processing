import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.models.state import DocumentState
from app.services.blob_storage import BlobStorageService


logger = logging.getLogger(__name__)


def input_storage_agent(state: DocumentState) -> DocumentState:
    """Persist the source document before downstream processing can fail."""
    try:
        settings = get_settings()
        blob_name = f"{state['document_id']}/{state['file_name']}"
        state["input_blob_url"] = BlobStorageService().upload_file(
            settings.azure_storage_input_container,
            blob_name,
            state["file_path"],
        )
        state.setdefault("audit_trail", []).append(
            {
                "agent": "input_storage",
                "action": "store_input",
                "status": "SUCCESS",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {"input_blob": blob_name},
            }
        )
    except Exception as exc:
        logger.exception("Input storage failed")
        state["error"] = str(exc)
        state["error_agent"] = "input_storage"
        state.setdefault("audit_trail", []).append(
            {
                "agent": "input_storage",
                "action": "store_input",
                "status": "FAILED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {"error": str(exc)},
            }
        )
    return state
