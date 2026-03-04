"""
Analysis Worker — runs as a separate ECS Fargate service.
Polls SQS continuously, processes one job at a time.
"""
import json
import time
import tempfile
import logging
from app.services.sqs_service import receive_messages, delete_message
from app.services.s3_service import download_file
from app.services.email_service import send_feedback_ready_email
from app.worker.analyzers.ppt_analyzer import analyze_ppt
from app.worker.analyzers.video_analyzer import analyze_video
from app.worker.analyzers.github_analyzer import analyze_github
from app.database import SessionLocal
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_job(job: dict) -> None:
    submission_id = job["submission_id"]
    db = SessionLocal()

    try:
        submission = db.query(models.Submission).filter_by(id=submission_id).first()
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return

        submission.status = models.SubmissionStatus.processing
        db.commit()

        assignment = submission.assignment
        rubric = [
            {"category": c.category, "description": c.description, "max_score": c.max_score}
            for c in assignment.rubric_criteria
        ]

        results = {}

        # PPT analysis
        if job.get("ppt_s3_key"):
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
                download_file(job["ppt_s3_key"], f.name)
                results["ppt"] = analyze_ppt(f.name, rubric)

        # Video analysis
        if job.get("video_s3_key"):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                download_file(job["video_s3_key"], f.name)
                results["video"] = analyze_video(f.name, rubric)

        # GitHub analysis
        if job.get("github_url"):
            results["github"] = analyze_github(job["github_url"], rubric)

        # TODO: merge results + write feedback to DB
        # TODO: send email notification

        submission.status = models.SubmissionStatus.done
        db.commit()
        logger.info(f"Completed analysis for submission {submission_id}")

    except Exception as e:
        logger.error(f"Analysis failed for {submission_id}: {e}")
        if submission:
            submission.status = models.SubmissionStatus.failed
            db.commit()
    finally:
        db.close()


def run_worker() -> None:
    logger.info("Worker started. Polling SQS...")
    while True:
        messages = receive_messages(max_number=1, wait_time=20)
        for msg in messages:
            try:
                job = json.loads(msg["Body"])
                logger.info(f"Processing job: {job.get('submission_id')}")
                process_job(job)
                delete_message(msg["ReceiptHandle"])
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
        if not messages:
            time.sleep(1)


if __name__ == "__main__":
    run_worker()
