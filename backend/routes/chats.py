import os
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
import cohere

# ====== Load config ======
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
CONNECTOR_API_KEY = os.getenv("CONNECTOR_API_KEY")  # For Cohere connector auth
GDRIVE_SERVICE_ACCOUNT_INFO = os.getenv("GDRIVE_SERVICE_ACCOUNT_INFO")  # JSON string
GDRIVE_CONNECTOR_ID = os.getenv("CONNECTOR_ID")

if not COHERE_API_KEY:
    raise ValueError("Missing COHERE_API_KEY in environment variables")

# ====== Initialize Cohere Client ======
co = cohere.ClientV2(COHERE_API_KEY)

router = APIRouter(tags=["chat"])

# ====== Helper functions ======
def should_use_gdrive_connector(message: str) -> bool:
    """Simple keyword-based decision for using Google Drive connector."""
    keywords = ["google drive", "gdrive", "my files", "spreadsheet", "doc", "pdf", "document"]
    return any(k in message.lower() for k in keywords)

def get_gdrive_service_account_json():
    """Validate and parse Google Drive service account JSON."""
    if not GDRIVE_SERVICE_ACCOUNT_INFO:
        return None
    try:
        return json.loads(GDRIVE_SERVICE_ACCOUNT_INFO)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in GDRIVE_SERVICE_ACCOUNT_INFO")

# ====== Routes ======
@router.get("/chats")
def get_chats(username: str = Query(...), session: Session = Depends(get_session)):
    """Return all chats for a given username."""
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
    """Handles chat requests between user and AI agent, optionally using Google Drive connector."""

    # 1️⃣ Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2️⃣ Find agent
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 3️⃣ Create chat record
    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    # 4️⃣ Save user message
    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

    # 5️⃣ Decide whether to use Google Drive connector
    connectors_payload = []
    if should_use_gdrive_connector(payload.message) and GDRIVE_CONNECTOR_ID:
        connectors_payload.append({"id": GDRIVE_CONNECTOR_ID})

    # 6️⃣ Get AI response
    if COHERE_API_KEY and co:
        try:
            response = co.chat(
                model="command-r-plus",
                messages=[
                    {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": payload.message}
                ],
                connectors=connectors_payload if connectors_payload else None
            )
            ai_text = response.message.content[0].text
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

    # 7️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {
        "chat_id": chat.id,
        "response": ai_text,
        "used_connector": bool(connectors_payload)
    }
