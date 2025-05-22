import os
import json
import time
import logging
import random
import hashlib
import re
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import textwrap
import csv
import requests

from rich import print as rprint
from rich.console import Console
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from openai import AsyncOpenAI, OpenAI
import anthropic
import groq  # Ensure you have the groq client installed or replace with the appropriate client

# ------------------------------ Configuration ------------------------------ #

# API Keys and Endpoints
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
NEBIUS_API_KEY_ENV_VAR = "NEBIUS_API_KEY"
ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"  # Assuming Groq also requires an API key

# Default LLM Settings
LLM_API_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/v1/completions",
    "ollama": "http://localhost:11434/api/generate",
    "anthropic": "https://api.anthropic.com/v1/complete"  # Example endpoint
}

MODEL_NAMES = {
    "openai": "gpt-4o-mini",  # Adjust as needed
    "groq": "mixtral-8x7b-32768",  # Adjust as needed
    "ollama": "llama3.2:1b",  # Adjust as needed
    "anthropic": "claude-3-sonnet-20240229"  # Adjust as needed
}

# Directories
PROJECT_NAME = input("Enter the project name: ").strip()
OUTPUT_DIR = Path("generated_documents") / PROJECT_NAME
LOG_DIR = Path("logs") / PROJECT_NAME
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging Configuration
LOG_LEVEL = logging.INFO
LOG_FILE = LOG_DIR / f"generation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RichHandler(console=Console(), rich_tracebacks=True),
        logging.FileHandler(LOG_FILE, encoding="utf-8")  # Explicitly set encoding
    ]
)

logger = logging.getLogger("LoreGenerator")

# Constants
MAX_RETRIES = 3  # Maximum retries for text generation
RETRY_BACKOFF = 2  # Seconds
MIN_ACCEPTABLE_LENGTH = 10  # Minimum acceptable length for generated text

TOKEN_LIMITS = {  # More generous token limits
    "original_tale": 15000,
    "supporting_document": {
        "sentence": 75,
        "short": 750,
        "medium": 1500,
        "long": 7500,
        "multi_volume_min": 15000,
        "multi_volume_max": 16000
    },
    "final_narrative": 15000
}

NUM_SUPPORTING_DOCS = 10
NUM_DISTILLERS = 3
LOSS_PERCENT_CHAR = 0.30
LOSS_PERCENT_DOCS = 0.40

DOCUMENT_TYPES = [  # Expanded document types
    "letter", "receipt", "police report", "state testimony", "scorecard",
    "poem", "autobiography", "biography", "autograph", "contract",
    "invoice", "testimonial", "journal entry", "diary", "memorandum",
    "protocol", "decree", "manifesto", "speech", "report",
    "essay", "research paper", "field notes", "interview transcript", "code of laws",
    "prophecy", "legend", "myth", "folktale", "song lyrics", "play script"
]

# Initialize Rich Console for colored outputs
console = Console()

# ------------------------------ Helper Classes ------------------------------ #

class APIKeyError(Exception):
    """Custom exception for API key errors."""
    pass


class APICallError(Exception):
    """Custom exception for API call errors."""
    pass

# ------------------------------ Helper Functions ------------------------------ #


def load_api_keys() -> tuple[str, str, str, str]:
    """Load the OpenAI, Nebius, Anthropic, and Groq API keys from environment variables."""
    openai_key = os.getenv(OPENAI_API_KEY_ENV_VAR)
    nebius_key = os.getenv(NEBIUS_API_KEY_ENV_VAR)
    anthropic_key = os.getenv(ANTHROPIC_API_KEY_ENV_VAR)
    groq_key = os.getenv(GROQ_API_KEY_ENV_VAR)

    missing_keys = []
    if not openai_key:
        missing_keys.append(OPENAI_API_KEY_ENV_VAR)
    if not nebius_key:
        missing_keys.append(NEBIUS_API_KEY_ENV_VAR)
    if not anthropic_key:
        missing_keys.append(ANTHROPIC_API_KEY_ENV_VAR)
    if not groq_key:
        missing_keys.append(GROQ_API_KEY_ENV_VAR)

    if missing_keys:
        raise APIKeyError(f"Please set the following environment variables: {', '.join(missing_keys)}")

    return openai_key, nebius_key, anthropic_key, groq_key


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitizes a filename to be OS-compatible and short enough."""
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.replace(" ", "_")
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename


def save_text(content: str, step: str, filename: Optional[str] = None):
    """Saves generated text to a file."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not filename:
            filename = f"{step}_{timestamp}.txt"
        safe_name = sanitize_filename(filename)
        file_path = OUTPUT_DIR / step / safe_name
        with file_path.open('w', encoding='utf-8') as file:
            file.write(content)
        logger.info(f"Saved {step} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save {step}: {e}")
        raise


