from __future__ import annotations

import json
from typing import Any

from src.aws.clients import create_aws_client
from src.config.settings import Settings, get_settings


class SqsQueueService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.sqs_queue_url:
            raise RuntimeError("SQS_QUEUE_URL is not configured.")
        self._client: Any | None = None

    @property
    def queue_url(self) -> str:
        return self.settings.sqs_queue_url or ""

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = create_aws_client("sqs", self.settings)
        return self._client

    def send_analysis_job(self, payload: dict[str, Any]) -> str | None:
        response = self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(payload),
        )
        return response.get("MessageId")

    def receive_analysis_jobs(self) -> list[dict[str, Any]]:
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=self.settings.worker_max_messages,
            WaitTimeSeconds=self.settings.worker_poll_wait_seconds,
        )
        return response.get("Messages", [])

    def delete_message(self, receipt_handle: str) -> None:
        self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
        )
