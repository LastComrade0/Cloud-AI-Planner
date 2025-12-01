"""Textract service for document processing"""
import uuid
import json
import time
from fastapi import HTTPException
from botocore.exceptions import ClientError

from app.utils.text_extraction import extract_text_from_response


async def process_sync_textract(textract_client, content: bytes) -> dict:
    """Process document synchronously (single-page PDFs, images)"""
    response = textract_client.detect_document_text(
        Document={'Bytes': content}
    )
    return extract_text_from_response(response)


async def process_async_textract(
    textract_client,
    s3_client,
    sqs_client,
    content: bytes,
    filename: str,
    s3_bucket: str,
    sns_topic_arn: str,
    role_arn: str,
    sqs_queue_url: str
) -> dict:
    """Process multi-page PDF using async Textract operations"""
    s3_key = f"textract/{uuid.uuid4()}/{filename}"

    try:
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=content,
        )

        # Start async text detection
        response = textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            },
            NotificationChannel={
                'SNSTopicArn': sns_topic_arn,
                'RoleArn': role_arn
            }
        )

        job_id = response['JobId']

        # Poll SQS for completion (with timeout)
        max_wait_time = 300  # 5 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Check SQS for messages
            messages = sqs_client.receive_message(
                QueueUrl=sqs_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            
            if 'Messages' in messages:
                for message in messages['Messages']:
                    body = json.loads(message['Body'])
                    sns_message = json.loads(body['Message'])
                    
                    if sns_message.get('JobId') == job_id:
                        status = sns_message.get('Status')
                        
                        if status == 'SUCCEEDED':
                            # Delete the message
                            sqs_client.delete_message(
                                QueueUrl=sqs_queue_url,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                            
                            # Get results
                            return await get_async_results(
                                textract_client, s3_client, job_id, s3_key, s3_bucket
                            )
                        elif status == 'FAILED':
                            # Delete the message
                            sqs_client.delete_message(
                                QueueUrl=sqs_queue_url,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                            
                            # Clean up S3
                            s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                            
                            raise HTTPException(
                                status_code=500,
                                detail=f"Textract job failed: {sns_message.get('StatusMessage', 'Unknown error')}"
                            )
            
            time.sleep(2)  # Wait before next poll

        # Timeout - clean up S3
        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
        
        raise HTTPException(
            status_code=504,
            detail="Textract job timed out. The document may be too large or complex."
        )
    
    except ClientError as e:
        # Clean up S3 on error
        try:
            s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
        except:
            pass
        
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise HTTPException(
            status_code=500,
            detail=f"AWS Error during async processing ({error_code}): {error_message}"
        )


async def start_async_textract_job(
    textract_client,
    s3_client,
    content: bytes,
    filename: str,
    s3_bucket: str,
    sns_topic_arn: str,
    role_arn: str
) -> dict:
    """Start async Textract job without waiting - returns immediately with job info"""
    s3_key = f"textract/{uuid.uuid4()}/{filename}"

    # Upload to S3
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=content,
    )

    # Start async text detection
    response = textract_client.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': s3_bucket,
                'Name': s3_key
            }
        },
        NotificationChannel={
            'SNSTopicArn': sns_topic_arn,
            'RoleArn': role_arn
        }
    )

    textract_job_id = response['JobId']
    
    return {
        'textract_job_id': textract_job_id,
        's3_key': s3_key,
        's3_bucket': s3_bucket
    }


async def get_async_results(
    textract_client,
    s3_client,
    job_id: str,
    s3_key: str,
    s3_bucket: str
) -> dict:
    """Get results from async Textract job"""
    lines = []
    next_token = None
    
    while True:
        if next_token:
            response = textract_client.get_document_text_detection(
                JobId=job_id,
                NextToken=next_token,
                MaxResults=1000
            )
        else:
            response = textract_client.get_document_text_detection(
                JobId=job_id,
                MaxResults=1000
            )
        
        # Extract lines
        for block in response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text = block.get('Text')
                if text:
                    lines.append(text)
        
        # Check for more pages
        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break
    
    # Clean up S3
    try:
        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
    except:
        pass
    
    return {
        'num_lines': len(lines),
        'preview': '\n'.join(lines[:15]),
        'full_text': '\n'.join(lines)
    }