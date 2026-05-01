from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import Settings
from src.db.base import Base
from src.submissions.schemas import ArtifactInput, RubricCriterionInput, SubmissionCreateRequest
from src.submissions.service import create_submission


class FakeQueuePublisher:
    def __init__(self) -> None:
        self.payloads = []

    def send_analysis_job(self, payload):
        self.payloads.append(payload)
        return "message-123"


def test_create_submission_persists_artifact_and_enqueues_job() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    settings = Settings(S3_BUCKET_NAME="uploads", SQS_QUEUE_URL="queue-url")
    queue = FakeQueuePublisher()

    with session_factory() as session:
        created = create_submission(
            session,
            SubmissionCreateRequest(
                team_name="Team Alpha",
                repo_url="https://github.com/octocat/Hello-World",
                branch="main",
                rubric_criteria=[
                    RubricCriterionInput(
                        category="Architecture",
                        description="Evaluate architecture quality.",
                        max_score=10,
                    )
                ],
                artifacts=[
                    ArtifactInput(
                        kind="ppt",
                        object_key="submissions/1/ppt/deck.pptx",
                        file_name="deck.pptx",
                        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    )
                ],
            ),
            settings=settings,
            queue_publisher=queue,
        )

        assert created.queued is True
        assert created.analysis_job.sqs_message_id == "message-123"
        assert queue.payloads == [
            {
                "job_id": created.analysis_job.id,
                "submission_id": created.submission.id,
                "event_id": None,
                "team_name": "Team Alpha",
                "repo_url": "https://github.com/octocat/Hello-World",
                "branch": "main",
            }
        ]
        assert created.submission.artifacts[0].bucket == "uploads"
        assert created.submission.rubric_snapshot[0]["category"] == "Architecture"
