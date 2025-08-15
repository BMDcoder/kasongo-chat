from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import chats
from database import init_db  # Import init_db instead of create_db_and_tables
from routes.chats import router as chats_router


app = FastAPI(title="RAG Chatbot")
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kasongo-chat.vercel.app"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats_router, prefix="/api")
