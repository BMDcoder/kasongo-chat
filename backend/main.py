from fastapi import FastAPI
from routes.chats import router as chat_router
from database import init_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kasongo-chat.vercel.app"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and guest user
init_db()

# Include router with /api prefix
app.include_router(chat_router, prefix="/api")
