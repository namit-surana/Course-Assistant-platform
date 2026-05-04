from __future__ import annotations

import logging
import time
from typing import Any

from botocore.exceptions import ClientError

from src.aws.clients import create_aws_client
from src.config.settings import Settings

logger = logging.getLogger(__name__)


def bootstrap_local_aws_resources(settings: Settings) -> None:
    """
    Ensure localstack resources needed by the app exist.
    Safe to call multiple times.
    """
    endpoint = (settings.aws_endpoint_url or "").lower()
    if "localstack" not in endpoint and "localhost:4566" not in endpoint:
        return
    if not settings.s3_bucket_name:
        return

    s3 = create_aws_client("s3", settings)
    sqs = create_aws_client("sqs", settings)

    _ensure_bucket_with_retries(s3, settings.s3_bucket_name, settings.aws_region)
    _ensure_bucket_cors(s3, settings.s3_bucket_name, settings.cors_allowed_origins)
    if settings.sqs_queue_url:
        queue_name = settings.sqs_queue_url.rstrip("/").split("/")[-1]
        _ensure_queue_exists(sqs, queue_name)


def _ensure_bucket_with_retries(s3: Any, bucket: str, region: str, retries: int = 8) -> None:
    for attempt in range(1, retries + 1):
        try:
            s3.create_bucket(Bucket=bucket)
            logger.info("Created S3 bucket %s", bucket)
            return
        except ClientError as exc:
            code = (exc.response or {}).get("Error", {}).get("Code", "")
            if code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                return
            if attempt == retries:
                raise
            time.sleep(min(0.5 * attempt, 2.0))
        except Exception:
            if attempt == retries:
                raise
            time.sleep(min(0.5 * attempt, 2.0))


def _ensure_queue_exists(sqs: Any, queue_name: str) -> None:
    if not queue_name:
        return
    try:
        sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                "VisibilityTimeout": "1800",
                "MessageRetentionPeriod": "345600",
            },
        )
        logger.info("Ensured SQS queue %s exists", queue_name)
    except Exception:
        logger.exception("Could not ensure SQS queue %s exists", queue_name)


def _ensure_bucket_cors(s3: Any, bucket: str, origins: list[str]) -> None:
    allowed_origins = sorted({origin for origin in origins if origin.startswith("http")})
    if not allowed_origins:
        return
    cors = {
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["PUT", "POST", "GET", "HEAD"],
                "AllowedOrigins": allowed_origins,
                "ExposeHeaders": ["ETag", "x-amz-request-id", "x-amz-id-2"],
                "MaxAgeSeconds": 3000,
            }
        ]
    }
    try:
        s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors)
        logger.info("Ensured bucket CORS for %s", bucket)
    except Exception:
        logger.exception("Could not apply CORS on bucket %s", bucket)
