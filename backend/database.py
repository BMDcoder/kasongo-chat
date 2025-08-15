from sqlmodel import create_engine, SQLModel, Session, select
from os import environ
from models import User
from auth import get_password_hash
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


engine = create_engine(DATABASE_URL)

def init_db():
    """Initialize database and create guest user if not exists."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        guest_user = session.exec(select(User).where(User.username == "guest")).first()
        if not guest_user:
            logger.info("Creating guest user")
            guest_user = User(
                username="guest",
                password_hash=get_password_hash("guestpassword")  # Hardcoded for guest
            )
            session.add(guest_user)
            session.commit()
        else:
            logger.info("Guest user already exists")

def get_session():
    with Session(engine) as session:
        yield session
