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

def auto_map_fields(row: Dict, current_index: int) -> Dict:
    """Auto-detect id, title, content, and url fields based on key names."""
    # Lowercase keys for matching
    keys = {k.lower(): k for k in row.keys()}

    # ID detection
    id_key = next((keys[k] for k in keys if "id" in k), None)

    # Title detection
    title_key = next(
        (keys[k] for k in keys if "name" in k or "title" in k or "subject" in k),
        None
    )

    # URL detection
    url_key = next(
        (keys[k] for k in keys if "url" in k or "link" in k or "email" in k or "website" in k),
        None
    )

    # Content = everything else
    excluded_keys = {id_key, title_key, url_key}
    content_parts = [
        f"{k}: {row[k]}" for k in row.keys()
        if k not in excluded_keys and row.get(k)
    ]
    content_str = ", ".join(content_parts)

    return {
        "id": str(row.get(id_key, current_index + 1)) if id_key else str(current_index + 1),
        "title": str(row.get(title_key, "") or ""),
        "content": content_str,
        "url": str(row.get(url_key, "") or "")
    }

def load_local_files() -> List[Dict]:
    """Load and combine data from CSV and JSON files with auto-detected mapping."""
    documents = []

    # Load CSV
    csv_path = Path(DATA_CSV_PATH)
    if csv_path.exists():
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    documents.append(auto_map_fields(row, len(documents)))
        except Exception as e:
            logger.error(f"Failed to load {DATA_CSV_PATH}: {str(e)}")
    else:
        logger.warning(f"{DATA_CSV_PATH} not found")

    # Load JSON
    json_path = Path(DATA_JSON_PATH)
    if json_path.exists():
        try:
            with open(json_path, mode="r", encoding="utf-8") as f:
                try:
                    json_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in {DATA_JSON_PATH}: {str(e)}")
                    json_data = []

                for item in json_data:
                    if isinstance(item, dict):
                        documents.append(auto_map_fields(item, len(documents)))
        except Exception as e:
            logger.error(f"Failed to load {DATA_JSON_PATH}: {str(e)}")
    else:
        logger.warning(f"{DATA_JSON_PATH} not found")

    return documents

def search_local_files(query: str) -> List[Dict]:
    """Search local files for relevant documents."""
    try:
        documents = load_local_files()
        if not documents:
            return []

        query_words = set(re.findall(r'\w+', query.lower()))
        relevant_docs = []

        for doc in documents:
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            if any(word in content or word in title for word in query_words):
                relevant_docs.append(doc)

        return relevant_docs[:5]  # Limit results
    except Exception as e:
        logger.error(f"Local file search failed: {str(e)}")
        return []
