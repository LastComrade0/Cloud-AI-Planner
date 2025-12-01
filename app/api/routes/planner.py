from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user
from app.models.db_models import PlannerItem, Course, User
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["planner"])


class PlannerItemUpdate(BaseModel):
    """Fields that can be updated on a planner item."""
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    end_date: Optional[date] = None
    item_type: Optional[str] = None
    weight: Optional[float] = None
    is_completed: Optional[bool] = None


def _serialize_planner_item(item: PlannerItem) -> dict:
    """Serialize PlannerItem to the shape expected by the frontend."""
    course = item.course
    return {
        "id": str(item.id),
        "title": item.title,
        "description": item.description,
        "date": item.date,
        "end_date": item.end_date,
        "item_type": item.item_type,
        "weight": float(item.weight) if item.weight is not None else None,
        "source_type": item.source_type,
        "source_ref": item.source_ref,
        "is_completed": item.is_completed,
        "course": {
            "id": str(course.id) if course else None,
            "course_code": course.course_code if course else None,
            "course_name": course.course_name if course else None,
        },
    }


@router.get("/planner")
def get_planner(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Return all planner items for the current user,
    optionally filtered by date range.
    """

    q = db.query(PlannerItem).filter(PlannerItem.user_id == user.id)

    if from_date:
        q = q.filter(PlannerItem.date >= from_date)
    if to_date:
        q = q.filter(PlannerItem.date <= to_date)

    q = q.order_by(PlannerItem.date.asc().nulls_last(), PlannerItem.created_at.asc())

    items = q.all()

    # join course info for convenience
    # (could also do joinedload, but simple version first)
    results = [_serialize_planner_item(item) for item in items]

    return {
        "user_id": str(user.id),
        "user_email": user.email,
        "items": results
    }


@router.patch("/planner/{item_id}")
def update_planner_item(
    item_id: UUID,
    payload: PlannerItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a single planner item for the current user.
    Only fields provided in the payload will be updated.
    """
    item = (
        db.query(PlannerItem)
        .filter(PlannerItem.id == item_id, PlannerItem.user_id == user.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planner item not found",
        )

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return _serialize_planner_item(item)


@router.delete("/planner/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planner_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a single planner item for the current user."""
    item = (
        db.query(PlannerItem)
        .filter(PlannerItem.id == item_id, PlannerItem.user_id == user.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planner item not found",
        )

    db.delete(item)
    db.commit()


@router.delete("/planner", status_code=status.HTTP_204_NO_CONTENT)
def purge_planner(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Delete all planner items for the current user.
    Does not affect courses/documents, only planner entries.
    """
    db.query(PlannerItem).filter(PlannerItem.user_id == user.id).delete()
    db.commit()
