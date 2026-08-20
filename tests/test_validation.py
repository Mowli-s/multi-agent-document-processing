from app.agents.validator import validator_agent


def test_invoice_total_validation_passes():
    state = {
        "document_id": "test-001",
        "file_name": "invoice.pdf",
        "file_path": "invoice.pdf",
        "document_type": "invoice",
        "classification_confidence": 0.98,
        "extracted_data": {
            "InvoiceId": "INV-001",
            "InvoiceTotal": 1180.0,
            "SubTotal": 1000.0,
            "TotalTax": 180.0,
        },
        "field_confidence": {
            "InvoiceId": 0.98,
            "InvoiceTotal": 0.97,
            "SubTotal": 0.96,
            "TotalTax": 0.95,
        },
        "audit_trail": [],
    }

    result = validator_agent(state)

    assert result["validation_passed"] is True
    assert result["requires_human_review"] is False
    assert len(result["validation_results"]) == 0


def test_invoice_total_validation_fails():
    state = {
        "document_id": "test-002",
        "file_name": "invoice.pdf",
        "file_path": "invoice.pdf",
        "document_type": "invoice",
        "classification_confidence": 0.98,
        "extracted_data": {
            "InvoiceId": "INV-002",
            "InvoiceTotal": 1200.0,
            "SubTotal": 1000.0,
            "TotalTax": 180.0,
        },
        "field_confidence": {
            "InvoiceId": 0.98,
            "InvoiceTotal": 0.97,
            "SubTotal": 0.96,
            "TotalTax": 0.95,
        },
        "audit_trail": [],
    }

    result = validator_agent(state)

    assert result["validation_passed"] is False
    assert result["requires_human_review"] is True

    assert any(
        issue["field"] == "InvoiceTotal"
        for issue in result["validation_results"]
    )


def test_low_confidence_requires_human_review():
    state = {
        "document_id": "test-003",
        "file_name": "invoice.pdf",
        "file_path": "invoice.pdf",
        "document_type": "invoice",
        "classification_confidence": 0.90,
        "extracted_data": {
            "InvoiceId": "INV-003",
            "InvoiceTotal": 1180.0,
            "SubTotal": 1000.0,
            "TotalTax": 180.0,
        },
        "field_confidence": {
            "InvoiceId": 0.65,
            "InvoiceTotal": 0.95,
            "SubTotal": 0.95,
            "TotalTax": 0.95,
        },
        "audit_trail": [],
    }

    result = validator_agent(state)

    assert result["requires_human_review"] is True

    low_confidence_issue = next(
        issue
        for issue in result["validation_results"]
        if issue["field"] == "InvoiceId"
    )

    assert low_confidence_issue["confidence"] == 0.65