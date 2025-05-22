# src/utils/file_utils.py

import re
import hashlib
from pathlib import Path
from typing import Optional
from src.logging_setup import setup_logging
import logging

logger = logging.getLogger("LoreGenerator")

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitizes a filename to be OS-compatible and short enough."""
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove illegal characters
    filename = filename.replace(" ", "_")  # Replace spaces with underscores
    name, ext = (filename.rsplit('.', 1) if '.' in filename else (filename, ''))
    if len(name) + len(ext) > max_length:
        name = name[:max_length - len(ext) - 9]
        name += '_' + hashlib.md5(name.encode()).hexdigest()[:8]
    return f"{name}.{ext}" if ext else name

def save_text(content: str, step: str, filename: Optional[str], output_dir: Path):
    """Saves generated text to a file within the specified step directory."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not filename:
            filename = f"{step}_{timestamp}.txt"
        safe_name = sanitize_filename(filename)
        file_path = output_dir / step / safe_name
        with file_path.open('w', encoding='utf-8') as file:
            file.write(content)
        logger.info(f"Saved {step} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save {step}: {e}")
        raise
