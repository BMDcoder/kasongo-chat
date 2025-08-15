from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message
from routes.ai_service import build_cohere_messages, co, needs_tool
from cohere.error import CohereAPIError
import csv, json, os

LOCAL_FILE_TOOL_NAME = "local_file_search"

router = APIRouter(tags=["chat"])

# --- Local RAG function ---
def process_tool_call(tool_call):
    """Search local CSV and JSON for matching content."""
    query = tool_call["parameters"]["query"].lower()
    results = []

    # Search CSV
    csv_path = os.path.join(os.getcwd(), "data.csv")
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if query in row["title"].lower() or query in row["content"].lower():
                    results.append({
                        "title": row["title"],
                        "content": row["content"],
                        "url": row["url"]
                    })

    # Search JSON
    json_path = os.path.join(os.getcwd(), "data.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as jsonfile:
            json_data = json.load(jsonfile)
            for item in json_data:
                if query in item.get("title", "").lower() or query in item.get("content", "").lower():
                    results.append(item)

    return results


@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session)):
    """Handles chat requests using Cohere V2 with RAG from local files."""
    
    # Find or create user (no auth)
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash="temppw")
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

    # Decide whether to use local file search tool
    tools = [{"name": LOCAL_FILE_TOOL_NAME, 
              "description": "Searches local data.csv and data.json files for relevant information.",
              "parameters": [
                  {"name": "query", "type": "string", "description": "Search query for local files."}
              ]}] if needs_tool(payload.message) else None

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
