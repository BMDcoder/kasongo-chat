from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY  # Your Cohere API key here
import httpx

router = APIRouter(tags=["chat"])

COHERE_API_URL = "https://api.cohere.ai/generate"

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
        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json",
        }
        # Construct prompt combining system prompt and user message
        prompt = f"{agent.system_prompt}\nUser: {payload.message}\nAssistant:"

        body = {
            "model": "command-xlarge-nightly",  # Use your chosen model here
            "prompt": prompt,
            "max_tokens": 300,
            "temperature": 0.7,
            "k": 0,
            "p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stop_sequences": ["User:", "Assistant:"],
        }

        try:
            response = httpx.post(
                COHERE_API_URL,
                headers=headers,
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            ai_text = data["generations"][0]["text"].strip()
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = "Cohere API key not configured; running in mock mode. Echo: " + payload.message

    # Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
