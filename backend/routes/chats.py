import os
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY
import cohere

router = APIRouter(tags=["chat"])

# Initialize Cohere client with api_key explicitly
co = cohere.ClientV2(api_key=COHERE_API_KEY) if COHERE_API_KEY else None

# Google Drive Connector ID from environment (set this after creating the connector in Cohere)
COHERE_CONNECTOR_ID = os.getenv("CONNECTOR_ID")


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
def handle_chat(payload: ChatIn, session: Session = Depends(get_session)):
    """Handles chat requests between user and AI agent. Supports creating new chats or continuing existing ones."""

    # 1️⃣ Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2️⃣ Get or create chat
    if payload.chat_id:
        chat = session.get(Chat, payload.chat_id)
        if not chat or chat.user_id != user.id:
            raise HTTPException(status_code=404, detail="Chat not found")
        agent = session.get(Agent, chat.agent_id)
    else:
        if not payload.agent_id:
            raise HTTPException(status_code=400, detail="agent_id required for new chats")
        agent = session.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        chat = Chat(user_id=user.id, agent_id=agent.id)
        session.add(chat)
        session.commit()
        session.refresh(chat)

    # 3️⃣ Save user message
    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

def build_cohere_messages(agent, existing_messages, latest_user_query):
    # Build system prompt
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    system_prompt += (
        "\nYou have access to a Google Drive connector for searching information "
        "about professionals, service providers, and suppliers. Only use the connector "
        "when the user's query is about finding such entities. For all other queries, "
        "answer based on your knowledge without using the connector."
    )

    # Ensure existing_messages is iterable
    existing_messages = existing_messages or []

    # Build base array with system prompt + history
    cohere_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in existing_messages
    ]

    # Append the latest user query
    cohere_messages.append({"role": "user", "content": latest_user_query})

    return cohere_messages


# Inside your route handler (not inside build_cohere_messages)
if COHERE_API_KEY and co:
    try:
        connectors = [{"id": COHERE_CONNECTOR_ID}] if COHERE_CONNECTOR_ID else None
        cohere_messages = build_cohere_messages(agent, existing_messages, payload.message)
        
        response = co.chat(
            model="command-xlarge-nightly",  # Use a recent model suitable for RAG
            messages=cohere_messages,
            connectors=connectors,
        )
        ai_text = response.message.content[0].text
        
        # Optionally handle citations if present
        if response.citations:
            ai_text += "\n\nCitations:\n" + "\n".join(
                [f"{c['start']}-{c['end']}: {c['text']}" for c in response.citations]
            )
    except Exception as e:
        ai_text = f"(Cohere API call failed) {str(e)}"
else:
    ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

# Save AI response
ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
session.add(ai_msg)
session.commit()

return {"chat_id": chat.id, "response": ai_text}
