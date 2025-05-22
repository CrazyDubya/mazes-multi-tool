# src/generators/final_narrative_compiler.py

from typing import Optional, List, Dict, Any
from src.llm_clients.base_client import BaseLLMClient
from src.utils.file_utils import save_text
from src.utils.progress_display import display_progress
import logging
from datetime import datetime
from pathlib import Path
logger = logging.getLogger("LoreGenerator")

def compile_final_narrative(tale: str, supporting_docs: List[Dict[str, Any]], distilled_docs: List[Dict[str, Any]], llm_client: BaseLLMClient, prompts: list, project_name: str, token_limit: int, output_dir: Path) -> Optional[str]:
    """Compiles the final narrative."""
    try:
        prompt = " ".join(prompts).format(
            tale=tale,
            supporting_docs=format_documents(supporting_docs),
            distilled_docs=format_documents(distilled_docs),
            PROJECT_NAME=project_name,
            generation_time=datetime.now().isoformat()
        )

        logger.info("Compiling final narrative...")
        display_progress("Compiling final narrative...")
        final_narrative = llm_client.generate_text(prompt, token_limit)

        if final_narrative:
            save_text(final_narrative, "final_narrative", "final_narrative.txt", output_dir)
            logger.info("Final narrative compiled and saved successfully.")
            return final_narrative
        else:
            logger.warning("Failed to generate the final narrative.")
            return None
    except Exception as e:
        logger.error(f"Failed to compile final narrative: {e}")
        return None

def format_documents(documents: List[Dict[str, Any]]) -> str:
    """Formats documents for inclusion in the prompt."""
    formatted = ""
    for doc in documents:
        formatted += f"Name: {doc['name']}\nDescription: {doc['description']}\nType: {doc['type']}\nContent:\n{doc['content']}\n\n"
    return formatted
