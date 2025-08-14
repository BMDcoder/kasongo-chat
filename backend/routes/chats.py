from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.connector import build_cohere_messages, co, CONNECTOR_ID

router = APIRouter(tags=["chat"])

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session)):
    # Lookup user, chat, agent, save message (same logic as before)
    
    existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()
    cohere_messages, connectors = build_cohere_messages(agent, existing_messages, payload.message, COHERE_CONNECTOR_ID)

    if co:
        response = co.chat(model="command-xlarge-nightly", messages=cohere_messages, connectors=connectors)
        ai_text = response.message.content[0].text
    else:
        ai_text = f"Echo (mock mode): {payload.message}"

    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
