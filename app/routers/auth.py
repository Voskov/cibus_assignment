import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Token, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
import bcrypt

router = APIRouter(tags=["auth"])


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        username=payload.username,
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    raw_token = secrets.token_hex(32)
    token_row = Token(token=raw_token, user_id=user.id)
    db.add(token_row)
    db.commit()

    return TokenResponse(access_token=raw_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization", "")
    raw_token = auth_header.removeprefix("Bearer ").strip()

    if raw_token:
        db.query(Token).filter(Token.token == raw_token).delete()
        db.commit()

    return {"detail": "Logged out successfully"}
