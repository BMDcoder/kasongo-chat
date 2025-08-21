from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.ai_service import build_cohere_messages, co, needs_tool, process_tool_call
from auth import get_current_user
from utils import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_FILE_TOOL_NAME = "local_file_search"

router = APIRouter(tags=["chat"])

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Handles chat requests using Cohere V2 with local file RAG documents."""
    logger.info(f"Chat request from username: {payload.username}")

    if user.username != payload.username:
        logger.error(f"Unauthorized: Token username {user.username} does not match payload {payload.username}")
        raise HTTPException(status_code=403, detail="Unauthorized user")

    try:
        # Find user
        db_user = session.exec(select(User).where(User.username == payload.username)).first()
        if not db_user:
            logger.error(f"User not found: {payload.username}")
            raise HTTPException(status_code=404, detail="User not found")

        # Get or create chat
        if payload.chat_id:
            chat = session.get(Chat, payload.chat_id)
            if not chat or chat.user_id != db_user.id:
                raise HTTPException(status_code=404, detail="Chat not found")
            agent = session.get(Agent, chat.agent_id)
        else:
            if not payload.agent_id:
                raise HTTPException(status_code=400, detail="agent_id required for new chats")
            agent = session.get(Agent, payload.agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            chat = Chat(user_id=db_user.id, agent_id=agent.id)
            session.add(chat)
            session.commit()
            session.refresh(chat)

        # Save user message
        user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
        session.add(user_msg)
        session.commit()

        # Fetch existing messages
        existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()

        # Build messages for Cohere V2
        cohere_messages = build_cohere_messages(agent, existing_messages, payload.message)

        # Check if tool is needed
        documents = []
        if needs_tool(payload.message):
            tool_call = {"name": "local_file_search", "parameters": {"query": payload.message}}
            documents = process_tool_call(tool_call)

        # Call Cohere V2 chat
        if co:
            try:
                response = co.chat(
                    model="command-a-03-2025",
                    max_tokens=200,
                    temperature=0.8,
                    messages=cohere_messages,
                    documents=documents  # attach RAG docs here
                )
                ai_text = response.message.content[0].text if response.message.content else "No response"
            except Exception as e:
                logger.error(f"Cohere API error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Cohere API error: {str(e)}")
        else:
            ai_text = f"Echo (mock mode): {payload.message}"

        # Save AI response
        ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
        session.add(ai_msg)
        session.commit()

        logger.info(f"Chat response generated for chat_id: {chat.id}")
        return {"chat_id": chat.id, "response": ai_text}

    except Exception as e:
        logger.error(f"Error in handle_chat: {str(e)}")
        try:
            session.rollback()
        except Exception as rollback_e:
            logger.error(f"Rollback failed: {str(rollback_e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