def load_state() -> Optional[Dict[str, Any]]:
    """Loads the state from a file if it exists."""
    state_file = OUTPUT_DIR / "state.json"
    if state_file.exists():
        with state_file.open('r', encoding='utf-8') as f:
            state = json.load(f)
            logger.info("State loaded from file.")
            return state
    else:
        logger.info("No existing state found. Starting fresh.")
        return None


def save_state(state: Dict[str, Any]):
    """Save the current state to a file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state_file = OUTPUT_DIR / "state.json"
    with state_file.open('w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    logger.info("State saved to file.")


def display_progress(task_description: str, duration: float = 1.0):
    """Displays a progress spinner."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(description=task_description, total=None)
        time.sleep(duration)
        progress.remove_task(task)


def parse_json_response(response: str) -> Any:
    """Parse JSON response with fallback mechanisms."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from the response if it's embedded in other text
        try:
            json_start = response.index('{')
            json_end = response.rindex('}') + 1
            return json.loads(response[json_start:json_end])
        except (ValueError, json.JSONDecodeError):
            # If still fails, return the raw string
            logger.warning("Failed to parse JSON. Returning raw string.")
            return response


async def call_api(api_choice: str, prompt: str, max_tokens: int = 15000,
                  temperature: float = 0.7, retry_backoff: int = RETRY_BACKOFF) -> str:
    """Call the selected API with the given prompt."""
    for attempt in range(MAX_RETRIES):
        try:
            openai_key, nebius_key, anthropic_key, groq_key = load_api_keys()
            if api_choice == "openai":
                client = AsyncOpenAI(api_key=openai_key)
                response = await client.chat.completions.create(
                    model=MODEL_NAMES["openai"],
                    messages=[{"role": "system", "content": "You are a helpful assistant."},
                              {"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.9
                )
                return response.choices[0].message.content.strip()
            elif api_choice == "nebius":
                client = OpenAI(base_url="https://api.studio.nebius.ai/v1/", api_key=nebius_key)
                completion = client.chat.completions.create(
                    model=MODEL_NAMES["groq"],  # Assuming Nebius uses the same model naming
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9
                )
                return completion.choices[0].message.content.strip()
            elif api_choice == "ollama":
                # Ollama might have a different client or method
                headers = {"Content-Type": "application/json"}
                data = {
                    "model": MODEL_NAMES["ollama"],
                    "prompt": prompt,
                    "options": {"max_tokens": max_tokens, "temperature": temperature, "top_p": 0.9}
                }
                logger.debug(f"Sending request to Ollama API: {data}")
                response = requests.post(LLM_API_URLS["ollama"], headers=headers, data=json.dumps(data), timeout=600)
                response.raise_for_status()
                response_json = response.json()
                logger.debug(f"Received response from Ollama API: {response_json}")
                return response_json.get("response", "").strip()
            elif api_choice == "anthropic":
                client = anthropic.Anthropic(api_key=anthropic_key)
                message = client.completions.create(
                    model=MODEL_NAMES["anthropic"],
                    prompt=prompt,
                    max_tokens_to_sample=max_tokens,
                    temperature=temperature
                )
                return message.completion.strip()
            else:
                raise ValueError(f"Invalid API choice: {api_choice}")
        except Exception as e:
            logger.error(f"{api_choice.capitalize()} API error on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(retry_backoff * (attempt + 1))
            else:
                raise APICallError(f"Max retries reached for {api_choice.capitalize()} API call.") from e


async def generate_initial_tale(llm: str, user_prose: str) -> Optional[str]:
    """Generates the initial tale using the specified LLM."""
    try:
        prompt = (
            f"You are a renowned historian tasked with writing an epic tale about the legendary {PROJECT_NAME} from the POV of those who witnessed or were told tales shortly after. "
            f"Compose a detailed and engaging narrative that outlines {PROJECT_NAME} and its enduring legacy. "
            "Ensure the story is rich with cultural context, vivid descriptions, and maintains an ancient storytelling style. Consider this is all that will be known of the story and then it will be left to time to tell."
        )
        if user_prose:
            prompt += f" Incorporate the following user-provided guidance and information into the tale: {user_prose}"

        logger.info("Generating initial tale...")
        display_progress("Generating initial tale...")
        tale = await call_api(llm, prompt, max_tokens=TOKEN_LIMITS["original_tale"])
        if tale:
            save_text(tale, "original_tale", "initial_tale.txt")
            logger.info("Initial tale generated and saved successfully.")
            return tale
        else:
            logger.warning("Failed to generate the initial tale.")
            return None

    except Exception as e:
        logger.error(f"Error in generating initial tale: {e}")
        return None


def load_existing_documents(subdirectory: str) -> Optional[List[Dict[str, Any]]]:
    """Loads existing documents from the specified subdirectory."""
    doc_dir = OUTPUT_DIR / subdirectory
    documents = []
    try:
        for filename in os.listdir(doc_dir):
            if filename.endswith("_metadata.json"):  # load from metadata
                filepath = doc_dir / filename
                try:
                    with open(filepath, 'r', encoding="utf-8") as f:
                        metadata = json.load(f)
                        content_filename = metadata.get("filename")
                        if content_filename:
                            content_filepath = doc_dir / content_filename
                            try:
                                with open(content_filepath, 'r', encoding="utf-8") as cf:
                                    metadata["content"] = cf.read()
                                    documents.append(metadata)
                            except Exception as e:
                                logger.error(f"Error loading content file {content_filepath}: {e}")

                except Exception as e:
                    logger.error(f"Error loading metadata file {filepath}: {e}")

        return documents if documents else None
    except FileNotFoundError:  # Directory may not exist yet
        return None  # return empty list for now
    except Exception as e:
        logger.error(f"Unexpected error during document loading: {e}")
        return None


async def generate_text(prompt: str, llm: str, max_tokens: int, retries: int = MAX_RETRIES) -> Optional[str]:
    """Generates text with retries and minimum length checking."""
    for attempt in range(retries):
        try:
            generated_text = await call_api(llm, prompt, max_tokens)
            if generated_text and len(generated_text) >= MIN_ACCEPTABLE_LENGTH:
                return generated_text
            elif generated_text:
                logger.warning(
                    f"Generated text too short ({len(generated_text)} characters). Retrying (attempt {attempt + 1}/{retries}).")
            else:
                logger.warning(f"Generated text is None. Retrying (attempt {attempt + 1}/{retries}).")
        except APICallError as e:
            logger.error(f"API call failed: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error during text generation: {e}")
        time.sleep(1)
    logger.error(f"Failed to generate text of acceptable length after {retries} retries.")
    return None


def save_output(state: Dict[str, Any], output_dir: Path):
    """Save the generated content to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "detailed_world.txt", "w", encoding='utf-8') as f:
        f.write(state.get("detailed_world", ""))

    with open(output_dir / "lore_material.json", "w", encoding='utf-8') as f:
        json.dump(state.get("lore_material", {}), f, indent=2, ensure_ascii=False)

    with open(output_dir / "documents.json", "w", encoding='utf-8') as f:
        json.dump(state.get("documents", {}), f, indent=2, ensure_ascii=False)

    with open(output_dir / "letters_to_show.json", "w", encoding='utf-8') as f:
        json.dump(state.get("letters_to_show", []), f, indent=2, ensure_ascii=False)

    with open(output_dir / "episodes.json", "w", encoding='utf-8') as f:
        json.dump(state.get("episodes", []), f, indent=2, ensure_ascii=False)

    with open(output_dir / "refined_episodes.json", "w", encoding='utf-8') as f:
        json.dump(state.get("refined_episodes", []), f, indent=2, ensure_ascii=False)


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


