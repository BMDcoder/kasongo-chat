import os
import uuid
from datetime import datetime
from typing import Optional

import cohere
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")  # e.g., "postgresql://user:password@localhost/dbname"
GOOGLE_DRIVE_CONNECTOR_ID = os.getenv("GOOGLE_DRIVE_CONNECTOR_ID")

if not all([COHERE_API_KEY, POSTGRES_URL, GOOGLE_DRIVE_CONNECTOR_ID]):
    raise ValueError("Missing required environment variables: COHERE_API_KEY, POSTGRES_URL, GOOGLE_DRIVE_CONNECTOR_ID")

# Cohere client
co = cohere.Client(COHERE_API_KEY)

# Database setup
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, index=True)
    role = Column(String)  # "USER" or "CHATBOT"
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Request model
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

# Function to check if query needs search in Google Drive
def needs_search(query: str) -> bool:
    query_lower = query.lower()
    trigger_phrases = ["find", "recommend", "looking for", "search for", "need a"]
    target_keywords = ["professional", "service provider", "supplier"]
    
    has_trigger = any(phrase in query_lower for phrase in trigger_phrases)
    has_target = any(kw in query_lower for kw in target_keywords)
    
    return has_trigger and has_target

@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Get DB session
    db: Session = SessionLocal()
    
    # Fetch chat history
    history_query = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
    history = history_query.all()
    chat_history = [{"role": msg.role, "message": msg.content} for msg in history]
    
    # Determine if search is needed
    is_search_needed = needs_search(message)
    connectors = [{"id": GOOGLE_DRIVE_CONNECTOR_ID}] if is_search_needed else []
    
    # Call Cohere Chat API
    response = co.chat(
        model="command-a-03-2025",
        message=message,
        chat_history=chat_history,
        connectors=connectors
    )
    
    bot_response = response.text
    
    # Save user message and bot response to DB
    user_msg = Message(
        conversation_id=conversation_id,
        role="USER",
        content=message,
        timestamp=datetime.utcnow()
    )
    db.add(user_msg)
    
    bot_msg = Message(
        conversation_id=conversation_id,
        role="CHATBOT",
        content=bot_response,
        timestamp=datetime.utcnow()
    )
    db.add(bot_msg)
    
    db.commit()
    db.close()
    
    return {
        "response": bot_response,
        "conversation_id": conversation_id
    }
