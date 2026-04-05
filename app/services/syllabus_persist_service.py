from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.db_models import User, Course, Document, PlannerItem
from app.models.schemas import ParsedSyllabus
from config import OPENAI_API_KEY
import logging

logger = logging.getLogger(__name__)


def get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).first()
    if user:
        return user
    user = User(email="demo@example.com", cognito_sub=None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def parse_date_string(date_str: str | None) -> date | None:
    """
    Parse a date string into a date object.
    Handles various formats and invalid dates gracefully.
    Returns None if the date cannot be parsed.
    """
    if not date_str:
        return None
    
    # If it's already a date object, return it
    if isinstance(date_str, date):
        return date_str
    
    # If it's not a string, return None
    if not isinstance(date_str, str):
        return None
    
    # Remove leading/trailing whitespace
    date_str = date_str.strip()
    
    # If it's empty or looks like a description (not a date), return None
    if not date_str or len(date_str) > 50:  # Dates shouldn't be that long
        return None
    
    # Common date formats to try
    date_formats = [
        "%Y-%m-%d",           # 2025-10-15
        "%m/%d/%Y",           # 10/15/2025
        "%m-%d-%Y",           # 10-15-2025
        "%d/%m/%Y",           # 15/10/2025
        "%d-%m-%Y",           # 15-10-2025
        "%Y/%m/%d",           # 2025/10/15
        "%B %d, %Y",          # October 15, 2025
        "%b %d, %Y",          # Oct 15, 2025
        "%d %B %Y",           # 15 October 2025
        "%d %b %Y",           # 15 Oct 2025
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt).date()
            return parsed_date
        except ValueError:
            continue
    
    # If all formats fail, return None (invalid date)
    return None


def save_parsed_syllabus_to_planner(
    db: Session,
    parsed: ParsedSyllabus,
    user: User,
    doc_type: str = "syllabus",
    source_label: str | None = None,
    s3_object_key: str | None = None,
) -> Document:
    try:
        print(f"🔵 save_parsed_syllabus_to_planner called for user {user.id}, source: {source_label}")
        logger.info(f"Saving syllabus to database for user {user.id}, source: {source_label}")
        
        # Check if this document was already processed (prevent duplicates)
        if source_label:
            existing_doc = (
                db.query(Document)
                .filter(
                    Document.user_id == user.id,
                    Document.doc_type == doc_type,
                    Document.source_label == source_label,
                )
                .first()
            )
            if existing_doc:
                print(f"⚠️ Document already exists: {existing_doc.id} - returning existing document")
                logger.info(f"Document already exists: {existing_doc.id}")
                # Document already processed, return it without creating duplicates
                return existing_doc

        # 1) Optional course
        course = None
        if parsed.course:
            course = (
                db.query(Course)
                .filter(
                    Course.user_id == user.id,
                    Course.course_code == parsed.course.course_code,
                    Course.course_name == parsed.course.course_name,
                )
                .one_or_none()
            )
            if course is None:
                logger.info(f"Creating new course: {parsed.course.course_code}")
                course = Course(
                    user_id=user.id,
                    course_code=parsed.course.course_code,
                    course_name=parsed.course.course_name,
                    instructor=parsed.course.instructor,
                    semester=parsed.course.semester,
                    year=str(parsed.course.year) if parsed.course.year else None,
                    credits=parsed.course.credits,
                )
                db.add(course)
                db.flush()
                logger.info(f"Course created with ID: {course.id}")

        # 2) Document row
        logger.info("Creating document record")
        doc = Document(
            user_id=user.id,
            doc_type=doc_type,
            source_label=source_label,
            s3_object_key=s3_object_key,
            raw_text=parsed.raw_text,
        )
        db.add(doc)
        db.flush()
        logger.info(f"Document created with ID: {doc.id}")

        # 3) Assignments → planner_items (with duplicate check)
        logger.info(f"Processing {len(parsed.assignments)} assignments")
        for a in parsed.assignments:
            # Parse the date string to a date object
            parsed_date = parse_date_string(a.due_date)
            
            # Check if this assignment already exists
            # Build filter conditions
            filter_conditions = [
                PlannerItem.user_id == user.id,
                PlannerItem.course_id == (course.id if course else None),
                PlannerItem.title == a.name,
                PlannerItem.item_type == "assignment",
            ]
            
            # Only filter by date if we have a valid parsed date
            if parsed_date:
                filter_conditions.append(PlannerItem.date == parsed_date)
            else:
                # If date is invalid, only match items with null date
                filter_conditions.append(PlannerItem.date.is_(None))
            
            existing_item = (
                db.query(PlannerItem)
                .filter(*filter_conditions)
                .first()
            )
            
            if not existing_item:
                item = PlannerItem(
                    user_id=user.id,
                    course_id=course.id if course else None,
                    document_id=doc.id,
                    title=a.name,
                    description=a.description,
                    date=parsed_date,  # Use parsed date (None if invalid)
                    item_type="assignment",
                    weight=a.weight,
                    source_type=doc_type,       # 'syllabus'
                    source_ref=source_label,
                )
                db.add(item)
                logger.debug(f"Added assignment: {a.name}")

        # 4) Reminders → planner_items (with duplicate check)
        logger.info(f"Processing {len(parsed.reminders)} reminders")
        for r in parsed.reminders:
            # Parse the date string to a date object
            parsed_date = parse_date_string(r.date)
            
            # Check if this reminder already exists
            # Build filter conditions
            filter_conditions = [
                PlannerItem.user_id == user.id,
                PlannerItem.course_id == (course.id if course else None),
                PlannerItem.title == r.title,
                PlannerItem.item_type == "reminder",
            ]
            
            # Only filter by date if we have a valid parsed date
            if parsed_date:
                filter_conditions.append(PlannerItem.date == parsed_date)
            else:
                # If date is invalid, only match items with null date
                filter_conditions.append(PlannerItem.date.is_(None))
            
            existing_item = (
                db.query(PlannerItem)
                .filter(*filter_conditions)
                .first()
            )
            
            if not existing_item:
                item = PlannerItem(
                    user_id=user.id,
                    course_id=course.id if course else None,
                    document_id=doc.id,
                    title=r.title,
                    description=r.description,
                    date=parsed_date,  # Use parsed date (None if invalid)
                    item_type="reminder",       # or 'event' if you want
                    source_type=doc_type,
                    source_ref=source_label,
                )
                db.add(item)
                logger.debug(f"Added reminder: {r.title}")

        print(f"🔵 About to commit transaction. Document ID will be: {doc.id}")
        print(f"🔵 Assignments to save: {len(parsed.assignments)}")
        print(f"🔵 Reminders to save: {len(parsed.reminders)}")
        print(f"🔵 Total planner items added: {len([i for i in db.new if isinstance(i, PlannerItem)])}")
        logger.info("Committing database transaction")
        
        # Force flush before commit to ensure all objects are in the session
        db.flush()
        print(f"🔵 Flushed pending changes to database")
        
        try:
            db.commit()
            print(f"✅ Transaction committed successfully")
            # Verify commit by checking if we can still access the document
            db.refresh(doc)
            print(f"✅ Document refreshed after commit. Final ID: {doc.id}")
        except Exception as commit_error:
            print(f"❌ COMMIT FAILED: {str(commit_error)}")
            import traceback
            print(traceback.format_exc())
            db.rollback()
            print(f"🔄 Rolled back transaction due to commit error")
            raise
        
        logger.info(f"Successfully saved document {doc.id} with {len(parsed.assignments)} assignments and {len(parsed.reminders)} reminders")
        print(f"✅ Returning document {doc.id}")
        return doc
        
    except SQLAlchemyError as e:
        print(f"❌ SQLAlchemyError: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Database error while saving syllabus: {str(e)}", exc_info=True)
        db.rollback()
        print("🔄 Transaction rolled back due to SQLAlchemyError")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Unexpected error while saving syllabus: {str(e)}", exc_info=True)
        db.rollback()
        print("🔄 Transaction rolled back due to unexpected error")
        raise
