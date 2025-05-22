import os
import json
import random
import asyncio
from collections import defaultdict
from tqdm import tqdm
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
import aiohttp
import requests

# Ensure NLTK data is downloaded
nltk.download('punkt')

# ----------------------------
# Configuration and Setup
# ----------------------------

# Define the target number of tokens
TARGET_TOKENS = 6_000_000

# Define the main categories and their subcategories
TOPIC_HIERARCHY = {
    "Language Skills and Vocabulary": {
        "Simple Storytelling": {
            "Daily Adventures": [],
            "Imaginative Scenarios": []
        },
        "Expressing Curiosity": {
            "Nature and Environment": [],
            "Everyday Phenomena": []
        },
        "Interactive Dialogue": {
            "Conversations with Adults": [],
            "Peer Interactions": []
        },
        "Emotional Expression": {
            "Happiness and Excitement": [],
            "Sadness and Frustration": []
        },
        "Vocabulary Building": {
            "Descriptive Words": [],
            "Action Words": []
        },
        "Interactive Learning": {
            "Simple Questions and Answers": [],
            "Basic Problem-Solving": []
        },
        "Imaginative Play": {
            "Pretend Games": [],
            "Fantasy Adventures": []
        },
        "Common Phrases and Expressions": {
            "Everyday Expressions": [],
            "Expressing Needs and Wants": []
        },
        "Theme-Based Vocabulary": {
            "Animals": [],
            "Family and Friends": []
        },
        "Safety and Manners": {
            "Safety Guidelines": [],
            "Manners and Respect": []
        },
        "Interactive Learning Enhancement": {
            "Repetition for Reinforcement": [],
            "Positive Reinforcement": []
        },
        "Parental and Educator Input": {
            "Community Contributions": [],
            "Parental Observations": []
        }
    }
}

# Directory to store generated data
DATA_DIR = "synthetic_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize tracking structures
tracking = defaultdict(lambda: {"lines": 0, "characters": 0, "tokens": 0})


# ----------------------------
# Utility Functions
# ----------------------------

def tokenize(text):
    """
    Tokenize the input text and return the number of tokens.
    """
    tokens = word_tokenize(text)
    return len(tokens)


def save_example(category, subcategory, subsubcat, example):
    """
    Save the generated example to a JSON file categorized by topics.
    """
    path = os.path.join(DATA_DIR, category, subcategory, subsubcat)
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, "data.json")

    # Load existing data
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Append the new example
    data.append(example)

    # Save back to the file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def update_tracking(category, subcategory, subsubcat, example):
    """
    Update the tracking statistics for the given category.
    """
    tokens = tokenize(example)
    characters = len(example)
    tracking_key = f"{category} > {subcategory} > {subsubcat}"

    tracking[tracking_key]["lines"] += 1
    tracking[tracking_key]["characters"] += characters
    tracking[tracking_key]["tokens"] += tokens


def get_total_tokens():
    """
    Calculate the total number of tokens generated so far.
    """
    return sum([v["tokens"] for v in tracking.values()])


def get_percentage_breakdown():
    """
    Get the percentage breakdown of tokens per category.
    """
    total = get_total_tokens()
    breakdown = {}
    for category, stats in tracking.items():
        breakdown[category] = (stats["tokens"] / total) * 100 if total > 0 else 0
    return breakdown


def display_statistics():
    """
    Display the current statistics in a readable format.
    """
    total = get_total_tokens()
    breakdown = get_percentage_breakdown()

    print(f"\nTotal Tokens Generated: {total}")
    print("Percentage Breakdown by Category:")
    for category, pct in sorted(breakdown.items(), key=lambda item: item[1], reverse=True):
        print(f"  {category}: {pct:.2f}%")


def save_statistics():
    """
    Save the tracking statistics to a CSV file.
    """
    data = []
    for category, stats in tracking.items():
        data.append({
            "Category": category,
            "Lines": stats["lines"],
            "Characters": stats["characters"],
            "Tokens": stats["tokens"]
        })
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(DATA_DIR, "tracking_statistics.csv"), index=False)


# ----------------------------
# Ollama Integration Functions
# ----------------------------

