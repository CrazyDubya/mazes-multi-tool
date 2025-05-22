# src/generators/distillation.py

from typing import List, Dict, Any
from src.utils.text_utils import truncate_text
from src.utils.file_utils import save_text
from src.utils.progress_display import display_progress
import logging
from pathlib import Path
import random

logger = logging.getLogger("LoreGenerator")

def simulate_distillation(documents: List[Dict[str, Any]], num_distillers: int, loss_char: float, loss_docs: float, output_dir: Path) -> List[Dict[str, Any]]:
    """Simulates the distillation process over multiple layers."""
    distilled_documents = documents.copy()

    for layer in range(1, num_distillers + 1):
        logger.info(f"Starting distillation layer {layer}...")
        display_progress(f"Distillation layer {layer} in progress...")

        num_docs_current = len(distilled_documents)
        num_docs_to_lose = int(num_docs_current * loss_docs)

        if num_docs_to_lose > 0:
            docs_to_remove = random.sample(distilled_documents, num_docs_to_lose)
            for doc in docs_to_remove:
                distilled_documents.remove(doc)
            logger.info(f"Distillation layer {layer}: Removed {num_docs_to_lose} documents.")

        for doc in distilled_documents:
            original_length = len(doc["content"])
            doc["content"] = truncate_text(doc["content"], loss_char)
            truncated_length = len(doc["content"])
            logger.debug(
                f"Distillation layer {layer}: Truncated document '{doc['name']}' from {original_length} to {truncated_length} characters."
            )
            doc["token_allocation"] = max(int(doc["token_allocation"] * (truncated_length / original_length)), 1)

        layer_dir = output_dir / "distilled_layers" / f"layer_{layer}"
        layer_dir.mkdir(parents=True, exist_ok=True)
        for doc in distilled_documents:
            filename = f"{doc['name']}.txt"
            save_text(doc["content"], f"distilled_layers/layer_{layer}", filename, output_dir)
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
            metadata_path = layer_dir / metadata_filename

            try:
                with metadata_path.open("w", encoding="utf-8") as meta_file:
                    json.dump(metadata, meta_file, indent=4)
            except Exception as e:
                logger.error(f"Failed to save metadata for '{doc['name']}' in layer {layer}: {e}")

        logger.info(f"Distillation layer {layer} completed. {len(distilled_documents)} documents remaining.")

    return distilled_documents
