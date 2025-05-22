# src/llm_clients/openai_client.py

import os
from typing import Optional
from openai import OpenAI
from src.llm_clients.base_client import BaseLLMClient

class OpenAIClient(BaseLLMClient):
    """Client for interacting with OpenAI's API."""

    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("OpenAI API key must be provided.")
        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key)

    def generate_text(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI API request failed: {e}")
