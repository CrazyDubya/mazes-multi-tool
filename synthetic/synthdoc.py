import os
import json
import time
import textwrap
import concurrent.futures
from pathlib import Path
import hashlib
import pickle
from openai import AsyncOpenAI
import asyncio

# Constants
API_KEY_ENV_VAR = "OPENAI_API_KEY"
OUTPUT_DIR = "generated_documents"
CACHE_DIR = "cache"
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # Seconds
DEFAULT_MAX_TOKENS = 1500
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PARALLEL_CALLS = True
DEPLOYMENT_NAME = "gpt-4o-mini"  # Example deployment name

# Load OpenAI API key
def load_api_key():
    """
    Load the OpenAI API key from environment variables.
    """
    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(f"Please set the {API_KEY_ENV_VAR} environment variable with your OpenAI API key.")
    return api_key

# Ensure cache directory exists
def ensure_cache_dir():
    """
    Ensure the cache directory exists.
    """
    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(parents=True, exist_ok=True)

# Caching helper functions
def get_cache_key(prompt):
    """
    Generate a cache key based on the prompt.
    """
    return hashlib.sha256(prompt.encode()).hexdigest()

def save_to_cache(cache_key, response):
    """
    Save response to cache.
    """
    ensure_cache_dir()
    cache_path = Path(CACHE_DIR) / cache_key
    with open(cache_path, 'wb') as f:
        pickle.dump(response, f)

def load_from_cache(cache_key):
    """
    Load response from cache if it exists.
    """
    cache_path = Path(CACHE_DIR) / cache_key
    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    return None

# OpenAI API call
async def call_openai_api(prompt, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE):
    """
    Call the OpenAI API with the given prompt and handle retries.
    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int, optional): The maximum number of tokens to generate.
        temperature (float, optional): Sampling temperature.
    Returns:
        str: The API's response text.
    """
    # TODO: Make max_tokens dynamic based on document type
    cache_key = get_cache_key(prompt)
    cached_response = load_from_cache(cache_key)
    if cached_response:
        return cached_response

    client = AsyncOpenAI(api_key=load_api_key())

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                n=1,
                stop=None
            )
            response_text = response.choices[0].message.content.strip()
            save_to_cache(cache_key, response_text)
            return response_text
        except Exception as e:
            print(f"OpenAI API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_BACKOFF} seconds...")
                await asyncio.sleep(RETRY_BACKOFF)
            else:
                print("Max retries reached. Exiting.")
                raise e

# Generate document types based on user story
async def generate_document_types(story_details):
    """
    Generate a list of document types based on the user's story.
    Args:
        story_details (str): The user's story description.
    Returns:
        list: List of dictionaries containing document type information.
    """
    prompt = f"""
You are an assistant that helps writers create rich lore and background material for their stories.
Based on the following story description, suggest ten diverse document types that can be used as background material.
For each document type, provide:
1. The name of the document type.
2. A brief description of its purpose in the story.
3. The level of detail (e.g., sentence, paragraph, page, multi-page, excerpt, transcript).

Story Description:
{story_details}

Please format your response as a JSON array of objects with the following keys:
- "name"
- "description"
- "detail_level"

Example:
[
    {{
        "name": "Newspaper Article",
        "description": "Reports on significant events within the story's world.",
        "detail_level": "page"
    }},
    ...
]
"""
    response = await call_openai_api(prompt)
    response = response.strip("` ")  # Strip backticks and spaces if the response is wrapped in a code block
    response = response.replace('```json', '').replace('```', '').strip()  # Remove markdown code block markers
    try:
        doc_types = json.loads(response)
        if not isinstance(doc_types, list):
            raise ValueError("Response is not a list.")
        for doc in doc_types:
            if not all(k in doc for k in ("name", "description", "detail_level")):
                raise ValueError("Missing keys in one of the document types.")
    except json.JSONDecodeError:
        print("Error: Unable to parse JSON from the API response.")
        print("Response received:")
        print(response)
        # Secondary parser to extract document types manually
        doc_types = []
        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                doc_types = json.loads(json_str)
        except Exception as e:
            print(f"Secondary parsing failed: {e}")
            doc_types = []
    except ValueError as ve:
        print(f"Error: {ve}")
        print("Response received:")
        print(response)
        doc_types = []
    return doc_types

# Generate documents with optional parallelization
async def generate_documents(story_details, doc_types, runs, parallel_calls=DEFAULT_PARALLEL_CALLS):
    """
    Generate synthetic documents based on the document types and number of runs.
    Args:
        story_details (str): The user's story description.
        doc_types (list): List of document type dictionaries.
        runs (int): Number of iterations to perform.
        parallel_calls (bool, optional): Whether to use parallelized API calls.
    """
    print("\n--- Generating Documents ---")
    for run in range(1, runs + 1):
        run_dir = Path(OUTPUT_DIR) / f"run_{run}"
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nGenerating documents for Run {run}...")

        if parallel_calls:
            await asyncio.gather(*(generate_and_save_document(story_details, doc, run_dir) for doc in doc_types))
        else:
            for doc in doc_types:
                await generate_and_save_document(story_details, doc, run_dir)

# Helper function to generate and save a document
async def generate_and_save_document(story_details, doc, run_dir):
    """
    Generate a document based on the document type and save it to disk.
    Args:
        story_details (str): The user's story description.
        doc (dict): The document type dictionary.
        run_dir (Path): Directory path where the document will be saved.
    """
    doc_name = doc['name']
    prompt = f"""
You are an assistant that helps writers create rich lore and background material for their stories.
Based on the following story description and document type, generate a synthetic {doc_name}.

Story Description:
{story_details}

Document Type:
{doc['description']}
Detail Level:
{doc['detail_level']}

Please provide the content for the {doc_name}. Ensure it adheres to the specified detail level and avoids clichés and mundane details.
"""
    content = await call_openai_api(prompt)
    save_document(run_dir, doc_name, content)
    print(f" - {doc_name} generated and saved.")

# Save document to disk
def save_document(run_dir, doc_type, content):
    """
    Save the generated document content to a file.
    Args:
        run_dir (Path): Directory path where the document will be saved.
        doc_type (str): The type/name of the document.
        content (str): The content of the document.
    """
    filename = "".join(c for c in doc_type if c.isalnum() or c in (' ', '_')).rstrip()
    filename = filename.replace(" ", "_") + ".txt"
    file_path = run_dir / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

# Main execution function
async def main():
    """
    Main function to orchestrate the synthetic document generation process.
    """
    print(textwrap.dedent("""
    ==========================================
           Synthetic Story Document Generator
    ==========================================
    """))

    try:
        load_api_key()
        ensure_cache_dir()
    except ValueError as e:
        print(e)
        return

    # Get user story input
    story_details = input("Please enter a brief description of your story: ")
    if not story_details.strip():
        print("Error: Story description cannot be empty.")
        return

    # Generate document types
    doc_types = await generate_document_types(story_details)
    if not doc_types:
        print("Failed to generate document types. Exiting.")
        return

    # Generate documents
    await generate_documents(story_details, doc_types, runs=2, parallel_calls=True)

if __name__ == "__main__":
    asyncio.run(main())