#!/usr/bin/env python3
"""
Long-poll SQS and process syllabus jobs. Requires SYLLABUS_PROCESSING_QUEUE_URL and same env as the API.

Usage:
  python syllabus_worker.py
"""
import logging
import sys
import time

from app.services.syllabus_job_worker import handle_sqs_record_body
from config import SYLLABUS_PROCESSING_QUEUE_URL, sqs_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("syllabus_worker")


def main() -> None:
    if not SYLLABUS_PROCESSING_QUEUE_URL:
        logger.error("SYLLABUS_PROCESSING_QUEUE_URL is not set; nothing to poll.")
        sys.exit(1)

    logger.info("Polling %s", SYLLABUS_PROCESSING_QUEUE_URL)
    while True:
        try:
            resp = sqs_client.receive_message(
                QueueUrl=SYLLABUS_PROCESSING_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=20,
                VisibilityTimeout=300,
            )
        except Exception:
            logger.exception("receive_message failed; retrying in 5s")
            time.sleep(5)
            continue

        messages = resp.get("Messages") or []
        for msg in messages:
            body = msg.get("Body", "{}")
            receipt = msg.get("ReceiptHandle")
            try:
                handle_sqs_record_body(body)
                if receipt:
                    sqs_client.delete_message(
                        QueueUrl=SYLLABUS_PROCESSING_QUEUE_URL,
                        ReceiptHandle=receipt,
                    )
            except Exception:
                logger.exception("Failed processing message; leaving for retry after visibility timeout")


if __name__ == "__main__":
    main()
