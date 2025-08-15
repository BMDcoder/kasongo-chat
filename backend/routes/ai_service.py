import os
import logging
from typing import List
from models import Agent, Message
from services.local_file_service import search_local_files
import cohere

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Cohere V2 client
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
if not COHERE_API_KEY:
    logger.error("COHERE_API_KEY not set")
    co = None
else:
    try:
        co = cohere.ClientV2(COHERE_API_KEY)
        logger.info("Cohere ClientV2 initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Cohere ClientV2: {str(e)}")
        co = None


def build_cohere_messages(agent: Agent, existing_messages: List[Message], new_message: str) -> List[dict]:
    """
    Build messages for Cohere V2 chat API.
    Each message must be a dict: {"role": "...", "content": "..."}.
    """
    try:
        messages = []

        # 1️⃣ System message
        system_prompt = agent.system_prompt or "You are a helpful assistant."
        system_prompt += "\nUse local file RAG documents if relevant; otherwise answer normally."
        messages.append({"role": "system", "content": system_prompt})

        # 2️⃣ Existing conversation
        for msg in existing_messages:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        # 3️⃣ Latest user message
        messages.append({"role": "user", "content": new_message})

        return messages
    except Exception as e:
        logger.error(f"Error building chat messages: {str(e)}")
        raise


def needs_tool(message: str) -> bool:
    """
    Returns True if the query should trigger local file search RAG.
    """
    try:
        return any(keyword in message.lower() for keyword in ["find", "search", "lookup", "recommend"])
    except Exception as e:
        logger.error(f"Error in needs_tool: {str(e)}")
        return False


def process_tool_call(tool_call: dict) -> List[dict]:
    """
    Process a tool call. Currently supports 'local_file_search'.
    Returns a list of documents compatible with Cohere's `documents` parameter.
    """
    try:
        if tool_call.get("name") == "local_file_search":
            query = tool_call.get("parameters", {}).get("query", "")
            results = search_local_files(query)
            # Each document must have "id", "title", "content", optionally "url"
            return [{"id": doc.get("id"), "title": doc.get("title"), "content": doc.get("content"), "url": doc.get("url")}
                    for doc in results]
        return []
    except Exception as e:
        logger.error(f"Error processing tool call: {str(e)}")
        return []
