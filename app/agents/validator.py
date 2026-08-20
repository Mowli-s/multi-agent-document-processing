import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.models.state import DocumentState
from app.models.common import ValidationIssue, ValidationResult


logger = logging.getLogger(__name__)


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("amount", "value", "Amount", "Value"):
            if key in value:
                return _numeric_value(value[key])
    return None


def _line_item_total(items: Any) -> float | None:
    if not isinstance(items, list):
        return None
    amounts = []
    for item in items:
        if isinstance(item, dict):
            amount = _numeric_value(item.get("Amount", item.get("amount")))
            if amount is not None:
                amounts.append(amount)
    return round(sum(amounts), 2) if amounts else None


def validator_agent(
    state: DocumentState,
) -> DocumentState:

    try:

        settings = get_settings()

        issues = []

        confidence_map = state.get(
            "field_confidence",
            {},
        )

        # -----------------------------------------------------
        # Confidence validation
        # -----------------------------------------------------

        for field, confidence in confidence_map.items():

            if confidence < settings.confidence_threshold:

                issues.append(
                    {
                        "field": field,
                        "message": (
                            "Field confidence is below "
                            "configured threshold"
                        ),
                        "severity": "WARNING",
                        "confidence": confidence,
                    }
                )

        # -----------------------------------------------------
        # Required fields
        # -----------------------------------------------------

        document_type = state["document_type"]

        data = state.get(
            "extracted_data",
            {},
        )

        required_fields = {
            "invoice": [
                "InvoiceId",
                "InvoiceTotal",
            ],
            "receipt": [
                "MerchantName",
                "Total",
            ],
            "contract": ["parties"],
            "resume": ["name", "email"],
        }

        for field in required_fields.get(
            document_type,
            [],
        ):

            if not data.get(field):

                issues.append(
                    {
                        "field": field,
                        "message": (
                            "Required field is missing"
                        ),
                        "severity": "ERROR",
                    }
                )

        # -----------------------------------------------------
        # Invoice arithmetic validation
        # -----------------------------------------------------

        if document_type == "invoice":

            subtotal = data.get(
                "SubTotal"
            )

            tax = data.get(
                "TotalTax"
            )

            total = data.get(
                "InvoiceTotal"
            )

            if (
                _numeric_value(subtotal) is not None
                and _numeric_value(tax) is not None
                and _numeric_value(total) is not None
            ):

                expected = round(
                    _numeric_value(subtotal) + _numeric_value(tax),
                    2,
                )

                actual = round(
                    _numeric_value(total),
                    2,
                )

                if abs(expected - actual) > 0.01:

                    issues.append(
                        {
                            "field": "InvoiceTotal",
                            "message": (
                                "Subtotal + tax does "
                                "not equal invoice total"
                            ),
                            "severity": "ERROR",
                        }
                    )

            item_total = _line_item_total(data.get("Items"))
            subtotal_value = _numeric_value(subtotal)
            if item_total is not None and subtotal_value is not None and abs(item_total - subtotal_value) > 0.01:
                issues.append(
                    {
                        "field": "Items",
                        "message": "Line item amounts do not equal invoice subtotal",
                        "severity": "ERROR",
                    }
                )

        if document_type == "receipt":
            subtotal = data.get("Subtotal")
            tax = data.get("TotalTax")
            total = data.get("Total")
            if all(_numeric_value(value) is not None for value in (subtotal, tax, total)):
                if abs(round(_numeric_value(subtotal) + _numeric_value(tax), 2) - round(_numeric_value(total), 2)) > 0.01:
                    issues.append(
                        {
                            "field": "Total",
                            "message": "Subtotal + tax does not equal receipt total",
                            "severity": "ERROR",
                        }
                    )

        has_errors = any(
            issue["severity"] == "ERROR"
            for issue in issues
        )

        requires_review = (
            len(issues) > 0
        )

        validation = ValidationResult(
            passed=not has_errors,
            issues=[ValidationIssue(**issue) for issue in issues],
        )
        state["validation_results"] = [
            issue.model_dump(mode="json") for issue in validation.issues
        ]

        state["validation_passed"] = validation.passed

        state["requires_human_review"] = (
            requires_review
        )

        state.setdefault(
            "audit_trail",
            [],
        ).append(
            {
                "agent": "validator",
                "action": "validation",
                "status": (
                    "REVIEW_REQUIRED"
                    if requires_review
                    else "PASSED"
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "details": {
                    "issue_count": len(issues),
                },
            }
        )

        return state

    except Exception as exc:

        logger.exception(
            "Validation failed"
        )

        state["error"] = str(exc)
        state["error_agent"] = "validator"

        return state
