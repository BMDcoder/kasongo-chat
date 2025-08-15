# chat_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select, Session
from schemas import ChatIn
from database import get_session
from models import User, Agent, Chat, Message, UserCredentials
from services.ai_service import build_cohere_messages, co, needs_tool, process_tool_call
from services.google_drive_service import get_oauth_flow, store_credentials
from auth import get_password_hash, get_current_user
from cohere.error import CohereAPIError

GOOGLE_DRIVE_TOOL_NAME = "google_drive_connector"
router = APIRouter(tags=["chat", "auth"])

@router.get("/auth/google")
def initiate_google_auth(user: User = Depends(get_current_user)):
    """Initiate Google OAuth flow."""
    flow = get_oauth_flow()
    flow.redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(user.id)  # Pass user_id as state
    )
    return RedirectResponse(authorization_url)

@router.get("/auth/google/callback")
def google_auth_callback(request: Request, state: str, code: str, session: Session = Depends(get_session)):
    """Handle Google OAuth callback."""
    flow = get_oauth_flow()
    flow.redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        user_id = int(state)  # Get user_id from state
        store_credentials(user_id, creds, session)
        return {"message": "Google Drive authentication successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")

@router.post("/chats")
def handle_chat(payload: ChatIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    # ... (same as previous chat_router.py, with minor updates)
    try:
        documents = []
        if tools:
            try:
                documents = process_tool_call({"name": GOOGLE_DRIVE_TOOL_NAME, "parameters": {"query": payload.message}}, user.id, session)
            except ValueError as e:
                return {"chat_id": chat.id, "response": "Please authenticate with Google Drive at /auth/google"}
        
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
