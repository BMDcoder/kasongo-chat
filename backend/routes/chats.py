from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import OPENAI_API_KEY
from openai import OpenAI

router = APIRouter(tags=["chat"])

# Initialize OpenAI client once
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


@router.api_route("/chats", methods=["GET", "POST"])
def chat_endpoint(
    payload: Optional[ChatIn] = None,
    chat_id: Optional[int] = Query(None),
    session: Session = Depends(get_session)
):
    """Handles chat GET and POST requests."""

    # ----- GET: Return existing chat history -----
    if payload is None and chat_id is not None:
        chat = session.get(Chat, chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        messages = session.exec(
            select(Message).where(Message.chat_id == chat_id)
        ).all()

        return {
            "chat_id": chat_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages]
        }

    # ----- POST: Start a new chat -----
    if payload is None:
        raise HTTPException(status_code=400, detail="Request body required for POST")

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

    # 5️⃣ Get AI response
    if OPENAI_API_KEY and client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": payload.message}
                ]
            )
            ai_text = response.choices[0].message["content"]
        except Exception as e:
            ai_text = f"(OpenAI API call failed) {str(e)}"
    else:
        ai_text = f"OpenAI API key not configured; mock mode. Echo: {payload.message}"

    # 6️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
