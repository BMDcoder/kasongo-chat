from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, engine
from routes import admin_agents, auth, chat
from auth import get_password_hash
from sqlmodel import Session, select
from models import User
from routes.auth import router as auth_router
from routes.admin_agents import router as agent_router
from routes.chat import router as chat_router
from routes.chats import router as chats_router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    create_db_and_tables()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(username="admin", password_hash=get_password_hash("adminpass"), is_admin=True)
            session.add(admin)
            session.commit()
    
    yield  # application runs here
    
    # (optional) shutdown code can go here

app = FastAPI(title="Kasongo - AI Agent Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/admin")
app.include_router(agent_router, prefix="/api/admin")
app.include_router(chat_router, prefix="/api")
app.include_router(chats_router, prefix="/api")
