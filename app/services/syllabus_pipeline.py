"""Shared syllabus processing: Textract → OpenAI → persist."""
import logging
from typing import Any

from botocore.exceptions import ClientError
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.db_models import User, Document
from app.services.openai_service import parse_syllabus_with_openai
from app.services.syllabus_persist_service import save_parsed_syllabus_to_planner
from app.services.textract_service import process_sync_textract, process_async_textract
from app.utils.file_validation import check_pdf_requirements
from config import (
    S3_BUCKET,
    SNS_TOPIC_ARN,
    SQS_QUEUE_URL,
    TEXTRACT_ROLE_ARN,
    textract,
    s3_client,
    sqs_client,
)

logger = logging.getLogger(__name__)


async def extract_text_with_textract(
    content: bytes,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Run Textract (sync or async) and return extraction dict."""
    is_pdf = content_type == "application/pdf"

    if is_pdf:
        can_sync, _ = check_pdf_requirements(content)
        if can_sync:
            try:
                return await process_sync_textract(textract, content)
            except ClientError as e:
                _raise_aws_http(e)
        try:
            return await process_async_textract(
                textract_client=textract,
                s3_client=s3_client,
                sqs_client=sqs_client,
                content=content,
                filename=filename or "document.pdf",
                s3_bucket=S3_BUCKET,
                sns_topic_arn=SNS_TOPIC_ARN,
                role_arn=TEXTRACT_ROLE_ARN,
                sqs_queue_url=SQS_QUEUE_URL,
            )
        except ClientError as e:
            _raise_aws_http(e)

    try:
        return await process_sync_textract(textract, content)
    except ClientError as e:
        _raise_aws_http(e)


def _raise_aws_http(e: ClientError) -> None:
    error_code = e.response.get("Error", {}).get("Code", "")
    error_message = e.response.get("Error", {}).get("Message", str(e))
    raise HTTPException(
        status_code=500,
        detail=f"AWS Error ({error_code}): {error_message}",
    )


def parse_and_save_syllabus(
    db: Session,
    user: User,
    full_text: str,
    source_label: str | None,
    s3_object_key: str | None,
    num_lines: int,
    preview: str,
) -> tuple[Document, dict]:
    """OpenAI parse + DB persist; returns document and response-shaped dict."""
    if not full_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Textract returned no text. Is the document readable?",
        )
    logger.info("Parsing syllabus with OpenAI")
    try:
        parsed_syllabus = parse_syllabus_with_openai(text=full_text)
    except Exception as e:
        logger.error("OpenAI parsing failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse syllabus: {str(e)}",
        ) from e

    document_row = save_parsed_syllabus_to_planner(
        db=db,
        parsed=parsed_syllabus,
        user=user,
        doc_type="syllabus",
        source_label=source_label,
        s3_object_key=s3_object_key,
    )
    payload = {
        "message": "Syllabus processed and saved",
        "document_id": str(document_row.id),
        "extraction": {
            "num_lines": num_lines,
            "preview": preview,
        },
        "parsed": parsed_syllabus.model_dump(),
    }
    return document_row, payload
