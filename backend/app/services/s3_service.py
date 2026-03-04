import boto3
from app.config import get_settings

settings = get_settings()

s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def generate_presigned_upload_url(key: str, content_type: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for direct browser-to-S3 upload."""
    return s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def download_file(key: str, local_path: str) -> None:
    s3_client.download_file(settings.S3_BUCKET_NAME, key, local_path)
