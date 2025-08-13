import os
import glob
import pandas as pd
import threading
import time
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY

# LangChain imports
from langchain_cohere import CohereRagRetriever
from langchain.embeddings import CohereEmbeddings
from langchain.chat_models import ChatCohere

router = APIRouter(tags=["chat"])

# ===== 1️⃣ Initialize embeddings and chat model =====
embeddings = CohereEmbeddings(cohere_api_key=COHERE_API_KEY)
chat_model = ChatCohere(cohere_api_key=COHERE_API_KEY)

# ===== 2️⃣ Auto-reloading RAG Retriever with background thread =====
class AutoReloadRagRetriever:
    def __init__(self, data_folder="data", reload_interval=30):
        self.data_folder = data_folder
        self.reload_interval = reload_interval
        self.current_files = set()
        self.retriever = None
        self.lock = threading.Lock()
        self.load_retriever()
        # Start background thread
        threading.Thread(target=self._background_reload, daemon=True).start()

    def load_retriever(self):
        csv_files = glob.glob(os.path.join(self.data_folder, "*.csv"))
        json_files = glob.glob(os.path.join(self.data_folder, "*.json"))
        new_files = set(csv_files + json_files)

        # If no changes, do nothing
        if new_files == self.current_files and self.retriever is not None:
            return

        self.current_files = new_files
        all_chunks = []

        # Load CSV files
        for f in csv_files:
            df = pd.read_csv(f)
            for idx, row in df.iterrows():
                all_chunks.append({"id": row.get("id", idx), "text": row["text"]})

        # Load JSON files
        for f in json_files:
            df = pd.read_json(f)
            for idx, row in df.iterrows():
                all_chunks.append({"id": row.get("id", idx), "text": row["text"]})

        # Chunk long texts
        def chunk_text(text, chunk_size=500):
            words = text.split()
            return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

        final_chunks = []
        for doc in all_chunks:
            for chunk in chunk_text(doc["text"]):
                final_chunks.append({"id": doc["id"], "text": chunk})

        # Initialize Cohere RAG Retriever with LLM
        retriever = CohereRagRetriever(
            llm=chat_model,          # Required LLM
            embeddings=embeddings,
            documents=final_chunks,
            search_kwargs={"k": 5},
        )

        with self.lock:
            self.retriever = retriever

    def _background_reload(self):
        while True:
            try:
                self.load_retriever()
            except Exception as e:
                print(f"[RAG reload error]: {e}")
            time.sleep(self.reload_interval)

    def retrieve(self, query):
        with self.lock:
            if self.retriever is None:
                return []
            return self.retriever.retrieve(query)

# Initialize retriever with auto background reload
rag_retriever = AutoReloadRagRetriever(reload_interval=30)  # reload every 30 seconds

# ===== GET /chats endpoint =====
@router.get("/chats")
def get_chats(username: str = Query(...), session: Session = Depends(get_session)):
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

# ===== POST /chats endpoint =====
@router.post("/chats")
def create_chat(payload: ChatIn, session: Session = Depends(get_session)):
    # 1️⃣ Find or create user
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user:
        user = User(username=payload.username, password_hash=get_password_hash("temppw"))
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2️⃣ Find agent
    agent = session.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 3️⃣ Create chat record
    chat = Chat(user_id=user.id, agent_id=agent.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    # 4️⃣ Save user message
    msg = Message(chat_id=chat.id, role="user", content=payload.message)
    session.add(msg)
    session.commit()

    # ===== 5️⃣ Retrieve relevant RAG context =====
    if COHERE_API_KEY:
        retrieved = rag_retriever.retrieve(payload.message)
        context = "\n".join([r["text"] for r in retrieved])
        prompt_message = (
            f"{agent.system_prompt or 'You are a helpful assistant.'}\n\n"
            f"Context from documents:\n{context}\n\n"
            f"User message: {payload.message}"
        )

        try:
            response = chat_model.invoke([prompt_message])
            ai_text = response[0]['text'] if response else "No response from model"
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

    # 6️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
