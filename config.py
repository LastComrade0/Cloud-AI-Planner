import os
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Configuration - Set these as environment variables or update directly
AWS_REGION = os.getenv('AWS_REGION', 'us-west-1')
S3_BUCKET = os.getenv('TEXTRACT_S3_BUCKET', 'your-textract-bucket')
SNS_TOPIC_ARN = os.getenv('TEXTRACT_SNS_TOPIC_ARN', 'arn:aws:sns:region:account:topic-name')
SQS_QUEUE_URL = os.getenv('TEXTRACT_SQS_QUEUE_URL', 'https://sqs.region.amazonaws.com/account/queue-name')
TEXTRACT_ROLE_ARN = os.getenv('TEXTRACT_ROLE_ARN', 'arn:aws:iam::account:role/textract-role')
# Optional: when set, POST /upload_syllabus enqueues work here and returns 202 (run syllabus_worker.py or Lambda)
SYLLABUS_PROCESSING_QUEUE_URL = os.getenv('SYLLABUS_PROCESSING_QUEUE_URL', '').strip()

# AWS Clients
textract = boto3.client('textract', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)
sqs_client = boto3.client('sqs', region_name=AWS_REGION)

#OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")