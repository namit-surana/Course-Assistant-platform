from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Any

from src.aws.sqs_service import SqsQueueService
from src.config.settings import get_settings
from src.utils.logging import configure_logging
from src.worker.processor import process_analysis_job


logger = logging.getLogger(__name__)


def run_worker_once() -> int:
    settings = get_settings()
    queue = SqsQueueService(settings)
    processed = 0
    try:
        messages = queue.receive_analysis_jobs()
    except Exception:
        logger.exception("Unable to receive SQS messages")
        return processed
    for message in messages:
        if _process_message(queue, message):
            processed += 1
    return processed


def run_worker_forever() -> None:
    settings = get_settings()
    queue = SqsQueueService(settings)
    logger.info("Worker polling SQS queue")
    while True:
        processed = 0
        try:
            messages = queue.receive_analysis_jobs()
        except Exception:
            logger.exception("Unable to receive SQS messages; retrying")
            time.sleep(settings.worker_idle_sleep_seconds)
            continue
        for message in messages:
            if _process_message(queue, message):
                processed += 1
        if processed == 0:
            time.sleep(settings.worker_idle_sleep_seconds)


def _process_message(queue: SqsQueueService, message: dict[str, Any]) -> bool:
    receipt_handle = message.get("ReceiptHandle")
    try:
        payload = json.loads(message.get("Body", "{}"))
        job_id = payload["job_id"]
        process_analysis_job(job_id)
        if receipt_handle:
            queue.delete_message(receipt_handle)
        logger.info("Processed analysis job %s", job_id)
        return True
    except Exception:
        logger.exception("Failed to process SQS message")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Coursework analysis worker")
    parser.add_argument("--once", action="store_true", help="Poll SQS once and exit.")
    parser.add_argument("--job-id", help="Process a specific DB analysis job without polling SQS.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    if args.job_id:
        process_analysis_job(args.job_id, settings)
        return
    if args.once:
        run_worker_once()
        return
    run_worker_forever()


if __name__ == "__main__":
    main()
