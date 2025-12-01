"""Syllabus upload API routes"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user
from app.models.db_models import User
from app.services.openai_service import parse_syllabus_with_openai
from app.services.syllabus_persist_service import save_parsed_syllabus_to_planner

from botocore.exceptions import ClientError

from config import (
    AWS_REGION, S3_BUCKET, SNS_TOPIC_ARN, SQS_QUEUE_URL, TEXTRACT_ROLE_ARN,
    OPENAI_API_KEY,
    textract, s3_client, sqs_client
)
from app.utils.file_validation import validate_file_format, check_pdf_requirements
from app.services.textract_service import process_sync_textract, process_async_textract

router = APIRouter(prefix="/api/v1", tags=["syllabus"])


@router.post("/upload_syllabus")
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Upload and process syllabus document"""
    # Basic content-type check
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
            detail=f"Unsupported file type: {file.content_type}. Use PDF or image (jpg/png/tiff)"
        )

    # Read the file bytes into memory
    content = await file.read()
    
    # Validate that we actually got content
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty or could not be read"
        )
    
    # Validate file format matches content-type
    if not validate_file_format(content, file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match declared type {file.content_type}."
        )
    
    # Determine processing strategy
    is_pdf = file.content_type == "application/pdf"
    
    if is_pdf:
        # Check if PDF meets requirements for sync processing
        can_sync, sync_error = check_pdf_requirements(content)
        
        if can_sync:
            # Single-page PDF: use sync processing
            try:
                result = await process_sync_textract(textract, content)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                raise HTTPException(
                    status_code=500,
                    detail=f"AWS Error ({error_code}): {error_message}",
                )
        else:
            # Multi-page PDF: use async processing
            try:
                result = await process_async_textract(
                    textract_client=textract,
                    s3_client=s3_client,
                    sqs_client=sqs_client,
                    content=content,
                    filename=file.filename or "document.pdf",
                    s3_bucket=S3_BUCKET,
                    sns_topic_arn=SNS_TOPIC_ARN,
                    role_arn=TEXTRACT_ROLE_ARN,
                    sqs_queue_url=SQS_QUEUE_URL
                )
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                raise HTTPException(
                    status_code=500,
                    detail=f"AWS Error ({error_code}): {error_message}",
                )
    else:
        # Image: use sync processing
        try:
            result = await process_sync_textract(textract, content)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            raise HTTPException(
                status_code=500,
                detail=f"AWS Error ({error_code}): {error_message}",
            )
    
    if not result['full_text'].strip():
        raise HTTPException(
            status_code=422,
            detail="Textract returned no text. Is the document readable?",
        )
    
    # Parse with OpenAI
    parsed_syllabus = parse_syllabus_with_openai(text=result['full_text'])
    
    # Save to database
    document_row = save_parsed_syllabus_to_planner(
        db=db,
        parsed=parsed_syllabus,
        user=user,
        doc_type="syllabus",
        source_label=file.filename,
        s3_object_key=None,
    )
    
    return {
        "message": "Syllabus processed and saved",
        "document_id": str(document_row.id),
        "extraction": {
            "num_lines": result["num_lines"],
            "preview": result["preview"],
        },
        "parsed": parsed_syllabus.model_dump(),
    }

