from fastapi import FastAPI
from routes.chats import router as chat_router
from database import init_db

app = FastAPI()

# Initialize database and guest user
init_db()

# Include router with /api prefix
app.include_router(chat_router, prefix="/api")
