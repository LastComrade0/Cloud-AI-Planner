"""Background processing for syllabus jobs (SQS consumer)."""
import asyncio
import json
import logging
from datetime import datetime

from botocore.exceptions import ClientError
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.dependencies.db import SessionLocal
from app.models.db_models import ProcessingJob
from app.services.syllabus_pipeline import extract_text_with_textract, parse_and_save_syllabus
from config import s3_client

logger = logging.getLogger(__name__)


def _download_s3_bytes(bucket: str, key: str) -> bytes:
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def _fail_job(db: Session, job_id: str, message: str, bucket: str, key: str) -> None:
    try:
        db.rollback()
    except Exception:
        pass
    row = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if row:
        row.status = "failed"
        row.error_message = message[:4000]
        row.updated_at = datetime.utcnow()
        db.commit()
    _delete_s3_object(bucket, key)


def _delete_s3_object(bucket: str, key: str) -> None:
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        logger.warning("Could not delete staging object s3://%s/%s: %s", bucket, key, e)


async def process_syllabus_processing_job(db: Session, job_id: str) -> None:
    """
    Load job by public job_id, download staged file from S3, Textract → OpenAI → DB.
    Idempotent: skips if job already completed or failed.
    """
    job = (
        db.query(ProcessingJob)
        .options(joinedload(ProcessingJob.user))
        .filter(ProcessingJob.job_id == job_id)
        .first()
    )
    if job is None:
        logger.warning("ProcessingJob not found for job_id=%s", job_id)
        return

    if job.status in ("completed", "failed"):
        logger.info("Job %s already terminal (%s), skipping", job_id, job.status)
        return

    if job.status == "processing":
        logger.warning("Job %s already marked processing; continuing", job_id)

    job.status = "processing"
    job.updated_at = datetime.utcnow()
    db.commit()

    bucket = job.s3_bucket
    key = job.s3_key
    filename = job.filename or "document"
    content_type = job.content_type or "application/octet-stream"

    try:
        content = _download_s3_bytes(bucket, key)
        result = await extract_text_with_textract(content, filename, content_type)

        document_row, _payload = parse_and_save_syllabus(
            db,
            job.user,
            result["full_text"],
            job.filename,
            job.s3_key,
            result["num_lines"],
            result["preview"],
        )

        row = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if row:
            row.status = "completed"
            row.document_id = document_row.id
            row.error_message = None
            row.updated_at = datetime.utcnow()
            db.commit()

        _delete_s3_object(bucket, key)

    except HTTPException as e:
        detail = e.detail
        msg = detail if isinstance(detail, str) else json.dumps(detail)
        _fail_job(db, job_id, msg, bucket, key)
    except Exception as e:
        logger.exception("Syllabus job %s failed", job_id)
        _fail_job(db, job_id, str(e), bucket, key)


def handle_sqs_record_body(body: str) -> None:
    """Parse SQS message body and run one job (creates own DB session)."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid SQS message JSON: %s", body[:200])
        return
    job_id = data.get("job_id")
    if not job_id:
        logger.error("SQS message missing job_id: %s", body[:500])
        return

    db = SessionLocal()
    try:
        asyncio.run(process_syllabus_processing_job(db, job_id))
    finally:
        db.close()


def sqs_lambda_handler(event, context):
    """AWS Lambda entry for SQS trigger (separate from API Gateway Mangum handler)."""
    for record in event.get("Records", []):
        handle_sqs_record_body(record.get("body", "{}"))
