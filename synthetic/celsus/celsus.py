import requests
import json
import time
import logging
import os
import random
import hashlib
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
from pathlib import Path
from openai import OpenAI
import groq

# ------------------------------ Configuration ------------------------------ #

# Define API endpoints and model names dynamically
LLM_API_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/v1/completions",
    "ollama": "http://localhost:11434/api/generate"
}


PROJECT_NAME = input("Enter the project name: ")
OUTPUT_DIR = Path("generated_documents") / PROJECT_NAME
LOG_DIR = Path("logs") / PROJECT_NAME
DEFAULT_LLM = "ollama"  # Default to Ollama


# Model names for each service
MODEL_NAMES = {
    "openai": "gpt-4o-mini",  # Adjust as needed
    "groq": "mixtral-8x7b-32768",  # Adjust as needed
    "ollama": "llama3.2:1b"  # Adjust as needed
}

# API keys from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')


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
MAX_RETRIES = 3  # Maximum retries for text generation
MIN_ACCEPTABLE_LENGTH = 10  # Minimum acceptable length for generated text

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

LOG_LEVEL = logging.INFO
LOG_FILE = LOG_DIR / f"generation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

console = Console()

# ------------------------------ Setup Logging ------------------------------ #

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True),
        logging.FileHandler(LOG_FILE, encoding="utf-8")  # Explicitly set encoding
    ]
)

logger = logging.getLogger("LoreGenerator")


# ------------------------------ Helper Functions ------------------------------ #


def create_output_dirs():
    """Creates necessary output directories."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # Create project-specific dir
        for sub_dir in ["original_tale", "supporting_documents", "fragments", "distilled_layers", "final_narrative"]:
            (OUTPUT_DIR / sub_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Output directories created successfully.")
    except Exception as e:
        logger.error(f"Failed to create output directories: {e}")
        raise


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitizes a filename to be OS-compatible and short enough."""
    # Remove illegal characters
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    # Split filename and extension
    if '.' in filename:
        name, ext = filename.rsplit('.', 1)
        ext = '.' + ext
    else:
        name, ext = filename, ''
    # Truncate and append hash if necessary
    if len(name) + len(ext) > max_length:
        # Reserve 9 characters: 8 for hash and 1 for underscore
        name = name[:max_length - len(ext) - 9]
        name += '_' + hashlib.md5(name.encode()).hexdigest()[:8]
    return name + ext


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


def generate_text(prompt: str, llm: str, max_tokens: int, retries: int = MAX_RETRIES) -> Optional[str]:
    """Generates text with retries and minimum length checking."""
    for attempt in range(retries):
        generated_text = _generate_text_once(prompt, llm, max_tokens)
        if generated_text and len(generated_text) >= MIN_ACCEPTABLE_LENGTH:
            return generated_text
        elif generated_text:
            logger.warning(
                f"Generated text too short ({len(generated_text)} characters). Retrying (attempt {attempt + 1}/{retries}).")
        else:
            logger.warning(f"Generated text is None. Retrying (attempt {attempt + 1}/{retries}).")
        time.sleep(1)
    logger.error(f"Failed to generate text of acceptable length after {retries} retries.")
    return None

def _generate_text_once(prompt: str, llm: str, max_tokens: int) -> Optional[str]:
    """Generates text using the specified language model (single attempt)."""
    if llm == "ollama":
        return _generate_text_ollama(prompt, max_tokens)
    elif llm == "openai":
        return _generate_text_openai(prompt, max_tokens)
    elif llm == "groq":
        return _generate_text_groq(prompt, max_tokens)
    else:
        logger.error(f"Unsupported LLM: {llm}")
        return None


def _generate_text_openai(prompt: str, max_tokens: int) -> Optional[str]:
    """Generates text using the OpenAI API."""
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
        return None

    client = OpenAI()  # The API key will be read from the environment variable
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAMES["openai"],
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
        logger.error(f"OpenAI API request failed: {e}")
        return None

def _generate_text_groq(prompt: str, max_tokens: int) -> Optional[str]:
    """Generates text using the Groq API."""
    if not GROQ_API_KEY:
        logger.error("Groq API key is not set. Please set the GROQ_API_KEY environment variable.")
        return None

    client = groq.Client(api_key=GROQ_API_KEY)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAMES["groq"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API request failed: {e}")
        return None

def _generate_text_ollama(prompt: str, max_tokens: int) -> Optional[str]:
    """Generates text using the Ollama language model."""
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL_NAMES["ollama"],
        "prompt": prompt,
        "options": {"max_tokens": max_tokens, "temperature": 0.7, "top_p": 0.9}
    }

    try:
        with requests.post(LLM_API_URLS["ollama"], headers=headers, data=json.dumps(data), stream=True, timeout=600) as response:
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
                        logger.error(f"JSON decoding failed: {e}")
                        return None

            return generated_text.strip() if generated_text else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred with Ollama: {e}")
    return None

