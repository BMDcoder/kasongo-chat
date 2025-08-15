import re
import cohere
from config import COHERE_API_KEY, CONNECTOR_ID

co = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None

def build_cohere_messages(agent, existing_messages, latest_user_query, google_drive_connector_id=None):
    system_prompt = agent.system_prompt or "You are a helpful assistant."
    system_prompt += (
        "\nYou have access to a Google Drive connector for searching information "
        "about professionals, service providers, and suppliers. Only use the connector "
        "when the user's query is about finding such entities. For all other queries, "
        "answer based on your knowledge without using the connector."
    )

    existing_messages = existing_messages or []

    messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in existing_messages
    ]
    messages.append({"role": "user", "content": latest_user_query})

    def needs_connector(query: str) -> bool:
        trigger_pattern = r"(find|recommend|looking for|search(ing)? for|need a)"
        target_pattern = r"(professional|service\s?provider|supplier|vendor)"
        return bool(re.search(trigger_pattern, query.lower()) and re.search(target_pattern, query.lower()))

    connectors = None
    if google_drive_connector_id and needs_connector(latest_user_query):
        connectors = [{"id": google_drive_connector_id, "type": "google_drive"}]

    return messages, connectors
