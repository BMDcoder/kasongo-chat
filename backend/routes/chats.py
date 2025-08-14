# Important: Ensure you have the latest version of the Cohere Python SDK installed.
# Run `pip install --upgrade cohere` to get version 5.17.0 or later, which includes ClientV2 and v2 API support.
# If you're encountering errors like AttributeError or API failures, this upgrade should resolve them.

# schemas.py remains the same as before

# The updated router code
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

# Note: To set up the Google Drive connector:
# 1. Use Cohere's quick-start-connectors repo: https://github.com/cohere-ai/quick-start-connectors
# 2. Select the Google Drive connector, configure authentication (Service Account or OAuth).
#    - For Service Account: Create in Google Cloud Console, download JSON credentials, set env vars.
# 3. Deploy the connector API (e.g., on Vercel, AWS, etc.).
# 4. Register the connector via Cohere API: POST to /v1/connectors with url, name, service_auth if needed.
# 5. Get the connector ID from the response and set COHERE_CONNECTOR_ID env var.
# The connector can be configured to search specific folders via its implementation or options.

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

    # 4️⃣ Prepare messages for Cohere
    existing_messages = session.exec(
        select(Message).where(Message.chat_id == chat.id).order_by(Message.id)
    ).all()

    cohere_messages = []
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    # Append instruction for conditional use of connector
    system_prompt += "\nYou have access to a Google Drive connector for searching information about professionals, service providers, and suppliers. Only use the connector when the user's query is about finding such entities. For all other queries, answer based on your knowledge without using the connector."
    cohere_messages.append({"role": "system", "content": system_prompt})

    for m in existing_messages:
        role = "user" if m.role == "user" else "assistant"
        cohere_messages.append({"role": role, "content": m.content})

    # 5️⃣ Get AI response from Cohere ClientV2 chat API with connector
    if COHERE_API_KEY and co:
        try:
            connectors = [{"id": COHERE_CONNECTOR_ID}] if COHERE_CONNECTOR_ID else None
            response = co.chat(
                model="command-r-plus-08-2024",  # Use a recent model suitable for RAG
                messages=cohere_messages,
                connectors=connectors,
            )
            ai_text = response.message.content[0].text
            # Optionally handle citations if present
            if response.citations:
                ai_text += "\n\nCitations:\n" + "\n".join([f"{c['start']}-{c['end']}: {c['text']}" for c in response.citations])
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

    # 6️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
