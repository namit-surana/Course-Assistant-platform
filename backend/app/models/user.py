import uuid
from sqlalchemy import Column, String, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    professor = "professor"
    ta = "ta"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    google_id = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)       # professors only
    cognito_sub = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    courses_owned = relationship("Course", back_populates="professor")
    team_memberships = relationship("TeamMember", back_populates="user")
    course_memberships = relationship("CourseMember", back_populates="user")
