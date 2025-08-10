from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import OPENAI_KEY
from openai import OpenAI

router = APIRouter(tags=["chat"])

# Initialize OpenAI client once
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

@router.post("/chats")
def chat_endpoint(payload: ChatIn, session: Session = Depends(get_session)):
    """Handles chat requests between user and AI agent."""

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

    # 5️⃣ Get AI response from OpenAI
    if OPENAI_KEY and client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # You can change to "gpt-4o" or another available model
                messages=[
                    {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": payload.message}
                ],
                max_tokens=500
            )

            ai_text = response.choices[0].message.content.strip()

        except Exception as e:
            ai_text = f"(OpenAI API call failed) {str(e)}"

    else:
        ai_text = f"OpenAI API key not configured; running in mock mode. Echo: {payload.message}"

    # 6️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
