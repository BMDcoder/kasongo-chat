from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.ai_service import build_cohere_messages, co, needs_tool, process_tool_call
from auth import get_password_hash, get_current_user
from cohere.error import CohereAPIError

GOOGLE_DRIVE_TOOL_NAME = "google_drive_connector"

router = APIRouter(tags=["chat"])

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Handles chat requests using Cohere V2 with RAG and Google Drive tool."""
    # Verify user
    if user.username != payload.username:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    # Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))  # Replace with proper auth
        session.add(user)
        session.commit()
        session.refresh(user)

    # Get or create chat
    with session.begin():
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

        # Save user message
        user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
        session.add(user_msg)
        session.commit()

    # Fetch existing messages
    existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()

    # Build Cohere messages
    cohere_messages = build_cohere_messages(agent, existing_messages, payload.message)

    # Decide whether to use Google Drive tool
    tools = [{"name": GOOGLE_DRIVE_TOOL_NAME, 
              "description": "Searches Google Drive for files matching the query.",
              "parameters": [
                  {"name": "query", "type": "string", "description": "Search query for Google Drive files."}
              ]}] if needs_tool(payload.message) else None

    # Call Cohere V2 chat API with RAG
    try:
        documents = []
        if tools:
            documents = process_tool_call({"name": GOOGLE_DRIVE_TOOL_NAME, "parameters": {"query": payload.message}}, user.id, session)
        
        if co:
            response = co.chat(
                model="command-r-plus",
                messages=cohere_messages,
                tools=tools,
                documents=documents
            )
            
            if response.tool_calls:
                documents = process_tool_call(response.tool_calls[0], user.id, session)
                # Re-call Cohere with updated documents
                response = co.chat(
                    model="command-r-plus",
                    messages=cohere_messages,
                    tools=tools,
                    documents=documents
                )
            
            ai_text = response.message.content[0].text if response.message.content else "No response"
        else:
            ai_text = f"Echo (mock mode): {payload.message}"
    except CohereAPIError as e:
        raise HTTPException(status_code=500, detail=f"Cohere API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Save AI response
    with session.begin():
        ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
        session.add(ai_msg)
        session.commit()

    return {"chat_id": chat.id, "response": ai_text}
