# src/logging_setup.py

import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler

def setup_logging(log_dir: Path, project_name: str, log_level: str = "INFO") -> logging.Logger:
    log_dir = log_dir / project_name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"generation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    console = Console()

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

    logger = logging.getLogger("LoreGenerator")
    logger.info("Logging is set up.")
    return logger
