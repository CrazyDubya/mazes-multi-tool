import asyncio
import aiohttp
import uuid
import os
import json
import yaml
import aiofiles
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from jsonschema import validate, ValidationError

# Setup Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Capture all levels; handlers will filter

# File handler for detailed logs
file_handler = logging.FileHandler("multi_branch_reasoning.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler for less verbose output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Change to INFO to reduce verbosity
console_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class ConfigLoader:
    """Loads configuration from a YAML file."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file {self.config_path} not found.")
            raise FileNotFoundError(f"{self.config_path} does not exist.")
        with open(self.config_path, 'r') as file:
            try:
                config = yaml.safe_load(file)
                logger.info("Configuration loaded successfully.")
                return config
            except yaml.YAMLError as e:
                logger.error(f"Error parsing the configuration file: {e}")
                raise e


class OllamaClient:
    """Handles communication with the Ollama model via HTTP API."""

    def __init__(self, api_url: str, model_name: str, timeout: int = 120):
        self.api_url = api_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout  # seconds

    async def call_model(self, session: aiohttp.ClientSession, prompt: str) -> Optional[str]:
        """Calls the Ollama model with the given prompt and returns the response."""
        url = self.api_url
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        try:
            async with session.post(url, headers=headers, json=payload, timeout=self.timeout) as resp:
                response_status = resp.status
                response_text = await resp.text()
                logger.debug(f"Ollama API Response Status: {response_status}")
                logger.debug(f"Ollama API Raw Response:\n{response_text}")

                if resp.status != 200:
                    logger.error(f"Ollama API error: {resp.status} - {response_text}")
                    return None

                # Handle plain text response
                response_content = response_text.strip()
                logger.debug(f"Extracted Text Response: {response_content}")
                return response_content
        except asyncio.TimeoutError:
            logger.error("Ollama API call timed out.")
            return None
        except Exception as e:
            logger.error(f"Error during Ollama API call: {e}")
            return None


class ReasoningBranch:
    """Represents a single reasoning branch."""

    def __init__(self, name: str, config: Dict, ollama_client: OllamaClient, execution_config: Dict):
        self.name = name
        self.prompt_template = config.get('prompt', "")
        self.output_format = config.get('output_format', 'xml').lower()
        self.ollama_client = ollama_client
        self.max_iterations = execution_config.get('max_iterations', 10)
        self.stop_term = execution_config.get('stop_term', "END_OF_PATH")
        self.responses: List[str] = []
        self.previous_iterations = ""

    async def run(self, session: aiohttp.ClientSession, problem: str):
        """Runs the reasoning path until the stop condition is met or max iterations are reached."""
        logger.info(f"Starting branch '{self.name}'.")
        for iteration in range(1, self.max_iterations + 1):
            prompt = self.construct_prompt(problem)
            logger.debug(f"Branch '{self.name}' Iteration {iteration} Prompt:\n{prompt}")
            response = await self.ollama_client.call_model(session, prompt)
            if not response:
                logger.warning(f"No response received for branch '{self.name}' at iteration {iteration}.")
                break

            # Log the raw response for debugging
            logger.debug(f"Branch '{self.name}' Iteration {iteration} Raw Response:\n{response}")

            parsed = self.parse_response(response)
            if not parsed:
                logger.warning(f"Failed to parse response for branch '{self.name}' at iteration {iteration}.")
                break

            iteration_content = parsed.get("iteration", "")
            stop_term = parsed.get("stop_term", "")

            if iteration_content:
                self.responses.append(iteration_content)
                logger.info(f"Branch '{self.name}' Iteration {iteration}: {iteration_content}")
            else:
                logger.warning(f"No iteration content found for branch '{self.name}' at iteration {iteration}.")

            if stop_term == self.stop_term:
                logger.info(f"Stop term detected in branch '{self.name}' at iteration {iteration}.")
                break

            # Update previous iterations for next prompt
            self.update_previous_iterations(iteration_content)

    def construct_prompt(self, problem: str) -> str:
        """Constructs the prompt for the current iteration."""
        previous = self.previous_iterations.strip()
        previous_iterations = f"<PreviousIterations>{previous}</PreviousIterations>" if previous else ""
        prompt = self.prompt_template.format(problem=problem, previous_iterations=previous_iterations)
        return prompt

    def update_previous_iterations(self, content: str):
        """Updates the accumulated previous iterations."""
        self.previous_iterations += f"<Iteration>{content}</Iteration>\n"

    def parse_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parses the model's response based on the expected output format."""
        if self.output_format == "xml":
            return self.parse_xml(response)
        elif self.output_format == "json":
            return self.parse_json(response)
        else:
            logger.error(f"Unsupported output format '{self.output_format}' in branch '{self.name}'.")
            return None

    def parse_xml(self, response: str) -> Optional[Dict[str, str]]:
        """Parses XML response using BeautifulSoup for flexibility."""
        try:
            soup = BeautifulSoup(response, "lxml")

            # Remove the <Instruction> section to avoid parsing tags within it
            for instruction in soup.find_all('Instruction'):
                instruction.decompose()

            # Find the last <Iteration> tag
            iterations = soup.find_all('Iteration')
            iteration_text = iterations[-1].get_text(strip=True) if iterations else ""

            # Find the last <StopTerm> tag
            stop_terms = soup.find_all('StopTerm')
            stop_term_text = stop_terms[-1].get_text(strip=True) if stop_terms else ""

            if not iteration_text:
                logger.warning(f"Missing <Iteration> tag in response for branch '{self.name}'.")

            return {
                "iteration": iteration_text,
                "stop_term": stop_term_text
            }
        except Exception as e:
            logger.error(f"XML parsing error in branch '{self.name}': {e}")
            return None

    def parse_json(self, response: str) -> Optional[Dict[str, str]]:
        """Parses JSON response."""
        try:
            data = json.loads(response)
            iteration_text = data.get("iteration", "")
            stop_term_text = data.get("stop_term", "")
            return {
                "iteration": iteration_text,
                "stop_term": stop_term_text
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in branch '{self.name}': {e}")
            return None


class MultiBranchReasoningSystem:
    """Orchestrates the multi-branching reasoning process."""

    def __init__(self, config: Dict):
        self.config = config
        self.ollama_client = OllamaClient(
            api_url=self.config['ollama']['api_url'],
            model_name=self.config['ollama']['model_name'],
            timeout=self.config['ollama'].get('timeout', 120)
        )
        self.execution_config = self.config['execution']
        self.output_dir = self.execution_config.get('output_dir', 'run_outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        self.branches_config = self.config['reasoning_branches']
        self.branches: List[ReasoningBranch] = []

    def initialize_branches(self):
        """Initializes reasoning branches based on the configuration."""
        import random
        branch_names = list(self.branches_config.keys())
        if len(branch_names) < 3:
            logger.error("Not enough reasoning branches configured to select three.")
            raise ValueError("At least three reasoning branches are required.")
        selected_names = random.sample(branch_names, 3)
        logger.info(f"Selected reasoning branches: {selected_names}")
        for name in selected_names:
            branch = ReasoningBranch(
                name=name,
                config=self.branches_config[name],
                ollama_client=self.ollama_client,
                execution_config=self.execution_config
            )
            self.branches.append(branch)

    async def run_all_branches(self, problem: str):
        """Runs all selected reasoning branches asynchronously."""
        async with aiohttp.ClientSession() as session:
            tasks = [branch.run(session, problem) for branch in self.branches]
            await asyncio.gather(*tasks)

    def aggregate_responses(self) -> Dict[str, List[str]]:
        """Aggregates responses from all branches."""
        return {branch.name: branch.responses for branch in self.branches}

    async def summarize_responses(self, all_responses: Dict[str, List[str]]) -> str:
        """Summarizes all responses to determine the best answer."""
        summary_prompt = self.construct_summary_prompt(all_responses)
        logger.debug(f"Summary Prompt:\n{summary_prompt}")
        async with aiohttp.ClientSession() as session:
            summary_response = await self.ollama_client.call_model(session, summary_prompt)

        if not summary_response:
            logger.warning("No summary could be generated.")
            return "No summary could be generated."

        # Log the raw summary response for debugging
        logger.debug(f"Summary Raw Response:\n{summary_response}")

        # Attempt to parse the summary if it's in XML or JSON
        parsed = self.parse_summary_response(summary_response)
        if parsed and parsed.get("summary"):
            return parsed["summary"]
        else:
            # If not parsable, return as is
            logger.warning("Summary does not contain <summary> tags. Returning raw response.")
            return summary_response.strip()

    def construct_summary_prompt(self, all_responses: Dict[str, List[str]]) -> str:
        """Constructs the prompt for summarizing responses."""
        prompt = "<SummaryPrompt>\n    <Instruction>\n"
        prompt += "        Given the following responses from different reasoning paths,\n"
        prompt += "        summarize the best possible answer to the problem.\n"
        prompt += "        Ensure the summary is clear and concise.\n"
        prompt += "        Provide the summary within <summary></summary> tags.\n"
        prompt += "    </Instruction>\n"

        for branch, responses in all_responses.items():
            prompt += f"    <Branch name=\"{branch}\">\n"
            for idx, resp in enumerate(responses, 1):
                prompt += f"        <Response iteration=\"{idx}\">{resp}</Response>\n"
            prompt += "    </Branch>\n"

        prompt += "</SummaryPrompt>\n"
        return prompt

    def parse_summary_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parses the summary response."""
        # Attempt XML parsing
        try:
            soup = BeautifulSoup(response, "lxml")
            summary = soup.find('summary')
            if summary:
                return {"summary": summary.get_text(strip=True)}
            else:
                logger.warning("Missing <summary> tag in summary response.")
        except Exception as e:
            logger.warning(f"XML parsing failed for summary: {e}")

        # Attempt JSON parsing
        try:
            data = json.loads(response)
            summary_text = data.get("summary", "")
            if summary_text:
                return {"summary": summary_text}
        except json.JSONDecodeError:
            pass

        # Fallback to raw response
        return None

    def generate_unique_filename(self, prefix: str, extension: str = "json") -> str:
        """Generates a unique filename using UUID and current timestamp."""
        unique_id = uuid.uuid4()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}_{unique_id}.{extension}"

    async def save_run_data(self, final_solution: str, all_responses: Dict[str, List[str]]):
        """Saves the final solution and all run data into unique JSON files asynchronously."""
        if not final_solution.strip():
            logger.error("Final solution is empty. Skipping file saving.")
            return

        if not all_responses or not any(all_responses.values()):
            logger.error("Run data is empty. Skipping file saving.")
            return

        run_id = uuid.uuid4()
        final_filename = os.path.join(
            self.output_dir,
            self.generate_unique_filename(f"final_solution_{run_id}", "json")
        )
        data_filename = os.path.join(
            self.output_dir,
            self.generate_unique_filename(f"run_data_{run_id}", "json")
        )

        # Save final solution
        final_data = {"final_solution": final_solution}
        try:
            async with aiofiles.open(final_filename, "w", encoding="utf-8") as f:
                await f.write(json.dumps(final_data, indent=4))
            logger.info(f"Final solution saved to {final_filename}")
        except Exception as e:
            logger.error(f"Failed to save final solution to {final_filename}: {e}")

        # Save all run data
        run_data = {"all_responses": all_responses}
        try:
            async with aiofiles.open(data_filename, "w", encoding="utf-8") as f:
                await f.write(json.dumps(run_data, indent=4))
            logger.info(f"Run data saved to {data_filename}")
        except Exception as e:
            logger.error(f"Failed to save run data to {data_filename}: {e}")

    async def execute(self, problem: str):
        """Executes the entire reasoning process."""
        self.initialize_branches()
        await self.run_all_branches(problem)
        all_responses = self.aggregate_responses()
        logger.debug(f"Aggregated Responses:\n{json.dumps(all_responses, indent=4)}")
        final_solution = await self.summarize_responses(all_responses)
        logger.info(f"Final summarized solution:\n{final_solution}")
        await self.save_run_data(final_solution, all_responses)


def validate_final_solution(final_solution: str) -> bool:
    """Validates the final solution against a predefined schema."""
    # Define a simple schema; expand as needed
    schema = {
        "type": "string",
        "minLength": 10
    }
    try:
        validate(instance=final_solution, schema=schema)
        return True
    except ValidationError as e:
        logger.error(f"Final solution validation failed: {e}")
        return False


async def main():
    """Main function to execute the multi-branching reasoning system."""
    config_loader = ConfigLoader("config.yaml")
    config = config_loader.config

    problem = input("Enter the problem to solve: ").strip()
    if not problem:
        logger.error("No problem provided. Exiting.")
        return

    system = MultiBranchReasoningSystem(config)
    await system.execute(problem)

    # Optionally, validate the final solution
    # final_solution would be loaded from the saved JSON file if needed


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
