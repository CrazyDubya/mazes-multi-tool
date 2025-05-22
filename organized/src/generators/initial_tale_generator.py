# src/generators/initial_tale_generator.py

from typing import Optional
from src.llm_clients.base_client import BaseLLMClient
from src.utils.file_utils import save_text
from src.utils.progress_display import display_progress
import logging
from datetime import datetime
from pathlib import Path
logger = logging.getLogger("LoreGenerator")

def generate_initial_tale(llm_client: BaseLLMClient, prompts: list, output_dir: Path, project_name: str, user_prose: str, token_limit: int) -> Optional[str]:
    """Generates the initial tale."""
    try:
        prompt = " ".join(prompts).format(PROJECT_NAME=project_name, user_prose=user_prose)
        logger.info("Generating initial tale...")
        display_progress("Generating initial tale...")
        tale = llm_client.generate_text(prompt, token_limit)
        if tale:
            save_text(tale, "original_tale", "initial_tale.txt", output_dir)
            logger.info("Initial tale generated and saved successfully.")
            return tale
        else:
            logger.warning("Failed to generate the initial tale.")
            return None
    except Exception as e:
        logger.error(f"Error in generating initial tale: {e}")
        return None
