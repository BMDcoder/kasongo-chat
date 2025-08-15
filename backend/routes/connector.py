# services/ai_service.py
import re
from cohere import ClientV2
from config import COHERE_API_KEY

# Initialize Cohere V2 client globally
co = ClientV2(api_key=COHERE_API_KEY) if COHERE_API_KEY else None

def needs_tool(query: str) -> bool:
    """
    Return True if the query should trigger the Google Drive tool.
    """
    trigger_pattern = r"(find|recommend|looking for|search(ing)? for|need a)"
    target_pattern = r"(professional|service\s?provider|supplier|vendor)"
    return bool(re.search(trigger_pattern, query.lower()) and re.search(target_pattern, query.lower()))

def build_cohere_messages(agent, existing_messages, latest_user_query):
    """
    Build messages array for Cohere V2 chat API (tools handled separately).
    """
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    system_prompt += (
        "\nYou have access to a Google Drive tool named 'google_drive_connector' for searching information "
        "about professionals, service providers, and suppliers. Only use the tool "
        "when the user's query is about finding such entities. For all other queries, "
        "answer based on your knowledge without using the tool."
    )

    existing_messages = existing_messages or []

    cohere_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in existing_messages
    ]

    cohere_messages.append({"role": "user", "content": latest_user_query})

    return cohere_messages
