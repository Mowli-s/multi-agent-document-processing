from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing import Any

from app.agents.classifier import classifier_agent
from app.agents.enrichment import enrichment_agent
from app.agents.error_handler import error_handler_agent

from app.agents.extraction import (
    contract_extraction_agent,
    invoice_extraction_agent,
    receipt_extraction_agent,
    resume_extraction_agent,
)

from app.agents.human_review import human_review_agent
from app.agents.input_storage import input_storage_agent
from app.agents.output import output_agent
from app.agents.unsupported import unsupported_document_agent
from app.agents.validator import validator_agent

from app.models.state import DocumentState


def route_document(state: DocumentState) -> str:
    """
    Route the document after classification.
    """

    # If classifier failed, go directly to error handler.
    if state.get("error"):
        return "error"

    document_type = state.get("document_type")

    routes = {
        "invoice": "invoice_extraction",
        "receipt": "receipt_extraction",
        "contract": "contract_extraction",
        "resume": "resume_extraction",
        "unsupported": "unsupported",
    }

    return routes.get(
        document_type,
        "error",
    )


def route_after_extraction(state: DocumentState) -> str:
    """
    Route extraction result.

    Successful extraction:
        extraction -> validator

    Failed extraction:
        extraction -> error
    """

    if state.get("error"):
        return "error"

    if state.get("status") == "failed":
        return "error"

    return "validator"


def route_after_validation(state: DocumentState) -> str:
    """
    Route validation result.
    """

    if state.get("error"):
        return "error"

    if state.get("status") == "failed":
        return "error"

    if state.get(
        "requires_human_review",
        False,
    ):
        return "human_review"

    return "enrichment"


def route_after_processing(state: DocumentState) -> str:
    """Ensure failures in later agents also reach the error handler."""
    if state.get("error") or state.get("status") == "failed":
        return "error"
    return "output"


def route_after_human_review(state: DocumentState) -> str:
    if state.get("error") or state.get("human_review_status") == "REJECTED":
        return "error"
    return "enrichment"


def route_after_input_storage(state: DocumentState) -> str:
    return "error" if state.get("error") else "classifier"


def build_graph() -> Any:

    builder = StateGraph(DocumentState)

    # =========================================================
    # Nodes
    # =========================================================

    builder.add_node(
        "classifier",
        classifier_agent,
    )

    builder.add_node(
        "input_storage",
        input_storage_agent,
    )

    builder.add_node(
        "invoice_extraction",
        invoice_extraction_agent,
    )

    builder.add_node(
        "receipt_extraction",
        receipt_extraction_agent,
    )

    builder.add_node(
        "contract_extraction",
        contract_extraction_agent,
    )

    builder.add_node(
        "resume_extraction",
        resume_extraction_agent,
    )

    builder.add_node(
        "validator",
        validator_agent,
    )

    builder.add_node(
        "human_review",
        human_review_agent,
    )

    builder.add_node(
        "enrichment",
        enrichment_agent,
    )

    builder.add_node(
        "output",
        output_agent,
    )

    builder.add_node(
        "error",
        error_handler_agent,
    )

    builder.add_node(
        "unsupported",
        unsupported_document_agent,
    )

    # =========================================================
    # START
    # =========================================================

    builder.add_edge(
        START,
        "input_storage",
    )

    builder.add_conditional_edges(
        "input_storage",
        route_after_input_storage,
        {"classifier": "classifier", "error": "error"},
    )

    # =========================================================
    # CLASSIFIER -> EXTRACTION
    # =========================================================

    builder.add_conditional_edges(
        "classifier",
        route_document,
        {
            "invoice_extraction": "invoice_extraction",
            "receipt_extraction": "receipt_extraction",
            "contract_extraction": "contract_extraction",
            "resume_extraction": "resume_extraction",
            "unsupported": "unsupported",
            "error": "error",
        },
    )

    # =========================================================
    # EXTRACTION -> VALIDATOR / ERROR
    #
    # IMPORTANT:
    # Do NOT use direct edges from extraction to validator.
    # We need conditional routing so failures go to error.
    # =========================================================

    builder.add_conditional_edges(
        "invoice_extraction",
        route_after_extraction,
        {
            "validator": "validator",
            "error": "error",
        },
    )

    builder.add_conditional_edges(
        "receipt_extraction",
        route_after_extraction,
        {
            "validator": "validator",
            "error": "error",
        },
    )

    builder.add_conditional_edges(
        "contract_extraction",
        route_after_extraction,
        {
            "validator": "validator",
            "error": "error",
        },
    )

    builder.add_conditional_edges(
        "resume_extraction",
        route_after_extraction,
        {
            "validator": "validator",
            "error": "error",
        },
    )

    # =========================================================
    # VALIDATOR -> HUMAN REVIEW / ENRICHMENT / ERROR
    # =========================================================

    builder.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "human_review": "human_review",
            "enrichment": "enrichment",
            "error": "error",
        },
    )

    # =========================================================
    # HUMAN REVIEW -> ENRICHMENT
    # =========================================================

    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {"enrichment": "enrichment", "error": "error"},
    )

    # =========================================================
    # ENRICHMENT -> OUTPUT
    # =========================================================

    builder.add_conditional_edges(
        "enrichment",
        route_after_processing,
        {"output": "output", "error": "error"},
    )

    # =========================================================
    # OUTPUT -> END
    # =========================================================

    builder.add_conditional_edges(
        "output",
        lambda state: "error" if state.get("error") else "end",
        {"error": "error", "end": END},
    )

    # =========================================================
    # ERROR -> END
    # =========================================================

    builder.add_edge(
        "error",
        END,
    )

    builder.add_edge(
        "unsupported",
        END,
    )

    # =========================================================
    # CHECKPOINTING
    # =========================================================

    checkpointer = MemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
    )


graph = build_graph()
