import json
import boto3
from app.config import get_settings

settings = get_settings()

sqs_client = boto3.client(
    "sqs",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def publish_analysis_job(submission_id: str, ppt_s3_key: str, video_s3_key: str,
                          github_url: str, rubric_criteria: list) -> None:
    payload = {
        "submission_id": submission_id,
        "ppt_s3_key": ppt_s3_key,
        "video_s3_key": video_s3_key,
        "github_url": github_url,
        "rubric_criteria": rubric_criteria,
    }
    sqs_client.send_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MessageBody=json.dumps(payload),
    )


def receive_messages(max_number: int = 1, wait_time: int = 20) -> list:
    response = sqs_client.receive_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MaxNumberOfMessages=max_number,
        WaitTimeSeconds=wait_time,
    )
    return response.get("Messages", [])


def delete_message(receipt_handle: str) -> None:
    sqs_client.delete_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )
