import os
import shutil
import uuid

from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.graph.workflow import graph
from app.logging_config import configure_logging


configure_logging()

app = FastAPI(
    title="Multi-Agent Document Processing",
    version="1.0.0",
)


class HumanReviewRequest(BaseModel):
    approved: bool = True
    corrections: dict[str, Any] = Field(default_factory=dict)


UPLOAD_DIR = "sample_documents"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True,
)


@app.get("/health")
def health() -> dict[str, str]:

    return {
        "status": "healthy"
    }


@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
) -> dict[str, Any]:

    document_id = str(
        uuid.uuid4()
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{document_id}_{file.filename}",
    )

    with open(
        file_path,
        "wb",
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer,
        )

    initial_state = {
        "document_id": document_id,
        "file_name": file.filename,
        "file_path": file_path,
        "audit_trail": [],
        "requires_human_review": False,
    }

    config = {
        "configurable": {
            "thread_id": document_id
        }
    }

    result = graph.invoke(initial_state, config=config)

    if result.get("__interrupt__"):
        return {
            "status": "review_required",
            "document_id": document_id,
            "review_request": result["__interrupt__"],
        }

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=502,
            detail={
                "status": "failed",
                "document_id": result.get("document_id"),
                "failed_agent": result.get("failed_agent"),
                "error": result.get("error"),
            },
        )

    if result.get("status") == "unsupported":
        raise HTTPException(
            status_code=422,
            detail={
                "status": "unsupported",
                "document_id": document_id,
                "message": "The document could not be classified as a supported type.",
            },
        )

    if result.get("status") == "review_required":
        return {
            "status": "review_required",
            "document_id": result.get("document_id"),
            "review_items": result.get("validation_results", []),
            "data": result.get("extracted_data", {}),
        }

    return {
        "status": "completed",
        "document_id": result.get("document_id"),
        "document_type": result.get("document_type"),
        "classification_confidence": result.get(
            "classification_confidence"
        ),
        "extracted_data": result.get("extracted_data", {}),
        "validation_results": result.get(
            "validation_results", []
        ),
        "audit_trail": result.get("audit_trail", []),
    }


@app.post("/process/{document_id}/review")
def resume_human_review(
    document_id: str,
    review: HumanReviewRequest,
) -> dict[str, Any]:
    """Resume a checkpointed graph after a reviewer approves or corrects it."""
    config = {"configurable": {"thread_id": document_id}}
    response = {"corrections": review.corrections} if review.approved else None
    result = graph.invoke(Command(resume=response), config=config)

    if result.get("__interrupt__"):
        return {"status": "review_required", "document_id": document_id}

    if result.get("status") == "failed":
        raise HTTPException(status_code=502, detail=result.get("error", "Pipeline failed"))

    return {
        "status": "completed",
        "document_id": result.get("document_id"),
        "document_type": result.get("document_type"),
        "extracted_data": result.get("extracted_data", {}),
        "validation_results": result.get("validation_results", []),
        "audit_trail": result.get("audit_trail", []),
    }
