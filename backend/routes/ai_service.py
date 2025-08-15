import re
import logging
from os import environ
from cohere import ClientV2, CohereAPIError  # Updated import
from routes.local_file_service import local_file_operation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Cohere client
COHERE_API_KEY = environ.get("COHERE_API_KEY")
if not COHERE_API_KEY:
    logger.warning("COHERE_API_KEY is not set. Running in mock mode.")
    co = None
else:
    try:
        co = ClientV2(api_key=COHERE_API_KEY)
    except CohereAPIError as e:
        logger.error(f"Failed to initialize Cohere client: {str(e)}")
        co = None

LOCAL_FILE_TOOL_NAME = "local_file_search"

def needs_tool(query: str) -> bool:
    """Determine if the query requires the local file search tool for RAG."""
    trigger_pattern = r"(find|search(ing)? for|looking for|need a|retrieve|document|file)"
    target_pattern = r"(professional|service\s?provider|supplier|vendor|consultant|expert|contract|agreement|profile)"
    return bool(re.search(trigger_pattern, query.lower()) and re.search(target_pattern, query.lower()))

def build_cohere_messages(agent, existing_messages, latest_user_query):
    """Build messages array for Cohere V2 chat API."""
    base_prompt = agent.system_prompt or "You are a helpful assistant."
    tool_prompt = (
        f"You have access to a tool named '{LOCAL_FILE_TOOL_NAME}' that searches local files "
        "(data.csv and data.json) for information about professionals, service providers, suppliers, "
        "or specific documents. Use this tool when the user requests information from files or mentions "
        "documents related to these entities. For other queries, respond directly using your knowledge."
    )
    system_prompt = f"{base_prompt}\n\n{tool_prompt}"
    
    cohere_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in existing_messages or []
    ]
    cohere_messages.append({"role": "user", "content": latest_user_query})
    
    return cohere_messages

def process_tool_call(tool_call) -> list[dict]:
    """Process local file search tool call and return documents for RAG."""
    if tool_call.name == LOCAL_FILE_TOOL_NAME:
        query = tool_call.parameters.get('query', '')
        return local_file_operation(query)
    return []
