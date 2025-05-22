import requests
import json
import random
import time
from typing import List, Dict, Any


class OllamaPodcastGenerator:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.context = []
        self.documents = []

    def send_prompt(self, model: str, prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "options": {
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        response = requests.post(url, json=data)
        return response.json()

    def generate_document(self, doc_type: str, content: str) -> Dict[str, str]:
        return {
            "type": doc_type,
            "content": content
        }

    def create_world(self, model: str) -> None:
        prompt = "Create a rich, detailed world for our podcast series. Include historical events, cultural norms, and key locations."
        response = self.send_prompt(model, prompt)
        self.documents.append(self.generate_document("world_building", response['response']))

    def create_characters(self, model: str, num_characters: int) -> None:
        for i in range(num_characters):
            prompt = f"Create a complex character for our podcast series. Include background, motivations, and quirks."
            response = self.send_prompt(model, prompt)
            self.documents.append(self.generate_document("character", response['response']))

    def create_episode_outline(self, model: str, episode_number: int) -> None:
        context = "\n".join([doc['content'] for doc in self.documents])
        prompt = f"Using the world and characters we've established, create an outline for episode {episode_number}. Include key plot points and character development."
        response = self.send_prompt(model, prompt, max_tokens=1000)
        self.documents.append(self.generate_document("episode_outline", response['response']))

    def create_primary_source(self, model: str, episode_number: int) -> None:
        doc_types = ["journal_entry", "news_article", "official_report", "intercepted_communication"]
        doc_type = random.choice(doc_types)
        prompt = f"Create a {doc_type} that reveals key information for episode {episode_number}. This should be written from an in-world perspective."
        response = self.send_prompt(model, prompt)
        self.documents.append(self.generate_document(doc_type, response['response']))

    def create_listener_letter(self, model: str, episode_number: int) -> None:
        if episode_number > 1:
            prompt = f"Write a letter from a listener reacting to events in episode {episode_number - 1}. Include theories or questions that could guide the narrative."
            response = self.send_prompt(model, prompt)
            self.documents.append(self.generate_document("listener_letter", response['response']))

    def generate_podcast_series(self, model: str, num_episodes: int) -> List[Dict[str, Any]]:
        self.create_world(model)
        self.create_characters(model, 5)  # Create 5 main characters

        series = []
        for i in range(1, num_episodes + 1):
            print(f"Generating content for episode {i}...")
            self.create_episode_outline(model, i)
            self.create_primary_source(model, i)
            self.create_listener_letter(model, i)

            episode_docs = [doc for doc in self.documents if
                            doc['type'] in ['episode_outline', 'primary_source', 'listener_letter']]
            episode_content = "\n\n".join([doc['content'] for doc in episode_docs])

            series.append({
                "episode_number": i,
                "content": episode_content,
                "documents": episode_docs
            })

            # Clear episode-specific documents
            self.documents = [doc for doc in self.documents if
                              doc['type'] not in ['episode_outline', 'primary_source', 'listener_letter']]

            time.sleep(2)  # To avoid overwhelming the API

        return series


def main():
    generator = OllamaPodcastGenerator()
    model = "llama2"  # Adjust based on your available models
    num_episodes = 5

    podcast_series = generator.generate_podcast_series(model, num_episodes)

    with open("complex_podcast_series.json", "w") as f:
        json.dump(podcast_series, f, indent=2)

    print("Complex podcast series generated and saved to complex_podcast_series.json")


if __name__ == "__main__":
    main()