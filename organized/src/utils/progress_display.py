# src/utils/progress_display.py

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def display_progress(task_description: str, duration: float = 1.0):
    """Displays a progress spinner for a specified duration."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description=task_description, total=None)
        time.sleep(duration)
