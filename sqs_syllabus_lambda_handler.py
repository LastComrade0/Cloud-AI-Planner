"""
Lambda handler for SQS-triggered syllabus processing.

Set handler to: sqs_syllabus_lambda_handler.lambda_handler
(Package the project root so `app` and `config` resolve.)
"""
from app.services.syllabus_job_worker import sqs_lambda_handler as lambda_handler

__all__ = ["lambda_handler"]
