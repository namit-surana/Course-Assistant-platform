import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    processing = "processing"
    done = "done"
    failed = "failed"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    ppt_s3_key = Column(String, nullable=True)
    video_s3_key = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    status = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.submitted)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")
    feedback = relationship("Feedback", back_populates="submission", uselist=False)
