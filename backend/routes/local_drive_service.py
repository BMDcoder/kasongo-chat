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
    """Load and combine data from data.csv and data.json."""
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

def local_file_operation(query: str) -> List[Dict]:
    """Search local files for documents matching the query."""
    try:
        documents = load_local_files()
        if not documents:
            return []

        # Simple keyword-based search
        query_words = set(re.findall(r'\w+', query.lower()))
        relevant_docs = []
        for doc in documents:
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            if any(word in content or word in title for word in query_words):
                relevant_docs.append(doc)

        return relevant_docs[:5]  # Limit to 5 documents for performance
    except Exception as e:
        logger.error(f"Local file operation failed: {str(e)}")
        return []
