# google_drive_service.py
import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlmodel import Session, select
from models import UserCredentials
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_oauth_flow():
    """Create OAuth flow from environment variables."""
    client_config = {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ.get("GOOGLE_REDIRECT_URI")]
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

def authenticate_google_drive(user_id: int, session: Session):
    """Authenticate and return Google Drive service for the user."""
    creds = None
    user_creds = session.exec(select(UserCredentials).where(UserCredentials.user_id == user_id)).first()
    
    if user_creds:
        creds = pickle.loads(user_creds.credentials)
        if not creds.valid and creds.refresh_token:
            try:
                creds.refresh(Request())
                user_creds.credentials = pickle.dumps(creds)
                session.add(user_creds)
                session.commit()
            except Exception as e:
                logger.error(f"Failed to refresh Google Drive credentials: {str(e)}")
                creds = None

    if not creds or not creds.valid:
        raise ValueError("No valid credentials. Initiate OAuth flow via /auth/google.")

    return build('drive', 'v3', credentials=creds)

def store_credentials(user_id: int, creds, session: Session):
    """Store OAuth credentials in the database."""
    user_creds = session.exec(select(UserCredentials).where(UserCredentials.user_id == user_id)).first()
    if user_creds:
        user_creds.credentials = pickle.dumps(creds)
    else:
        user_creds = UserCredentials(user_id=user_id, credentials=pickle.dumps(creds))
    session.add(user_creds)
    session.commit()

def google_drive_operation(query: str, user_id: int, session: Session) -> list[dict]:
    """Search Google Drive for files matching the query and return content for RAG."""
    try:
        service = authenticate_google_drive(user_id, session)
        results = service.files().list(
            q=f"{query} from:me",
            fields="files(id, name, mimeType, webContentLink)",
            pageSize=5
        ).execute()
        files = results.get('files', [])
        
        documents = []
        for file in files:
            if 'text' in file.get('mimeType', '') or 'document' in file.get('mimeType', ''):
                try:
                    content = service.files().export(fileId=file['id'], mimeType='text/plain').execute()
                    documents.append({
                        'id': file['id'],
                        'title': file['name'],
                        'content': content.decode('utf-8')[:10000],
                        'url': file.get('webContentLink', '')
                    })
                except Exception as e:
                    logger.warning(f"Failed to process file {file['name']}: {str(e)}")
                    continue
        
        return documents
    except Exception as e:
        logger.error(f"Google Drive operation failed: {str(e)}")
        return []
