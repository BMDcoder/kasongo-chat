from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY
import cohere
import os
import json
from typing import Optional
from async_download import perform as async_download_files
from google.oauth2 import service_account, Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import logging

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Cohere ClientV2
co = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None

# Google Drive connector configuration
SERVICE_ACCOUNT_INFO = json.loads(os.getenv("GDRIVE_SERVICE_ACCOUNT_INFO", "{}"))
FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", None)
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", 10))
CONNECTOR_API_KEY = os.getenv("CONNECTOR_API_KEY", "")
CONNECTOR_URL = os.getenv("COHERE_CONNECTOR_URL")

# ------------------------------
# Utilities
# ------------------------------
def request_credentials():
    if not SERVICE_ACCOUNT_INFO:
        raise AssertionError("No Google service account info provided.")
    credentials = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=[
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    if not credentials.valid or credentials.expired:
        credentials.refresh(GoogleRequest())
    return credentials

def split_and_remove_stopwords(text: str):
    words = word_tokenize(text)
    stop_words = set(stopwords.words("english"))
    return [w for w in words if w.lower() not in stop_words]

def escape(text: str):
    return text.replace("'", "\\'")

def extract_links(files):
    id_to_urls = {}
    for f in files:
        export_links = f.get("exportLinks", {})
        file_id = f.get("id")
        if not file_id:
            continue
        if "text/plain" in export_links:
            id_to_urls[file_id] = export_links["text/plain"]
        elif "text/csv" in export_links:
            id_to_urls[file_id] = export_links["text/csv"]
    return id_to_urls

def process_data(files, credentials):
    if not files:
        return []

    id_to_urls = extract_links(files)
    id_to_texts = async_download_files(id_to_urls, credentials.token)

    results = []
    for f in files:
        file_id = f.get("id")
        text = id_to_texts.get(file_id)
        if not text:
            continue

        result = {
            "text": text,
            "title": f.get("name"),
            "url": f.get("webViewLink"),
            "modifiedTime": f.get("modifiedTime"),
        }
        if last_user := f.get("lastModifyingUser"):
            result["editedBy"] = last_user.get("displayName")
        results.append(result)
    return results

def search_google_drive(query: str):
    """Search Google Drive for relevant documents."""
    credentials = request_credentials()
    service = build("drive", "v3", credentials=credentials)

    query_words = split_and_remove_stopwords(query)
    mime_types = [
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation"
    ]

    conditions = [
        "(" + " or ".join([f"mimeType = '{m}'" for m in mime_types]) + ")",
        "(" + " or ".join([f"fullText contains '{escape(w)}'" for w in query_words]) + ")"
    ]
    if FOLDER_ID:
        conditions.append(f"'{FOLDER_ID}' in parents")

    q = " and ".join(conditions)

    try:
        results = service.files().list(
            pageSize=SEARCH_LIMIT,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, lastModifyingUser, modifiedTime, exportLinks)",
            q=q,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
    except HttpError as http_error:
        raise HTTPException(status_code=502, detail=str(http_error))

    return process_data(results.get("files", []), credentials)

# ------------------------------
# Endpoints
# ------------------------------
@router.get("/chats")
def get_chats(username: str = Query(...), session: Session = Depends(get_session)):
    """Return all chats for a given username."""
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chats = session.exec(select(Chat).where(Chat.user_id == user.id)).all()
    result = []
    for chat in chats:
        messages = session.exec(select(Message).where(Message.chat_id == chat.id)).all()
        result.append({
            "chat_id": chat.id,
            "agent_id": chat.agent_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages]
        })
    return result


@router.post("/chats")
def create_chat(payload: ChatIn, session: Session = Depends(get_session)):
    """Handles chat requests between user and AI agent with RAG support."""

    # --- User ---
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # --- Agent ---
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # --- Chat record ---
    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    # --- Save user message ---
    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

    # --- Search Google Drive for RAG ---
    retrieved_docs = search_google_drive(payload.message)
    context_text = "\n\n".join([f"{d['title']}: {d['text']}" for d in retrieved_docs]) if retrieved_docs else ""

    # --- Construct Cohere chat with retrieved context ---
    ai_text = ""
    if COHERE_API_KEY and co:
        try:
            messages = [
                {"role": "system", "content": agent.system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": f"{payload.message}\n\nContext:\n{context_text}"}
            ]
            # Include connectors as optional if you want Cohere to call your connector
            connectors = [
                {
                    "name": "Google Drive RAG Connector",
                    "url": CONNECTOR_URL,
                    "apikey": CONNECTOR_API_KEY
                }
            ] if CONNECTOR_URL else []

            response = co.chat(
                model="command-a-03-2025",
                messages=messages,
                connectors=connectors
            )
            ai_text = response.message.content[0].text
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

    # --- Save AI response ---
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
