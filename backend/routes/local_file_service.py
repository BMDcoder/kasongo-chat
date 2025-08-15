import csv
import json
import logging
from typing import List, Dict
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_CSV_PATH = "data/suppliers.csv"
DATA_JSON_PATH = "data/suppliers.json"

def load_local_files() -> List[Dict]:
    """Load and combine data from CSV and JSON files."""
    documents = []

    # Load CSV
    csv_path = Path(DATA_CSV_PATH)
    if csv_path.exists():
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    documents.append({
                        "id": row.get("id", str(len(documents) + 1)),
                        "title": row.get("title", ""),
                        "content": row.get("content", ""),
                        "url": row.get("url", "")
                    })
        except Exception as e:
            logger.error(f"Failed to load {DATA_CSV_PATH}: {str(e)}")
    else:
        logger.warning(f"{DATA_CSV_PATH} not found")

    # Load JSON
    json_path = Path(DATA_JSON_PATH)
    if json_path.exists():
        try:
            with open(json_path, mode="r", encoding="utf-8") as f:
                json_data = json.load(f)
                for item in json_data:
                    documents.append({
                        "id": item.get("id", str(len(documents) + 1)),
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "url": item.get("url", "")
                    })
        except Exception as e:
            logger.error(f"Failed to load {DATA_JSON_PATH}: {str(e)}")
    else:
        logger.warning(f"{DATA_JSON_PATH} not found")

    return documents

def generate_snippet(text: str, keywords: set, snippet_length: int = 150) -> str:
    """Generate a snippet around the first occurrence of any keyword."""
    text_lower = text.lower()
    for word in keywords:
        idx = text_lower.find(word)
        if idx != -1:
            start = max(0, idx - snippet_length // 2)
            end = min(len(text), idx + snippet_length // 2)
            snippet = text[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            return snippet
    return text[:snippet_length] + ("..." if len(text) > snippet_length else "")

def search_local_files(query: str, top_k: int = 5) -> List[Dict]:
    """Search local files for documents matching the query and return top results with snippets."""
    try:
        documents = load_local_files()
        if not documents:
            return []

        query_words = set(re.findall(r'\w+', query.lower()))
        scored_docs = []

        for doc in documents:
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            # Simple relevance score: number of query words found
            score = sum(1 for word in query_words if word in title or word in content)
            if score > 0:
                snippet = generate_snippet(doc.get("content", ""), query_words)
                scored_docs.append({
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "content": snippet,
                    "url": doc.get("url"),
                    "score": score
                })

        # Sort by score descending and limit to top_k
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:top_k]

    except Exception as e:
        logger.error(f"Local file search failed: {str(e)}")
        return []
