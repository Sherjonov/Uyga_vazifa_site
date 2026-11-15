from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from deps import get_db, get_current_user
from models.ticket import Ticket
from models.user import User
from schemas.ticket import TicketIn
from utils import iso

router = APIRouter(prefix="/tickets", tags=["tickets"])


def t_out(t: Ticket, author: str = None) -> dict:
    return {"id": t.id, "author_id": t.author_id, "author_name": author, "subject": t.subject, "body": t.body,
            "status": t.status, "admin_reply": t.admin_reply, "replied_at": iso(t.replied_at),
            "created_at": iso(t.created_at), "updated_at": iso(t.updated_at)}


@router.post("")
def create_ticket(data: TicketIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = Ticket(author_id=user.id, subject=data.subject.strip(), body=data.body.strip())
    db.add(t)
    db.commit()
    return t_out(t, user.name)


@router.get("/mine")
def my_tickets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Ticket).where(Ticket.author_id == user.id).order_by(Ticket.id.desc())).all()
    return [t_out(t, user.name) for t in rows]
