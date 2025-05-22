# src/generators/supporting_document_generator.py

from typing import Optional, Dict, Any, List
import random
import re
from pathlib import Path
from src.llm_clients.base_client import BaseLLMClient
from src.utils.file_utils import save_text, sanitize_filename
from src.utils.progress_display import display_progress
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger("LoreGenerator")

def generate_supporting_document(doc_number: int, llm_client: BaseLLMClient, prompts: Dict[str, list], document_types: List[str], project_name: str, token_limits: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generates a single supporting document."""
    try:
        doc_type = random.choice(document_types)

        # --- Stage 1: Concept Generation ---
        name_prompt = " ".join(prompts['supporting_document']['name_generation']).format(doc_type=doc_type, PROJECT_NAME=project_name)
        name = llm_client.generate_text(name_prompt, max_tokens=20)

        if not name:
            name = f"Supporting_Document_{doc_number}"
            logger.warning(f"Using fallback name: {name}")
        else:
            name = name.strip().split('\n')[0]
            name = re.sub(r'^\d+\.?\s*', '', name)
            name = sanitize_filename(name)

            if len(name) < 3 or "suggestions" in name.lower():
                logger.warning(f"Generated name '{name}' is invalid. Using fallback name.")
                name = f"Supporting_Document_{doc_number}"
                name = sanitize_filename(name)

        desc_prompt = " ".join(prompts['supporting_document']['description_generation']).format(doc_type=doc_type, name=name, PROJECT_NAME=project_name)
        description = llm_client.generate_text(desc_prompt, max_tokens=300)
        if not description:
            description = f"Description of {name}."
            logger.warning(f"Using fallback description for {name}")

        # --- Stage 2: Content Generation ---
        size_category = random.choices(
            ["sentence", "paragraph", "excerpt", "report", "multi_volume"],
            weights=[5, 20, 35, 25, 15],
            k=1
        )[0]
        token_allocation = token_limits["supporting_document"].get(size_category,
                            random.randint(
                                token_limits["supporting_document"]["multi_volume_min"],
                                token_limits["supporting_document"]["multi_volume_max"]
                            ))

        content_prompt = " ".join(prompts['supporting_document']['content_generation']).format(
            name=name, doc_type=doc_type, description=description, size_category=size_category
        )
        content = llm_client.generate_text(content_prompt, token_allocation)
        if not content:
            content = f"Content of {name}."
            logger.warning(f"Using fallback content for {name}")

        document = {
            "name": name,
            "description": description,
            "type": doc_type,
            "size": size_category,
            "token_allocation": token_allocation,
            "content": content
        }

        logger.info(f"Generated supporting document {doc_number}: {name} ({doc_type}, {size_category})")
        return document

    except Exception as e:
        logger.error(f"Failed to generate supporting document {doc_number}: {e}")
        return None

def generate_supporting_documents(num_docs: int, llm_client: BaseLLMClient, prompts: Dict[str, list], document_types: List[str], project_name: str, token_limits: Dict[str, Any], output_dir: Path) -> Optional[List[Dict[str, Any]]]:
    """Generates multiple supporting documents."""
    supporting_docs = []
    for i in range(1, num_docs + 1):
        display_progress(f"Generating supporting document {i}...")
        doc = generate_supporting_document(i, llm_client, prompts, document_types, project_name, token_limits)
        if doc:
            supporting_docs.append(doc)
            filename = f"{doc['name']}.txt"
            try:
                save_text(doc["content"], "supporting_documents", filename, output_dir)
            except Exception as e:
                logger.error(f"Failed to save content for document {i}: {e}")
                continue

            metadata = {
                "original_name": doc.get("original_name", doc["name"]),
                "name": doc["name"],
                "description": doc["description"],
                "type": doc["type"],
                "size": doc["size"],
                "token_allocation": doc["token_allocation"],
                "filename": filename
            }

            metadata_filename = f"{doc['name']}_metadata.json"
            metadata_path = output_dir / "supporting_documents" / metadata_filename
            try:
                with metadata_path.open('w', encoding='utf-8') as meta_file:
                    json.dump(metadata, meta_file, indent=4)
                logger.debug(f"Saved metadata for '{doc['name']}' to {metadata_path}")
            except Exception as e:
                logger.error(f"Failed to save metadata for document {i}: {e}")

    return supporting_docs if supporting_docs else None
