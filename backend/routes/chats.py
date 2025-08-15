from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, Session
from datetime import timedelta
import logging

from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.ai_service import build_cohere_messages, co, needs_tool, process_tool_call
from auth import create_access_token, get_current_user
from utils import get_password_hash, verify_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_FILE_TOOL_NAME = "local_file_search"

router = APIRouter(tags=["chat", "auth"])

# ----------------------
# AUTH ROUTES
# ----------------------
@router.post("/auth/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    logger.info(f"Login attempt for username: {form_data.username}")
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/signup")
def signup(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    if form_data.username == "guest":
        raise HTTPException(status_code=400, detail="Username 'guest' is reserved")
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=form_data.username, password_hash=get_password_hash(form_data.password))
    session.add(user)
    session.commit()
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ----------------------
# CHAT ROUTE
# ----------------------
@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Handles chat requests with Cohere V2 and local RAG content."""
    logger.info(f"Chat request from username: {payload.username}")

    if user.username != payload.username:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    # 1️⃣ Get user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2️⃣ Get or create chat
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

    # 3️⃣ Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(user_msg)
    session.commit()

    # 4️⃣ Fetch existing messages
    existing_messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()

    # 5️⃣ Build Cohere chat history
    cohere_messages = build_cohere_messages(agent, existing_messages, payload.message)

    # 6️⃣ RAG: Retrieve local docs
    if needs_tool(payload.message):
        retrieved_docs = process_tool_call({"name": LOCAL_FILE_TOOL_NAME, "parameters": {"query": payload.message}})
        if retrieved_docs:
            rag_content = "\n".join([f"{doc['title']}: {doc['content']}" for doc in retrieved_docs])
            cohere_messages.insert(1, {"role": "system", "message": f"Relevant info from local files:\n{rag_content}"})

    # 7️⃣ Call Cohere V2
    try:
        if not co:
            ai_text = f"Echo (mock mode): {payload.message}"
        else:
            response = co.chat(
                model="command-r-plus",
                messages=cohere_messages,
                tools=None  # Tools optional; local RAG is manually included
            )
            ai_text = response.message.content[0].text if response.message.content else "No response"

        # 8️⃣ Save AI response
        ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
        session.add(ai_msg)
        session.commit()

        return {"chat_id": chat.id, "response": ai_text}

    except Exception as e:
        logger.error(f"Cohere API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cohere API error: {str(e)}")
