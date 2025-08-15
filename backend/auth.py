from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from models import User
from database import get_session
from os import environ
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT configuration
SECRET_KEY = environ.get("JWT_SECRET_KEY", "your-default-secret-key")  # Set in Railway
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)  # Allow missing token

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created JWT token for user: {data.get('sub')}")
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    """Return authenticated user or default 'guest' user if no valid token."""
    if not token:
        logger.info("No token provided, using guest user")
        user = session.exec(select(User).where(User.username == "guest")).first()
        if not user:
            logger.error("Guest user not found in database")
            raise HTTPException(status_code=404, detail="Guest user not found")
        return user

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.error("JWT token missing 'sub' claim")
            return get_guest_user(session)
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}, falling back to guest user")
        return get_guest_user(session)

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        logger.error(f"User not found for username: {username}, falling back to guest user")
        return get_guest_user(session)
    logger.info(f"Authenticated user: {username}")
    return user

def get_guest_user(session: Session):
    """Helper function to retrieve guest user."""
    user = session.exec(select(User).where(User.username == "guest")).first()
    if not user:
        logger.error("Guest user not found in database")
        raise HTTPException(status_code=404, detail="Guest user not found")
    return user

def get_password_hash(password: str) -> str:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)
