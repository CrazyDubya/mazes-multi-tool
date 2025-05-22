import json
import requests


class PodcastDocumentGenerator:
    def __init__(self):
        self.base_url = "http://localhost:11434/api/generate"
        self.headers = {"Content-Type": "application/json"}
        self.context = ""

    def send_prompt(self, prompt):
        data = {
            "model": "llama3.2",
            "prompt": f"{self.context}\n\nHuman: {prompt}\n\nAssistant:",
            "stream": False
        }
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()['response']
            self.context += f"\nHuman: {prompt}\n\nAssistant: {result}\n"
            return result
        else:
            return f"Error: {response.status_code}, {response.text}"

    def initialize_project(self):
        prompt = "We're creating a podcast series. We need to develop the world, characters, and generate documents for each episode. Can you outline the steps we should take?"
        return self.send_prompt(prompt)

    def develop_world(self):
        prompt = "Let's develop the world for our podcast. What key elements should we consider?"
        return self.send_prompt(prompt)

    def create_characters(self):
        prompt = "We need to create main characters for our podcast. Can you suggest a process for this?"
        return self.send_prompt(prompt)

    def plan_episodes(self):
        prompt = "How should we approach planning the episodes for our podcast series?"
        return self.send_prompt(prompt)

    def generate_documents(self, episode_number):
        prompt = f"For episode {episode_number}, what types of documents should we create to support the story?"
        return self.send_prompt(prompt)

    def create_specific_document(self, doc_type, episode_number):
        prompt = f"Please create a {doc_type} document for episode {episode_number} of our podcast."
        return self.send_prompt(prompt)


def main():
    generator = PodcastDocumentGenerator()

    print("Initializing project...")
    print(generator.initialize_project())

    print("\nDeveloping world...")
    print(generator.develop_world())

    print("\nCreating characters...")
    print(generator.create_characters())

    print("\nPlanning episodes...")
    print(generator.plan_episodes())

    num_episodes = int(input("\nHow many episodes do you want to create? "))

    for episode in range(1, num_episodes + 1):
        print(f"\nGenerating documents for Episode {episode}...")
        doc_types = generator.generate_documents(episode).split(", ")

        for doc_type in doc_types:
            print(f"\nCreating {doc_type} document...")
            document = generator.create_specific_document(doc_type, episode)

            filename = f"episode_{episode}_{doc_type.lower().replace(' ', '_')}.txt"
            with open(filename, "w") as f:
                f.write(document)
            print(f"Document saved as {filename}")


if __name__ == "__main__":
    main()