def simulate_distillation(documents: List[Dict[str, Any]], num_distillers: int, loss_char: float, loss_docs: float) -> List[Dict[str, Any]]:
    """Simulates the distillation process over multiple layers."""
    distilled_documents = documents.copy()  # Corrected copy operation

    for layer in range(1, num_distillers + 1):
        logger.info(f"Starting distillation layer {layer}...")
        display_progress(f"Distillation layer {layer} in progress...")

        num_docs_current = len(distilled_documents)
        num_docs_to_lose = int(num_docs_current * loss_docs)

        if num_docs_to_lose > 0:
            docs_to_remove = random.sample(distilled_documents, num_docs_to_lose)
            for doc in docs_to_remove:  # Removed from distilled list
                distilled_documents.remove(doc)
            logger.info(f"Distillation layer {layer}: Removed {num_docs_to_lose} documents.")

        for doc in distilled_documents:
            original_length = len(doc["content"])
            doc["content"] = truncate_text(doc["content"], loss_char)
            truncated_length = len(doc["content"])
            logger.debug(
                f"Distillation layer {layer}: Truncated document '{doc['name']}' from {original_length} to {truncated_length} characters.")
            doc["token_allocation"] = max(int(doc["token_allocation"] * (truncated_length / original_length)), 1)

        layer_dir = OUTPUT_DIR / "distilled_layers" / f"layer_{layer}"
        layer_dir.mkdir(parents=True, exist_ok=True)
        for doc in distilled_documents:
            filename = doc['name'] + ".txt"
            save_text(doc["content"], f"distilled_layers/layer_{layer}", filename)
            metadata = {
                "original_name": doc.get("original_name", doc["name"]),
                "name": doc["name"],
                "description": doc["description"],
                "type": doc["type"],
                "size": doc["size"],
                "token_allocation": doc["token_allocation"],
                "filename": filename
            }
            metadata_filename = doc["name"] + "_metadata.json"
            metadata_path = layer_dir / metadata_filename

            try:  # Added error handling for metadata saving
                with metadata_path.open("w", encoding="utf-8") as meta_file:
                    json.dump(metadata, meta_file, indent=4)
            except Exception as e:
                logger.error(f"Failed to save metadata for '{doc['name']}' in layer {layer}: {e}")

        logger.info(f"Distillation layer {layer} completed. {len(distilled_documents)} documents remaining.")

    return distilled_documents


