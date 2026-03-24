from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Message, User, Vote
from app.schemas import MessageCreate, MessageOut, VoteRequest, VoteResponse

router = APIRouter(tags=["messages"])


def _message_vote_count(db: Session, message_id: int) -> int:
    result = db.query(func.coalesce(func.sum(Vote.value), 0)).filter(
        Vote.message_id == message_id
    ).scalar()
    return int(result)


def _build_message_out(message: Message, db: Session) -> MessageOut:
    return MessageOut(
        id=message.id,
        content=message.content,
        author_username=message.author.username,
        vote_count=_message_vote_count(db, message.id),
        created_at=message.created_at,
    )


@router.get("/messages", response_model=list[MessageOut])
def list_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).order_by(Message.created_at.desc()).all()
    return [_build_message_out(m, db) for m in messages]


@router.post("/messages", status_code=status.HTTP_201_CREATED, response_model=MessageOut)
def create_message(
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = Message(content=payload.content, author_id=current_user.id)
    db.add(message)
    db.commit()
    db.refresh(message)
    return _build_message_out(message, db)


@router.post("/messages/{message_id}/vote", response_model=VoteResponse)
def vote_message(
    message_id: int,
    payload: VoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    existing_vote = (
        db.query(Vote)
        .filter(Vote.user_id == current_user.id, Vote.message_id == message_id)
        .first()
    )

    if existing_vote:
        existing_vote.value = payload.value
    else:
        new_vote = Vote(user_id=current_user.id, message_id=message_id, value=payload.value)
        db.add(new_vote)

    db.commit()

    return VoteResponse(vote_count=_message_vote_count(db, message_id))


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if message.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages",
        )

    db.delete(message)
    db.commit()


@router.get("/user/messages", response_model=list[MessageOut])
def get_my_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = (
        db.query(Message)
        .filter(Message.author_id == current_user.id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return [_build_message_out(m, db) for m in messages]
