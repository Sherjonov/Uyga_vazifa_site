"""Demo ma'lumotlar: python seed.py --demo"""
import argparse
from datetime import timedelta

from sqlalchemy import select

import models  # noqa: F401
from database import Base, engine, SessionLocal
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.grid import GridColumn, GridCell
from models.group import Group, GroupMember
from models.test import Test, Question, TestAttempt
from models.user import User
from security import hash_password
from services import scoring
from utils import utcnow, today

DEMO_PASSWORD = "demo12345"


def _user(db, name, email, phone, role, track="english"):
    u = db.scalar(select(User).where(User.email == email))
    if u:
        return u
    u = User(name=name, email=email, phone=phone, password_hash=hash_password(DEMO_PASSWORD), role=role, track=track,
             onboarded=True, last_seen_at=utcnow(), last_login_at=utcnow())
    db.add(u)
    db.flush()
    return u


def ensure_env_teacher(db) -> None:
    """.env dagi TEACHER_PHONE (yoki TEACHER_EMAIL) + TEACHER_PASSWORD bo'yicha birinchi o'qituvchini yaratadi."""
    from config import settings
    from utils import normalize_identifier
    if not settings.TEACHER_PASSWORD or not (settings.TEACHER_PHONE or settings.TEACHER_EMAIL):
        return
    try:
        phone = normalize_identifier(settings.TEACHER_PHONE)[1] if settings.TEACHER_PHONE else None
        email = normalize_identifier(settings.TEACHER_EMAIL)[1] if settings.TEACHER_EMAIL else None
    except Exception:
        print("[WARN] .env dagi TEACHER_PHONE / TEACHER_EMAIL noto'g'ri formatda.")
        return
    conds = [c for c in ((User.phone == phone) if phone else None, (User.email == email) if email else None) if c is not None]
    from sqlalchemy import or_
    if db.scalar(select(User).where(or_(*conds)).limit(1)):
        return
    db.add(User(name=settings.TEACHER_NAME, phone=phone, email=email, password_hash=hash_password(settings.TEACHER_PASSWORD),
                role="teacher", onboarded=True))
    db.commit()
    print(f"[OK] .env dan o'qituvchi hisobi yaratildi: {phone or email}")


def create_demo(db) -> None:
    if db.scalar(select(User).where(User.email == "teacher@demo.uz")):
        print("[OK] Demo ma'lumotlar allaqachon mavjud.")
        return
    teacher = _user(db, "Demo O'qituvchi", "teacher@demo.uz", "+998900000000", "teacher")
    names = ["Ali Valiyev", "Madina Karimova", "Jasur Toshmatov", "Dilnoza Rahimova", "Sardor Abdullayev"]
    students = [_user(db, n, f"student{i + 1}@demo.uz", f"+99890000000{i + 1}", "student") for i, n in enumerate(names)]
    # Jasur uzoq vaqt kirmagan (Xavf zonasi uchun)
    students[2].last_seen_at = utcnow() - timedelta(days=15)

    group = Group(name="Beginner 1", kind="english", teacher_id=teacher.id)
    db.add(group)
    db.flush()
    for s in students:
        db.add(GroupMember(group_id=group.id, student_id=s.id))
    # Jadval
    c1 = GridColumn(group_id=group.id, title="1-nazorat", position=1)
    c2 = GridColumn(group_id=group.id, title="Mustaqil ish", position=2)
    db.add_all([c1, c2])
    db.flush()
    for s, v1, v2 in zip(students, ["5", "4", "3", "5", "4"], ["4", "5", "2", "5", "3"]):
        db.add(GridCell(column_id=c1.id, student_id=s.id, value=v1))
        db.add(GridCell(column_id=c2.id, student_id=s.id, value=v2))

    # Davomat (sozlamadagi jarima bilan)
    penalty = scoring.get_teacher_settings(db, teacher.id).absence_penalty
    for k, day_offset in enumerate((3, 2, 1)):
        day = today() - timedelta(days=day_offset)
        for idx, s in enumerate(students):
            status = "present"
            if idx == 2:
                status = "absent"            # Jasur: 3 marta sababsiz
            elif idx == 1 and k == 0:
                status = "excused"           # Madina: bir marta sababli (jarima yo'q)
            db.add(Attendance(group_id=group.id, student_id=s.id, date=day, status=status,
                              penalty_applied=penalty if status == "absent" else 0.0))

    # Uyga vazifalar: biri muddati o'tgan, biri kelasi
    past = Assignment(group_id=group.id, teacher_id=teacher.id, kind="homework", title="Kasrlar: 1-10 mashq",
                      description="Darslikdagi 1-10 mashqlarni yeching.", due_at=utcnow() - timedelta(days=2))
    future = Assignment(group_id=group.id, teacher_id=teacher.id, kind="homework", title="Tenglamalar",
                        description="Tenglamalar mavzusini takrorlang.", due_at=utcnow() + timedelta(days=2))
    db.add_all([past, future])
    db.flush()
    for s, score in zip(students[:2] + students[3:], [9, 8, 10]):
        db.add(Submission(assignment_id=past.id, student_id=s.id, text="Yechimlar...", submitted_at=utcnow() - timedelta(days=3),
                          score=score, comment="Yaxshi ish!", reviewed_at=utcnow() - timedelta(days=2)))

    # Test
    test = Test(group_id=group.id, teacher_id=teacher.id, title="Matematika: 1-test", duration_minutes=20, is_published=True)
    db.add(test)
    db.flush()
    qs = [("2 + 2 = ?", ["3", "4", "5", "6"], 1), ("10 / 2 = ?", ["2", "4", "5", "10"], 2), ("3 * 3 = ?", ["6", "8", "9", "12"], 2)]
    qids = []
    for i, (text, opts, ci) in enumerate(qs, 1):
        q = Question(test_id=test.id, position=i, text=text, options=opts, correct_index=ci)
        db.add(q)
        db.flush()
        qids.append((q.id, ci))
    now = utcnow()
    db.add(TestAttempt(test_id=test.id, student_id=students[0].id, status="finished", counted=True, started_at=now - timedelta(hours=2),
                       deadline_at=now - timedelta(hours=1, minutes=40), finished_at=now - timedelta(hours=1, minutes=45),
                       answers={str(q): c for q, c in qids}, correct_count=3, total=3, percent=100.0, score=10.0))
    db.add(TestAttempt(test_id=test.id, student_id=students[1].id, status="finished", counted=True, started_at=now - timedelta(hours=2),
                       deadline_at=now - timedelta(hours=1, minutes=40), finished_at=now - timedelta(hours=1, minutes=50),
                       answers={str(qids[0][0]): 1, str(qids[1][0]): 2, str(qids[2][0]): 0}, correct_count=2, total=3, percent=66.67, score=6.67))
    db.flush()
    for s in students:
        scoring.recalculate(db, s.id)
    db.commit()
    print("[OK] Demo ma'lumotlar yaratildi.")
    print(f"     O'qituvchi: teacher@demo.uz / {DEMO_PASSWORD}")
    print(f"     O'quvchilar: student1@demo.uz ... student5@demo.uz / {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learning English seed")
    parser.add_argument("--demo", action="store_true", help="demo o'qituvchi, o'quvchilar va guruh qo'shish")
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    import migrate
    migrate.run(engine, Base)
    with SessionLocal() as session:
        if args.demo:
            create_demo(session)
