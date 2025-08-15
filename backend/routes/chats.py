from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.ai_service import build_cohere_messages, co, needs_tool, process_tool_call
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_FILE_TOOL_NAME = "local_file_search"

router = APIRouter(tags=["chat", "auth"], prefix="/api")  # Added prefix for /api/chats

@router.post("/auth/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Authenticate user and return JWT token."""
    logger.info(f"Login attempt for username: {form_data.username}")
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        logger.error(f"Login failed for username: {form_data.username}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    logger.info(f"Login successful for username: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/signup")
def signup(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Create a new user."""
    logger.info(f"Signup attempt for username: {form_data.username}")
    if form_data.username == "guest":
        logger.error("Cannot sign up with reserved username 'guest'")
        raise HTTPException(status_code=400, detail="Username 'guest' is reserved")
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if user:
        logger.error(f"Signup failed: Username {form_data.username} already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=form_data.username, password_hash=get_password_hash(form_data.password))
    session.add(user)
    session.commit()
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"Signup successful for username: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Handles chat requests using Cohere V2 with RAG from local files."""
    logger.info(f"Chat request from username: {payload.username}")
    if user.username != payload.username:
        logger.error(f"Unauthorized: Token username {user.username} does not match payload {payload.username}")
        raise HTTPException(status_code=403, detail="Unauthorized user")

    # Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        logger.error(f"User not found: {payload.username}")
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create chat
    with session.begin():
        if payload.chat_id:
            chat = session.get(Chat, payload.chat_id)
            if not chat or chat.user_id != user.id:
                logger.error(f"Chat not found: chat_id={payload.chat_id}, user_id={user.id}")
                raise HTTPException(status_code=404, detail="Chat not found")
            agent = session.get(Agent, chat.agent_id)
        else:
            if not payload.agent_id:
                logger.error("agent_id required for new chats")
                raise HTTPException(status_code=400, detail="agent_id required for new chats")
            agent = session.get(Agent, payload.agent_id)
            if not agent:
                logger.error(f"Agent not found: agent_id={payload.agent_id}")
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

    # Decide whether to use local file search tool
    tools = [{"name": LOCAL_FILE_TOOL_NAME, 
              "description": "Searches local data.csv and data.json files for relevant information.",
              "parameters": [
                  {"name": "query", "type": "string", "description": "Search query for local files."}
              ]}] if needs_tool(payload.message) else None

    # Call Cohere V2 chat API with RAG
    try:
        documents = []
        if tools:
            documents = process_tool_call({"name": LOCAL_FILE_TOOL_NAME, "parameters": {"query": payload.message}})
        
        if co:
            response = co.chat(
                model="command-r-plus",
                messages=cohere_messages,
                tools=tools,
                documents=documents
            )
            
            if response.tool_calls:
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
        logger.error(f"Error processing Cohere request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

    # Save AI response
    with session.begin():
        ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
        session.add(ai_msg)
        session.commit()

    logger.info(f"Chat response generated for chat_id: {chat.id}")
    return {"chat_id": chat.id, "response": ai_text}
