"""Syllabus upload API routes"""
import json
import logging
import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user
from app.models.db_models import User, Document, ProcessingJob
from app.services.syllabus_pipeline import extract_text_with_textract, parse_and_save_syllabus
from app.utils.file_validation import validate_file_format

from config import (
    S3_BUCKET,
    SYLLABUS_PROCESSING_QUEUE_URL,
    s3_client,
    sqs_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["syllabus"])


@router.post("/upload_syllabus")
async def upload_syllabus(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload and process syllabus document (sync), or enqueue for background processing (async)."""
    logger.info("Upload request received from user %s for file: %s", user.id, file.filename)

    supported_types = (
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/tiff",
    )

    if file.content_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use PDF or image (jpg/png/tiff)",
        )

    content = await file.read()

    if not content or len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty or could not be read")

    if not validate_file_format(content, file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match declared type {file.content_type}.",
        )

    if SYLLABUS_PROCESSING_QUEUE_URL:
        return await _enqueue_syllabus_job(db, user, content, file.filename, file.content_type)

    result = await extract_text_with_textract(
        content,
        file.filename or "",
        file.content_type,
    )

    document_row, payload = parse_and_save_syllabus(
        db,
        user,
        result["full_text"],
        file.filename,
        None,
        result["num_lines"],
        result["preview"],
    )

    verify_doc = db.query(Document).filter(Document.id == document_row.id).first()
    if not verify_doc:
        raise HTTPException(
            status_code=500,
            detail=f"Document was not saved to database (ID: {document_row.id})",
        )

    return payload


async def _enqueue_syllabus_job(
    db: Session,
    user: User,
    content: bytes,
    filename: str | None,
    content_type: str,
):
    job_id = str(uuid.uuid4())
    safe_name = (filename or "document").replace("\\", "/").split("/")[-1][:200]
    s3_key = f"syllabus-jobs/{job_id}/{safe_name}"

    try:
        s3_client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stage upload to S3 ({error_code}): {error_message}",
        )

    job = ProcessingJob(
        user_id=user.id,
        job_id=job_id,
        s3_bucket=S3_BUCKET,
        s3_key=s3_key,
        filename=filename,
        content_type=content_type,
        status="pending",
    )
    db.add(job)
    db.commit()

    try:
        sqs_client.send_message(
            QueueUrl=SYLLABUS_PROCESSING_QUEUE_URL,
            MessageBody=json.dumps({"job_id": job_id}),
        )
    except ClientError as e:
        job.status = "failed"
        job.error_message = f"Failed to enqueue job: {e}"
        db.commit()
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        except ClientError:
            pass
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue syllabus job ({error_code}): {error_message}",
        )

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Syllabus queued for processing",
            "job_id": job_id,
            "status_url": f"/api/v1/syllabus_jobs/{job_id}",
        },
    )


@router.get("/syllabus_jobs/{job_id}")
async def get_syllabus_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.job_id == job_id, ProcessingJob.user_id == user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    body = {
        "job_id": job.job_id,
        "status": job.status,
        "document_id": str(job.document_id) if job.document_id else None,
        "error_message": job.error_message,
    }
    if job.status == "completed" and job.document_id:
        body["message"] = "Syllabus processed and saved"
    return body