def display_progress(task_description: str, duration: float = 1.0):
    """Displays a progress spinner."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description=task_description, total=None)
        time.sleep(duration)


def generate_supporting_document(doc_number: int, llm: str) -> Optional[Dict[str, Any]]:
    """Generates a single supporting document with a two-stage process using the specified LLM."""
    try:
        doc_type = random.choice(DOCUMENT_TYPES)

        # --- Stage 1: Concept Generation ---
        name_prompt = (
            f"Example: Excerptrs from Orion's Decree on \n\n"
            f"Generate ONLY ONE concise, unique name (a single noun or short phrase) for a {doc_type} related to '{PROJECT_NAME}'. "
            "The name should be a single line without any numbering, bullets, or additional explanations. "
            "Do not include phrases like 'Here are some suggestions:' or similar introductions. Build rich document"
        )
        name = generate_text(name_prompt, llm, max_tokens=20)

        if not name:
            name = f"Supporting_Document_{doc_number}"
            logger.warning(f"Using fallback name: {name}")
        else:
            name = name.strip().split('\n')[0]
            name = re.sub(r'^\d+\.?\s*', '', name)
            name = re.sub(r'[\\/*?:"<>|]', "", name)
            name = sanitize_filename(name)

            if len(name) < 3 or "suggestions" in name.lower():
                logger.warning(f"Generated name '{name}' is invalid. Using fallback name.")
                name = f"Supporting_Document_{doc_number}"
                name = sanitize_filename(name)

        desc_prompt = (f"Provide a detailed description (at least a paragraph) for a {doc_type} titled '{name}' related to '{PROJECT_NAME}'. "
                       f"Look at the document type and determine whether whole story or partial tale. Focus on Specifics"
                       f"first person and immediate second person accounts or Primary Documents and early secondary. ")
        description = generate_text(desc_prompt, llm, max_tokens=900)
        if not description:
            description = f"Description of {name}."
            logger.warning(f"Using fallback description for {name}")

        # --- Stage 2: Content Generation ---
        size_category = random.choices(
            ["sentence", "paragraph", "excerpt", "report", "multi_volume"],
            weights=[5, 20, 35, 30, 10],
            k=1
        )[0]
        token_allocation = TOKEN_LIMITS["supporting_document"].get(size_category) or random.randint(
            TOKEN_LIMITS["supporting_document"]["multi_volume_min"],
            TOKEN_LIMITS["supporting_document"]["multi_volume_max"]
        )

        content_prompt = (
            f"Based on the following concept:\n\n"
            f"Name: {name}\n"
            f"Type: {doc_type}\n"
            f"Description: {description}\n\n"
            f"Write a detailed {size_category} {doc_type}."
        )

        content = generate_text(content_prompt, llm, token_allocation)
        if not content:
            content = f"Content of {name}."
            logger.warning(f"Using fallback content for {name}")

        document = {
            "name": name,
            "description": description,
            "type": doc_type,
            "size": size_category,
            "token_allocation": token_allocation,
            "content": content
        }

        logger.info(f"Generated supporting document {doc_number}: {name} ({doc_type}, {size_category})")
        return document

    except Exception as e:
        logger.error(f"Failed to generate supporting document {doc_number}: {e}")
        return None

def generate_supporting_documents(num_docs: int, llm: str) -> Optional[List[Dict[str, Any]]]:
    """Generates multiple supporting documents, loading existing ones first."""
    existing_docs = load_existing_documents("supporting_documents")
    supporting_docs = existing_docs or []
    for i in range(len(supporting_docs) + 1, num_docs + 1):
        display_progress(f"Generating supporting document {i}...")
        doc = generate_supporting_document(i, llm)
        if doc:
            supporting_docs.append(doc)

            filename = doc["name"] + ".txt"
            try:
                save_text(doc["content"], "supporting_documents", filename)
            except Exception as e:
                logger.error(f"Failed to save content for document {i}: {e}")
                continue

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
            metadata_path = OUTPUT_DIR / "supporting_documents" / metadata_filename
            try:
                with metadata_path.open('w', encoding='utf-8') as meta_file:
                    json.dump(metadata, meta_file, indent=4)
                logger.debug(f"Saved metadata for '{doc['name']}' to {metadata_path}")
            except Exception as e:
                logger.error(f"Failed to save metadata for document {i}: {e}")

    return supporting_docs if supporting_docs else None


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

        return documents
    except FileNotFoundError:  # Directory may not exist yet
        return None  # return empty list for now
    except Exception as e:
        logger.error(f"Unexpected error during document loading: {e}")
        return None


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


def simulate_distillation(documents: List[Dict[str, Any]], num_distillers: int, loss_char: float, loss_docs: float) -> \
List[Dict[str, Any]]:
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


def compile_final_narrative(tale: str, supporting_docs: List[Dict[str, Any]], distilled_docs: List[Dict[str, Any]], llm: str) -> Optional[str]:
    """Compiles the final narrative using the specified LLM, leveraging larger context capabilities."""
    try:
        # Step 1: Summarize the initial tale
        initial_summary_prompt = (
            f"Summarize the following initial tale about {PROJECT_NAME} in key points:\n\n{tale}\n\n"
            "Provide the key points without additional explanation, but include all significant details."
        )
        initial_summary = generate_text(initial_summary_prompt, llm, TOKEN_LIMITS["original_tale"])
        logger.info("Generated summary of initial tale.")

        # Step 2: Extract key information from supporting documents
        supporting_info = []
        for doc in supporting_docs:
            doc_summary_prompt = (
                f"Extract key pieces of information from this {doc['type']} about {PROJECT_NAME}:\n\n"
                f"Content: {doc['content']}\n\n"
                "Provide the key information without additional explanation, capturing all important details."
            )
            doc_summary = generate_text(doc_summary_prompt, llm, doc['token_allocation'])
            supporting_info.append(f"{doc['name']} ({doc['type']}): {doc_summary}")
        logger.info("Extracted key information from supporting documents.")

        # Step 3: Analyze the distillation process
        distillation_analysis_prompt = (
            f"Analyze how the following distilled documents about {PROJECT_NAME} differ from the original supporting documents:\n\n"
            + "\n\n".join([f"{doc['name']} ({doc['type']}): {doc['content']}" for doc in distilled_docs])
            + "\n\nDescribe the key changes and potential loss of information in detail, considering all aspects of the distillation process."
        )
        distillation_analysis = generate_text(distillation_analysis_prompt, llm, TOKEN_LIMITS["supporting_document"]["long"])
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
        final_narrative = generate_text(final_narrative_prompt, llm, TOKEN_LIMITS["final_narrative"])

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
def generate_initial_tale(llm: str, user_prose: str) -> Optional[str]:
    """Generates the initial tale using the specified LLM."""
    try:
        prompt = (
            f"You are a renowned historian tasked with writing an epic tale about the legendary {PROJECT_NAME} from the POV of those who witnessed or were told tales hortly after. "
            f"Compose a detailed and engaging narrative that outlines {PROJECT_NAME} and its enduring legacy. "
            "Ensure the story is rich with cultural context, vivid descriptions, and maintains an ancient storytelling style. Consider this is all that will be known of story and then it will be lef tto time to tell."
        )
        if user_prose:
            prompt += f" Incorporate the following user-provided guidance and information into the tale: Always avoid the purple and cliches. Be fn. {user_prose}"

        logger.info("Generating initial tale...")
        display_progress("Generating initial tale...")
        tale = generate_text(prompt, llm, TOKEN_LIMITS["original_tale"])
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


# ------------------------------ Main Execution ------------------------------ #

def main():
    """Main function."""

    user_prose = input("Enter an optional prose description (press Enter to skip): ")

    console.print(f"[bold blue]Starting Synthetic Lore Generation for '{PROJECT_NAME}'[/bold blue]\n")
    try:
        create_output_dirs()

        llm_choice = input(f"Choose LLM (ollama/openai/groq) [default: {DEFAULT_LLM}]: ").lower() or DEFAULT_LLM
        if llm_choice not in LLM_API_URLS:
            logger.warning(f"Invalid LLM choice. Using default: {DEFAULT_LLM}")
            llm_choice = DEFAULT_LLM

        # Check for API keys before proceeding
        if llm_choice == "openai" and not os.getenv('OPENAI_API_KEY'):
            logger.error("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
            return
        elif llm_choice == "groq" and not os.getenv('GROQ_API_KEY'):
            logger.error("Groq API key is not set. Please set the GROQ_API_KEY environment variable.")
            return

        initial_tale = generate_initial_tale(llm_choice, user_prose)
        if not initial_tale:
            logger.error("Failed to generate the initial tale. Exiting.")
            return

        supporting_docs = generate_supporting_documents(NUM_SUPPORTING_DOCS, llm_choice)
        if not supporting_docs:
            logger.error("Failed to generate supporting documents. Exiting.")
            return

        distilled_docs = simulate_distillation(supporting_docs, NUM_DISTILLERS, LOSS_PERCENT_CHAR, LOSS_PERCENT_DOCS)

        all_supporting_docs = load_existing_documents("supporting_documents")
        if all_supporting_docs is None:
            all_supporting_docs = []

        final_narrative = compile_final_narrative(initial_tale, all_supporting_docs, distilled_docs, llm_choice)
        if not final_narrative:
            logger.error("Failed to compile the final narrative. Exiting.")
            return

        console.print("\n[bold green]--- Final Narrative Summary ---[/bold green]\n")
        summary_length = 1000
        summary = final_narrative[:summary_length] + "..." if len(final_narrative) > summary_length else final_narrative
        console.print(summary)
        console.print("\n[bold green]Final narrative saved successfully![/bold green]\n")

    except Exception as e:
        logger.critical(f"An unexpected error occurred in the main process: {e}", exc_info=True)
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")


if __name__ == "__main__":
    main()