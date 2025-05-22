# src/llm_clients/groq_client.py

import groq
from typing import Optional
from src.llm_clients.base_client import BaseLLMClient

class GroqClient(BaseLLMClient):
    """Client for interacting with Groq's API."""

    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Groq API key must be provided.")
        self.api_key = api_key
        self.model_name = model_name
        self.client = groq.Client(api_key=self.api_key)

    def generate_text(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Groq API request failed: {e}")
