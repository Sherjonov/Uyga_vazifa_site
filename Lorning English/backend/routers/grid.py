from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from deps import get_db, require_role, get_group_for_teacher, get_group_for_member, is_member
from messages import AppError
from models.grid import GridColumn, GridCell
from models.group import Group, GroupMember
from models.user import User
from schemas.grid import ColumnIn, CellIn
from services import scoring

router = APIRouter(prefix="/grid", tags=["grid"])


def _column_for_teacher(db: Session, column_id: int, user: User) -> GridColumn:
    col = db.get(GridColumn, column_id)
    if not col:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, col.group_id, user)
    return col


@router.get("/{group_id}")
def get_grid(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    g = get_group_for_teacher(db, group_id, user)
    cols = db.scalars(select(GridColumn).where(GridColumn.group_id == group_id).order_by(GridColumn.position, GridColumn.id)).all()
    students = db.scalars(
        select(User).join(GroupMember, GroupMember.student_id == User.id).where(GroupMember.group_id == group_id).order_by(User.name)
    ).all()
    cells = db.scalars(select(GridCell).where(GridCell.column_id.in_([c.id for c in cols] or [0]))).all()
    max_score = scoring.get_teacher_settings(db, g.teacher_id).grid_max_score
    db.commit()
    return {
        "max_score": max_score,
        "group": {"id": g.id, "name": g.name, "kind": g.kind},
        "columns": [{"id": c.id, "title": c.title, "position": c.position} for c in cols],
        "students": [{"id": s.id, "name": s.name, "phone": s.phone} for s in students],
        "cells": {f"{c.column_id}_{c.student_id}": c.value for c in cells},
    }


@router.get("/{group_id}/me")
def my_grades(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    get_group_for_member(db, group_id, user)
    cols = db.scalars(select(GridColumn).where(GridColumn.group_id == group_id).order_by(GridColumn.position, GridColumn.id)).all()
    cells = {
        c.column_id: c.value
        for c in db.scalars(select(GridCell).where(GridCell.student_id == user.id, GridCell.column_id.in_([c.id for c in cols] or [0]))).all()
    }
    return [{"column_id": c.id, "title": c.title, "value": cells.get(c.id, "")} for c in cols]


@router.post("/{group_id}/columns")
def add_column(group_id: int, data: ColumnIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    get_group_for_teacher(db, group_id, user)
    last = db.scalar(select(func.coalesce(func.max(GridColumn.position), 0)).where(GridColumn.group_id == group_id))
    col = GridColumn(group_id=group_id, title=data.title.strip(), position=(last or 0) + 1)
    db.add(col)
    db.commit()
    return {"id": col.id, "title": col.title, "position": col.position}


@router.put("/columns/{column_id}")
def rename_column(column_id: int, data: ColumnIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    col = _column_for_teacher(db, column_id, user)
    col.title = data.title.strip()
    db.commit()
    return {"id": col.id, "title": col.title}


@router.delete("/columns/{column_id}")
def delete_column(column_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    col = _column_for_teacher(db, column_id, user)
    affected = list(db.scalars(select(GridCell.student_id).where(GridCell.column_id == col.id)).all())
    db.delete(col)
    db.flush()
    for student_id in set(affected):
        scoring.recalculate(db, student_id)
    db.commit()
    return {"ok": True}


@router.put("/cells")
def set_cell(data: CellIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    col = _column_for_teacher(db, data.column_id, user)
    if not is_member(db, col.group_id, data.student_id):
        raise AppError(400, "not_in_group")
    cell = db.scalar(select(GridCell).where(GridCell.column_id == col.id, GridCell.student_id == data.student_id))
    value = data.value.strip()
    # Ball chegarasi: o'qituvchi sozlamalarida (standart 50). Raqam bo'lsa 0..chegara oralig'ida bo'lishi shart.
    limit = scoring.get_teacher_settings(db, db.get(Group, col.group_id).teacher_id).grid_max_score
    try:
        number = float(value.replace(",", ".")) if value else None
    except ValueError:
        number = None
    if number is not None and not (0 <= number <= limit):
        raise AppError(400, "grade_too_high", max=int(limit) if float(limit).is_integer() else limit)
    if not value:
        if cell:
            db.delete(cell)
    elif cell:
        cell.value = value
    else:
        db.add(GridCell(column_id=col.id, student_id=data.student_id, value=value))
    scoring.recalculate(db, data.student_id)
    db.commit()
    return {"column_id": col.id, "student_id": data.student_id, "value": value}
