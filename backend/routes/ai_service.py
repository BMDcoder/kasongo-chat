import cohere
import os
import logging
from models import Agent, Message
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Cohere ClientV2
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
    """Builds chat history for Cohere V2."""
    chat_history = [{"role": "system", "message": agent.system_prompt or "You are a helpful assistant."}]
    for msg in existing_messages:
        role = "user" if msg.role == "user" else "assistant"
        chat_history.append({"role": role, "message": msg.content})
    return chat_history  # new_message is passed separately as last user input

def needs_tool(message: str) -> bool:
    """Check if the message should trigger local RAG tool."""
    return any(word in message.lower() for word in ["find", "search", "lookup", "professional", "supplier", "contract"])

def process_tool_call(tool_call: dict) -> List[dict]:
    """Process local file search tool call."""
    from services.local_file_service import local_file_operation
    if tool_call.get("name") == "local_file_search":
        query = tool_call.get("parameters", {}).get("query", "")
        return local_file_operation(query)
    return []
