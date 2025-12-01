import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Numeric, Boolean,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cognito_sub = Column(String, unique=True, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    courses = relationship("Course", back_populates="user")
    documents = relationship("Document", back_populates="user")
    planner_items = relationship("PlannerItem", back_populates="user")


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    course_code = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    instructor = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    year = Column(String, nullable=True)
    credits = Column(Numeric, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="courses")
    planner_items = relationship("PlannerItem", back_populates="course")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    doc_type = Column(String, nullable=False)      # 'syllabus', 'email', 'poster', ...
    source_label = Column(String, nullable=True)   # filename, email subject, etc.
    s3_object_key = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="documents")
    planner_items = relationship("PlannerItem", back_populates="document")


class PlannerItem(Base):
    __tablename__ = "planner_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    item_type = Column(String, nullable=False)     # 'assignment', 'exam', 'event', ...
    weight = Column(Numeric, nullable=True)

    source_type = Column(String, nullable=False)   # 'syllabus', 'email', 'poster', 'manual'
    source_ref = Column(String, nullable=True)

    is_completed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="planner_items")
    course = relationship("Course", back_populates="planner_items")
    document = relationship("Document", back_populates="planner_items")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    job_id = Column(String, nullable=False, unique=True)  # Textract job ID or our internal job ID
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    
    status = Column(String, nullable=False, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    textract_job_id = Column(String, nullable=True)  # AWS Textract job ID
    
    error_message = Column(Text, nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)  # Link to final document
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")
    document = relationship("Document")