from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import (
    COHERE_API_KEY,
    CONNECTOR_ID,
    CONNECTOR_API_KEY
)
import cohere

router = APIRouter(tags=["chat"])

# Initialize Cohere client
co = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None

@router.get("/chats")
def get_chats(username: str, session: Session = Depends(get_session)):
    """Return all chats for a user."""
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chats = session.exec(select(Chat).where(Chat.user_id == user.id)).all()
    result = []
    for chat in chats:
        messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()
        result.append({
            "chat_id": chat.id,
            "agent_id": chat.agent_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages]
        })
    return result

@router.post("/chats")
def create_chat(payload: ChatIn, session: Session = Depends(get_session)):
    """Create a chat and get AI response using Cohere RAG connector."""

    # --- 1. Find or create user ---
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # --- 2. Find agent ---
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # --- 3. Create chat record ---
    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    # --- 4. Save user message ---
    user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(user_msg)
    session.commit()

    # --- 5. Send message to Cohere Chat API with RAG connector ---
    ai_text = f"(Cohere API key not configured; echoing user message) {payload.message}"

    if COHERE_API_KEY and co:
        try:
            messages = [
                {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": payload.message}
            ]

            connectors = []
            if CONNECTOR_ID and CONNECTOR_API_KEY:
                connectors.append({"id": CONNECTOR_ID, "apikey": CONNECTOR_API_KEY})

            response = co.chat(
                model="command-a-03-2025",
                messages=messages,
                connectors=connectors
            )
            ai_text = response.message.content[0].text

        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"

    # --- 6. Save AI response ---
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
