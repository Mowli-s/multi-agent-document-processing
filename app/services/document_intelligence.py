import logging
from pathlib import Path
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings


logger = logging.getLogger(__name__)


class DocumentIntelligenceService:

    def __init__(self) -> None:
        settings = get_settings()

        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(
                settings.azure_document_intelligence_key
            ),
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def analyze_file(
        self,
        file_path: str,
        model_id: str,
    ) -> dict[str, Any]:

        logger.info(
            "Analyzing document using model=%s file=%s",
            model_id,
            file_path,
        )

        with Path(file_path).open("rb") as document:

            poller = self.client.begin_analyze_document(
                model_id=model_id,
                body=document,
            )

            result = poller.result()

        return self._parse_result(result)

    def _parse_result(self, result: Any) -> dict[str, Any]:

        extracted_fields: dict[str, Any] = {}
        field_confidence: dict[str, Any] = {}
        spatial_data: dict[str, Any] = {}

        documents: list[dict[str, Any]] = []

        if result.documents:

            for document_index, document in enumerate(result.documents):

                document_fields: dict[str, Any] = {}

                for field_name, field in document.fields.items():

                    value = self._to_jsonable(field.value)

                    # Keep a backwards-compatible flat view for model-specific
                    # validation, while preserving every analyzed document.
                    extracted_fields.setdefault(field_name, value)
                    document_fields[field_name] = value

                    field_confidence[field_name] = (
                        field.confidence or 0.0
                    )

                    if field.bounding_regions:
                        spatial_data[field_name] = {
                            "regions": [
                                {
                                    "page_number": region.page_number,
                                    "polygon": list(region.polygon)
                                    if region.polygon
                                    else None,
                                }
                                for region in field.bounding_regions
                            ],
                        }

                documents.append(
                    {
                        "document_index": document_index,
                        "document_type": document.doc_type,
                        "fields": document_fields,
                    }
                )

        raw_text = ""

        if result.content:
            raw_text = result.content

        tables: list[dict[str, Any]] = []

        if result.tables:

            for table in result.tables:

                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [],
                }

                for cell in table.cells:

                    table_data["cells"].append(
                        {
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                        }
                    )

                tables.append(table_data)

        return {
            "fields": extracted_fields,
            "field_confidence": field_confidence,
            "spatial_data": spatial_data,
            "raw_text": raw_text,
            "tables": tables,
            "documents": documents,
        }

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        """Convert Azure SDK values (currency, addresses, dates) to JSON data."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [DocumentIntelligenceService._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): DocumentIntelligenceService._to_jsonable(item)
                for key, item in value.items()
            }
        if hasattr(value, "as_dict"):
            return DocumentIntelligenceService._to_jsonable(value.as_dict())
        return str(value)