def fetch_available_models():
    """
    Fetch the list of available models from Ollama's /api/tags endpoint.
    """
    try:
        response = requests.get('http://localhost:11434/api/tags')
        response.raise_for_status()
        tags = response.json()

        # Adjust the parsing based on the actual response structure
        # Example assumes models are under 'tags' key and have a 'name' field
        models = [tag['name'] for tag in tags.get('tags', []) if 'model' in tag['name'].lower()]

        if not models:
            print("No models found with 'model' in their name. Using default model 'stablelm-zephyr'.")
            models = ['stablelm-zephyr']

        print(f"Available Models: {models}")
        return models
    except requests.exceptions.RequestException as e:
        print(f"Error fetching models from Ollama: {e}")
        print("Using default model 'stablelm-zephyr'.")
        return ['stablelm-zephyr']


def select_model(models):
    """
    Select a model from the list of available models.
    This function can be modified to implement different selection strategies.
    For simplicity, we'll select the first available model.
    """
    if not models:
        raise ValueError("No models available to select.")

    selected_model = models[0]  # Select the first model
    print(f"Selected Model: {selected_model}")
    return selected_model


async def generate_example_with_ollama_async(session, model, prompt, context):
    """
    Asynchronously generate a synthetic example using Ollama based on the prompt and context.
    Handles streaming responses and returns the complete generated text.
    """
    try:
        async with session.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model,
                    'prompt': prompt,
                    'context': context,
                },
                timeout=None  # Wait indefinitely for the stream
        ) as resp:
            resp.raise_for_status()
            generated_text = ""
            async for line in resp.content:
                if not line:
                    continue
                try:
                    body = json.loads(line.decode('utf-8'))
                    if 'error' in body:
                        raise Exception(body['error'])
                    response_part = body.get('response', '')
                    generated_text += response_part
                    if body.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue
            return generated_text.strip()
    except aiohttp.ClientError as e:
        print(f"Error communicating with Ollama: {e}")
        return "This is a generated example for the category."


# ----------------------------
# Data Generation Loop
# ----------------------------

async def handle_generation(session, model, category, subcat, subsubcat, pbar):
    """
    Handle the generation and tracking for a single example.
    """
    if get_total_tokens() >= TARGET_TOKENS:
        return
    prompt = (
        f"Provide a detailed and engaging example for the following topic hierarchy:\n"
        f"Category: {category}\n"
        f"Subcategory: {subcat}\n"
        f"Subsubcategory: {subsubcat}\n"
        f"Example:"
    )
    example = await generate_example_with_ollama_async(session, model, prompt, context=[])
    save_example(category, subcat, subsubcat, example)
    update_tracking(category, subcat, subsubcat, example)
    pbar.update(tokenize(example))


async def generate_data_async(model):
    """
    Asynchronous main loop to generate synthetic data until the target token count is reached.
    """
    # Flatten the topic hierarchy for easy iteration
    categories = []
    for category, subcats in TOPIC_HIERARCHY.items():
        for subcat, subsubcats in subcats.items():
            for subsubcat in subsubcats.keys():
                categories.append((category, subcat, subsubcat))

    # Shuffle the categories to ensure balanced generation
    random.shuffle(categories)

    print("Starting data generation...")

    async with aiohttp.ClientSession() as session:
        with tqdm(total=TARGET_TOKENS, desc="Generating Tokens") as pbar:
            tasks = []
            for category, subcat, subsubcat in categories:
                if get_total_tokens() >= TARGET_TOKENS:
                    break
                task = asyncio.create_task(
                    handle_generation(session, model, category, subcat, subsubcat, pbar)
                )
                tasks.append(task)

                # Limit the number of concurrent tasks to avoid overwhelming Ollama
                if len(tasks) >= 10:
                    await asyncio.gather(*tasks)
                    tasks = []

            # Await any remaining tasks
            if tasks:
                await asyncio.gather(*tasks)

    print("Data generation completed.")
    display_statistics()
    save_statistics()


# ----------------------------
# Execution
# ----------------------------

def main():
    # Step 1: Fetch available models
    models = fetch_available_models()

    # Step 2: Select a model
    selected_model = select_model(models)

    # Step 3: Run the asynchronous data generation
    asyncio.run(generate_data_async(selected_model))


if __name__ == "__main__":
    main()