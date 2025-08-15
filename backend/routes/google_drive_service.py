import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlmodel import Session, select
from models import UserCredentials
from config import GOOGLE_CREDENTIALS_PATH
import logging
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def authenticate_google_drive(user_id: int, session: Session):
    """Authenticate and return Google Drive service for the user."""
    creds = None
    # Check for stored credentials
    user_creds = session.exec(select(UserCredentials).where(UserCredentials.user_id == user_id)).first()
    
    if user_creds:
        creds = pickle.loads(user_creds.credentials)
        # Refresh credentials if expired
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
        # Perform OAuth flow
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            creds = flow.run_local_server(port=0)
            # Store credentials
            if user_creds:
                user_creds.credentials = pickle.dumps(creds)
            else:
                user_creds = UserCredentials(user_id=user_id, credentials=pickle.dumps(creds))
            session.add(user_creds)
            session.commit()
        except Exception as e:
            logger.error(f"Google Drive OAuth failed: {str(e)}")
            raise

    return build('drive', 'v3', credentials=creds)

def google_drive_operation(query: str, user_id: int, session: Session) -> list[dict]:
    """Search Google Drive for files matching the query and return content for RAG."""
    try:
        service = authenticate_google_drive(user_id, session)
        # Search files
        results = service.files().list(
            q=f"{query} from:me",
            fields="files(id, name, mimeType, webContentLink)",
            pageSize=5
        ).execute()
        files = results.get('files', [])
        
        documents = []
        for file in files:
            # Only process text-based files (e.g., Google Docs, plain text)
            if 'text' in file.get('mimeType', '') or 'document' in file.get('mimeType', ''):
                try:
                    # Export file content
                    content = service.files().export(fileId=file['id'], mimeType='text/plain').execute()
                    documents.append({
                        'id': file['id'],
                        'title': file['name'],
                        'content': content.decode('utf-8')[:10000],  # Limit size
                        'url': file.get('webContentLink', '')
                    })
                except Exception as e:
                    logger.warning(f"Failed to process file {file['name']}: {str(e)}")
                    continue
        
        return documents
    except Exception as e:
        logger.error(f"Google Drive operation failed: {str(e)}")
        return []
