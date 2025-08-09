from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from .auth import get_password_hash
from config import OPENAI_KEY
import httpx

router = APIRouter(tags=["chat"])

@router.post("/chat")
def chat_endpoint(payload: ChatIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

    if OPENAI_KEY:
        headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
        system_prompt = agent.system_prompt or "You are a helpful assistant."
        body = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ],
            "max_tokens": 800
        }
        try:
            r = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=30.0)
            r.raise_for_status()
            data = r.json()
            ai_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            ai_text = f"(OpenAI call failed) {str(e)}"
    else:
        ai_text = "OpenAI API key not configured; running in mock mode. Echo: " + payload.message

    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
