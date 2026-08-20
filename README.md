# Multi-Agent Document Processing

An Azure-backed Intelligent Document Processing pipeline built with FastAPI and
LangGraph. It accepts PDF and image documents, classifies them, extracts data,
validates confidence and totals, pauses for human review when needed, enriches
the result, and stores the input, result, and processing report in Azure Blob
Storage.

## Setup

1. Create `.env` from `.env.example` and replace every `YOUR_*` value with the
   corresponding Azure resource value.
2. Install the packages in `requirements.txt`.
3. Start the API with:

```powershell
uvicorn app.main:app --reload
```

The required Azure settings are validated at startup. A missing setting causes
Pydantic to raise a `ValidationError` and the application will not start.

## Process and review a document

Upload a document to `POST /process` as multipart field `file`. A document
with validation issues returns `status: "review_required"` and its document ID.
Resume that same in-memory LangGraph checkpoint with:

```http
POST /process/{document_id}/review
Content-Type: application/json

{"approved": true, "corrections": {"InvoiceId": "INV-1001"}}
```

Submitting `{"approved": false}` records a rejection. The memory checkpointer
is intended for a single running application process; use a durable LangGraph
checkpointer before deploying across multiple instances or restarts.

## Pipeline

`input Blob storage → classifier → typed extraction route → validator → human review (when needed)
→ enrichment → output storage`

Failures from each stage route to the error handler. Azure Document
Intelligence, Azure OpenAI, and Azure Blob requests retry up to three times
with exponential backoff. The processing report includes classification and
field confidence, validation findings, reviewer activity, spatial field data,
and the audit trail.

Unrecognised documents take a dedicated fallback path and return HTTP 422
instead of attempting an incompatible extraction model.

Set the optional `ERROR_NOTIFICATION_WEBHOOK_URL` to receive a JSON callback
when the error-handling node is reached.
