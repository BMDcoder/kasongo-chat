import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
import cohere

# ====== Configuration & Logging ======
logger = logging.getLogger(__name__)
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
CONNECTOR_API_KEY = os.getenv("CONNECTOR_API_KEY")
GDRIVE_SERVICE_ACCOUNT_INFO = os.getenv("GDRIVE_SERVICE_ACCOUNT_INFO")
GDRIVE_CONNECTOR_ID = os.getenv("CONNECTOR_ID")

if not COHERE_API_KEY:
    raise RuntimeError("Missing COHERE_API_KEY environment variable")

router = APIRouter(tags=["chat"])
cohere_client = cohere.ClientV2(COHERE_API_KEY)

# ====== Helper Functions ======
def should_use_gdrive_connector(message: str) -> bool:
    """Determine if Google Drive connector should be used based on keywords."""
    keywords = {"google drive", "gdrive", "my files", "spreadsheet", "doc", "pdf", "document"}
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in keywords)


def parse_gdrive_service_account() -> dict | None:
    """Parse Google Drive service account JSON."""
    if not GDRIVE_SERVICE_ACCOUNT_INFO:
        return None
    try:
        return json.loads(GDRIVE_SERVICE_ACCOUNT_INFO)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid GDRIVE_SERVICE_ACCOUNT_JSON: {str(e)}")
        return None


def get_cohere_response(
    user_message: str,
    system_prompt: str,
    connectors: list[dict] | None = None
) -> str:
    """Get response from Cohere API with optional RAG connectors."""
    try:
        response = cohere_client.chat(
            model="command-r-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            connectors=connectors
        )
        return response.message.content[0].text
    except cohere.CohereAPIError as e:
        logger.error(f"Cohere API error: {str(e)}")
        return "I encountered an error processing your request. Please try again later."
    except Exception as e:
        logger.exception("Unexpected error in Cohere API call")
        return "Sorry, I'm having trouble responding right now."


# ====== Database Services ======
class ChatService:
    @staticmethod
    def get_or_create_user(session: Session, username: str) -> User:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            return user
        new_user = User(
            username=username,
            password_hash=get_password_hash("temppw")  # Temporary password
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user

    @staticmethod
    def create_chat(session: Session, user_id: int, agent_id: int) -> Chat:
        new_chat = Chat(user_id=user_id, agent_id=agent_id)
        session.add(new_chat)
        session.commit()
        session.refresh(new_chat)
        return new_chat

    @staticmethod
    def save_message(session: Session, chat_id: int, role: str, content: str) -> Message:
        new_message = Message(chat_id=chat_id, role=role, content=content)
        session.add(new_message)
        session.commit()
        session.refresh(new_message)
        return new_message

    @staticmethod
    def get_user_chats(session: Session, username: str) -> list[dict]:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        chats = session.exec(select(Chat).where(Chat.user_id == user.id)).all()
        results = []
        for chat in chats:
            messages = session.exec(
                select(Message)
                .where(Message.chat_id == chat.id)
                .order_by(Message.created_at)
            ).all()
            results.append({
                "chat_id": chat.id,
                "agent_id": chat.agent_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    } for msg in messages
                ]
            })
        return results


# ====== API Endpoints ======
@router.get("/chats", response_model=list[dict])
def get_chats(
    username: str = Query(..., description="Username to retrieve chats for"),
    session: Session = Depends(get_session)
):
    """Retrieve all chat history for a user."""
    return ChatService.get_user_chats(session, username)


@router.post("/chats", response_model=dict)
def create_chat(payload: ChatIn, session: Session = Depends(get_session)) -> dict:
    """Process chat message with RAG capabilities using Cohere and Google Drive."""
    # 1️⃣ User handling
    user = ChatService.get_or_create_user(session, payload.username)

    # 2️⃣ Agent validation
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 3️⃣ Create chat record
    chat = ChatService.create_chat(session, user.id, agent.id)

    # 4️⃣ Save user message
    ChatService.save_message(session, chat.id, "user", payload.message)

    # 5️⃣ Decide if Google Drive connector should be used
    connectors = []
    if should_use_gdrive_connector(payload.message) and GDRIVE_CONNECTOR_ID:
        connectors.append({"id": GDRIVE_CONNECTOR_ID})
        logger.info(f"Using Google Drive connector for chat {chat.id}")

    # 6️⃣ Get AI response from Cohere
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    ai_response = get_cohere_response(
        user_message=payload.message,
        system_prompt=system_prompt,
        connectors=connectors if connectors else None
    )

    # 7️⃣ Save AI response
    ChatService.save_message(session, chat.id, "agent", ai_response)

    return {
        "chat_id": chat.id,
        "response": ai_response,
        "used_connector": bool(connectors)
    }
