import os
import json
import time
import textwrap
import csv
from pathlib import Path
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI, OpenAI
import anthropic

# Constants
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
NEBIUS_API_KEY_ENV_VAR = "NEBIUS_API_KEY"
ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
OUTPUT_DIR = Path("generated_documents")
RUNS_RECORD_FILE = Path("runs_record.csv")
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # Seconds
DEFAULT_MAX_TOKENS = 1500
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PARALLEL_CALLS = True
OPENAI_DEPLOYMENT_NAME = "gpt-4o-mini"  # Example deployment name
NEBIUS_MODEL_NAME = "meta-llama/Meta-Llama-3.1-405B-Instruct"
OLLAMA_MODEL_NAME = "llama3.2"
CLAUDE_MODEL_NAME = "claude-3-5-sonnet-20240620"

# Type aliases
DocumentType = Dict[str, str]

class APIKeyError(Exception):
    """Custom exception for API key errors."""
    pass

class APICallError(Exception):
    """Custom exception for API call errors."""
    pass

def load_api_keys() -> tuple[str, str, str]:
    """
    Load the OpenAI, Nebius, and Anthropic API keys from environment variables.

    Returns:
        tuple: A tuple containing the OpenAI, Nebius, and Anthropic API keys.

    Raises:
        APIKeyError: If any of the API keys are not set in the environment variables.
    """
    openai_key = os.getenv(OPENAI_API_KEY_ENV_VAR)
    nebius_key = os.getenv(NEBIUS_API_KEY_ENV_VAR)
    anthropic_key = os.getenv(ANTHROPIC_API_KEY_ENV_VAR)

    if not openai_key:
        raise APIKeyError(f"Please set the {OPENAI_API_KEY_ENV_VAR} environment variable with your OpenAI API key.")
    if not nebius_key:
        raise APIKeyError(f"Please set the {NEBIUS_API_KEY_ENV_VAR} environment variable with your Nebius API key.")
    if not anthropic_key:
        raise APIKeyError(f"Please set the {ANTHROPIC_API_KEY_ENV_VAR} environment variable with your Anthropic API key.")

    return openai_key, nebius_key, anthropic_key

