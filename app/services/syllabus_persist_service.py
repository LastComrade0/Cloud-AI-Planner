from sqlalchemy.orm import Session
from app.models.db_models import User, Course, Document, PlannerItem
from app.models.schemas import ParsedSyllabus
from config import OPENAI_API_KEY


def get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).first()
    if user:
        return user
    user = User(email="demo@example.com", cognito_sub=None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_parsed_syllabus_to_planner(
    db: Session,
    parsed: ParsedSyllabus,
    user: User,
    doc_type: str = "syllabus",
    source_label: str | None = None,
    s3_object_key: str | None = None,
) -> Document:
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

    # 2) Document row
    doc = Document(
        user_id=user.id,
        doc_type=doc_type,
        source_label=source_label,
        s3_object_key=s3_object_key,
        raw_text=parsed.raw_text,
    )
    db.add(doc)
    db.flush()

    # 3) Assignments → planner_items (with duplicate check)
    for a in parsed.assignments:
        # Check if this assignment already exists
        existing_item = (
            db.query(PlannerItem)
            .filter(
                PlannerItem.user_id == user.id,
                PlannerItem.course_id == (course.id if course else None),
                PlannerItem.title == a.name,
                PlannerItem.date == a.due_date,
                PlannerItem.item_type == "assignment",
            )
            .first()
        )
        
        if not existing_item:
            item = PlannerItem(
                user_id=user.id,
                course_id=course.id if course else None,
                document_id=doc.id,
                title=a.name,
                description=a.description,
                date=a.due_date,
                item_type="assignment",
                weight=a.weight,
                source_type=doc_type,       # 'syllabus'
                source_ref=source_label,
            )
            db.add(item)

    # 4) Reminders → planner_items (with duplicate check)
    for r in parsed.reminders:
        # Check if this reminder already exists
        existing_item = (
            db.query(PlannerItem)
            .filter(
                PlannerItem.user_id == user.id,
                PlannerItem.course_id == (course.id if course else None),
                PlannerItem.title == r.title,
                PlannerItem.date == r.date,
                PlannerItem.item_type == "reminder",
            )
            .first()
        )
        
        if not existing_item:
            item = PlannerItem(
                user_id=user.id,
                course_id=course.id if course else None,
                document_id=doc.id,
                title=r.title,
                description=r.description,
                date=r.date,
                item_type="reminder",       # or 'event' if you want
                source_type=doc_type,
                source_ref=source_label,
            )
            db.add(item)

    db.commit()
    db.refresh(doc)
    return doc
