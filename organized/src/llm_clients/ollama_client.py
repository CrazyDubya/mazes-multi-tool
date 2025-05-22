# src/llm_clients/ollama_client.py

import requests
import json
from typing import Optional
from src.llm_clients.base_client import BaseLLMClient

class OllamaClient(BaseLLMClient):
    """Client for interacting with Ollama's API."""

    def __init__(self, api_url: str, model_name: str):
        self.api_url = api_url
        self.model_name = model_name

    def generate_text(self, prompt: str, max_tokens: int) -> Optional[str]:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "options": {"max_tokens": max_tokens, "temperature": 0.7, "top_p": 0.9}
        }

        try:
            with requests.post(self.api_url, headers=headers, data=json.dumps(data), stream=True, timeout=600) as response:
                response.raise_for_status()
                generated_text = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            json_obj = json.loads(line.decode('utf-8'))
                            response_text = json_obj.get("response", "")
                            generated_text += response_text
                            if json_obj.get("done", False):
                                break
                        except json.JSONDecodeError as e:
                            raise ValueError(f"JSON decoding failed: {e}")
                return generated_text.strip() if generated_text else None
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred with Ollama: {e}")
