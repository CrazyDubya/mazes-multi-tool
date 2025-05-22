# src/llm_clients/base_client.py

from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Generates text based on a prompt."""
        pass
