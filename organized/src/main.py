# src/main.py

import sys
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Now import modules
from src.config_loader import ConfigLoader
from src.logging_setup import setup_logging
from src.llm_clients.openai_client import OpenAIClient
from src.llm_clients.groq_client import GroqClient
from src.llm_clients.ollama_client import OllamaClient
from src.generators.initial_tale_generator import generate_initial_tale
from src.generators.supporting_document_generator import generate_supporting_document
from src.generators.distillation import simulate_distillation
from src.generators.final_narrative_compiler import compile_final_narrative

from typing import List, Dict, Any
from src.utils.text_utils import truncate_text
from src.utils.file_utils import save_text
from src.utils.progress_display import display_progress
import logging
from pathlib import Path
import random
from rich.console import Console
logger = logging.getLogger("LoreGenerator")

def main():
    """Main function."""
    console = Console()

    # Determine the absolute paths based on the script's location
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "config.yaml"
    prompts_path = project_root / "config" / "prompts.yaml"

    # Initialize ConfigLoader
    config_path = Path("config") / "config.yaml"
    prompts_path = Path("config") / "prompts.yaml"
    config_loader = ConfigLoader(config_path, prompts_path)
    config_loader.load_config()
    config_loader.load_prompts()
    config = config_loader.get_config()
    prompts = config_loader.get_prompts()

    # Setup Logging
    log_dir = project_root / config['project']['log_dir']  # Corrected access
    project_name = config['project']['name']
    logger = setup_logging(log_dir, project_name, config.get('log_level', 'INFO'))

    logger.info("Starting the Lore Generation Process.")


    # Create Output Directories
    base_output_dir = project_root / config['project']['output_dir']
    create_output_dirs(base_output_dir, project_name)

    # Gather User Inputs
    project_name_input = input("Enter the project name: ") or project_name
    user_prose = input("Enter an optional prose description (press Enter to skip): ")

    console.print(f"[bold blue]Starting Synthetic Lore Generation for '{project_name_input}'[/bold blue]\n")

    # Choose LLM
    default_llm = config['project'].get('default_llm', 'ollama')
    llm_choice = input(f"Choose LLM (ollama/openai/groq) [default: {default_llm}]: ").lower() or default_llm
    if llm_choice not in config['llm']:
        logger.warning(f"Invalid LLM choice. Using default: {default_llm}")
        llm_choice = default_llm

    # Initialize LLM Client
    llm_client = None
    llm_config = config['llm'][llm_choice]
    if llm_choice == "openai":
        api_key = os.getenv(llm_config['api_key_env'])
        if not api_key:
            logger.error("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
            return
        llm_client = OpenAIClient(api_key=api_key, model_name=llm_config['model_name'], api_url=llm_config['api_url'])
    elif llm_choice == "groq":
        api_key = os.getenv(llm_config['api_key_env'])
        if not api_key:
            logger.error("Groq API key is not set. Please set the GROQ_API_KEY environment variable.")
            return
        llm_client = GroqClient(api_key=api_key, model_name=llm_config['model_name'], api_url=llm_config['api_url'])
    elif llm_choice == "ollama":
        llm_client = OllamaClient(model_name=llm_config['model_name'], api_url=llm_config['api_url'])
    else:
        logger.error(f"Unsupported LLM choice: {llm_choice}")
        return

    # Initialize Generators
    supporting_doc_generator = generate_supporting_document
    distillation_processor = simulate_distillation
    narrative_compiler = compile_final_narrative

    # Generate Initial Tale
    initial_tale = generate_initial_tale(
        llm_client=llm_client,
        prompts=prompts['tale_generation']['prompt'],
        output_dir=base_output_dir,
        project_name=project_name_input,
        user_prose=user_prose,
        token_limit=config['token_limits']['original_tale']
    )
    if not initial_tale:
        logger.error("Failed to generate the initial tale. Exiting.")
        return

    # Generate Supporting Documents
    num_supporting_docs = config['generation']['num_supporting_docs']
    supporting_docs = supporting_doc_generator(
        num_docs=num_supporting_docs,
        llm_client=llm_client,
        prompts=prompts,
        document_types=config['document_types'],
        project_name=project_name_input,
        token_limits=config['token_limits'],
        output_dir=base_output_dir
    )
    if not supporting_docs:
        logger.error("Failed to generate supporting documents. Exiting.")
        return

    # Simulate Distillation
    num_distillers = config['generation']['num_distillers']
    loss_percent_char = config['generation']['loss_percent_char']
    loss_percent_docs = config['generation']['loss_percent_docs']
    distilled_docs = distillation_processor(
        documents=supporting_docs,
        num_distillers=num_distillers,
        loss_char=loss_percent_char,
        loss_docs=loss_percent_docs,
        output_dir=base_output_dir
    )

    # Compile Final Narrative
    final_narrative = narrative_compiler(
        tale=initial_tale,
        supporting_docs=supporting_docs,
        distilled_docs=distilled_docs,
        llm_client=llm_client,
        prompts=prompts['final_narrative_compilation']['prompt'],
        project_name=project_name_input,
        token_limit=config['token_limits']['final_narrative'],
        output_dir=base_output_dir
    )
    if not final_narrative:
        logger.error("Failed to compile the final narrative. Exiting.")
        return

    # Display Summary
    console.print("\n[bold green]--- Final Narrative Summary ---[/bold green]\n")
    summary_length = 1000
    summary = final_narrative[:summary_length] + "..." if len(final_narrative) > summary_length else final_narrative
    console.print(summary)
    console.print("\n[bold green]Final narrative saved successfully![/bold green]\n")

if __name__ == "__main__":
    main()
