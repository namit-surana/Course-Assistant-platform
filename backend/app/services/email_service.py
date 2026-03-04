import boto3
from app.config import get_settings

settings = get_settings()

ses_client = boto3.client(
    "ses",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def send_feedback_ready_email(to_emails: list[str], team_name: str, assignment_title: str,
                               feedback_url: str) -> None:
    body = f"""
Hi {team_name},

Your AI feedback for "{assignment_title}" is ready!

View your feedback here: {feedback_url}

This feedback was generated automatically. Your TA or professor may adjust scores.

Best,
CourseWork Eval Platform
    """.strip()

    ses_client.send_email(
        Source=settings.SES_SENDER_EMAIL,
        Destination={"ToAddresses": to_emails},
        Message={
            "Subject": {"Data": f"Feedback Ready: {assignment_title}"},
            "Body": {"Text": {"Data": body}},
        },
    )
