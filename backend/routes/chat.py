from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import OPENAI_KEY, HF_API_TOKEN  # Add HF_API_TOKEN to your config
import httpx

router = APIRouter(tags=["chat"])

HF_MODEL = "openai/gpt-oss-20b:hyperbolic"  # Replace with your actual Hugging Face model

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

    # Prefer Hugging Face if token exists, else fallback to OpenAI, else mock
    if HF_API_TOKEN:
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        json_data = {"inputs": payload.message}
        try:
            r = httpx.post(
                f"https://huggingface.co/{HF_MODEL}",
                headers=headers,
                json=json_data,
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            # Adjust extraction according to your model's response format
            ai_text = data[0]["generated_text"] if isinstance(data, list) else str(data)
        except Exception as e:
            ai_text = f"(Hugging Face API call failed) {str(e)}"
    elif OPENAI_KEY:
        headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
        system_prompt = agent.system_prompt or "You are a helpful assistant."
        body = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message},
            ],
            "max_tokens": 800,
        }
        try:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            ai_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            ai_text = f"(OpenAI call failed) {str(e)}"
    else:
        ai_text = "No API key configured; running in mock mode. Echo: " + payload.message

    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