async def compile_final_narrative(tale: str, supporting_docs: List[Dict[str, Any]], distilled_docs: List[Dict[str, Any]], llm: str) -> Optional[str]:
    """Compiles the final narrative using the specified LLM, leveraging larger context capabilities."""
    try:
        # Step 1: Summarize the initial tale
        initial_summary_prompt = (
            f"Summarize the following initial tale about {PROJECT_NAME} in key points:\n\n{tale}\n\n"
            "Provide the key points without additional explanation, but include all significant details."
        )
        initial_summary = await generate_text(initial_summary_prompt, llm, TOKEN_LIMITS["original_tale"])
        logger.info("Generated summary of initial tale.")

        # Step 2: Extract key information from supporting documents
        supporting_info = []
        for doc in supporting_docs:
            doc_summary_prompt = (
                f"Extract key pieces of information from this {doc['type']} about {PROJECT_NAME}:\n\n"
                f"Content: {doc['content']}\n\n"
                "Provide the key information without additional explanation, capturing all important details."
            )
            doc_summary = await generate_text(doc_summary_prompt, llm, doc['token_allocation'])
            supporting_info.append(f"{doc['name']} ({doc['type']}): {doc_summary}")
        logger.info("Extracted key information from supporting documents.")

        # Step 3: Analyze the distillation process
        distillation_analysis_prompt = (
            f"Analyze how the following distilled documents about {PROJECT_NAME} differ from the original supporting documents:\n\n"
            + "\n\n".join([f"{doc['name']} ({doc['type']}): {doc['content']}" for doc in distilled_docs])
            + "\n\nDescribe the key changes and potential loss of information in detail, considering all aspects of the distillation process."
        )
        distillation_analysis = await generate_text(distillation_analysis_prompt, llm, TOKEN_LIMITS["supporting_document"]["long"])
        logger.info("Analyzed the distillation process.")

        # Step 4: Compile the final narrative
        final_narrative_prompt = (
            f"Using only the following distilled information about {PROJECT_NAME}, reconstruct the legend as it might be told after the passage of time:\n\n"
            f"Original Tale Summary: {initial_summary}\n\n"
            f"Key Information from Supporting Documents:\n" + "\n".join(supporting_info) + "\n\n"
            f"Analysis of Distillation Effects: {distillation_analysis}\n\n"
            f"Distilled Documents:\n" + "\n\n".join([f"{doc['name']} ({doc['type']}): {doc['content']}" for doc in distilled_docs]) + "\n\n"
            "Create a comprehensive and coherent narrative that attempts to retell the original legend of "
            f"{PROJECT_NAME} using only the surviving distilled documents. Incorporate the effects of historical "
            "distillation on the existing lore, showing how the story may have changed over time. Ensure the "
            "narrative is rich in detail while reflecting the potential loss or alteration of information. "
            "Use all available context to create a deep, nuanced retelling of the legend."
        )

        logger.info("Compiling final narrative...")
        display_progress("Compiling final narrative...")
        final_narrative = await generate_text(final_narrative_prompt, llm, TOKEN_LIMITS["final_narrative"])

        if final_narrative:
            save_text(final_narrative, "final_narrative", "final_narrative.txt")
            logger.info("Final narrative compiled and saved successfully.")
            return final_narrative
        else:
            logger.warning("Failed to generate the final narrative.")
            return None

    except Exception as e:
        logger.error(f"Failed to compile final narrative: {e}")
        return None


async def generate_detailed_world(story_details: str, api_choice: str) -> str:
    """Generate a detailed world based on the user's story description."""
    prompt = f"""
    Expand the following story description into a detailed world, including:
    1. History of the world
    2. Main characters and their backgrounds
    3. Key locations and their significance
    4. Major plot points and story arcs
    5. Unique aspects of the world (e.g., technology, magic systems, cultural practices)

    Story Description:
    {story_details}

    Provide a comprehensive and cohesive world description that can support multiple episodes and diverse document types.
    """
    return await call_api(api_choice, prompt)


