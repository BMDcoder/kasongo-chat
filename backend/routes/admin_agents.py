from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from typing import List
from models import Agent
from schemas import AgentIn
from .auth import admin_required
from database import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/agents", response_model=dict)
def create_agent(agent: AgentIn, admin=Depends(admin_required), session: Session = Depends(get_session)):
    a = Agent.from_orm(agent)
    session.add(a)
    session.commit()
    session.refresh(a)
    return {"id": a.id, "name": a.name}

@router.get("/agents", response_model=List[AgentIn])
def list_agents(admin=Depends(admin_required), session: Session = Depends(get_session)):
    agents = session.exec(select(Agent)).all()
    return agents

@router.put("/agents/{agent_id}", response_model=dict)
def update_agent(agent_id: int, payload: AgentIn, admin=Depends(admin_required), session: Session = Depends(get_session)):
    a = session.get(Agent, agent_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    a.name = payload.name
    a.system_prompt = payload.system_prompt
    a.description = payload.description
    session.add(a)
    session.commit()
    return {"ok": True}

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, admin=Depends(admin_required), session: Session = Depends(get_session)):
    a = session.get(Agent, agent_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    session.delete(a)
    session.commit()
    return {"ok": True}
