from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from models import User, Agent, Chat, Message
from schemas import ChatIn
from database import get_session
from auth import get_password_hash
from config import COHERE_API_KEY
import cohere
import pandas as pd

router = APIRouter(tags=["chat"])

# ===== 1️⃣ Initialize Cohere client (once) =====
co = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None

# ===== 2️⃣ Initialize RAG retriever at startup =====
def load_rag_retriever():
    # Load documents from multiple sources
    data_csv = pd.read_csv("data/documents.csv")   # Columns: id, text
    data_json = pd.read_json("data/more_documents.json")  # Columns: id, text
    all_data = pd.concat([data_csv, data_json], ignore_index=True)

    # Chunk long documents
    def chunk_text(text, chunk_size=500):
        words = text.split()
        return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

    all_chunks = []
    for idx, row in all_data.iterrows():
        for chunk in chunk_text(row["text"]):
            all_chunks.append({"id": row.get("id", idx), "text": chunk})

    # Initialize Cohere RAG retriever
    retriever = cohere.rag.RagRetriever(
        data_source=all_chunks,
        embedding_model="large",
        text_column="text",
        normalize_embeddings=True
    )
    return retriever

# Load retriever once
rag_retriever = load_rag_retriever()


# ===== FastAPI endpoints =====

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
    if COHERE_API_KEY and co:
        retrieved = rag_retriever.retrieve(payload.message, top_k=5)
        context = "\n".join([r["text"] for r in retrieved])
        prompt_message = (
            f"{agent.system_prompt or 'You are a helpful assistant.'}\n\n"
            f"Context from documents:\n{context}\n\n"
            f"User message: {payload.message}"
        )

        try:
            response = co.chat(
                model="command-a-03-2025",
                messages=[{"role": "user", "content": prompt_message}],
            )
            ai_text = response.message.content[0].text
        except Exception as e:
            ai_text = f"(Cohere API call failed) {str(e)}"
    else:
        ai_text = f"Cohere API key not configured; running in mock mode. Echo: {payload.message}"

    # 6️⃣ Save AI response
    ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
    session.add(ai_msg)
    session.commit()

    return {"chat_id": chat.id, "response": ai_text}
