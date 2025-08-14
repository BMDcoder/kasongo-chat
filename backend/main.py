from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, engine
from routes import admin_agents, auth, chat
from auth import get_password_hash
from sqlmodel import Session, select
from models import User
from routes.chats import router as chats_router


app = FastAPI(title="RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kasongo-chat.vercel.app"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats_router, prefix="/api")
