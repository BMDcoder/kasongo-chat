from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Optional, List
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kasongo.db")
SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

engine = create_engine(DATABASE_URL, echo=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Kasongo - AI Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    is_admin: bool = False

class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    system_prompt: str
    description: Optional[str] = None

class Chat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = None
    agent_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chat.id")
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

SQLModel.metadata.create_all(engine)

# --- Auth utilities ---
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(pw):
    return pwd_context.hash(pw)

def create_access_token(data: dict, expires_delta: Optional[timedelta]=None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_admin(token: str = Depends(lambda: None)):
    # This dependency will be used via OAuth2 in real flows; here we keep simple.
    raise HTTPException(status_code=501, detail="Use explicit endpoints for login and admin actions.")

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    username: str
    password: str

class AgentIn(BaseModel):
    name: str
    system_prompt: str
    description: Optional[str] = None

class ChatIn(BaseModel):
    username: Optional[str] = "guest"
    agent_id: int
    message: str

# --- Startup helper: create default admin if missing ---
def ensure_admin():
    with Session(engine) as session:
        q = session.exec(select(User).where(User.username == "admin")).first()
        if not q:
            admin = User(username="admin", password_hash=get_password_hash("adminpass"), is_admin=True)
            session.add(admin)
            session.commit()
ensure_admin()

# --- Auth endpoints ---
@app.post("/admin/login", response_model=Token)
def admin_login(payload: LoginIn):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == payload.username)).first()
        if not user or not verify_password(payload.password, user.password_hash) or not user.is_admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token({"sub": user.username})
        return {"access_token": token}

def get_user_by_token(token: str = ""):
    if token.startswith("Bearer "):
        token = token.split(" ",1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")
        return user

# Dependency for admin protected routes
from fastapi import Header
def admin_required(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    user = get_user_by_token(authorization)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not admin")
    return user

# --- Agent management ---
@app.post("/admin/agents", response_model=dict)
def create_agent(agent: AgentIn, admin=Depends(admin_required)):
    with Session(engine) as session:
        a = Agent.from_orm(agent)
        session.add(a)
        session.commit()
        session.refresh(a)
        return {"id": a.id, "name": a.name}

@app.get("/admin/agents", response_model=List[AgentIn])
def list_agents(admin=Depends(admin_required)):
    with Session(engine) as session:
        agents = session.exec(select(Agent)).all()
        return agents

@app.put("/admin/agents/{agent_id}", response_model=dict)
def update_agent(agent_id: int, payload: AgentIn, admin=Depends(admin_required)):
    with Session(engine) as session:
        a = session.get(Agent, agent_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agent not found")
        a.name = payload.name
        a.system_prompt = payload.system_prompt
        a.description = payload.description
        session.add(a)
        session.commit()
        return {"ok": True}

@app.delete("/admin/agents/{agent_id}")
def delete_agent(agent_id: int, admin=Depends(admin_required)):
    with Session(engine) as session:
        a = session.get(Agent, agent_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.delete(a)
        session.commit()
        return {"ok": True}

# --- Chat endpoint ---
import httpx
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

@app.post("/chat")
def chat_endpoint(payload: ChatIn):
    # find or create user
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == payload.username)).first()
        if not user:
            user = User(username=payload.username, password_hash=get_password_hash("temppw"))
            session.add(user)
            session.commit()
            session.refresh(user)
        agent = session.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        # create chat
        chat = Chat(user_id=user.id, agent_id=agent.id)
        session.add(chat)
        session.commit()
        session.refresh(chat)
        # save user message
        msg = Message(chat_id=chat.id, role="user", content=payload.message)
        session.add(msg)
        session.commit()
        # call OpenAI if key present
        if OPENAI_KEY:
            headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
            system_prompt = agent.system_prompt or "You are a helpful assistant."
            body = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": payload.message}
                ],
                "max_tokens": 800
            }
            try:
                r = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=30.0)
                r.raise_for_status()
                data = r.json()
                ai_text = data["choices"][0]["message"]["content"]
            except Exception as e:
                ai_text = f"(OpenAI call failed) {str(e)}"
        else:
            ai_text = "OpenAI API key not configured; running in mock mode. Echo: " + payload.message
        # save ai message
        ai_msg = Message(chat_id=chat.id, role="agent", content=ai_text)
        session.add(ai_msg)
        session.commit()
        return {"chat_id": chat.id, "response": ai_text}
