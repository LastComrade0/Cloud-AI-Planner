"""Service to process completed async Textract jobs"""
import asyncio
from sqlalchemy.orm import Session
from app.models.db_models import ProcessingJob, Document
from app.services.textract_service import get_async_results
from app.services.openai_service import parse_syllabus_with_openai
from app.services.syllabus_persist_service import save_parsed_syllabus_to_planner
from config import textract, s3_client, S3_BUCKET
from botocore.exceptions import ClientError
from fastapi import HTTPException


async def process_completed_job(db: Session, job: ProcessingJob) -> Document:
    """Process a completed Textract job - get results, parse with OpenAI, save to DB"""
    try:
        # Get Textract results
        result = await get_async_results(
            textract_client=textract,
            s3_client=s3_client,
            job_id=job.textract_job_id,
            s3_key=job.s3_key,
            s3_bucket=job.s3_bucket
        )
        
        if not result['full_text'].strip():
            job.status = "failed"
            job.error_message = "Textract returned no text"
            db.commit()
            raise HTTPException(status_code=422, detail="Textract returned no text")
        
        # Parse with OpenAI
        parsed_syllabus = parse_syllabus_with_openai(text=result['full_text'])
        
        # Save to database
        document_row = save_parsed_syllabus_to_planner(
            db=db,
            parsed=parsed_syllabus,
            user=job.user,
            doc_type="syllabus",
            source_label=job.filename,
            s3_object_key=job.s3_key,
        )
        
        # Update job status
        job.status = "completed"
        job.document_id = document_row.id
        db.commit()
        
        return document_row
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise


async def check_and_process_jobs(db: Session, user_id=None):
    """Check for processing jobs and update their status based on Textract job status"""
    query = db.query(ProcessingJob).filter(ProcessingJob.status == "processing")
    if user_id:
        query = query.filter(ProcessingJob.user_id == user_id)
    
    jobs = query.all()
    
    results = []
    for job in jobs:
        try:
            # Check Textract job status
            response = textract.get_document_text_detection(JobId=job.textract_job_id)
            status = response.get('JobStatus')
            
            if status == 'SUCCEEDED':
                # Process the completed job
                document = await process_completed_job(db, job)
                results.append({
                    "job_id": str(job.id),
                    "status": "completed",
                    "document_id": str(document.id)
                })
            elif status == 'FAILED':
                job.status = "failed"
                job.error_message = response.get('StatusMessage', 'Textract job failed')
                db.commit()
                results.append({
                    "job_id": str(job.id),
                    "status": "failed",
                    "error": job.error_message
                })
            elif status == 'IN_PROGRESS':
                # Still processing, no action needed
                pass
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'InvalidJobIdException':
                job.status = "failed"
                job.error_message = "Textract job not found"
                db.commit()
            else:
                # Other errors - log but don't fail
                print(f"Error checking job {job.id}: {str(e)}")
        except Exception as e:
            print(f"Error processing job {job.id}: {str(e)}")
    
    return results