async def call_openai_api(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Call the OpenAI API with the given prompt and handle retries.

    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature to use.

    Returns:
        str: The generated content from the API.

    Raises:
        APICallError: If the API call fails after all retry attempts.
    """
    openai_key, _, _ = load_api_keys()
    client = AsyncOpenAI(api_key=openai_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                n=1,
                stop=None
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_BACKOFF} seconds...")
                await asyncio.sleep(RETRY_BACKOFF)
            else:
                raise APICallError("Max retries reached for OpenAI API call.") from e

def call_nebius_api(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Call the Nebius API with the given prompt and handle retries.

    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature to use.

    Returns:
        str: The generated content from the API.

    Raises:
        APICallError: If the API call fails after all retry attempts.
    """
    _, nebius_key, _ = load_api_keys()
    client = OpenAI(
        base_url="https://api.studio.nebius.ai/v1/",
        api_key=nebius_key,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.create(
                model=NEBIUS_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                n=1,
                stream=False,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Nebius API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_BACKOFF} seconds...")
                time.sleep(RETRY_BACKOFF)
            else:
                raise APICallError("Max retries reached for Nebius API call.") from e

def call_ollama_api(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Call local Ollama via OpenAI API with the given prompt and handle retries.

    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature to use.

    Returns:
        str: The generated content from the API.

    Raises:
        APICallError: If the API call fails after all retry attempts.
    """
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Ollama doesn't require an API key, but we need to provide a non-empty string
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.create(
                model=OLLAMA_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Ollama API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_BACKOFF} seconds...")
                time.sleep(RETRY_BACKOFF)
            else:
                raise APICallError("Max retries reached for Ollama API call.") from e

def call_claude_api(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Call the Anthropic Claude API with the given prompt and handle retries.

    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature to use.

    Returns:
        str: The generated content from the API.

    Raises:
        APICallError: If the API call fails after all retry attempts.
    """
    _, _, anthropic_key = load_api_keys()
    client = anthropic.Anthropic(api_key=anthropic_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=CLAUDE_MODEL_NAME,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            print(f"Claude API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_BACKOFF} seconds...")
                time.sleep(RETRY_BACKOFF)
            else:
                raise APICallError("Max retries reached for Claude API call.") from e

def ensure_runs_record() -> None:
    """
    Ensure that the runs_record.csv file exists and has the correct headers.
    """
    if not RUNS_RECORD_FILE.exists():
        with open(RUNS_RECORD_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['run_id', 'document_name', 'detail_level'])


def log_document(run_id: str, doc_name: str, detail_level: str) -> None:
    """
    Log the document's name and detail level in the runs_record.csv file.

    Args:
        run_id (str): A unique identifier for the current run.
        doc_name (str): The name of the document generated.
        detail_level (str): The detail level of the document.
    """
    with open(RUNS_RECORD_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([run_id, doc_name, detail_level])


def parse_document_types(response: str) -> List[DocumentType]:
    """
    Parse document types from the API response using a secondary parser to handle edge cases.

    Args:
        response (str): The response text from the API.

    Returns:
        List[DocumentType]: Parsed list of document types or an empty list in case of failure.
    """
    doc_types = []
    try:
        start_idx = response.find('[')
        end_idx = response.rfind(']')
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx + 1]
            doc_types = json.loads(json_str)

            if doc_types:
                print("Successfully parsed document types using the secondary parser.")
            else:
                print("The extracted JSON was empty, likely due to issues in the response formatting.")
        else:
            print("We failed to generate document types, and the response did not contain recognizable JSON.")
    except json.JSONDecodeError as e:
        print(f"Secondary parsing failed due to JSON decode error: {e}")
        print("Please check the response format for irregularities.")
    except Exception as e:
        print(f"Secondary parsing failed due to an unexpected error: {e}")

    return doc_types


async def generate_document_types(story_details: str, api_choice: str) -> List[DocumentType]:
    """
    Generate a list of document types based on the user's story.

    Args:
        story_details (str): The user's story description.
        api_choice (str): The chosen API ('openai', 'nebius', 'ollama', or 'claude').

    Returns:
        List[DocumentType]: List of dictionaries containing document type information.
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
"""
    if api_choice == "openai":
        response = await call_openai_api(prompt)
    elif api_choice == "nebius":
        response = call_nebius_api(prompt)
    elif api_choice == "ollama":
        response = call_ollama_api(prompt)
    else:  # claude
        response = call_claude_api(prompt)

    response = response.strip("` ")  # Strip backticks and spaces if the response is wrapped in a code block
    response = response.replace('```json', '').replace('```', '').strip()  # Remove markdown code block markers

    doc_types = parse_document_types(response)

    if not doc_types:
        raise ValueError("Failed to generate document types.")

    return doc_types

async def generate_and_save_document(story_details: str, doc: DocumentType, run_dir: Path, run_id: str, api_choice: str) -> None:
    """
    Generate a document based on the document type and save it to disk.

    Args:
        story_details (str): The user's story description.
        doc (DocumentType): The document type dictionary.
        run_dir (Path): Directory path where the document will be saved.
        run_id (str): Unique identifier for this run.
        api_choice (str): The chosen API ('openai', 'nebius', 'ollama', or 'claude').
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
    if api_choice == "openai":
        content = await call_openai_api(prompt)
    elif api_choice == "nebius":
        content = call_nebius_api(prompt)
    elif api_choice == "ollama":
        content = call_ollama_api(prompt)
    else:  # claude
        content = call_claude_api(prompt)

    unique_doc_name = f"{doc_name}_{run_id}"
    save_document(run_dir, unique_doc_name, content)
    log_document(run_id, unique_doc_name, doc['detail_level'])
    print(f" - {doc_name} generated and saved as {unique_doc_name}.")



def save_document(run_dir: Path, doc_name: str, content: str) -> None:
    """
    Save the generated document content to a file.

    Args:
        run_dir (Path): Directory path where the document will be saved.
        doc_name (str): The name of the document.
        content (str): The content of the document.
    """
    filename = "".join(c for c in doc_name if c.isalnum() or c in (' ', '_')).rstrip()
    filename = filename.replace(" ", "_") + ".txt"
    file_path = run_dir / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


async def generate_documents(story_details: str, doc_types: List[DocumentType], runs: int, parallel_calls: bool,
                             api_choice: str, run_dir: Path = None) -> None:
    """
    Generate synthetic documents based on the document types and number of runs.

    Args:
        story_details (str): The user's story description.
        doc_types (List[DocumentType]): List of document type dictionaries.
        runs (int): Number of iterations to perform.
        parallel_calls (bool): Whether to use parallelized API calls.
        api_choice (str): The chosen API ('openai' or 'nebius').
        run_dir (Path, optional): Directory to save the generated documents.
    """
    print("\n--- Generating Documents ---")

    if not run_dir:
        story_key = "".join(c for c in story_details[:16] if c.isalnum() or c in (' ', '_')).replace(" ", "_")
        run_dir = OUTPUT_DIR / story_key

    run_id = str(int(time.time()))  # Unique run identifier based on timestamp

    for run in range(1, runs + 1):
        current_run_dir = run_dir / f"run_{run}"
        current_run_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nGenerating documents for Run {run}...")

        if parallel_calls:
            await asyncio.gather(
                *(generate_and_save_document(story_details, doc, current_run_dir, run_id, api_choice) for doc in
                  doc_types))
        else:
            for doc in doc_types:
                await generate_and_save_document(story_details, doc, current_run_dir, run_id, api_choice)

    print("\nDocument generation complete.")
    user_choice = input(
        "\nWould you like to: \n1. Generate the same documents with new content\n2. Generate a new set of documents\n3. Finish\nChoose an option (1, 2, or 3): ")
    if user_choice == "1":
        await generate_documents(story_details, doc_types, runs=1, parallel_calls=parallel_calls, api_choice=api_choice,
                                 run_dir=run_dir)
    elif user_choice == "2":
        new_doc_types = await generate_document_types(story_details, api_choice)
        if new_doc_types:
            await generate_documents(story_details, new_doc_types, runs=1, parallel_calls=parallel_calls,
                                     api_choice=api_choice, run_dir=run_dir)
    else:
        print("Process finished.")


async def main() -> None:
    """
    Main function to orchestrate the synthetic document generation process.
    """
    print(textwrap.dedent("""
    ==========================================
           Synthetic Story Document Generator
    ==========================================
    """))

    try:
        load_api_keys()
        ensure_runs_record()
    except APIKeyError as e:
        print(e)
        return

    # API choice
    api_choice = input("Choose an API to use (openai/nebius/ollama/anthropic): ").lower()
    while api_choice not in ["openai", "nebius", "ollama", "anthropic"]:
        api_choice = input("Invalid choice. Please enter 'openai', 'nebius', 'ollama', or 'anthropic': ").lower()


    # Pre-generation user choice
    choice = input("Would you like to:\n1. Load a previous run\n2. Enter a new story prompt\nChoose an option (1 or 2): ")

    if choice == "1":
        run_dir = input("Enter the unique directory (first 16 characters of story): ")
        run_dir = OUTPUT_DIR / run_dir
        if not run_dir.exists():
            print("Directory not found. Please try again.")
            return

        try:
            story_details_file = next(run_dir.glob("story_details.txt"), None)
            if story_details_file and story_details_file.exists():
                with open(story_details_file, 'r') as f:
                    story_details = f.read().strip()
            else:
                print("Story details file not found. Please provide the same story description manually.")
                story_details = input("Please enter the same story description to continue: ")

            doc_types_file = next(run_dir.glob("doc_types.json"), None)
            if doc_types_file and doc_types_file.exists():
                with open(doc_types_file, 'r') as f:
                    doc_types = json.load(f)
            else:
                print("Could not find document types from previous run. Exiting.")
                return

        except StopIteration:
            print("Invalid directory structure. Exiting.")
            return

    elif choice == "2":
        story_details = input("Please enter a brief description of your story: ")
        if not story_details.strip():
            print("Error: Story description cannot be empty.")
            return
        try:
            doc_types = await generate_document_types(story_details, api_choice)
        except ValueError as e:
            print(e)
            return

        # Save story details and document types for future runs
        story_key = "".join(c for c in story_details[:16] if c.isalnum() or c in (' ', '_')).replace(" ", "_")
        run_dir = OUTPUT_DIR / story_key
        run_dir.mkdir(parents=True, exist_ok=True)

        with open(run_dir / "story_details.txt", 'w', encoding='utf-8') as f:
            f.write(story_details)

        with open(run_dir / "doc_types.json", 'w', encoding='utf-8') as f:
            json.dump(doc_types, f, indent=4)

    else:
        print("Invalid choice. Exiting.")
        return

    # Generate documents
    try:
        await generate_documents(story_details, doc_types, runs=1, parallel_calls=True, api_choice=api_choice, run_dir=run_dir)
    except APICallError as e:
        print(f"Error during document generation: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())