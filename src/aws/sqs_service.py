from __future__ import annotations

import json
from typing import Any

from src.aws.clients import create_aws_client
from src.config.settings import Settings, get_settings


class SqsQueueService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        queue_url: str | None = None,
        job_type: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._default_queue_url = queue_url
        if self._default_queue_url is None and job_type:
            self._default_queue_url = self._queue_url_for_job_type(job_type)
        if self._default_queue_url is None:
            self._default_queue_url = self.settings.sqs_queue_url
        if job_type and not self._default_queue_url:
            raise RuntimeError(f"No SQS queue configured for worker job type {job_type!r}.")
        self._client: Any | None = None

    @property
    def queue_url(self) -> str:
        if not self._default_queue_url:
            raise RuntimeError("No default SQS queue URL is configured for this service instance.")
        return self._default_queue_url

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = create_aws_client("sqs", self.settings)
        return self._client

    def send_analysis_job(self, payload: dict[str, Any]) -> str | None:
        job_type = str(payload.get("job_type", "")).strip() or None
        queue_url = self._queue_url_for_job_type(job_type) if job_type else self.settings.sqs_queue_url
        if not queue_url:
            raise RuntimeError("No SQS queue URL configured for analysis job enqueue.")
        response = self.client.send_message(
            QueueUrl=queue_url,
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

    def _queue_url_for_job_type(self, job_type: str | None) -> str | None:
        if job_type == "submission_analysis":
            return self.settings.sqs_queue_url_submission or self.settings.sqs_queue_url
        if job_type == "git_analysis":
            return self.settings.sqs_queue_url_git or self.settings.sqs_queue_url
        if job_type == "ppt_analysis":
            return self.settings.sqs_queue_url_ppt or self.settings.sqs_queue_url
        if job_type == "video_analysis":
            return self.settings.sqs_queue_url_video or self.settings.sqs_queue_url
        if job_type == "final_grading_analysis":
            return self.settings.sqs_queue_url_final_grading or self.settings.sqs_queue_url
        return self.settings.sqs_queue_url
