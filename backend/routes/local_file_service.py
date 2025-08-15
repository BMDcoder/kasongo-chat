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
                        "id": str(row.get("id", len(documents)+1)),
                        "title": str(row.get("title", "") or ""),
                        "content": str(row.get("content", "") or ""),
                        "url": str(row.get("url", "") or "")
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
                try:
                    json_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in {DATA_JSON_PATH}: {str(e)}")
                    json_data = []

                for item in json_data:
                    documents.append({
                        "id": str(item.get("id", len(documents)+1)),
                        "title": str(item.get("title", "") or ""),
                        "content": str(item.get("content", "") or ""),
                        "url": str(item.get("url", "") or "")
                    })
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
