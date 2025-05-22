# src/config_loader.py

import yaml
from pathlib import Path
import logging

logger = logging.getLogger("LoreGenerator.ConfigLoader")

class ConfigLoader:
    def __init__(self, config_path: Path, prompts_path: Path):
        self.config_path = config_path
        self.prompts_path = prompts_path
        self.config = {}
        self.prompts = {}

    def load_config(self):
        try:
            with self.config_path.open('r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            logger.debug(f"Configuration content: {self.config}")  # Add this line
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_path}: {e}")
            raise

    def load_prompts(self):
        try:
            with self.prompts_path.open('r', encoding='utf-8') as f:
                self.prompts = yaml.safe_load(f)
            logger.info(f"Loaded prompts from {self.prompts_path}")
            logger.debug(f"Prompts content: {self.prompts}")  # Add this line
        except Exception as e:
            logger.error(f"Failed to load prompts file {self.prompts_path}: {e}")
            raise

    def get_config(self):
        return self.config

    def get_prompts(self):
        return self.prompts
