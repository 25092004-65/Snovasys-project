from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import User
from ..schemas import RegisterIn, LoginIn, TokenOut
from ..security import hash_password, verify_password, create_access_token
from ..dependencies import current_user
from ..audit import log_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    # Public registration can create only viewer accounts. Admin/owner roles are assigned by admin.
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password), role="viewer")
    db.add(user); db.commit(); db.refresh(user)
    log_event(db, user.id, "REGISTER", detail="New viewer account")
    return {"access_token": create_access_token(user.id, user.role), "user": user}

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        log_event(db, user.id if user else None, "LOGIN_FAILED", detail="Invalid credentials", success=False)
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    log_event(db, user.id, "LOGIN")
    return {"access_token": create_access_token(user.id, user.role), "user": user}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}
