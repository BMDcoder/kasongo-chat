from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User
from schemas import LoginIn, Token
from auth import verify_password, create_access_token
from database import get_session

router = APIRouter(tags=["auth"])

@router.post("/admin/login", response_model=Token)
def admin_login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token}