async def create_lore_material(detailed_world: str, api_choice: str) -> Dict[str, List[str]]:
    """Extract key elements from the detailed world to create lore and background material."""
    prompt = f"""
    Based on the detailed world description below, extract key elements to create lore and background material.
    Organize the lore into the following categories:
    1. Historical events
    2. Character profiles
    3. Location descriptions
    4. Cultural practices
    5. Technologies or magical systems

    Detailed World:
    {detailed_world}

    For each category, provide at least 5 concise but informative entries.
    Format your response as a JSON object with the categories as keys and lists of entries as values.
    """
    response = await call_api(api_choice, prompt)
    lore_material = parse_json_response(response)

    # Ensure the response has the expected structure
    expected_categories = ["Historical events", "Character profiles", "Location descriptions", "Cultural practices",
                           "Technologies or magical systems"]
    for category in expected_categories:
        if category not in lore_material or not isinstance(lore_material[category], list):
            lore_material[category] = [f"{category} entry {i + 1}" for i in range(5)]

    return lore_material


async def generate_documents(lore_material: Dict[str, List[str]], api_choice: str) -> Dict[str, List[str]]:
    """Generate primary, secondary, and tertiary documents based on the lore material."""
    documents = {}

    for doc_type, count in [("primary", 5), ("secondary", 7), ("tertiary", 10)]:
        prompt = f"""
        Using the following lore material, generate {count} {doc_type} documents that relate to the story.
        {doc_type.capitalize()} documents should be {"core materials directly related to the main plot" if doc_type == "primary" else "materials providing context or background" if doc_type == "secondary" else "peripheral items adding depth to the world"}.

        Lore Material:
        {json.dumps(lore_material, indent=2)}

        Format your response as a JSON array of strings, where each string is the content of a {doc_type} document.
        """
        response = await call_api(api_choice, prompt)
        parsed_response = parse_json_response(response)

        # Ensure we have the correct number of documents
        if isinstance(parsed_response, list):
            documents[doc_type] = parsed_response[:count]
        else:
            documents[doc_type] = [f"{doc_type.capitalize()} document {i + 1}" for i in range(count)]

        # Pad the list if we don't have enough documents
        while len(documents[doc_type]) < count:
            documents[doc_type].append(f"{doc_type.capitalize()} document {len(documents[doc_type]) + 1}")

    return documents


async def craft_letters_to_show(detailed_world: str, api_choice: str) -> List[str]:
    """Craft letters to the show to subtly guide the hosts' discussions."""
    prompt = f"""
    Based on the detailed world description below, write 5 letters to the show 'Deep Dive'.
    These letters should subtly guide the hosts' discussions and hint at episodic themes.
    In each letter:
    1. Reference 'Host 1' and 'Host 2' by name
    2. Mention a specific aspect of the story or world
    3. Pose a question or theory that could spark discussion
    4. Use the phrase 'Deep Dive' at least once

    Detailed World:
    {detailed_world}

    Format your response as a JSON array of strings, where each string is the content of a letter.
    """
    response = await call_api(api_choice, prompt)
    letters = parse_json_response(response)

    # Ensure we have 5 letters
    if not isinstance(letters, list) or len(letters) < 5:
        letters = [f"Letter to Deep Dive show {i + 1}" for i in range(5)]

    return letters[:5]


def organize_into_episodes(documents: Dict[str, List[str]], letters_to_show: List[str]) -> List[Dict[str, Any]]:
    """Organize documents and letters into episodes, maintaining tension and surprises."""
    num_episodes = min(len(documents['primary']), len(letters_to_show))
    episodes = []

    for i in range(num_episodes):
        episode = {
            'primary': documents['primary'][i],
            'secondary': documents['secondary'][i * 2:(i + 1) * 2] if i * 2 < len(documents['secondary']) else [],
            'tertiary': documents['tertiary'][i * 3:(i + 1) * 3] if i * 3 < len(documents['tertiary']) else [],
            'letter': letters_to_show[i]
        }
        episodes.append(episode)

    return episodes


