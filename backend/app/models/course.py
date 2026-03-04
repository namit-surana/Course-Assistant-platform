import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class CourseMemberRole(str, enum.Enum):
    ta = "ta"
    student = "student"


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    professor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    professor = relationship("User", back_populates="courses_owned")
    members = relationship("CourseMember", back_populates="course")
    assignments = relationship("Assignment", back_populates="course")
    teams = relationship("Team", back_populates="course")


class CourseMember(Base):
    __tablename__ = "course_members"

    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(Enum(CourseMemberRole), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="members")
    user = relationship("User", back_populates="course_memberships")
