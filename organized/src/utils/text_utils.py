# src/utils/text_utils.py

import random
import logging

logger = logging.getLogger("LoreGenerator")

def truncate_text(text: str, loss_percent: float) -> str:
    """Truncates a percentage of characters from the text."""
    try:
        num_chars = len(text)
        num_chars_to_remove = int(num_chars * loss_percent)
        if num_chars_to_remove == 0:
            return text
        indices_to_remove = sorted(random.sample(range(num_chars), num_chars_to_remove), reverse=True)
        text_list = list(text)
        for idx in indices_to_remove:
            text_list.pop(idx)
        truncated_text = "".join(text_list)
        logger.debug(f"Truncated {num_chars_to_remove} characters from text.")
        return truncated_text
    except Exception as e:
        logger.error(f"Failed to truncate text: {e}")
        return text
