from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.aws.clients import create_aws_client
from src.config.settings import Settings, get_settings


_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def build_upload_object_key(kind: str, file_name: str, submission_id: str | None = None) -> str:
    cleaned_name = _SAFE_FILENAME_PATTERN.sub("-", Path(file_name).name).strip(".-")
    if not cleaned_name:
        cleaned_name = "upload"
    owner = submission_id or uuid4().hex
    return f"submissions/{owner}/{kind}/{uuid4().hex}-{cleaned_name}"


class S3StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured.")
        self._client: Any | None = None

    @property
    def bucket_name(self) -> str:
        return self.settings.s3_bucket_name or ""

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = create_aws_client("s3", self.settings)
        return self._client

    def create_presigned_put_url(self, object_key: str, content_type: str) -> dict[str, Any]:
        upload_url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=self.settings.s3_presign_expires_seconds,
        )
        if self.settings.aws_endpoint_url and self.settings.aws_public_endpoint_url:
            upload_url = upload_url.replace(
                self.settings.aws_endpoint_url.rstrip("/"),
                self.settings.aws_public_endpoint_url.rstrip("/"),
                1,
            )
        return {
            "upload_url": upload_url,
            "method": "PUT",
            "bucket": self.bucket_name,
            "object_key": object_key,
            "headers": {"Content-Type": content_type},
            "expires_in": self.settings.s3_presign_expires_seconds,
        }

    def download_file(self, object_key: str, destination: str | Path) -> None:
        self.client.download_file(self.bucket_name, object_key, str(destination))
