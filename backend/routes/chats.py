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
    """Handles chat requests using Cohere V2 RAG with local file search."""
    logger.info(f"Chat request from username: {payload.username}")

    if user.username != payload.username:
        logger.error(f"Unauthorized: Token username {user.username} does not match payload {payload.username}")
        raise HTTPException(status_code=403, detail="Unauthorized user")

    # --- Find or create chat ---
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

    # --- Save user message ---
    user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(user_msg)
    session.commit()

    # --- Fetch all messages for this chat ---
    existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()

    # --- Build messages array for Cohere ---
    cohere_messages = build_cohere_messages(agent, existing_messages, payload.message)

    # --- Prepare tool call if needed ---
    tools = [{"name": LOCAL_FILE_TOOL_NAME,
              "description": "Searches local data.csv and data.json files for relevant info.",
              "parameters": [{"name": "query", "type": "string", "description": "Search query"}]}] if needs_tool(payload.message) else None

    documents = []
    if tools:
        documents = process_tool_call({"name": LOCAL_FILE_TOOL_NAME, "parameters": {"query": payload.message}})

    # --- Call Cohere V2 Chat API ---
    try:
        if co:
            response = co.chat(
                model="command-r-plus",
                messages=cohere_messages,   # <-- Only use 'messages'
                tools=tools,
                documents=documents
            )

            # Process tool calls returned by Cohere
            if getattr(response, "tool_calls", None):
                documents = process_tool_call(response.tool_calls[0])
                response = co.chat(
                    model="command-r-plus",
                    messages=cohere_messages,
                    tools=tools,
                    documents=documents
                )

            ai_text = response.message.content[0].text if response.message.content else "No response"
        else:
            ai_text = f"Echo (mock mode): {payload.message}"
    except Exception as e:
        logger.error(f"Cohere API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cohere API error: {str(e)}")

    # --- Save AI response ---
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    logger.info(f"Chat response generated for chat_id: {chat.id}")
    return {"chat_id": chat.id, "response": ai_text}
