import os
import logging
from typing import List
from models import Agent, Message
from routes.local_file_service import search_local_files
import cohere

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize Cohere V2 client ---
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
co = None
if COHERE_API_KEY:
    try:
        co = cohere.ClientV2(COHERE_API_KEY)
        logger.info("Cohere ClientV2 initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Cohere ClientV2: {str(e)}")
else:
    logger.error("COHERE_API_KEY not set")


def build_cohere_messages(agent: Agent, existing_messages: List[Message], new_message: str) -> List[dict]:
    """
    Build messages array for Cohere V2 chat API.
    Each message must be: {"role": "...", "content": "..."}.
    """
    messages = []

    # System prompt
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    system_prompt += "\nUse local file RAG documents if relevant; otherwise answer normally."
    messages.append({"role": "system", "content": system_prompt})

    # Previous conversation
    for msg in existing_messages:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content})

    # Latest user message
    messages.append({"role": "user", "content": new_message})

    return messages


def needs_tool(message: str) -> bool:
    """Return True if local file search RAG should be used."""
    try:
        return any(keyword in message.lower() for keyword in ["find", "search", "lookup", "recommend"])
    except Exception as e:
        logger.error(f"Error in needs_tool: {str(e)}")
        return False


def process_tool_call(tool_call: dict) -> List[dict]:
    """
    Process a tool call. Currently supports 'local_file_search'.
    Returns a list of documents compatible with Cohere V2 RAG.
    """
    try:
        if tool_call.get("name") == "local_file_search":
            query = tool_call.get("parameters", {}).get("query", "")
            results = search_local_files(query)
            # Format for Cohere V2 RAG
            formatted_docs = []
            for doc in results:
                formatted_docs.append({
                    "id": str(doc.get("id")),
                    "data": {"text": doc.get("content", "")},
                    "metadata": {
                        "title": doc.get("title", ""),
                        "url": doc.get("url", "")
                    }
                })
            return formatted_docs
        return []
    except Exception as e:
        logger.error(f"Error processing tool call: {str(e)}")
        return []
