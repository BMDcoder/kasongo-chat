from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.connector import build_cohere_messages, co, CONNECTOR_ID
from config import COHERE_API_KEY
from auth import get_password_hash  # for creating new users

router = APIRouter(tags=["chat"])

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session)):
    """Handles chat requests with AI agent using RAG via Cohere and Google Drive connector."""

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
    user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(user_msg)
    session.commit()

    # 4️⃣ Fetch existing messages
    existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()

    # 5️⃣ Build Cohere messages with connector decision
    cohere_messages, connectors = build_cohere_messages(agent, existing_messages, payload.message, CONNECTOR_ID)

    # 6️⃣ Get AI response
    if COHERE_API_KEY and co:
        try:
            response = co.chat(
                model="command-xlarge-nightly",
                messages=[
                    {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": payload.message}
                ],
                connectors=connectors,
            )
            ai_text = response.message.content[0].text
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Echo (mock mode): {payload.message}"

    # 7️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
