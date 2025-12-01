from datetime import date

from app.db.session import SessionLocal
from app.models.db_models import User, Course, Document, PlannerItem


def main():
    db = SessionLocal()
    try:
        # 1. Create a user
        user = User(email="demo@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        print("User id:", user.id)

        # 2. Create a course
        course = Course(
            user_id=user.id,
            course_code="CS 686",
            course_name="Cloud Computing",
            instructor="Mario Lim Kam",
            semester="Fall",
            year="2025",
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        print("Course id:", course.id)

        # 3. Create a document (fake syllabus text)
        doc = Document(
            user_id=user.id,
            doc_type="syllabus",
            source_label="cs686_syllabus.pdf",
            raw_text="UNIVERSITY OF SAN FRANCISCO\nCS 686 Cloud Computing syllabus...",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        print("Document id:", doc.id)

        # 4. Create a planner item (Midterm)
        item = PlannerItem(
            user_id=user.id,
            course_id=course.id,
            document_id=doc.id,
            title="Midterm Presentation",
            description="Present project progress",
            date=date(2025, 10, 15),
            item_type="assignment",
            weight=25,
            source_type="syllabus",
            source_ref="cs686_syllabus.pdf",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        print("Planner item id:", item.id)

        # 5. Query back
        items = (
            db.query(PlannerItem)
            .filter(PlannerItem.user_id == user.id)
            .order_by(PlannerItem.date.asc())
            .all()
        )
        print("Planner items for user:")
        for it in items:
            print(" -", it.date, it.title, it.item_type)

    finally:
        db.close()


if __name__ == "__main__":
    main()
