from sqlmodel import create_engine, Session, SQLModel
from os import getenv

DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./kasongo.db")

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
