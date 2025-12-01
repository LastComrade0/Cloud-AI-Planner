"""Pydantic models for structured syllabus data"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Assignment(BaseModel):
    """Assignment model"""
    name: str = Field(..., description="Assignment name/title")
    due_date: Optional[str] = Field(None, description="Due date in ISO format or readable string")
    weight: Optional[float] = Field(None, description="Assignment weight/percentage (0-100)")
    description: Optional[str] = Field(None, description="Assignment description")

class Reminder(BaseModel):
    """Reminder model"""
    title: str = Field(..., description="Reminder title")
    date: Optional[str] = Field(None, description="Reminder date")
    description: Optional[str] = Field(None, description="Reminder description")

class Course(BaseModel):
    """Course information model"""
    course_code: Optional[str] = Field(None, description="Course code (e.g., CS 686)")
    course_name: Optional[str] = Field(None, description="Course name")
    instructor: Optional[str] = Field(None, description="Instructor name")
    semester: Optional[str] = Field(None, description="Semester/term")
    year: Optional[str] = Field(None, description="Academic year")
    credits: Optional[float] = Field(None, description="Number of credits")


class ParsedSyllabus(BaseModel):
    """Complete parsed syllabus structure"""
    course: Optional[Course] = Field(None, description="Course information")
    assignments: List[Assignment] = Field(default_factory=list, description="List of assignments")
    reminders: List[Reminder] = Field(default_factory=list, description="List of reminders")
    raw_text: Optional[str] = Field(None, description="Original extracted text")