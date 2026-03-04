import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, Enum, Float, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class FeedbackSource(str, enum.Enum):
    ai = "ai"
    ta = "ta"
    professor = "professor"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id"), unique=True, nullable=False)
    generated_by = Column(Enum(FeedbackSource), nullable=False, default=FeedbackSource.ai)
    overall_comment = Column(Text, nullable=True)
    total_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submission = relationship("Submission", back_populates="feedback")
    scores = relationship("FeedbackScore", back_populates="feedback")


class FeedbackScore(Base):
    __tablename__ = "feedback_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(UUID(as_uuid=True), ForeignKey("feedback.id"), nullable=False)
    criteria_id = Column(UUID(as_uuid=True), ForeignKey("rubric_criteria.id"), nullable=False)
    score = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)           # AI explanation for this score
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback = relationship("Feedback", back_populates="scores")
    criteria = relationship("RubricCriteria", back_populates="feedback_scores")
    override = relationship("FeedbackOverride", back_populates="feedback_score", uselist=False)


class FeedbackOverride(Base):
    __tablename__ = "feedback_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_score_id = Column(UUID(as_uuid=True), ForeignKey("feedback_scores.id"), unique=True, nullable=False)
    overridden_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_score = Column(Float, nullable=False)
    new_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    overridden_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback_score = relationship("FeedbackScore", back_populates="override")
