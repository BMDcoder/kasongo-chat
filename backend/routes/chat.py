from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY
import cohere

router = APIRouter(tags=["chat"])

co = cohere.ClientV2(COHERE_API_KEY)  # Initialize once

@router.post("/chat")
def chat_endpoint(payload: ChatIn, session: Session = Depends(get_session)):
    # Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # Find agent
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create chat record
    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    # Save user message
    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

    if COHERE_API_KEY:
        try:
            response = co.chat(
                model="command-a-03-2025",  # or agent-specific model if you want
                messages=[
                    {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": payload.message}
                ],
            )
            if response.message.content and len(response.message.content) > 0:
                ai_text = response.message.content[0].text
            else:
                ai_text = str(response.message)
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = "Cohere API key not configured; running in mock mode. Echo: " + payload.message

    # Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
