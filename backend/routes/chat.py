from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import OPENAI_KEY, HF_API_TOKEN
import httpx

router = APIRouter(tags=["chat"])

HF_MODEL = "deepseek-ai/DeepSeek-V3-0324"  # Replace with your Hugging Face model name

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

    ai_text = ""

    # Try OpenAI first
    if OPENAI_KEY:
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
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            ai_text = data["choices"][0]["message"]["content"]
        except Exception as openai_err:
            ai_text = f"(OpenAI call failed) {str(openai_err)}"
            # Fallback to Hugging Face if token available
            if HF_API_TOKEN:
                try:
                    hf_headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
                    hf_json = {"inputs": payload.message}
                    hf_response = httpx.post(
                        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                        headers=hf_headers,
                        json=hf_json,
                        timeout=30.0,
                    )
                    hf_response.raise_for_status()
                    hf_data = hf_response.json()
                    # Extract generated text (adjust based on your model response)
                    ai_text = hf_data[0]["generated_text"] if isinstance(hf_data, list) else str(hf_data)
                except Exception as hf_err:
                    ai_text = f"(Hugging Face call failed) {str(hf_err)}"

    # If no OpenAI key, try Hugging Face directly
    elif HF_API_TOKEN:
        try:
            hf_headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
            hf_json = {"inputs": payload.message}
            hf_response = httpx.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                headers=hf_headers,
                json=hf_json,
                timeout=30.0,
            )
            hf_response.raise_for_status()
            hf_data = hf_response.json()
            ai_text = hf_data[0]["generated_text"] if isinstance(hf_data, list) else str(hf_data)
        except Exception as hf_err:
            ai_text = f"(Hugging Face call failed) {str(hf_err)}"

    # If no API keys configured, mock response
    else:
        ai_text = "No API key configured; running in mock mode. Echo: " + payload.message

    # Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
