import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="assignments")
    rubric_criteria = relationship("RubricCriteria", back_populates="assignment", order_by="RubricCriteria.order_index")
    submissions = relationship("Submission", back_populates="assignment")


class RubricCriteria(Base):
    __tablename__ = "rubric_criteria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    category = Column(String, nullable=False)        # e.g. "Presentation Quality"
    description = Column(Text, nullable=True)        # what the AI should look for
    max_score = Column(Integer, nullable=False, default=10)
    order_index = Column(Integer, nullable=False, default=0)

    assignment = relationship("Assignment", back_populates="rubric_criteria")
    feedback_scores = relationship("FeedbackScore", back_populates="criteria")
