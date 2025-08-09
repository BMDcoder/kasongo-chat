from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, engine
from routes import admin_agents, auth, chat
from auth import get_password_hash
from sqlmodel import Session, select
from models import User

app = FastAPI(title="Kasongo - AI Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(username="admin", password_hash=get_password_hash("adminpass"), is_admin=True)
            session.add(admin)
            session.commit()

app.include_router(auth.router)
app.include_router(admin_agents.router)
app.include_router(chat.router)
