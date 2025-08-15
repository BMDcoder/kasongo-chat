import cohere
import os
import logging
from models import Agent, Message
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Cohere client
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None

def build_cohere_messages(agent: Agent, existing_messages: List[Message], new_message: str) -> List[dict]:
    """Builds message history for Cohere API."""
    try:
        messages = [{"role": "system", "content": agent.system_prompt}]
        for msg in existing_messages:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        messages.append({"role": "user", "content": new_message})
        return messages
    except Exception as e:
        logger.error(f"Error building Cohere messages: {str(e)}")
        raise

def needs_tool(message: str) -> bool:
    """Determines if the message requires a tool (e.g., file search)."""
    try:
        # Simple heuristic: check for keywords indicating search
        return any(keyword in message.lower() for keyword in ["find", "search", "lookup"])
    except Exception as e:
        logger.error(f"Error in needs_tool: {str(e)}")
        return False

def process_tool_call(tool_call: dict) -> List[dict]:
    """Processes tool calls (e.g., local file search)."""
    from services.local_file_service import search_local_files
    try:
        if tool_call.get("name") == "local_file_search":
            query = tool_call.get("parameters", {}).get("query", "")
            return search_local_files(query)
        return []
    except Exception as e:
        logger.error(f"Error processing tool call: {str(e)}")
        return []