async def evaluate_and_refine(episodes: List[Dict[str, Any]], api_choice: str) -> List[Dict[str, Any]]:
    """Evaluate the coherence of episodes and refine if necessary."""
    refined_episodes = []

    for i, episode in enumerate(episodes):
        evaluation_prompt = f"""
        Evaluate the coherence and impact of the following episode materials:

        Primary Document: {episode['primary']}
        Secondary Documents: {episode['secondary']}
        Tertiary Documents: {episode['tertiary']}
        Letter to Show: {episode['letter']}

        Provide a JSON object with the following keys:
        - "is_coherent": boolean indicating if the episode is coherent
        - "suggestions": list of suggestions for improvement if not coherent
        """
        response = await call_api(api_choice, evaluation_prompt)
        evaluation = parse_json_response(response)

        if not isinstance(evaluation, dict) or 'is_coherent' not in evaluation:
            evaluation = {"is_coherent": False, "suggestions": ["Improve coherence"]}

        if not evaluation.get('is_coherent', False):
            refinement_prompt = f"""
                        Refine the following episode materials based on these suggestions:
                        {json.dumps(evaluation.get('suggestions', []), indent=2)}

                        Current Episode:
                        {json.dumps(episode, indent=2)}

                        Provide a refined version of the episode, maintaining the same structure but improving coherence and impact.
                        """
            response = await call_api(api_choice, refinement_prompt)
            refined_episode = parse_json_response(response)
            if isinstance(refined_episode, dict) and all(key in refined_episode for key in episode.keys()):
                refined_episodes.append(refined_episode)
            else:
                refined_episodes.append(episode)  # Fallback to original if refinement fails
        else:
            refined_episodes.append(episode)

        return refined_episodes

        def generate_ascii_diagram(state: Dict[str, Any], previous_state: Dict[str, Any] = {}) -> Text:
            """Generates an ASCII diagram of the data flow with color-coding."""
            # Define the standard flow
            standard_flow = [
                "Initial Prose",
                "Initial Tale",
                "Supporting Documents",
                "Distilled Documents",
                "Final Narrative"
            ]

            # Determine current flow based on state
            current_flow = []
            if 'initial_prose' in state:
                current_flow.append("Initial Prose")
            if 'initial_tale' in state:
                current_flow.append("Initial Tale")
            if 'supporting_documents' in state:
                current_flow.append("Supporting Documents")
            if 'distilled_documents' in state:
                current_flow.append("Distilled Documents")
            if 'final_narrative' in state:
                current_flow.append("Final Narrative")

            # Compare standard flow with current flow to identify changes
            additions = set(current_flow) - set(standard_flow)
            removals = set(standard_flow) - set(current_flow)

            # Start building the diagram
            diagram = Text()
            for i, step in enumerate(standard_flow):
                if step in removals:
                    # Highlight removed steps in red
                    diagram.append(f"+------------------+\n| [bold red]{step}[/bold red] |\n+--------+---------+\n",
                                   style="red")
                elif step in additions and step not in standard_flow:
                    # Highlight added steps in green
                    diagram.append(f"+------------------+\n| [bold green]{step}[/bold green] |\n+--------+---------+\n",
                                   style="green")
                else:
                    # Standard steps in default color
                    diagram.append(f"+------------------+\n| {step} |\n+--------+---------+\n", style="white")

                # Add arrows if not the last step
                if i < len(standard_flow) - 1:
                    if step in removals:
                        # Broken path indicated by a red arrow
                        diagram.append("         |\n         v\n", style="red")
                    else:
                        # Normal path
                        diagram.append("         |\n         v\n", style="white")

            return diagram

        def provide_modification_instructions():
            """Provides instructions for modifying and extending the script."""
            instructions = textwrap.dedent("""
                # ------------------------------ Modification Instructions ------------------------------ #

                This script is designed to be modular and easily modifiable. Each major step is encapsulated in its own function:

                - `generate_initial_tale`: Generates the initial tale based on the initial prose input.
                - `generate_supporting_documents`: Generates supporting documents that expand on the initial tale.
                - `simulate_distillation`: Simulates the loss of information over time by distilling the supporting documents.
                - `compile_final_narrative`: Compiles the final narrative using the distilled documents.
                - `truncate_text`: Truncates a percentage of characters from a text to simulate information loss.
                - `call_api`: Handles API calls to different LLM services.
                - `parse_json_response`: Parses JSON responses with fallback mechanisms.

                Data from each step is stored in the `state` dictionary and saved to `state.json`. This allows you to access previous data and modify it as needed.

                To add recursion, branching, or other prompt techniques, you can modify the existing functions or add new ones. Ensure that you update the `state` dictionary accordingly.

                The script includes an ASCII diagram generator (`generate_ascii_diagram`) to visualize the data flow. The diagram dynamically reflects additions or removals in the data flow, with color-coding:

                - **Green** indicates newly added paths.
                - **Red** indicates removed or broken paths.
                - **White** represents standard, unchanged paths.

                **Important Notes:**

                - Avoid hardcoding any project-specific names. Titles and filenames should be derived by the LLM from the initial input.
                - Use the `save_state` and `load_state` functions to maintain continuity across runs.
                - Ensure that any modifications maintain the modular structure of the script to prevent breaking functionality.
                - When working with LLMs, make sure to handle API calls responsibly and comply with the API terms of service.

                # --------------------------------------------------------------------------------------- #
                """)
            rprint(instructions)
            logger.info("Modification instructions provided.")

        # ------------------------------ Main Execution ------------------------------ #

        async def generate_story_content(story_details: str, api_choice: str, state: Optional[Dict[str, Any]] = None) -> \
        Dict[str, Any]:
            """Generate all story content, with the ability to resume from a saved state."""
            if state is None:
                state = {}

            steps = [
                ("detailed_world", generate_detailed_world),
                ("lore_material", create_lore_material),
                ("documents", generate_documents),
                ("letters_to_show", craft_letters_to_show),
                ("episodes", organize_into_episodes),
                ("refined_episodes", evaluate_and_refine)
            ]

            for step_name, step_function in steps:
                if step_name not in state:
                    logger.info(f"Generating {step_name}...")
                    if step_name == "episodes":
                        state[step_name] = step_function(state["documents"], state["letters_to_show"])
                    elif step_name == "refined_episodes":
                        state[step_name] = await step_function(state["episodes"], api_choice)
                    elif step_name in ["detailed_world", "letters_to_show"]:
                        state[step_name] = await step_function(story_details, api_choice)
                    elif step_name == "lore_material":
                        state[step_name] = await step_function(state["detailed_world"], api_choice)
                    elif step_name == "documents":
                        state[step_name] = await step_function(state["lore_material"], api_choice)
                    save_state(state)
                else:
                    logger.info(f"Skipping {step_name} generation (already exists in state)")

            return state

        async def main_async():
            """Main asynchronous function to run the script."""
            print(textwrap.dedent("""
                ==========================================
                       Robust Story Document Generator
                ==========================================
                """))

            try:
                load_api_keys()
            except APIKeyError as e:
                logger.error(e)
                return

            api_choice = input("Choose an API to use (openai/nebius/ollama/groq/anthropic): ").lower()
            while api_choice not in ["openai", "nebius", "ollama", "groq", "anthropic"]:
                api_choice = input(
                    "Invalid choice. Please enter 'openai', 'nebius', 'ollama', 'groq', or 'anthropic': ").lower()

            state = load_state()
            if state:
                use_existing = input(
                    "Existing state found. Do you want to continue from this state? (y/n): ").lower() == 'y'
                if not use_existing:
                    state = None

            if not state:
                story_details = input("Please enter a brief description of your story: ").strip()
                if not story_details:
                    logger.error("Error: Story description cannot be empty.")
                    return
                state = {"story_details": story_details}

            run_id = state.get("run_id", str(uuid.uuid4()))
            state["run_id"] = run_id

            output_dir = OUTPUT_DIR / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            try:
                state = await generate_story_content(state["story_details"], api_choice, state)
                save_output(state, output_dir)
                logger.info(f"Content generation complete. Files saved in {output_dir}")
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                logger.info("Partial results have been saved. You can resume from this point later.")

            while True:
                choice = input(
                    "\nDo you want to:\n1. Regenerate a specific component\n2. Start over with a new story\n3. Exit\nEnter your choice (1/2/3): ")

                if choice == '1':
                    component = input(
                        "Which component do you want to regenerate? (detailed_world/lore_material/documents/letters_to_show/episodes/refined_episodes): ").lower()
                    if component in state:
                        del state[component]
                        if component == 'detailed_world':
                            # If regenerating detailed_world, we need to regenerate everything that depends on it
                            for key in ['lore_material', 'documents', 'letters_to_show', 'episodes',
                                        'refined_episodes']:
                                state.pop(key, None)
                        elif component in ['lore_material', 'documents', 'letters_to_show']:
                            # If regenerating these, we need to regenerate episodes and refined_episodes
                            state.pop('episodes', None)
                            state.pop('refined_episodes', None)
                        save_state(state)
                        state = await generate_story_content(state["story_details"], api_choice, state)
                        save_output(state, output_dir)
                        logger.info(f"Regenerated {component}. Updated files saved in {output_dir}")
                    else:
                        logger.error(f"Invalid component: {component}")

                elif choice == '2':
                    state = None
                    story_details = input("Please enter a brief description of your new story: ").strip()
                    if not story_details:
                        logger.error("Error: Story description cannot be empty.")
                        continue
                    state = {"story_details": story_details, "run_id": str(uuid.uuid4())}
                    output_dir = OUTPUT_DIR / state["run_id"]
                    output_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        state = await generate_story_content(state["story_details"], api_choice, state)
                        save_output(state, output_dir)
                        logger.info(f"New content generation complete. Files saved in {output_dir}")
                    except Exception as e:
                        logger.error(f"An error occurred: {e}")
                        logger.info("Partial results have been saved. You can resume from this point later.")

                elif choice == '3':
                    logger.info("Exiting the program. Goodbye!")
                    break

                else:
                    logger.error("Invalid choice. Please enter 1, 2, or 3.")

            # After regeneration, display the ASCII diagram
            previous_state = load_state()
            changes = detect_path_changes(previous_state, state)
            display_ascii_diagram(state, previous_state)

            # Highlight changes if any
            if changes['added'] or changes['removed']:
                change_text = ""
                if changes['added']:
                    added_steps = ", ".join(changes['added'])
                    change_text += f"[bold green]Added paths:[/bold green] {added_steps}\n"
                if changes['removed']:
                    removed_steps = ", ".join(changes['removed'])
                    change_text += f"[bold red]Removed paths:[/bold red] {removed_steps}\n"
                rprint(change_text)
            else:
                rprint("[bold yellow]No changes detected in the data flow.[/bold yellow]")

            # Provide Modification Instructions
            provide_modification_instructions()

            # Optionally, display the final narrative summary
            final_narrative = state.get("final_narrative", "")
            if final_narrative:
                summary_length = 1000
                summary = final_narrative[:summary_length] + "..." if len(
                    final_narrative) > summary_length else final_narrative
                rprint("\n[bold green]--- Final Narrative Summary ---[/bold green]\n")
                rprint(summary)
                rprint("\n[bold green]Final narrative saved successfully![/bold green]\n")

        def detect_path_changes(previous_state: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Detects additions or removals in the data flow paths between previous and current state.
            Returns a dictionary with 'added' and 'removed' keys listing the changes.
            """
            standard_flow = [
                "Initial Prose",
                "Initial Tale",
                "Supporting Documents",
                "Distilled Documents",
                "Final Narrative"
            ]

            previous_flow = []
            if 'initial_prose' in previous_state:
                previous_flow.append("Initial Prose")
            if 'initial_tale' in previous_state:
                previous_flow.append("Initial Tale")
            if 'supporting_documents' in previous_state:
                previous_flow.append("Supporting Documents")
            if 'distilled_documents' in previous_state:
                previous_flow.append("Distilled Documents")
            if 'final_narrative' in previous_state:
                previous_flow.append("Final Narrative")

            current_flow = []
            if 'initial_prose' in current_state:
                current_flow.append("Initial Prose")
            if 'initial_tale' in current_state:
                current_flow.append("Initial Tale")
            if 'supporting_documents' in current_state:
                current_flow.append("Supporting Documents")
            if 'distilled_documents' in current_state:
                current_flow.append("Distilled Documents")
            if 'final_narrative' in current_state:
                current_flow.append("Final Narrative")

            added = set(current_flow) - set(standard_flow)
            removed = set(standard_flow) - set(current_flow)

            return {"added": list(added), "removed": list(removed)}

        def display_ascii_diagram(state: Dict[str, Any], previous_state: Dict[str, Any] = {}):
            """Displays the ASCII diagram of the data flow with color-coding."""
            diagram = generate_ascii_diagram(state, previous_state)
            rprint(diagram)
            logger.info("ASCII diagram displayed.")

        def provide_modification_instructions():
            """Provides instructions for modifying and extending the script."""
            instructions = textwrap.dedent("""
                # ------------------------------ Modification Instructions ------------------------------ #

                This script is designed to be modular and easily modifiable. Each major step is encapsulated in its own function:

                - `generate_initial_tale`: Generates the initial tale based on the initial prose input.
                - `generate_supporting_documents`: Generates supporting documents that expand on the initial tale.
                - `simulate_distillation`: Simulates the loss of information over time by distilling the supporting documents.
                - `compile_final_narrative`: Compiles the final narrative using the distilled documents.
                - `truncate_text`: Truncates a percentage of characters from a text to simulate information loss.
                - `call_api`: Handles API calls to different LLM services.
                - `parse_json_response`: Parses JSON responses with fallback mechanisms.

                Data from each step is stored in the `state` dictionary and saved to `state.json`. This allows you to access previous data and modify it as needed.

                To add recursion, branching, or other prompt techniques, you can modify the existing functions or add new ones. Ensure that you update the `state` dictionary accordingly.

                The script includes an ASCII diagram generator (`generate_ascii_diagram`) to visualize the data flow. The diagram dynamically reflects additions or removals in the data flow, with color-coding:

                - **Green** indicates newly added paths.
                - **Red** indicates removed or broken paths.
                - **White** represents standard, unchanged paths.

                **Important Notes:**

                - Avoid hardcoding any project-specific names. Titles and filenames should be derived by the LLM from the initial input.
                - Use the `save_state` and `load_state` functions to maintain continuity across runs.
                - Ensure that any modifications maintain the modular structure of the script to prevent breaking functionality.
                - When working with LLMs, make sure to handle API calls responsibly and comply with the API terms of service.

                # --------------------------------------------------------------------------------------- #
                """)
            rprint(instructions)
            logger.info("Modification instructions provided.")

        # ------------------------------ Start the Script ------------------------------ #

        if __name__ == "__main__":
            asyncio.run(main_async())